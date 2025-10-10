import requests
import threading
from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from requests import Response
from web3 import Web3
from web3.contract import Contract
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import Wei, TxParams

import config
import database
import log
import merkle_tree
import util
import zk
from blockchain import EventPoller, EventDeposit, EventWithdraw
from mytype import ChainID, CircuitInput, Key, MerkleProof, Metadata, Note, Second, Symbol, TornadoUnit, SymbolType, chain_to_string
from util import get_symbol_type, unit_to_wei, wait


class Tornado(EventPoller.Handler):

    class Handler(object):

        def on_first_catchup(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit) -> None:
            """Called when the first catchup is done."""
            pass

        def on_sync(self, block_from: int, block_to: int, deposits: list[EventDeposit], withdrawals: list[EventWithdraw]) -> None:
            """Called when a sync is done."""
            pass

        def on_latest_block(self, block_number: int) -> None:
            """Called when the latest block number is updated."""
            pass

    def __init__(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit):
        self.tag                : str                           = f'{__class__.__name__}'
        self.chain              : ChainID                       = chain
        self.symbol             : Symbol                        = symbol
        self.unit               : TornadoUnit                   = unit
        self.initialized        : bool                          = False
        self.sync_only          : bool                          = False  # If True, only sync events without rebuilding the merkle tree, 'withdraw()' will not be available
        self.db                 : database.Interface            = database.create(database.Backend.SQLITE)
        self.meta               : Metadata                      = util.load_metadata()[chain]
        self.proxy_address      : ChecksumAddress               = self.meta.proxy_address
        self.deployment_address : ChecksumAddress               = self.meta.deployment[self.symbol][self.unit][0]
        self.poller             : EventPoller                   = EventPoller(chain)
        self.tree               : merkle_tree.Interface | None  = None
        self.zksnark            : zk.circuit.Interface          = zk.circuit.create(zk.circuit.ImplType.JAVASCRIPT)
        self.mutex              : threading.Lock                = threading.Lock()
        self.handlers           : list[Tornado.Handler]         = []

    '''
    Initialize Tornado instance
    @param  sync_only   If True, only sync events without rebuilding the merkle tree, 'withdraw()' will not be available
    '''
    def init(self, sync_only: bool) -> bool:
        if self.initialized:
            log.warn(self.tag, 'init() already initialized')
            return False
        # Open database
        if not self.db.open(self.chain, self.symbol, self.unit):
            log.error(f'Opening database failed for {self.chain}_{self.unit}{self.symbol}')
            return False
        # Check integrity
        if not self.db.check_integrity():
            log.error(self.tag, 'init() failed to check database integrity')
            self.db.close()
            return False
        # Rebuild merkle tree
        self.sync_only = sync_only
        if not sync_only:
            log.info(self.tag, 'Rebuilding merkle tree from database, please wait...')
            commitments: list[HexBytes] | None = self.db.get_commitments()
            if commitments is None:
                log.error(self.tag, 'init() failed to get commitments from database')
                self.db.close()
                return False
            self.tree = merkle_tree.create(merkle_tree.ImplType.MEMORY, config.MERKLE_TREE_HEIGHT, commitments)
            log.info(self.tag, 'Merkle tree ready')
        # Add handlers
        self.poller.add_handler(self)
        self.initialized = True
        log.debug(self.tag, f'init()')
        return True

    def un_init(self):
        if not self.initialized:
            log.warn(self.tag, 'un_init() already un-initialized')
            return
        log.debug(self.tag, 'un_init() shutting down')
        self.initialized = False
        if self.poller.is_started():
            self.poller.stop()
        self.poller.remove_all_handlers()
        self.db.close()
        self.tree = None
        self.sync_only = False
        log.debug(self.tag, 'un_init() done')

    def is_initialized(self) -> bool:
        return not self.initialized

    def add_handler(self, handler: Handler) -> None:
        with self.mutex:
            self.handlers.append(handler)

    def remove_all_handlers(self) -> None:
        with self.mutex:
            self.handlers.clear()

    # Check if a note has been deposited
    # @param    commitment      The commitment to query
    # @return   True : The corresponding note has been deposited
    #           False: The corresponding note has not been used
    #           None : Failed to query the blockchain, e.g. RPC connection error
    def note_deposited(self, commitment: HexBytes, w3: Web3 | None = None) -> bool | None:
        # Create RPC client
        if w3 is None:
            url: str = config.RPC_URLS[self.chain]
            if url.startswith('http'):
                w3: Web3 = Web3(Web3.HTTPProvider(url))
            elif url.startswith('ws'):
                w3: Web3 = Web3(Web3.LegacyWebSocketProvider(url))
            else:
                log.error(self.tag, f'note_deposited(), unsupported RPC url: {url}')
                return None
            if not w3.is_connected():
                log.error(self.tag, f'note_deposited(), failed to connect to RPC: {url}')
                return None
        # Call contract function
        with open(config.TORNADO_ABI_PATH, 'r') as f:
            abi: str = f.read()
        try:
            contract: Contract = w3.eth.contract(address=self.deployment_address, abi=abi)
            function = contract.functions.commitments(commitment)
            result: bool = function.call()
        except BaseException as e:
            log.error(self.tag, f'note_deposited(), failed to call contract function commitments(bytes32): {e}')
            return None
        return result

    # Check if a note has been withdrawn
    # @param    nullifier_hash  The nullifier hash to query
    # @return   True : The corresponding note has been withdrawn
    #           False: The corresponding note has not been used
    #           None : Failed to query the blockchain, e.g. RPC connection error
    def note_withdrawn(self, nullifier_hash: HexBytes, w3: Web3 | None = None) -> bool | None:
        # Create RPC client
        if w3 is None:
            url: str = config.RPC_URLS[self.chain]
            if url.startswith('http'):
                w3: Web3 = Web3(Web3.HTTPProvider(url))
            elif url.startswith('ws'):
                w3: Web3 = Web3(Web3.LegacyWebSocketProvider(url))
            else:
                log.error(self.tag, f'note_withdrawn(), unsupported RPC url: {url}')
                return None
            if not w3.is_connected():
                log.error(self.tag, f'note_withdrawn(), failed to connect to RPC: {url}')
                return None
        # Call contract function
        with open(config.TORNADO_ABI_PATH, 'r') as f:
            abi: str = f.read()
        try:
            contract: Contract = w3.eth.contract(address=self.deployment_address, abi=abi)
            function = contract.functions.nullifierHashes(nullifier_hash)
            result: bool = function.call()
        except BaseException as e:
            log.error(self.tag, f'note_withdrawn(), failed to call contract function nullifierHashes(bytes32): {e}')
            return None
        return result

    # Deposit
    # @param    commitment  The commitment of the note to deposit
    # @param    key         The private key to make the deposit
    # @return   HexBytes of transaction hash on success, None if failed
    def deposit(self, commitment: HexBytes, key: Key) -> HexBytes | None:
        # Create RPC client
        url: str = config.RPC_URLS[self.chain]
        if url.startswith('http'):
            w3: Web3 = Web3(Web3.HTTPProvider(url))
        elif url.startswith('ws'):
            w3: Web3 = Web3(Web3.LegacyWebSocketProvider(url))
        else:
            log.error(self.tag, f'deposit(from={key.eth_address()}), unsupported RPC url: {url}')
            return None
        if not w3.is_connected():
            log.error(self.tag, f'deposit(from={key.eth_address()}), failed to connect to RPC: {url}')
            return None

        # Polygon requires the POA middleware
        if self.chain == ChainID.POLYGON:
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Check if the note has already been deposited
        deposited: bool | None = self.note_deposited(commitment, w3)
        if deposited is None:
            return None
        elif deposited:
            log.error(self.tag, f'deposit(from={key.eth_address()}), note commitment already deposited: {commitment.to_0x_hex()}')
            return None
        wait(Second(0.5))  # Prevent RPC rate limit

        # Allowance for ERC20 token
        if SymbolType.ERC20 == get_symbol_type(self.symbol):
            need_increase: bool = True
            with open(config.ERC20_ABI_PATH, 'r') as f:
                erc20_abi: str = f.read()
            # Check allowance
            try:
                contract: Contract = w3.eth.contract(address=self.meta.token_address[self.symbol], abi=erc20_abi)
                function = contract.functions.allowance(key.eth_address(), self.proxy_address)
                result: int = function.call()
                if result >= unit_to_wei(self.unit, self.meta.decimals[self.symbol]):
                    need_increase = False
            except BaseException as e:
                log.error(self.tag, f'deposit(from={key.eth_address()}), failed to call contract function allowance(address,address): {e}')
                return None
            # Increase allowance
            if need_increase:
                try:
                    contract: Contract = w3.eth.contract(address=self.meta.token_address[self.symbol], abi=erc20_abi)
                    call = contract.functions.approve(self.proxy_address, unit_to_wei(self.unit, self.meta.decimals[self.symbol]))
                    tx: TxParams = {
                        'from'   : key.eth_address(),
                        'chainId': self.chain.value,
                        'nonce'  : w3.eth.get_transaction_count(key.eth_address()),
                    }
                    tx = call.build_transaction(tx)
                    signed: SignedTransaction = w3.eth.account.sign_transaction(tx, key.private())
                    w3.eth.send_raw_transaction(signed.raw_transaction)
                except BaseException as e:
                    log.error(self.tag, f'deposit(from={key.eth_address()}), failed to increase allowance: {e}')
                    return None
                # Wait for the allowance to be updated
                while True:
                    try:
                        contract: Contract = w3.eth.contract(address=self.meta.token_address[self.symbol], abi=erc20_abi)
                        function = contract.functions.allowance(key.eth_address(), self.proxy_address)
                        result: int = function.call()
                        if result >= unit_to_wei(self.unit, self.meta.decimals[self.symbol]):
                            break
                    except BaseException as e:
                        log.error(self.tag, f'deposit(from={key.eth_address()}), failed to call contract function allowance(address,address): {e}')
                        return None
                    wait(Second(1))

        # Make deposit
        with open(config.TORNADO_PROXY_ABI_PATH, 'r') as f:
            proxy_abi: str = f.read()
        try:
            contract: Contract = w3.eth.contract(address=self.proxy_address, abi=proxy_abi)
            call = contract.functions.deposit(self.deployment_address, commitment, b'')
            tx: TxParams = {
                'from'   : key.eth_address(),
                'chainId': self.chain.value,
                'nonce'  : w3.eth.get_transaction_count(key.eth_address()),
            }
            if SymbolType.NATIVE == get_symbol_type(self.symbol):
                tx['value'] = unit_to_wei(self.unit, self.meta.decimals[self.symbol])
            tx = call.build_transaction(tx)
            signed: SignedTransaction = w3.eth.account.sign_transaction(tx, key.private())
            tx_hash: HexBytes = w3.eth.send_raw_transaction(signed.raw_transaction)
        except BaseException as e:
            log.error(self.tag, f'deposit(from={key.eth_address()}), failed to deposit: {e}')
            return None
        log.info(self.tag, f'deposit(from={key.eth_address()}) succeed, tx hash: {tx_hash.hex()}')
        return tx_hash

    # Withdraw
    # @param    note            The note to withdraw
    # @param    recipient       Address to receive the withdrawal
    # @param    key_or_relayer  The private key to pay the gas fee, or the URL of the relayer
    # @param    refund          Amount to send to the recipient, make sure the `key_or_relayer` is a key and has enough balance
    # @return   HexBytes of transaction hash on success, None if failed or sync-only mode
    def withdraw(self, note: Note, recipient: ChecksumAddress, key_or_relayer: Key | str, refund: Wei = Wei(0)) -> HexBytes | None:
        if self.sync_only:
            log.error(self.tag, f'withdraw(to={recipient}), not available in sync-only mode')
            return None
        key        : Key | None = None
        relayer_url: str | None = None
        if isinstance(key_or_relayer, Key):
            key = key_or_relayer
        elif isinstance(key_or_relayer, str):
            relayer_url = key_or_relayer
        else:
            log.error(self.tag, f'withdraw(to={recipient}), key_or_relayer is either a Key or a relayer URL string, value: {key_or_relayer}')
            return None
        use_relayer: bool = relayer_url is not None and relayer_url.startswith('http')
        total_wei  : Wei  = unit_to_wei(self.unit, self.meta.decimals[self.symbol])

        # Create RPC client
        url: str = config.RPC_URLS[self.chain]
        if url.startswith('http'):
            w3: Web3 = Web3(Web3.HTTPProvider(url))
        elif url.startswith('ws'):
            w3: Web3 = Web3(Web3.LegacyWebSocketProvider(url))
        else:
            log.error(self.tag, f'withdraw(to={recipient}), unsupported RPC url: {url}')
            return None
        if not w3.is_connected():
            log.error(self.tag, f'withdraw(to={recipient}), failed to connect to RPC: {url}')
            return None

        # Polygon requires the POA middleware
        if self.chain == ChainID.POLYGON:
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Check if the note has already been withdrawn
        withdrawn: bool | None = self.note_withdrawn(note.nullifier_hash, w3)
        if withdrawn is None:
            return None
        elif withdrawn:
            log.error(self.tag, f'withdraw(to={recipient}), note nullifier hash already withdrawn: {note.nullifier_hash.to_0x_hex()}')
            return None
        wait(Second(0.5))  # Prevent RPC rate limit

        relayer_address   : ChecksumAddress    = Web3.to_checksum_address('0x0000000000000000000000000000000000000000')
        relayer_eth_prices: dict[Symbol, Wei]  = {}
        relayer_fee       : Wei                = Wei(0)
        if use_relayer:
            # HTTP Get relayer status
            try:
                resp: Response = requests.get(relayer_url.rstrip('/') + '/status')
            except BaseException as e:
                log.error(self.tag, f'withdraw(to={recipient}), failed to get relayer status from {relayer_url}, exception: {e}')
                return None
            # Check HTTP response status code
            if resp.status_code < 200 or resp.status_code >= 300:
                log.error(self.tag, f'withdraw(to={recipient}), relayer status request failed with status code {resp.status_code}, response: {resp.text}')
                return None
            # Parse HTTP response
            try:
                relayer_status: dict = resp.json()
            except BaseException as e:
                log.error(self.tag, f'withdraw(to={recipient}), failed to parse relayer status to JSON, exception: {e}, response: {resp}')
                return None
            # Response to JSON
            try:
                if int(relayer_status['netId']) != self.chain.value:
                    log.error(self.tag, f'withdraw(to={recipient}), relayer netId {relayer_status["netId"]} does not match chain {self.chain.value}')
                    return None
                for k, v in relayer_status['ethPrices'].items():
                    if k not in Symbol:
                        continue
                    relayer_eth_prices[Symbol(k)] = Wei(int(v))
                try:
                    relayer_instance: ChecksumAddress = Web3.to_checksum_address(relayer_status['instances'][self.symbol.value]['instanceAddress'][self.unit.value])
                except BaseException as e:
                    log.error(self.tag, f'withdraw(to={recipient}), failed to parse relayer instance address, exception: {e}, response: {relayer_status}')
                    return None
                if relayer_instance != self.deployment_address:
                    log.error(self.tag, f'withdraw(to={recipient}), relayer instance address {relayer_instance} does not match deployment '
                                        f'({chain_to_string(self.chain)}@{self.unit.value}{self.symbol.value}) address {self.deployment_address}')
                    return None
                if get_symbol_type(self.symbol) != SymbolType.NATIVE and self.symbol not in relayer_eth_prices:
                    log.error(self.tag, f'withdraw(to={recipient}), relayer does not support symbol {self.symbol}')
                    return None
                relayer_address = relayer_status['rewardAccount']
            except BaseException as e:
                log.error(self.tag, f'withdraw(to={recipient}), invalid relayer status format, exception: {e}, response: {relayer_status}')
                return None
            # Calculate fee
            decimal_points: int = 0 if '.' not in config.RELAYER_FEE_RATE else len(config.RELAYER_FEE_RATE.split('.')[1])
            round_decimal : int = 10 ** decimal_points
            fee_percent   : Wei = Wei(
                (total_wei * int(float(config.RELAYER_FEE_RATE) * round_decimal)) // (round_decimal * 100)
            )
            try:
                gas_price: Wei = w3.eth.gas_price
            except BaseException as e:
                log.error(self.tag, f'withdraw(to={recipient}), failed to get gas price from RPC: {e}')
                return None
            expense: Wei = Wei(gas_price * 500_000)
            if get_symbol_type(self.symbol) == SymbolType.NATIVE:
                relayer_fee = Wei(expense + fee_percent)
            else:
                expense += refund
                expense *= 10 ** self.meta.decimals[self.symbol]
                expense /= relayer_eth_prices[self.symbol]
                relayer_fee = Wei(int(expense + fee_percent))
            # Check if fee greater than total
            if relayer_fee >= total_wei:
                log.error(self.tag, f'withdraw(to={recipient}), relayer fee {relayer_fee} is greater than or equal to total {total_wei}')
                return None
            log.info(self.tag, f'withdraw(to={recipient}), relayer fee {relayer_fee} Wei ({relayer_fee * 100 / total_wei:.2f}%), relayer address {relayer_address}, relayer URL {relayer_url}')

        # Get merkle proof
        with self.mutex:
            leaf_index: int | None = self.tree.get_index(note.commitment)
            if leaf_index is None:
                log.error(self.tag, f'withdraw(to={recipient}), note commitment not found in the tree: {note.commitment.to_0x_hex()}')
                return None
            merkle_proof: MerkleProof | None = self.tree.get_merkle_proof(leaf_index)
            if merkle_proof is None:
                log.error(self.tag, f'withdraw(to={recipient}), failed to get merkle proof for note commitment: {note.commitment.to_0x_hex()}')
                return None
        # Circuit input
        circuit_input: CircuitInput = CircuitInput(
            merkle_proof=merkle_proof,
            note=note,
            recipient=recipient,
            relayer=relayer_address,
            fee=relayer_fee,
            refund=refund
        )
        # Prove
        proof: dict | None = self.zksnark.prove(circuit_input)
        if proof is None:
            log.error(self.tag, f'withdraw(to={recipient}), failed to prove for commitment: {note.commitment.to_0x_hex()}')
            return None
        # Verify
        if not self.zksnark.verify(proof):
            log.error(self.tag, f'withdraw(to={recipient}), failed to test verify proof for commitment: {note.commitment.to_0x_hex()}')
            return None
        log.info(self.tag, f'withdraw(to={recipient}), proof generated for commitment: {note.commitment.to_0x_hex()}')

        # Make withdrawal via relayer
        if use_relayer:
            # Submit withdrawal to relayer and get job ID
            try:
                resp: Response = requests.post(
                    url=relayer_url.rstrip('/') + '/v1/tornadoWithdraw',
                    json={
                        'contract': self.deployment_address,
                        'proof': proof['solidity']['proof'],
                        'args': [
                            proof['solidity']['publicSignals'][0],  # root
                            proof['solidity']['publicSignals'][1],  # nullifierHash
                            recipient,                              # recipient address
                            relayer_address,                        # relayer address
                            proof['solidity']['publicSignals'][4],  # fee
                            proof['solidity']['publicSignals'][5],  # refund
                        ]
                    }
                )
            except BaseException as e:
                log.error(self.tag, f'withdraw(to={recipient}), failed to submit withdrawal to relayer: {e}')
                return None
            if resp.status_code < 200 or resp.status_code >= 300:
                log.error(self.tag, f'withdraw(to={recipient}), relayer request failed with status code {resp.status_code}, response: {resp.text}')
                return None
            try:
                job_id: str = resp.json()['id']  # {'id': '06194b2a-f51a-4428-848b-cf4c5adff7d0'}
            except BaseException as e:
                log.error(self.tag, f'withdraw(to={recipient}), failed to parse ID from relayer response: {e}, response: {resp}')
                return None
            log.info(self.tag, f'withdraw(to={recipient}), relayer job id "{job_id}"')

            # Wait for relayer to process the job and return the transaction hash
            count_attempts    : int = 0
            count_attempts_max: int = 10
            log.info(self.tag, f'withdraw(to={recipient}), waiting for job to be processed')
            wait(Second(5))
            def recursive_query():
                nonlocal count_attempts
                nonlocal count_attempts_max
                try:
                    resp = requests.get(relayer_url.rstrip('/') + f'/v1/jobs/{job_id}')
                except BaseException as e:
                    log.error(self.tag, f'withdraw(to={recipient}), failed to get job status from relayer: {e}')
                    return None
                if resp.status_code < 200 or resp.status_code >= 300:
                    log.error(self.tag, f'withdraw(to={recipient}), query relayer job failed with status code {resp.status_code}, response: {resp.text}')
                    return None
                # Response JSON Example: {
                #     'id': '7985f894-ec91-4183-b62e-4147753a3fdc',
                #     'type': 'TORNADO_WITHDRAW',
                #     'status': 'FAILED',
                #     'contract': '0xA160cdAB225685dA1d56aa342Ad8841c3b53f291',
                #     'proof': '0x15778ac72233a060a5da3e134c3a2f169cd5ad7a5fea1eb62b20b95cd0c7d4fd196cf95aaa616f77a6252769e486fcb4f5668f35db0847eee237d6c102f38a0422c0d58923ed8cc32680ca2b94deb58bfd6129960828a53272cb490dcf255dc324e712818c69298fb216145e86adc075d612f710e5aa3578c66f204ba3c81456036b9616782348ff331698215265ed0bdf514c975ffb11219711017361aee72f03ce139bfbb13e39e3b1b4df397280602aa999101db82ea5495abaf359e34aea1d7660721bcb862d78d883d83de484dbb7c023cb0215c808c18a67a8c17888041369fe158f1e5ee45e6d22e0f663df900a883934106148b5cbb5089b563fe819',
                #     'args': ['0x1545d0fd81f378de328f10a21f954c56ddf780728ff3ea1f437873774f25b191', '0x1a1f75570a3bf2f38bf85e87eff2f3a8f6666e19676df1a49063f48801998194', '0x02395233b8175b0a04D5A0AD0F62Eaf7aFE55d5c', '0x000000Cd6521Ed1a65FAe0678eA15aF4EEAD74fe', '0x000000000000000000000000000000000000000000000000000aa87bee538000', '0x0000000000000000000000000000000000000000000000000000000000000000'],
                #     'failedReason': 'Provided fee is not enough. Probably it is a Gas Price spike, try to resubmit.'
                # }
                # Possible Status: ['QUEUED', 'ACCEPTED', 'SENT', 'MINED', 'RESUBMITTED', 'CONFIRMED', 'FAILED' ]
                try:
                    result: dict = resp.json()
                except BaseException as e:
                    log.error(self.tag, f'withdraw(to={recipient}), failed to parse relayer job response to JSON, exception: {e}, response: {resp}')
                    return None
                if result['status'] == 'CONFIRMED':
                    try:
                        relayer_tx_hash: str = result['txHash']
                        log.info(self.tag, f'withdraw(to={recipient}) succeed, tx hash: {relayer_tx_hash}')
                        return HexBytes.fromhex(relayer_tx_hash[2:] if relayer_tx_hash.startswith('0x') else relayer_tx_hash)
                    except BaseException as e:
                        log.error(self.tag, f'withdraw(to={recipient}), failed to get transaction hash from relayer job response, exception: {e}, response: {result}')
                        return None
                elif result['status'] == 'FAILED':
                    log.error(self.tag, f'withdraw(to={recipient}), relayer job failed with reason: {result.get("failedReason", "Unknown")}')
                    return None
                else:
                    count_attempts += 1
                    if count_attempts >= count_attempts_max:
                        log.error(self.tag, f'withdraw(to={recipient}), job status is "{result["status"]}", max attempts reached ({count_attempts_max}), giving up')
                        return None
                    log.warn(self.tag, f'withdraw(to={recipient}), job status is "{result["status"]}", waiting 5 seconds before next attempt')
                    wait(Second(5))
                    return recursive_query()
            return recursive_query()

        # Make withdrawal directly
        with open(config.TORNADO_PROXY_ABI_PATH, 'r') as f:
            proxy_abi: str = f.read()
        try:
            contract: Contract = w3.eth.contract(address=self.proxy_address, abi=proxy_abi)
            call = contract.functions.withdraw(
                self.deployment_address,
                HexBytes.fromhex(proof['solidity']['proof'][2:] if proof['solidity']['proof'].startswith('0x') else proof['solidity']['proof']),
                merkle_proof.root,
                note.nullifier_hash,
                recipient,
                relayer_address,
                relayer_fee,
                refund,
            )
            tx: TxParams = {
                'from'   : key.eth_address(),
                'chainId': self.chain.value,
                'nonce'  : w3.eth.get_transaction_count(key.eth_address()),
            }
            tx = call.build_transaction(tx)
            signed: SignedTransaction = w3.eth.account.sign_transaction(tx, key.private())
            tx_hash: HexBytes = w3.eth.send_raw_transaction(signed.raw_transaction)
        except BaseException as e:
            log.error(self.tag, f'withdraw(to={recipient}), failed to deposit: {e}')
            return None
        log.info(self.tag, f'withdraw(to={recipient}) succeed, tx hash: {tx_hash.to_0x_hex()}')
        return tx_hash

    def start_sync(self) -> bool:
        contract    : ChecksumAddress = self.meta.deployment[self.symbol][self.unit][0]
        latest_block: int | None      = self.db.get_latest_block_number()
        if latest_block is None:
            log.error(self.tag, 'start_sync(), failed to get latest block number from database')
            return False
        if latest_block > self.meta.deployment[self.symbol][self.unit][1]:
            latest_block += 1
        return self.poller.start(contract, latest_block)

    def stop_sync(self) -> None:
        self.poller.stop()

    def on_first_catchup(self) -> None:
        with self.mutex:
            for h in self.handlers:
                h.on_first_catchup(self.chain, self.symbol, self.unit)

    def on_sync(self, block_from: int, block_to: int, deposits: list[EventDeposit], withdrawals: list[EventWithdraw]) -> None:
        with self.mutex:
            if not self.db.add_synchronized(block_to, deposits, withdrawals):
                raise RuntimeError(f'on_sync() failed to add synchronized data to database')
            if not self.sync_only:
                for e in deposits:
                    self.tree.add(e.commitment)
            for h in self.handlers:
                h.on_sync(block_from, block_to, deposits, withdrawals)

    def on_latest_block(self, block_number: int) -> None:
        with self.mutex:
            for h in self.handlers:
                h.on_latest_block(block_number)
