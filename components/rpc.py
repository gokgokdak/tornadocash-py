from enum import Enum
from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from typing import Any, Callable
from web3 import Web3
from web3.contract import Contract
from web3.datastructures import AttributeDict
from web3.eth import Eth
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import LogReceipt, Nonce, TxReceipt, TxParams, Wei
import threading
import traceback

from . import log, util
from .mytype import ChainID, Key
import config


class ErrorCode(Enum):
    UNKNOWN             = 'UNKNOWN'
    RPC_NOT_STARTED     = 'RPC_NOT_STARTED'
    RPC_CALL_RATE_LIMIT = 'RPC_CALL_RATE_LIMIT'
    SSL_ERROR           = 'SSL_ERROR'
    CONNECTION_ABORTED  = 'CONNECTION_ABORTED'
    SERVER_ERROR_504    = 'SERVER_ERROR_504'
    GATEWAY_TIMEOUT     = 'GATEWAY_TIMEOUT'
    NONCE_TOO_LOW       = 'NONCE_TOO_LOW'
    TX_HASH_NOT_FOUND   = 'TX_HASH_NOT_FOUND'
    MAX_FEE_TOO_LOW     = 'MAX_FEE_LESS_THAN_BASE'
    INSUFFICIENT_FUNDS  = 'INSUFFICIENT_FUNDS'
    REPLACE_UNDERPRICE  = 'REPLACE_UNDERPRICE'
    ADDRESS_SANCTIONED  = 'ADDRESS_SANCTIONED'
    EXECUTION_REVERTED  = 'EXECUTION_REVERTED'


class Error(object):

    def __init__(self, code: ErrorCode, call_param: tuple[Any, ...], msg: str = '') -> None:
        self.code      : ErrorCode       = code
        self.call_param: tuple[Any, ...] = call_param
        self.msg       : str             = msg


def is_error(value: Any) -> bool:
    if isinstance(value, Error):
        return True
    return False


def parse_exception_to_error_code(e: Exception) -> ErrorCode:
    text: str = str(e).lower()
    if all(key in text for key in ['too many requests', 'rate limit']):
        return ErrorCode.RPC_CALL_RATE_LIMIT
    elif any(key in text for key in ['sslerror', 'ssleoferror']):
        return ErrorCode.SSL_ERROR
    elif all(key in text for key in ['connection', 'abort']):
        return ErrorCode.CONNECTION_ABORTED
    elif any(key in text for key in ['504', 'server', 'error']):
        return ErrorCode.SERVER_ERROR_504
    elif any(key in text for key in ['gateway', 'timeout']):
        return ErrorCode.GATEWAY_TIMEOUT
    elif all(key in text for key in ['nonce', 'low']):
        return ErrorCode.NONCE_TOO_LOW
    elif all(key in text for key in ['transaction', 'hash', 'not found']):
        return ErrorCode.TX_HASH_NOT_FOUND
    elif all(key in text for key in ['max fee', 'less than', 'base fee']):
        return ErrorCode.MAX_FEE_TOO_LOW
    elif all(key in text for key in ['insufficient']) and any(key in text for key in ['balance', 'funds']):
        return ErrorCode.INSUFFICIENT_FUNDS
    elif all(key in text for key in ['replace', 'underprice']):
        return ErrorCode.REPLACE_UNDERPRICE
    elif any(key in text for key in ['sanction', 'sanctioned', 'blacklist']):
        return ErrorCode.ADDRESS_SANCTIONED
    elif all(key in text for key in ['execution', 'reverted']):
        return ErrorCode.EXECUTION_REVERTED
    return ErrorCode.UNKNOWN


def contract_call(contract: Contract, method: str, *args) -> Any | Error:
    try:
        func = contract.get_function_by_name(method)
        result: Any = func(*args).call()
        return result
    except Exception as e:
        code: ErrorCode = parse_exception_to_error_code(e)
        return Error(code, (contract.address, method, args), str(e))


def contract_build_tx(contract: Contract, method: str, tx_params: TxParams, *args) -> TxParams | Error:
    try:
        func = contract.get_function_by_name(method)
        tx: TxParams = func(*args).build_transaction(tx_params)
        return tx
    except Exception as e:
        code: ErrorCode = parse_exception_to_error_code(e)
        return Error(code, (contract.address, method, tx_params, args), str(e))


class Web3EthWrapper(Eth):

    def __init__(self, web3: Web3, chain: ChainID) -> None:
        super().__init__(web3)
        self.__chain: ChainID = chain

    @property
    def chain_id(self):
        return self.__chain.value


