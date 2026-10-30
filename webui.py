"""Local WebSocket backend; www/ is an independent static frontend."""

import asyncio
import json
import re
import signal
import threading
from dataclasses import dataclass, field
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

import config
from components import log, rpc, util
from components.blockchain import EventDeposit, EventPoller, EventWithdraw
from components.core import Tornado
from components.mytype import ChainID, Metadata, Note, Symbol, SymbolType, TornadoUnit, chain_to_string


STATUS_MESSAGES: dict[str, str] = {
    'starting'    : 'Waiting to initialize.',
    'initializing': 'Opening and checking the local database.',
    'connecting'  : 'Waiting for a response from the blockchain RPC.',
    'retrying'    : 'RPC request failed. Retrying; synchronization is paused.',
    'syncing'     : 'Synchronizing deposit and withdrawal events.',
    'ready'       : 'Synchronized with the blockchain RPC.',
    'stopped'     : 'Event polling has stopped.',
    'error'       : 'Backend initialization or synchronization failed.',
}

ACTIVITY_MESSAGES: dict[str, str] = {
    'fetching_head'  : 'Fetching the latest block from RPC.',
    'fetching_events': 'Fetching deposit and withdrawal events from RPC.',
    'retry_wait'     : 'Waiting before the next RPC retry.',
    'persisting'     : 'Saving events to the local database.',
    'idle'           : '',
    'creating_note'  : 'Creating a note.',
    'checking_note'  : 'Checking the note on chain.',
    'checking_tx'    : 'Checking the transaction receipt.',
    'syncing'        : 'Syncing with the blockchain RPC.',
    'building_tree'  : 'Preparing the withdrawal Merkle tree.',
    'proving'        : 'Preparing and verifying the withdrawal proof.',
    'relaying'       : 'Preparing and submitting the relayer withdrawal.',
    'approving'      : 'Building the token approval transaction.',
    'depositing'     : 'Building the deposit transaction.',
}


