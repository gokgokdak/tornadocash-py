import requests
import threading
from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress
from functools import wraps
from hexbytes import HexBytes
from requests import Response
from web3 import Web3
from web3.contract import Contract
from web3.types import Nonce, Wei, TxParams

from . import database, log, merkle_tree, rpc, util
from .blockchain import EventPoller, EventDeposit, EventWithdraw
from .mytype import ChainID, CircuitInput, Key, MerkleProof, Metadata, Note, Second, Symbol, TornadoUnit, SymbolType, chain_to_string
from .util import get_requests_proxies, get_symbol_type, unit_to_wei, wait
import config
import zk


class Tornado(EventPoller.Handler):

    @staticmethod
    def locked(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            with self.mutex:
                return method(self, *args, **kwargs)
        return wrapper

    @staticmethod
    def locked_initialized(default=None):
        def decorator(method):
            @wraps(method)
            def wrapper(self, *args, **kwargs):
                with self.mutex:
                    if not self.initialized:
                        log.error(self.tag, f'{method.__name__}(), not initialized')
                        return default
                    return method(self, *args, **kwargs)
            return wrapper
        return decorator

    class Handler(object):

        # Synchronized to the blockchain at the first startup
        def on_blockchain_first_catchup(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit) -> None:
            pass

        # Notify the sync progress
        def on_blockchain_sync(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit, block_from: int, block_to: int, deposits: list[EventDeposit], withdrawals: list[EventWithdraw]) -> None:
            pass

        # Notify the latest block number
        def on_blockchain_latest_block(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit, block_number: int) -> None:
            pass

        # Notify the progress of rebuilding the merkle tree from database, only called when 'sync_only' is False
        def on_merkle_tree_rebuilt_progress(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit, numerator: int, denominator: int) -> None:
            pass

    def __init__(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit, connection: rpc.Interface | None = None):
        self.tag                : str                           = f'{__class__.__name__}'
        self.chain              : ChainID                       = chain
        self.symbol             : Symbol                        = symbol
        self.unit               : TornadoUnit                   = unit
        self.connection         : rpc.Interface | None          = connection
        self.external           : bool                          = connection is not None  # If True, the RPC connection is managed outside
        self.initialized        : bool                          = False
        self.sync_only          : bool                          = False  # If True, only sync events without rebuilding the merkle tree, 'withdraw()' will not be available
        self.db                 : database.Interface            = database.create(database.Backend.SQLITE)
        self.meta               : Metadata                      = util.load_metadata()[chain]
        self.proxy_address      : ChecksumAddress               = self.meta.proxy_address
        self.deployment_address : ChecksumAddress               = self.meta.deployment[self.symbol][self.unit][0]
        self.proxy_contract     : Contract | rpc.Error | None   = None
        self.deployment_contract: Contract | rpc.Error | None   = None
        self.token_contract     : Contract | rpc.Error | None   = None
        self.poller             : EventPoller                   = EventPoller(chain)
        self.catchup            : bool                          = False
        self.tree               : merkle_tree.Interface | None  = None
        self.zksnark            : zk.circuit.Interface          = zk.circuit.create(zk.circuit.ImplType.JAVASCRIPT)
        self.mutex              : threading.RLock               = threading.RLock()
        self.sync_cond          : threading.Condition           = threading.Condition(self.mutex)
        self.sync_transitioning : bool                          = False
        self.handlers           : list[Tornado.Handler]         = []
        with open(config.TORNADO_PROXY_ABI_PATH, 'r') as f:
            proxy_abi: str = f.read()
        with open(config.TORNADO_ABI_PATH, 'r') as f:
            deployment_abi: str = f.read()
        with open(config.ERC20_ABI_PATH, 'r') as f:
            erc20_abi: str = f.read()
        if self.connection is None:
            self.connection = rpc.Connection(self.chain, config.RPC_URLS[self.chain])
            if not self.connection.start():
                raise RuntimeError(f'Failed to start RPC connection for {self.chain}')
        self.proxy_contract      = self.connection.get_contract(address=self.proxy_address, abi=proxy_abi)
        self.deployment_contract = self.connection.get_contract(self.deployment_address, deployment_abi)
        self.token_contract      = self.connection.get_contract(self.meta.token_address[self.symbol], erc20_abi) if SymbolType.ERC20 == get_symbol_type(self.symbol) else None
        if rpc.is_error(self.proxy_contract):
            raise RuntimeError(f'Failed to get proxy contract instance, RPC error: {self.proxy_contract.code.value}')
        if rpc.is_error(self.deployment_contract):
            raise RuntimeError(f'Failed to get deployment contract instance, RPC error: {self.deployment_contract.code.value}')
        if rpc.is_error(self.token_contract):
            raise RuntimeError(f'Failed to get token contract instance, RPC error: {self.deployment_contract.code.value}')

    def __del__(self):
        if not self.external:
            if self.connection.started():
                self.connection.stop()

    '''
    Initialize Tornado instance
    @param  sync_only   If True, only sync events without rebuilding the merkle tree, 'withdraw()' will not be available
    '''
    def init(self, sync_only: bool) -> bool:
        with self.sync_cond:
            while self.sync_transitioning:
                self.sync_cond.wait()
            if self.initialized:
                log.debug(self.tag, 'init() already initialized')
                return True
            self.sync_transitioning = True
        try:
            with self.mutex:
                # Start RPC connection
                if not self.external:
                    if not self.connection.start():
                        log.error(self.tag, f'Failed to start RPC connection for {self.chain}')
                        return False
                elif not self.connection.started():
                    log.error(self.tag, 'The external RPC connection is not started')
                    return False
                # Open database
                if not self.db.open(self.chain, self.symbol, self.unit):
                    log.error(self.tag, f'Opening database failed for {self.chain}_{self.unit}{self.symbol}')
                    return False
                # Check integrity
                if not self.db.check_integrity():
                    log.error(self.tag, 'init() failed to check database integrity')
                    self.db.close()
                    return False
                # Rebuild merkle tree
                self.sync_only = sync_only
                self.catchup = False
                if not sync_only:
                    log.info(self.tag, 'Rebuilding merkle tree from database, please wait...')
                    commitments: list[HexBytes] | None = self.db.get_commitments()
                    if commitments is None:
                        log.error(self.tag, 'init() failed to get commitments from database')
                        self.db.close()
                        return False
                    def _(numerator: int, denominator: int) -> None:
                        self.callback('on_merkle_tree_rebuilt_progress', numerator, denominator)
                    self.tree = merkle_tree.create(merkle_tree.ImplType.MEMORY, config.MERKLE_TREE_HEIGHT, commitments, _)
                    log.info(self.tag, 'Merkle tree ready')
                # Add handlers
                self.poller.add_handler(self)
                self.initialized = True
                log.debug(self.tag, f'init()')
                return True
        finally:
            with self.sync_cond:
                self.sync_transitioning = False
                self.sync_cond.notify_all()

    def un_init(self) -> None:
        with self.sync_cond:
            while self.sync_transitioning:
                self.sync_cond.wait()
            if not self.initialized:
                log.debug(self.tag, 'un_init() already un-initialized')
                return
            log.debug(self.tag, 'un_init() shutting down')
            self.initialized = False
            self.sync_transitioning = True
            poller_started: bool = self.poller.is_started()
        try:
            if poller_started:
                self.poller.stop()
        finally:
            with self.sync_cond:
                self.poller.remove_all_handlers()
                self.db.close()
                if not self.external:
                    if self.connection.started():
                        self.connection.stop()
                self.tree = None
                self.sync_only = False
                self.catchup = False
                self.sync_transitioning = False
                self.sync_cond.notify_all()
                log.debug(self.tag, 'un_init() done')

    @locked
    def is_initialized(self) -> bool:
        return not self.initialized

    @locked
    def is_catchup(self) -> bool:
        return self.catchup

    @locked
    def add_handler(self, handler: Handler) -> None:
        self.handlers.append(handler)

    @locked
    def remove_all_handlers(self) -> None:
        self.handlers.clear()

    def start_sync(self) -> bool:
        with self.sync_cond:
            while self.sync_transitioning:
                self.sync_cond.wait()
            if not self.initialized:
                log.error(self.tag, 'start_sync(), not initialized')
                return False
            if self.poller.is_started():
                log.warn(self.tag, 'start_sync() already started')
                return False
            self.sync_transitioning = True
        try:
            with self.mutex:
                contract    : ChecksumAddress = self.meta.deployment[self.symbol][self.unit][0]
                latest_block: int | None      = self.db.get_latest_block_number()
                if latest_block is None:
                    log.error(self.tag, 'start_sync(), failed to get latest block number from database')
                    return False
                if latest_block > self.meta.deployment[self.symbol][self.unit][1]:
                    latest_block += 1
                self.catchup = False
            return self.poller.start(contract, latest_block)
        finally:
            with self.sync_cond:
                self.sync_transitioning = False
                self.sync_cond.notify_all()

    def stop_sync(self) -> None:
        with self.sync_cond:
            while self.sync_transitioning:
                self.sync_cond.wait()
            if not self.poller.is_started():
                log.warn(self.tag, 'stop_sync() already stopped')
                return
            self.sync_transitioning = True
        try:
            self.poller.stop()
        finally:
            with self.sync_cond:
                self.sync_transitioning = False
                self.sync_cond.notify_all()

    def callback(self, method_name: str, *args, **kwargs) -> None:
        with self.mutex:
            handlers: list[Tornado.Handler] = list(self.handlers)
        for h in handlers:
            fn = getattr(h, method_name, None)
            if fn is None:
                raise AttributeError(f'Handler {h} does not have method {method_name}')
            if not callable(fn):
                raise AttributeError(f'Handler {h} does not have callable method {method_name}')
            fn(self.chain, self.symbol, self.unit, *args, **kwargs)

    def on_first_catchup(self) -> None:
        with self.mutex:
            self.catchup = True
        self.callback('on_blockchain_first_catchup')

    def on_sync(self, block_from: int, block_to: int, deposits: list[EventDeposit], withdrawals: list[EventWithdraw]) -> None:
        with self.mutex:
            if not self.db.add_synchronized(block_to, deposits, withdrawals):
                raise RuntimeError(f'on_sync() failed to add synchronized data to database')
            if not self.sync_only:
                if self.tree is None:
                    raise RuntimeError(f'on_sync() merkle tree is not initialized')
                for e in deposits:
                    self.tree.add(e.commitment)
        self.callback('on_blockchain_sync', block_from, block_to, deposits, withdrawals)

    def on_latest_block(self, block_number: int) -> None:
        self.callback('on_blockchain_latest_block', block_number)

    # Check if a note has been deposited
    # @param    commitment      The commitment to query
    # @return   True : The corresponding note has been deposited
    #           False: The corresponding note has not been used
    #           None : Failed to query the blockchain, e.g. RPC connection error
    @locked_initialized()
    def note_deposited(self, commitment: HexBytes) -> bool | None:
        result: bool | rpc.Error = rpc.contract_call(self.deployment_contract, 'commitments', commitment)
        if rpc.is_error(result):
            log.error(self.tag, f'note_deposited(), failed to call contract function commitments(bytes32), RPC error: {result.code.value}')
            return None
        return result

    # Check if a note has been withdrawn
    # @param    nullifier_hash  The nullifier hash to query
    # @return   True : The corresponding note has been withdrawn
    #           False: The corresponding note has not been used
    #           None : Failed to query the blockchain, e.g. RPC connection error
    @locked_initialized()
    def note_withdrawn(self, nullifier_hash: HexBytes) -> bool | None:
        result: bool | rpc.Error = rpc.contract_call(self.deployment_contract, 'nullifierHashes', nullifier_hash)
        if rpc.is_error(result):
            log.error(self.tag, f'note_withdrawn(), failed to call contract function nullifierHashes(bytes32), RPC error: {result.code.value}')
            return None
        return result

    # Get how many deposit and withdrawal events happened after the note was deposited
    # @param    commitment  The commitment of the note to query
    # @return   Tuple of (num_deposits, num_withdrawals) on success, None if failed
    @locked_initialized()
    def note_age(self, commitment: HexBytes) -> tuple[int, int] | None:
        return self.db.note_age(commitment)

    # Create unsigned approve transaction of 'self.unit' amounts of tokens for deposit
    # @param    address     The address to make the approval, must use the corresponding private key to sign the transaction
    # @param    nonce       The nonce of the address, if None, will be queried from the blockchain
    # @return   TxParams of the unsigned transaction on success, None if failed
    @locked_initialized()
    def approve_tx(self, address: ChecksumAddress, nonce: Nonce | rpc.Error | None = None) -> TxParams | None:
        if nonce is None:
            nonce = self.connection.nonce(address)
            if rpc.is_error(nonce):
                log.error(self.tag, f'approve_tx(), failed to get nonce, RPC error: {nonce.code.value}')
                return None
        tx: TxParams = {
            'from'   : address,
            'chainId': self.chain.value,
            'nonce'  : Nonce(nonce),
        }
        built_tx: TxParams | rpc.Error = rpc.contract_build_tx(
            self.token_contract, 'approve', tx,
            self.proxy_address, unit_to_wei(self.unit, self.meta.decimals[self.symbol])
        )
        if rpc.is_error(built_tx):
            log.error(self.tag, f'approve_tx(), failed to build transaction, RPC error: {built_tx.code.value}')
            return None
        return built_tx

    # Approve 'self.unit' amounts of tokens for deposit
    # @param    key     The private key to make the approval
    # @param    nonce   The nonce of the address, if None, will be queried from the blockchain
    # @return   HexBytes of transaction hash on success, None if failed
    @locked_initialized()
    def approve(self, key: Key, nonce: Nonce | rpc.Error | None = None) -> HexBytes | None:
        if nonce is None:
            nonce = self.connection.nonce(key.eth_address())
            if rpc.is_error(nonce):
                log.error(self.tag, f'approve(), failed to get nonce, RPC error: {nonce.code.value}')
                return None
        # Build
        built_tx: TxParams | None = self.approve_tx(key.eth_address(), nonce)
        # Sign
        signed_tx: SignedTransaction | rpc.Error = self.connection.sign_transaction(built_tx, key)
        if rpc.is_error(signed_tx):
            log.error(self.tag, f'approve(), failed to sign transaction, RPC error: {signed_tx.code.value}')
            return None
        # Send
        tx_hash: HexBytes | rpc.Error = self.connection.send_transaction(signed_tx)
        if rpc.is_error(tx_hash):
            log.error(self.tag, f'approve(), failed to send transaction, RPC error: {tx_hash.code.value}')
            return None
        # Wait for the allowance to be updated
        max_waits: int = 30
        counter  : int = 0
        while True:
            counter += 1
            allowance = rpc.contract_call(self.token_contract, 'allowance', key.eth_address(), self.proxy_address)
            if rpc.is_error(allowance):
                log.error(self.tag, f'approve(), failed to call contract function allowance(address,address), RPC error: {allowance.code.value}')
                return None
            if allowance >= unit_to_wei(self.unit, self.meta.decimals[self.symbol]):
                break
            if counter >= max_waits:
                log.error(self.tag, f'approve(), timeout waiting for allowance to be updated')
                return None
            log.info(self.tag, f'approve(), waiting for allowance to be updated...')
            wait(Second(2))
        return tx_hash

    # Create unsigned deposit transaction
    # @param    commitment      The commitment of the note to deposit
    # @param    from_address    The address to make the deposit, must use the corresponding private key to sign the transaction
    # @param    nonce           The nonce of the from_address, if None, will be queried from the blockchain
    # @return   TxParams of the unsigned transaction on success, None if failed
    @locked_initialized()
    def deposit_tx(self, commitment: HexBytes, from_address: ChecksumAddress, nonce: Nonce | rpc.Error | None = None) -> TxParams | None:
        if nonce is None:
            nonce = self.connection.nonce(from_address)
            if rpc.is_error(nonce):
                log.error(self.tag, f'deposit_tx(from={from_address}), failed to get nonce, RPC error: {nonce.code.value}')
                return None
        tx: TxParams = {
            'from'   : from_address,
            'chainId': self.chain.value,
            'nonce'  : Nonce(nonce),
        }
        if SymbolType.NATIVE == get_symbol_type(self.symbol):
            tx['value'] = unit_to_wei(self.unit, self.meta.decimals[self.symbol])
        built_tx: TxParams | rpc.Error = rpc.contract_build_tx(self.proxy_contract, 'deposit', tx, self.deployment_address, commitment, b'')
        if rpc.is_error(built_tx):
            log.error(self.tag, f'deposit_tx(from={from_address}), failed to build transaction, RPC error: {built_tx.code.value}')
            return None
        return built_tx

    # Deposit
    # @param    commitment  The commitment of the note to deposit
    # @param    key         The private key to make the deposit
    # @param    nonce       The nonce of the from_address, if None, will be queried from the blockchain
    # @return   HexBytes of transaction hash on success, None if failed
    @locked_initialized()
    def deposit(self, commitment: HexBytes, key: Key, nonce: Nonce | rpc.Error | None = None) -> HexBytes | None:
        if nonce is None:
            nonce = self.connection.nonce(key.eth_address())
            if rpc.is_error(nonce):
                log.error(self.tag, f'deposit(from={key.eth_address()}), failed to get nonce, RPC error: {nonce.code.value}')
                return None
        # Allowance for ERC20 token
        if SymbolType.ERC20 == get_symbol_type(self.symbol):
            # Check allowance
            allowance: int | rpc.Error = rpc.contract_call(self.token_contract, 'allowance', key.eth_address(), self.proxy_address)
            if rpc.is_error(allowance):
                log.error(self.tag, f'deposit(from={key.eth_address()}), failed to call contract function allowance(address,address), RPC error: {allowance.code.value}')
                return None
            # Approve if not enough
            if allowance < unit_to_wei(self.unit, self.meta.decimals[self.symbol]):
                tx_hash: HexBytes | None = self.approve(key, nonce)
                if tx_hash is None:
                    return None
            # Increase nonce manually
            nonce += 1
        # Build
        built_tx: TxParams | None = self.deposit_tx(commitment, key.eth_address(), nonce)
        if built_tx is None:
            return None
        # Sign
        signed_tx: SignedTransaction | rpc.Error = self.connection.sign_transaction(built_tx, key)
        if rpc.is_error(signed_tx):
            log.error(self.tag, f'deposit(from={key.eth_address()}), failed to sign transaction, RPC error: {signed_tx.code.value}')
            return None
        # Send
        tx_hash: HexBytes | rpc.Error = self.connection.send_transaction(signed_tx)
        if rpc.is_error(tx_hash):
            log.error(self.tag, f'deposit(from={key.eth_address()}), failed to send transaction, RPC error: {tx_hash.code.value}')
            return None
        log.info(self.tag, f'Deposit {self.unit.value} {self.symbol.value.upper()} succeed, tx hash: {tx_hash.hex()}', log.Color.CYAN, log.Style.BOLD)
        return tx_hash

    # Create unsigned withdraw transaction
    # @param    note            The note to withdraw
    # @param    withdrawer      The address to make the withdrawal, must use the corresponding private key to sign the transaction
    # @param    recipient       Address to receive the withdrawal
    # @param    merkle_proof    The merkle proof of the note
    # @param    zk_proof        The zk-SNARK proof of the note
    # @param    nonce           The nonce of the withdrawer address, if None, will be queried from the blockchain
    # @param    refund          Amount to send to the recipient
    # @return   TxParams of the unsigned transaction on success, None if failed
    @locked_initialized()
    def withdraw_tx(self,
                    note: Note,
                    withdrawer: ChecksumAddress,
                    recipient: ChecksumAddress,
                    merkle_proof: MerkleProof,
                    zk_proof: dict,
                    nonce: Nonce | rpc.Error | None = None,
                    refund: Wei = Wei(0)) -> TxParams | None:
        if nonce is None:
            nonce = self.connection.nonce(withdrawer)
            if rpc.is_error(nonce):
                log.error(self.tag, f'withdraw_tx(withdrawer={withdrawer}, recipient={recipient}), failed to get withdrawer nonce, RPC error: {nonce.code.value}')
                return None
        tx: TxParams = {
            'from'   : withdrawer,
            'chainId': self.chain.value,
            'nonce'  : Nonce(nonce),
        }
        built_tx: TxParams | rpc.Error = rpc.contract_build_tx(
            self.proxy_contract, 'withdraw', tx,
            self.deployment_address,
            HexBytes.fromhex(zk_proof['solidity']['proof'][2:] if zk_proof['solidity']['proof'].startswith('0x') else zk_proof['solidity']['proof']),
            merkle_proof.root,
            note.nullifier_hash,
            recipient,
            Web3.to_checksum_address('0x0000000000000000000000000000000000000000'),  # Relayer address
            Wei(0),  # Relayer fee
            refund,
        )
        if rpc.is_error(built_tx):
            log.error(self.tag, f'withdraw_tx(withdrawer={withdrawer}, recipient={recipient}), failed to build transaction, RPC error: {built_tx.code.value}')
            return None
        return built_tx

    # Withdraw
    # @param    note            The note to withdraw
    # @param    recipient       Address to receive the withdrawal
    # @param    key_or_relayer  The private key to pay the gas fee, or the URL of the relayer
    # @param    nonce           The nonce of the withdrawer address, if None and not using relayer, will be queried from the blockchain
    # @param    refund          Amount to send to the recipient, make sure the `key_or_relayer` is a key and has enough balance
    # @return   HexBytes of transaction hash on success, None if failed or sync-only mode
    @locked_initialized()
    def withdraw(self,
                 note: Note,
                 recipient: ChecksumAddress,
                 key_or_relayer: Key | str,
                 nonce: Nonce | rpc.Error | None = None,
                 refund: Wei = Wei(0)) -> HexBytes | None:
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

        relayer_address   : ChecksumAddress    = Web3.to_checksum_address('0x0000000000000000000000000000000000000000')
        relayer_eth_prices: dict[Symbol, Wei]  = {}
        relayer_fee       : Wei                = Wei(0)
        if use_relayer:
            # HTTP Get relayer status
            try:
                resp: Response = requests.get(relayer_url.rstrip('/') + '/status', proxies=get_requests_proxies(config.RPC_PROXY_URL))
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
            gas_price: Wei | rpc.Error = self.connection.gas_price()
            if rpc.is_error(gas_price):
                log.error(self.tag, f'withdraw(to={recipient}), failed to get gas price, RPC error: {gas_price.code.value}')
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
        zk_proof: dict | None = self.zksnark.prove(circuit_input)
        if zk_proof is None:
            log.error(self.tag, f'withdraw(to={recipient}), failed to prove for commitment: {note.commitment.to_0x_hex()}')
            return None
        # Verify test
        if not self.zksnark.verify(zk_proof):
            log.error(self.tag, f'withdraw(to={recipient}), failed to test verify proof for commitment: {note.commitment.to_0x_hex()}')
            return None
        log.info(self.tag, f'Proof generated for commitment: {note.commitment.to_0x_hex()}')

        # Make withdrawal via relayer
        if use_relayer:
            # Submit withdrawal to relayer and get job ID
            try:
                resp: Response = requests.post(
                    url=relayer_url.rstrip('/') + '/v1/tornadoWithdraw',
                    json={
                        'contract': self.deployment_address,
                        'proof': zk_proof['solidity']['proof'],
                        'args': [
                            zk_proof['solidity']['publicSignals'][0],  # root
                            zk_proof['solidity']['publicSignals'][1],  # nullifierHash
                            recipient,                                 # recipient address
                            relayer_address,                           # relayer address
                            zk_proof['solidity']['publicSignals'][4],  # fee
                            zk_proof['solidity']['publicSignals'][5],  # refund
                        ]
                    },
                    proxies=get_requests_proxies(config.RPC_PROXY_URL)
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
                    resp = requests.get(relayer_url.rstrip('/') + f'/v1/jobs/{job_id}', proxies=get_requests_proxies(config.RPC_PROXY_URL))
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
                if result['status'] == 'MINED' or result['status'] == 'CONFIRMED':
                    try:
                        relayer_tx_hash: str = result['txHash']
                        log.info(self.tag, f'Withdraw {self.unit.value} {self.symbol.value.upper()} succeed, tx hash: {relayer_tx_hash}')
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

        # Otherwise, make withdrawal directly
        if nonce is None:
            nonce = self.connection.nonce(key.eth_address())
            if rpc.is_error(nonce):
                log.error(self.tag, f'withdraw(withdrawer={key.eth_address()}, recipient={recipient}), failed to get withdrawer nonce, RPC error: {nonce.code.value}')
                return None
        # Build
        built_tx: TxParams | None = self.withdraw_tx(note, key.eth_address(), recipient, merkle_proof, zk_proof, nonce, refund)
        if built_tx is None:
            return None
        # Sign
        signed_tx: SignedTransaction | rpc.Error = self.connection.sign_transaction(built_tx, key)
        if rpc.is_error(signed_tx):
            log.error(self.tag, f'withdraw(withdrawer={key.eth_address()}, recipient={recipient}), failed to sign transaction, RPC error: {signed_tx.code.value}')
            return None
        # Send
        tx_hash: HexBytes | rpc.Error = self.connection.send_transaction(signed_tx)
        if rpc.is_error(tx_hash):
            log.error(self.tag, f'withdraw(withdrawer={key.eth_address()}, recipient={recipient}), failed to send transaction, RPC error: {tx_hash.code.value}')
            return None
        log.info(self.tag, f'Withdraw {self.unit.value} {self.symbol.value.upper()} succeed, tx hash: {tx_hash.to_0x_hex()}')
        return tx_hash