class Interface(object):

    def __init__(self, chain: ChainID) -> None:
        self.chain = chain

    def start(self) -> bool:
        raise NotImplementedError

    def started(self) -> bool:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def gas_price(self, callback: Callable[[Wei | Error], None] = None) -> Wei | Error | None:
        raise NotImplementedError

    def get_contract(self, address: ChecksumAddress, abi: str, callback: Callable[[Contract | Error], None] = None) -> Contract | Error | None:
        raise NotImplementedError

    def latest_block_number(self, callback: Callable[[int | Error], None] = None) -> int | Error | None:
        raise NotImplementedError

    def log_receipt(self, contract_address: ChecksumAddress, blk_num_from: int, blk_num_to: int, event_hash: list[HexBytes], callback: Callable[[list[LogReceipt]|Error], None] = None) -> list[LogReceipt]|Error|None:
        raise NotImplementedError

    def transaction_receipt(self, tx_hash: HexBytes, callback: Callable[[tuple[HexBytes, TxReceipt] | Error], None] = None) -> TxReceipt | Error | None:
        raise NotImplementedError

    def nonce(self, address: ChecksumAddress, callback: Callable[[int | Error], None] = None) -> int | Error | None:
        raise NotImplementedError

    def sign_transaction(self, transaction: TxParams, private_key: Key, callback: Callable[[SignedTransaction | Error], None] = None) -> SignedTransaction | Error | None:
        raise NotImplementedError

    def send_transaction(self, transaction: SignedTransaction, callback: Callable[[HexBytes | Error], None] = None) -> HexBytes | Error | None:
        raise NotImplementedError