def encode_wallet_format_tx(value: Any) -> Any:
    """Encode Python transaction quantities for an EIP-1193 wallet."""
    if value is None:
        raise RuntimeError('Could not build transaction. Check backend logs; ERC20 deposits need token approval first.')
    if isinstance(value, bytes):
        return HexBytes(value).to_0x_hex()
    if isinstance(value, int):
        return hex(value)
    if isinstance(value, dict):
        return {key: encode_wallet_format_tx(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode_wallet_format_tx(item) for item in value]
    return value


@dataclass
class Instance:
    chain            : ChainID
    symbol           : Symbol
    unit             : TornadoUnit
    tornado          : Tornado | None               = None
    error            : str | None                   = None
    lock             : threading.Lock               = field(default_factory=threading.Lock)
    totals           : tuple[int, int]              = (0, 0)
    phase            : str                          = 'starting'
    activity         : str | None                   = None
    progress         : str | None                   = None
    progress_callback: Callable[[str], None] | None = None


class Counters(Tornado.Handler):

    def __init__(self, item: Instance) -> None:
        self.item: Instance = item

    def on_sync(self, block_from: int, block_to: int, deposits: list[EventDeposit], withdrawals: list[EventWithdraw]) -> None:
        deposited, withdrawn = self.item.totals
        self.item.totals = deposited + len(deposits), withdrawn + len(withdrawals)

    def on_progress(self, message: str) -> None:
        callback: Callable[[str], None] | None = self.item.progress_callback
        if callback is not None:
            callback(message)


class Backend:

    def __init__(self, chains: set[ChainID]) -> None:
        self.metadata   : dict[ChainID, Metadata]       = util.load_metadata()
        self.instances  : dict[str, Instance]           = {}
        self.connections: dict[ChainID, rpc.Connection] = {}
        self.stopping   : bool                          = False
        for chain, meta in self.metadata.items():
            if chain not in chains:
                continue
            for symbol, units in meta.deployment.items():
                for unit in units:
                    name: str = f'{chain_to_string(chain)}-{symbol.value}-{unit.value}'
                    self.instances[name] = Instance(chain, symbol, unit)

    async def start(self) -> None:
        # Start RPC connections
        async def start_chain(chain: ChainID) -> None:
            items: list[Instance] = [item for item in self.instances.values() if item.chain == chain]
            try:
                for item in items:
                    item.phase = 'connecting'
                connection: rpc.Connection = rpc.Connection(chain, config.RPC_URLS[chain])
                self.connections[chain] = connection
                if not await asyncio.to_thread(connection.start):
                    raise RuntimeError('RPC connection failed to start')
                await asyncio.gather(*(asyncio.to_thread(self._start, item) for item in items))
            except Exception as error:
                message: str = f'RPC initialization failed: {error}'[:300]
                log.error('WebUI', f'{chain_to_string(chain)}: {message}')
                for item in items:
                    item.error = message
        # Then starts core.Tornado
        await asyncio.gather(*(start_chain(chain) for chain in {item.chain for item in self.instances.values()}))

    def _start(self, item: Instance) -> None:
        with item.lock:
            if self.stopping:
                return
            tornado: Tornado | None = None
            try:
                item.phase = 'initializing'
                chain     : ChainID        = item.chain
                connection: rpc.Connection = self.connections[chain]
                tornado = Tornado(chain, item.symbol, item.unit, connection)
                tornado.poller = EventPoller(chain, connection)
                if not tornado.init(sync_only=True):
                    raise RuntimeError('Could not initialize database.')
                totals: tuple[int, int] | None = tornado.db.get_event_counts()
                if totals is None:
                    raise RuntimeError('Could not read event counts.')
                item.totals = totals
                tornado.add_handler(Counters(item))
                if not tornado.start_sync():
                    raise RuntimeError('Could not start synchronization.')
                item.tornado = tornado
            except Exception as error:
                item.error = f'Initialization failed: {error}'[:300]
                log.error('WebUI', f'{chain_to_string(item.chain)} {item.unit.value} {item.symbol.value}: {item.error}')
                if tornado is not None:
                    tornado.un_init()

    def status(self) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for name, item in self.instances.items():
            meta: Metadata = self.metadata[item.chain]
            tornado: Tornado | None = item.tornado
            deposited, withdrawn = item.totals
            sync: dict[str, Any] = tornado.poller.status() if tornado else {
                'synced_block'    : None,
                'latest_block'    : None,
                'start_block'     : None,
                'remaining_blocks': None,
                'progress'        : None,
                'deposits'        : 0,
                'withdrawals'     : 0,
                'error'           : item.error,
            }
            if tornado:
                phase: str = sync['phase']
            else:
                phase = 'error' if item.error else item.phase
            ready   : bool       = phase == 'ready'
            activity: str | None = item.activity or sync.get('activity')
            state   : str        = phase
            working : bool       = bool(item.activity) and phase not in ('error', 'stopped')
            if working:
                state = activity if activity in ('syncing', 'building_tree', 'proving', 'relaying') else 'working'
            message: str = (item.progress or ACTIVITY_MESSAGES[activity]) if working else STATUS_MESSAGES[phase]
            if phase not in ('syncing', 'ready'):
                sync['progress'] = sync['remaining_blocks'] = None
            rows.append({
                **sync,
                'id'                : name,
                'chain'             : chain_to_string(item.chain),
                'chain_id'          : item.chain.value,
                'symbol'            : item.symbol.value,
                'unit'              : item.unit.value,
                'address'           : meta.deployment[item.symbol][item.unit][0],
                'decimals'          : meta.decimals[item.symbol],
                'native'            : util.get_symbol_type(item.symbol) == SymbolType.NATIVE,
                'deposits_total'    : deposited,
                'withdrawals_total' : withdrawn,
                'anonymity_set'     : deposited,
                'last_update_sec'   : tornado.last_update_sec if tornado else None,
                'state'             : state,
                'sync_state'        : phase,
                'ready'             : ready,
                'message'           : message,
                'activity'          : ACTIVITY_MESSAGES.get(activity, ''),
                'sync_activity'     : ACTIVITY_MESSAGES.get(sync.get('activity'), ''),
                'operation_progress': item.progress if working else None,
            })
        return {
            'type'                    : 'status',
            'ready'                   : not self.stopping and bool(rows) and all(row['ready'] for row in rows),
            'stopping'                : self.stopping,
            'instances'               : rows,
            'relayer_fee_rate'        : config.RELAYER_FEE_RATE,
        }

    def dispatch(self, method: str, params: dict[str, Any], cancelled: threading.Event | None = None,
                 progress: Callable[[str], None] | None = None) -> dict[str, Any]:
        if method == 'status':
            return self.status()

        def check_cancelled() -> None:
            if self.stopping:
                raise ValueError('Backend is shutting down. Operations are locked.')
            if cancelled is not None and cancelled.is_set():
                raise ValueError('Request was cancelled.')

        fields: dict[str, tuple[str, ...]] = {
            'create_note'   : ('instance',),
            'approve'       : ('instance', 'account'),
            'deposit'       : ('instance', 'account', 'note'),
            'withdraw'      : ('note', 'recipient', 'account'),
            'relay_withdraw': ('note', 'recipient', 'relayer'),
            'note_status'   : ('note',),
            'receipt'       : ('instance', 'hash'),
        }
        if method not in fields:
            raise ValueError('Unknown method.')
        if not isinstance(params, dict):
            raise ValueError('params must be an object.')
        for field in fields[method]:
            if not isinstance(params.get(field), str) or not params[field].strip():
                raise ValueError(f'Missing or invalid field: {field}.')
        check_cancelled()
        name: str | None = params.get('instance')
        if 'note' in fields[method]:
            parsed: tuple[ChainID, Symbol, TornadoUnit, Note] | None = Note.from_text(params['note'])
            if parsed is None:
                raise ValueError('Invalid Tornado note.')
            chain, symbol, unit, note = parsed
            note_instance: str = f'{chain_to_string(chain)}-{symbol.value}-{unit.value}'
            if method == 'deposit' and name != note_instance:
                raise ValueError('Note belongs to a different instance.')
            name = note_instance
        addresses: dict[str, ChecksumAddress] = {}
        for field in ('account', 'recipient'):
            if field in fields[method]:
                if not Web3.is_address(params[field]):
                    raise ValueError(f'Invalid {field} address.')
                addresses[field] = Web3.to_checksum_address(params[field])
        item: Instance | None = self.instances.get(name)
        if item is None or (method != 'create_note' and item.tornado is None):
            raise ValueError('Instance is unavailable.')
        if not item.lock.acquire(blocking=False):
            raise ValueError('Instance is busy. Please wait for the current operation.')

        def report(message: str) -> None:
            if item.progress_callback is not report:
                return
            check_cancelled()
            item.progress = message
            if progress:
                progress(message)

        try:
            item.progress_callback = report
            check_cancelled()
            if method == 'create_note':
                return self._create_note(item, check_cancelled, report)
            if method == 'receipt':
                return self._receipt(item, params['hash'], check_cancelled, report)
            if method == 'note_status':
                return self._note_status(item, name, note, check_cancelled, report)
            if method in ('withdraw', 'relay_withdraw'):
                self._prepare_tree(item, cancelled, check_cancelled, report)
            if method == 'approve':
                return self._approve(item, addresses['account'], check_cancelled, report)
            if method == 'deposit':
                return self._deposit(item, note, addresses['account'], check_cancelled, report)
            if method == 'withdraw':
                return self._withdraw(item, note, addresses['account'], addresses['recipient'], check_cancelled, report)
            return self._relay_withdraw(item, note, addresses['recipient'], params['relayer'], cancelled, check_cancelled, report)
        finally:
            item.progress_callback = None
            item.progress = None
            item.activity = None
            item.lock.release()

    def _create_note(self, item: Instance, check_cancelled: Callable[[], None],
                     report: Callable[[str], None]) -> dict[str, Any]:
        item.activity = 'creating_note'
        report(ACTIVITY_MESSAGES['creating_note'])
        note: Note = Note.create()
        check_cancelled()
        return {
            'note'   : Note.to_text(item.chain, item.symbol, item.unit, note),
            'invoice': Note.to_invoice(item.chain, item.symbol, item.unit, note),
        }

    def _receipt(self, item: Instance, tx_hash: str, check_cancelled: Callable[[], None],
                 report: Callable[[str], None]) -> dict[str, Any]:
        item.activity = 'checking_tx'
        report(ACTIVITY_MESSAGES['checking_tx'])
        if not re.fullmatch(r'0x[0-9a-fA-F]{64}', tx_hash):
            raise ValueError('Invalid transaction hash.')
        tornado: Tornado = item.tornado
        result = tornado.connection.transaction_receipt(HexBytes(tx_hash))
        check_cancelled()
        if rpc.is_error(result):
            if result.code == rpc.ErrorCode.TX_HASH_NOT_FOUND:
                return {'status': 'pending'}
            raise RuntimeError(f'Receipt RPC error: {result.code.value}.')
        return {'status': 'confirmed' if result['status'] == 1 else 'failed'}

    def _note_status(self, item: Instance, name: str, note: Note, check_cancelled: Callable[[], None],
                     report: Callable[[str], None]) -> dict[str, Any]:
        item.activity = 'checking_note'
        report(ACTIVITY_MESSAGES['checking_note'])
        tornado: Tornado = item.tornado
        deposited = tornado.note_deposited(note.commitment)
        spent = tornado.note_withdrawn(note.nullifier_hash)
        if deposited is None or spent is None:
            raise RuntimeError('Could not query note status from RPC.')
        age = tornado.note_age(note.commitment) if deposited else None
        check_cancelled()
        return {
            'instance'         : name,
            'deposited'        : deposited,
            'spent'            : spent,
            'deposits_after'   : age[0] if age else 0,
            'withdrawals_after': age[1] if age else 0,
        }

    def _prepare_tree(self, item: Instance, cancelled: threading.Event | None,
                      check_cancelled: Callable[[], None], report: Callable[[str], None]) -> None:
        tornado: Tornado = item.tornado

        def wait_sync(refresh: bool = False) -> None:
            item.activity = 'syncing'
            report(ACTIVITY_MESSAGES['syncing'])
            if not tornado.poller.wait_sync(cancel=lambda: self.stopping or (cancelled is not None and cancelled.is_set()),
                                           refresh=refresh):
                check_cancelled()
                raise RuntimeError('Synchronization has stopped. Restart the instance and retry.')
            check_cancelled()

        # Check a new head once; reuse it after initializing the tree.
        wait_sync(refresh=True)
        item.activity = 'building_tree'
        report(ACTIVITY_MESSAGES['building_tree'])
        if not tornado.init(sync_only=False):
            raise RuntimeError('Could not initialize the withdrawal tree. Check backend logs.')
        wait_sync()

    def _approve(self, item: Instance, account: ChecksumAddress, check_cancelled: Callable[[], None],
                 report: Callable[[str], None]) -> dict[str, Any]:
        item.activity = 'approving'
        report(ACTIVITY_MESSAGES['approving'])
        if util.get_symbol_type(item.symbol) != SymbolType.ERC20:
            raise ValueError('Native currency does not require approval.')
        tornado: Tornado = item.tornado
        result = tornado.approve_tx(account)
        check_cancelled()
        return encode_wallet_format_tx(result)

    def _deposit(self, item: Instance, note: Note, account: ChecksumAddress, check_cancelled: Callable[[], None],
                 report: Callable[[str], None]) -> dict[str, Any]:
        item.activity = 'depositing'
        report(ACTIVITY_MESSAGES['depositing'])
        tornado: Tornado = item.tornado
        result = tornado.deposit_tx(note.commitment, account)
        check_cancelled()
        return encode_wallet_format_tx(result)

    def _withdraw(self, item: Instance, note: Note, account: ChecksumAddress, recipient: ChecksumAddress,
                  check_cancelled: Callable[[], None], report: Callable[[str], None]) -> dict[str, Any]:
        item.activity = 'proving'
        report(ACTIVITY_MESSAGES['proving'])
        tornado: Tornado = item.tornado
        proof = tornado.prepare_withdraw(note, recipient)
        check_cancelled()
        if proof is None:
            raise RuntimeError('Could not prepare withdrawal. Check note status, synchronization and backend logs.')
        result = tornado.withdraw_tx(note, account, recipient, *proof)
        check_cancelled()
        return encode_wallet_format_tx(result)

    def _relay_withdraw(self, item: Instance, note: Note, recipient: ChecksumAddress, relayer: str,
                        cancelled: threading.Event | None, check_cancelled: Callable[[], None],
                        report: Callable[[str], None]) -> dict[str, Any]:
        item.activity = 'relaying'
        report('Checking relayer status.')
        tornado: Tornado = item.tornado
        tx_hash = tornado.withdraw(
            note, recipient, relayer,
            can_submit=lambda: not self.stopping and not (cancelled is not None and cancelled.is_set()),
        )
        if tx_hash is None:
            check_cancelled()
            raise RuntimeError('Relayer withdrawal failed. Check backend logs.')
        return {'hash': HexBytes(tx_hash).to_0x_hex()}

    async def close(self) -> None:
        self.stopping = True

        def close_instance(item: Instance) -> None:
            with item.lock:
                if item.tornado:
                    item.tornado.un_init()

        errors: list[Any] = await asyncio.gather(*(asyncio.to_thread(close_instance, item) for item in self.instances.values()),
                                                return_exceptions=True)
        errors += await asyncio.gather(*(asyncio.to_thread(connection.stop) for connection in self.connections.values()),
                                       return_exceptions=True)
        for error in errors:
            if isinstance(error, Exception):
                log.error('WebUI', f'Shutdown failed: {type(error).__name__}')


async def handle_client(socket: ServerConnection, backend: Backend) -> None:
    cancelled: threading.Event = threading.Event()

    async def dispatch_request(request_id: str | int, method: str, params: Any) -> dict[str, Any]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        active: bool = True

        def progress(message: str) -> None:
            if active and not cancelled.is_set():
                loop.call_soon_threadsafe(queue.put_nowait, message)

        async def publish_progress() -> None:
            while (message := await queue.get()) is not None:
                await socket.send(json.dumps({'id': request_id, 'type': 'progress', 'message': message}))

        publisher: asyncio.Task[None] = asyncio.create_task(publish_progress())
        try:
            return await asyncio.to_thread(backend.dispatch, method, params, cancelled, progress)
        finally:
            active = False
            queue.put_nowait(None)
            await publisher

    async def publish() -> None:
        last_log_id: int  = 0
        reset_logs : bool = True
        while True:
            await socket.send(json.dumps(backend.status()))
            entries: list[dict] = log.get_recent(last_log_id)
            if entries or reset_logs:
                await socket.send(json.dumps({'type': 'logs', 'reset': reset_logs, 'entries': entries}))
                if entries:
                    last_log_id = entries[-1]['id']
                reset_logs = False
            await asyncio.sleep(1)

    async def respond() -> None:
        async for raw in socket:
            request_id: str | int | None = None
            try:
                request: Any = json.loads(raw)
                if not isinstance(request, dict):
                    raise ValueError('Request must be an object.')
                request_id = request.get('id')
                if type(request_id) not in (int, str) or len(str(request_id)) > 128:
                    request_id = None
                    raise ValueError('Request requires a string or integer id.')
                method: str | None = request.get('method')
                if not isinstance(method, str):
                    raise ValueError('Request requires a method.')
                result  : dict[str, Any] = await dispatch_request(request_id, method, request.get('params', {}))
                response: dict[str, Any] = {'id': request_id, 'result': result}
            except (ValueError, RuntimeError) as error:
                response = {'id': request_id, 'error': str(error)}
            except Exception:
                response = {'id': request_id, 'error': 'Operation failed. Check backend configuration and logs.'}
            await socket.send(json.dumps(response))

    tasks: list[asyncio.Task] = [asyncio.create_task(publish()), asyncio.create_task(respond()), asyncio.create_task(socket.wait_closed())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except ConnectionClosed:
        pass
    finally:
        cancelled.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


class HTTPHandler(SimpleHTTPRequestHandler):

    def log_message(self, format: str, *args: Any) -> None:
        log.info('HTTP', f'{self.address_string()} {format % args}'.translate(self._control_char_table))

    def log_error(self, format: str, *args: Any) -> None:
        log.error('HTTP', f'{self.address_string()} {format % args}'.translate(self._control_char_table))


async def run() -> None:
    backend: Backend                   = Backend(config.WEBUI_CHAINS)
    http   : ThreadingHTTPServer | None = None
    stop   : asyncio.Event             = asyncio.Event()
    loop   : asyncio.AbstractEventLoop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows uses asyncio.run's KeyboardInterrupt handling.
            pass
    startup: asyncio.Task[None] | None = None
    try:
        async with serve(partial(handle_client, backend=backend), config.WEBUI_HOST, config.WEBUI_WS_PORT, max_size=16_384):
            if config.WEBUI_SERVE_UI:
                handler = partial(HTTPHandler, directory=str(Path(__file__).parent / 'www'))
                http = ThreadingHTTPServer((config.WEBUI_HOST, config.WEBUI_PORT), handler)
                threading.Thread(target=http.serve_forever, daemon=True).start()
                ws = quote(f'ws://{config.WEBUI_HOST}:{config.WEBUI_WS_PORT}', safe='')
                print(f'Web UI: http://{config.WEBUI_HOST}:{config.WEBUI_PORT}/?ws={ws}', flush=True)
            print(f'WebSocket: ws://{config.WEBUI_HOST}:{config.WEBUI_WS_PORT}', flush=True)
            startup = asyncio.create_task(backend.start())
            await stop.wait()
    finally:
        if http:
            await asyncio.to_thread(http.shutdown)
            http.server_close()
        try:
            if startup:
                await startup
        finally:
            await backend.close()


if __name__ == '__main__':
    log.init(config.LOG_DIR, 'webui')
    log.set_level(log.Level.INFO)
    log.set_console_enable(True)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    finally:
        log.un_init()