class Connection(Interface):

    def __init__(self, chain: ChainID, url: str) -> None:
        super().__init__(chain)
        self.TAG        : str                       = f'{__name__}.Connection'
        self.url        : str                       = url
        self.w3         : Web3|None                 = None
        self.turn_off   : bool                      = True
        self.mutex      : threading.RLock           = threading.RLock()
        self.condition  : threading.Condition       = threading.Condition(self.mutex)
        self.tasks      : list[Callable[[], None]]  = []
        self.worker     : threading.Thread | None   = None
        log.debug(self.TAG, f'Init(url={self.url})')

    def start(self) -> bool:
        with self.condition:
            if not self.turn_off:
                log.debug(self.TAG, f'start({self}) already started')
                return True
            if self.worker is not None:
                if self.worker == threading.current_thread():
                    log.error(self.TAG, "start() cannot restart from the RPC worker thread while stop is pending")
                else:
                    log.warn(self.TAG, f'start({self}) stop is still pending')
                return False
            log.debug(self.TAG, f'start({self})')

            proxy_url: str | None = config.RPC_PROXY_URL
            proxy_info = util.parse_proxy_url(proxy_url)
            if proxy_url is not None and proxy_info is None:
                log.warn(self.TAG, f'Invalid RPC_PROXY_URL "{proxy_url}", only http/https/socks5/socks5h are supported. Proxy disabled.')
            if proxy_info is not None and proxy_info['port'] is None:
                log.warn(self.TAG, f'RPC_PROXY_URL "{proxy_url}" is missing port, proxy disabled.')
                proxy_info = None
            if self.url.startswith('http'):
                request_kwargs = {}
                if proxy_info:  # HTTP/HTTPS provider with proxy support
                    request_kwargs['proxies'] = {
                        'http': proxy_url,
                        'https': proxy_url,
                    }
                self.w3 = Web3(Web3.HTTPProvider(self.url, request_kwargs=request_kwargs))
            elif self.url.startswith('ws'):
                websocket_kwargs = {}
                if proxy_info:  # WebSocket provider with proxy support
                    proxy_scheme = proxy_info['scheme']
                    if proxy_scheme in ('socks5', 'socks5h'):
                        # SOCKS5 proxy for WebSocket
                        websocket_kwargs['proxy_type'] = proxy_scheme
                        websocket_kwargs['http_proxy_host'] = proxy_info['host']
                        websocket_kwargs['http_proxy_port'] = proxy_info['port']
                        if proxy_info['username'] and proxy_info['password']:
                            websocket_kwargs['http_proxy_auth'] = (proxy_info['username'], proxy_info['password'])
                    elif proxy_scheme in ('http', 'https'):
                        # HTTP proxy for WebSocket
                        websocket_kwargs['http_proxy_host'] = proxy_info['host']
                        websocket_kwargs['http_proxy_port'] = proxy_info['port']
                        if proxy_info['username'] and proxy_info['password']:
                            websocket_kwargs['http_proxy_auth'] = (proxy_info['username'], proxy_info['password'])
                self.w3 = Web3(Web3.LegacyWebSocketProvider(self.url, websocket_kwargs=websocket_kwargs))
            else:
                raise ValueError(f'Unsupported RPC url: {self.url}')
            if self.chain == ChainID.POLYGON or self.chain == ChainID.BSC:
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            self.w3.eth = Web3EthWrapper(self.w3, self.chain)
            self.turn_off = False
            self.worker = threading.Thread(target=self.work_loop)
            self.worker.start()
        return True

    def stop(self) -> None:
        with self.condition:
            if self.turn_off and self.worker is None:
                log.debug(self.TAG, f'stop({self}) already stopped')
                return
            log.debug(self.TAG, f'stop({self}) shutting down')
            self.turn_off = True
            worker: threading.Thread | None = self.worker
            self.condition.notify_all()
        if worker is not None and worker != threading.current_thread():
            worker.join()
        with self.condition:
            while self.worker is not None and self.worker != threading.current_thread():
                self.condition.wait()
        log.debug(self.TAG, f'stop({self}) done')

    def started(self) -> bool:
        with self.condition:
            return not self.turn_off

    def gas_price(self, callback: Callable[[Wei | Error], None] = None) -> Wei | Error | None:
        call_param: tuple[Any, ...] = (callback, )
        signature: str = f'gas_price(async={True if callback else False})'
        def _() -> Wei:
            return Wei(self.w3.eth.gas_price)
        if callback is None:
            return self.run_sync(_, signature, call_param)
        return self.run_async(_, signature, call_param, callback)

    def get_contract(self, address: ChecksumAddress, abi: str, callback: Callable[[Contract | Error], None] = None) -> Contract | Error | None:
        call_param: tuple[Any, ...] = (address, abi, callback)
        signature: str = f'any_contract(address={address}, async={True if callback else False})'
        def _() -> Contract:
            return self.w3.eth.contract(address=address, abi=abi)
        if callback is None:
            return self.run_sync(_, signature, call_param)
        return self.run_async(_, signature, call_param, callback)

    def latest_block_number(self, callback: Callable[[int | Error], None] = None) -> int | Error | None:
        call_param: tuple[Any, ...] = (callback, )
        signature: str = f'latest_block_number(async={True if callback else False})'
        def _() -> int:
            return self.w3.eth.block_number
        if callback is None:
            return self.run_sync(_, signature, call_param)
        return self.run_async(_, signature, call_param, callback)

    def log_receipt(self, contract_address: ChecksumAddress, blk_num_from: int, blk_num_to: int, event_hash: list[HexBytes], callback: Callable[[list[LogReceipt]|Error], None] = None) -> list[LogReceipt]|Error|None:
        call_param: tuple[Any, ...] = (contract_address, blk_num_from, blk_num_to, event_hash, callback)
        signature: str = f'log_receipt(contract_address={contract_address}, blk_num_from={blk_num_from}, blk_num_to={blk_num_to}, event_hash={event_hash}, async={True if callback else False})'
        def _() -> list[LogReceipt]:
            return self.w3.eth.get_logs({
                'address'  : contract_address,
                'fromBlock': blk_num_from,
                'toBlock'  : blk_num_to,
                'topics'   : event_hash
            })
        if callback is None:
            return self.run_sync(_, signature, call_param)
        return self.run_async(_, signature, call_param, callback)

    def transaction_receipt(self, tx_hash: HexBytes, callback: Callable[[tuple[HexBytes, TxReceipt] | Error], None] = None) -> TxReceipt | Error | None:
        call_param: tuple[Any, ...] = (tx_hash, callback)
        signature: str = f'transaction_receipt(tx_hash={tx_hash.to_0x_hex()}, async={True if callback else False})'
        def _() -> TxReceipt:
            return self.w3.eth.get_transaction_receipt(tx_hash)
        if callback is None:
            return self.run_sync(_, signature, call_param)
        def bridge(result: TxReceipt|Error) -> None:
            if isinstance(result, Error):
                callback(result)
            elif isinstance(result, AttributeDict):
                callback((tx_hash, result))
            else:
                msg: str = f'w3.eth.get_transaction_receipt(tx_hash="{tx_hash.to_0x_hex()}") return unexpected type "{type(result)}" with value "{result}"'
                log.error(self.TAG, msg)
                callback(Error(ErrorCode.UNKNOWN, call_param, msg))
        return self.run_async(_, signature, call_param, bridge)

    def nonce(self, address: ChecksumAddress, callback: Callable[[int | Error], None] = None) -> int | Error | None:
        call_param: tuple[Any, ...] = (address, callback)
        signature: str = f'nonce(address={address}, async={True if callback else False})'
        def _() -> Nonce:
            return self.w3.eth.get_transaction_count(address)
        if callback is None:
            return self.run_sync(_, signature, call_param)
        return self.run_async(_, signature, call_param, callback)

    def sign_transaction(self, transaction: TxParams, private_key: Key, callback: Callable[[SignedTransaction | Error], None] = None) -> SignedTransaction | Error | None:
        call_param: tuple[Any, ...] = (transaction, private_key, callback)
        signature: str = f'sign_transaction(transaction={transaction}, async={True if callback else False})'
        def _() -> SignedTransaction:
            return self.w3.eth.account.sign_transaction(transaction, private_key.private().to_bytes())
        if callback is None:
            return self.run_sync(_, signature, call_param)
        return self.run_async(_, signature, call_param, callback)

    def send_transaction(self, transaction: SignedTransaction, callback: Callable[[HexBytes | Error], None] = None) -> HexBytes | Error | None:
        call_param: tuple[Any, ...] = (transaction, callback)
        signature: str = f'send_transaction(transaction={transaction.raw_transaction.to_0x_hex()}, async={True if callback else False})'
        def _() -> HexBytes:
            return self.w3.eth.send_raw_transaction(transaction.raw_transaction)
        if callback is None:
            return self.run_sync(_, signature, call_param)
        return self.run_async(_, signature, call_param, callback)

    def work_loop(self) -> None:
        try:
            while True:
                task: Callable[[], None] | None = None
                with self.condition:
                    while 0 == len(self.tasks) and not self.turn_off:
                        try:
                            self.condition.wait(0.1)
                        except KeyboardInterrupt:
                            pass
                    if 0 == len(self.tasks) and self.turn_off:
                        break
                    task = self.tasks.pop(0)
                try:
                    task()
                except Exception as e:
                    stack: str = traceback.format_exc()
                    text : str = str(e)
                    lines: list[str] = [f'Exception in RPC task: {text}']
                    lines.extend(stack.split('\n'))
                    log.error(self.TAG, lines)
        finally:
            with self.condition:
                if self.worker == threading.current_thread():
                    self.turn_off = True
                    self.worker = None
                    self.w3 = None
                self.condition.notify_all()

    def _not_started_error(self, call_param: tuple[Any, ...]) -> Error:
        log.error(self.TAG, "Connection not started")
        return Error(ErrorCode.RPC_NOT_STARTED, call_param)

    def _run_action(self, action: Callable, signature: str, call_param: tuple[Any, ...]) -> Any:
        try:
            return action()
        except Exception as e:
            code : ErrorCode = parse_exception_to_error_code(e)
            stack: str       = traceback.format_exc()
            lines: list[str] = [f'{signature} raised {type(e)} exception, {code.value}']
            lines.extend(stack.split('\n'))
            log.debug(self.TAG, lines)
            return Error(code, call_param, str(e))

    def run_sync(self, action: Callable, signature: str, call_param: tuple[Any, ...]) -> Any:
        done_event: threading.Event = threading.Event()
        result    : Any             = None

        with self.condition:
            if self.turn_off:
                return self._not_started_error(call_param)
            run_inline: bool = self.worker == threading.current_thread()
        if run_inline:
            return self._run_action(action, signature, call_param)

        def task() -> None:
            nonlocal result
            result = self._run_action(action, signature, call_param)
            done_event.set()

        with self.condition:
            if self.turn_off:
                return self._not_started_error(call_param)
            self.tasks.append(task)
            self.condition.notify()
        while not done_event.is_set():
            try:
                done_event.wait(0.01)
            except KeyboardInterrupt:
                pass
        return result

    def run_async(self, action: Callable, signature: str, call_param: tuple[Any, ...], callback: Callable[[Any], None]) -> Error | None:
        def task() -> None:
            result: Any = self._run_action(action, signature, call_param)
            try:
                callback(result)
            except Exception as e:
                stack: str = traceback.format_exc()
                text : str = str(e)
                lines: list[str] = [f'Exception in RPC callback for {signature}: {text}']
                lines.extend(stack.split('\n'))
                log.error(self.TAG, lines)

        with self.condition:
            if self.turn_off:
                return self._not_started_error(call_param)
            self.tasks.append(task)
            self.condition.notify()
        return None
