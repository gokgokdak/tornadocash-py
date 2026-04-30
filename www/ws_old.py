from __future__ import annotations

import asyncio
import json
import threading
import uuid
from typing import Any, Callable

from fastapi import WebSocket, WebSocketDisconnect
from hexbytes import HexBytes

from components import core, rpc, util
from components.blockchain import EventDeposit, EventWithdraw
from components.mytype import ChainID, Symbol, TornadoUnit, chain_to_string, string_to_chain
import config


InstanceKey = tuple[ChainID, Symbol, TornadoUnit]


class _ClientSession(object):

    def __init__(self,
                 websocket: WebSocket,
                 key: InstanceKey,
                 operation: str,
                 queue_size: int) -> None:
        self.id: str = uuid.uuid4().hex
        self.websocket: WebSocket = websocket
        self.key: InstanceKey = key
        self.operation: str = operation
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=queue_size)

    async def send(self, message: dict[str, Any]) -> None:
        await self.queue.put(message)

    def notify(self, message: dict[str, Any]) -> None:
        def _put() -> None:
            if self.queue.full():
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                self.queue.put_nowait(message)
            except asyncio.QueueFull:
                pass

        try:
            self.loop.call_soon_threadsafe(_put)
        except RuntimeError:
            pass


class Server(core.Tornado.Handler):
    """
    WebSocket server facade for Tornado instances.

    Register routes with:
        server = Server()
        server.register(app)

    Client paths are instance scoped:
        /{chain}/{symbol}/{unit}
        /{chain}/{symbol}/{unit}/{operation}

    The URL selects the instance and operation. Client messages are JSON objects:
        {"id": "client-request-id", "params": {...}}

    Results are returned asynchronously as callback messages, while Tornado
    handler events are pushed proactively as event messages.
    """

    DEFAULT_OPERATION: str = 'subscribe'

    def __init__(self, client_queue_size: int = 1024, max_start_workers: int = 16) -> None:
        self.instances: dict[ChainID, dict[Symbol, dict[TornadoUnit, core.Tornado]]] = {}
        self.connections: dict[ChainID, rpc.Connection] = {}
        self.states: dict[InstanceKey, dict[str, Any]] = {}

        self._clients: dict[InstanceKey, set[_ClientSession]] = {}
        self._clients_lock: threading.RLock = threading.RLock()
        self._state_lock: threading.RLock = threading.RLock()
        self._lifecycle_lock: threading.RLock = threading.RLock()
        self._initialized: bool = False
        self._started: bool = False
        self._start_threads: dict[InstanceKey, threading.Thread] = {}
        self._stop_event: threading.Event = threading.Event()
        self._start_semaphore: threading.Semaphore = threading.Semaphore(max(1, max_start_workers))
        self._client_queue_size: int = client_queue_size

        self._operations: dict[str, Callable[[core.Tornado, dict[str, Any]], Any]] = {
            'subscribe': self._op_subscribe,
            'events': self._op_subscribe,
            'metadata': self._op_metadata,
        }

    def register(self, app: Any, prefix: str = '') -> None:
        prefix = prefix.strip('/')
        route_prefix: str = f'/{prefix}' if prefix else ''
        app.add_api_websocket_route(f'{route_prefix}/{{chain}}/{{symbol}}/{{unit}}', self.websocket)
        app.add_api_websocket_route(f'{route_prefix}/{{chain}}/{{symbol}}/{{unit}}/{{operation:path}}', self.websocket)

    def mount(self, app: Any, prefix: str = '') -> None:
        self.register(app, prefix)

    def init(self) -> bool:
        with self._lifecycle_lock:
            if self._initialized:
                return True

            try:
                metadata = util.load_metadata()
                for chain, meta in metadata.items():
                    connection = rpc.Connection(chain, config.RPC_URLS[chain])
                    if not connection.start():
                        raise RuntimeError(f'Failed to start RPC connection for {chain_to_string(chain)}')
                    self.connections[chain] = connection
                    self.instances[chain] = {}

                    for symbol, deployments in meta.deployment.items():
                        self.instances[chain][symbol] = {}
                        for unit in deployments.keys():
                            tornado = core.Tornado(chain, symbol, unit, connection)
                            tornado.add_handler(self)
                            key = (chain, symbol, unit)
                            self.instances[chain][symbol][unit] = tornado
                            self.states[key] = self._base_state(key, initialized=False, started=False)

                self._initialized = True
                return True
            except BaseException:
                self._destroy_instances()
                raise

    def un_init(self) -> None:
        with self._lifecycle_lock:
            if not self._initialized:
                return
            self.stop()
            self._destroy_instances()
            self._initialized = False

    def start(self) -> bool:
        with self._lifecycle_lock:
            if not self._initialized:
                raise RuntimeError('Server.start() called before Server.init()')
            if self._started:
                return True

            self._stop_event.clear()
            self._started = True
            for key, tornado in self._iter_instances():
                current = self._start_threads.get(key)
                if current is not None and current.is_alive():
                    continue
                self._set_state(
                    key,
                    initialized=getattr(tornado, 'initialized', False),
                    starting=True,
                    started=self._is_tornado_started(tornado),
                    start_error=None,
                )
                self._broadcast(key, 'instance_starting', self._state_snapshot(key))
                thread = threading.Thread(
                    target=self._start_instance,
                    args=(key, tornado),
                    name=f'tornado-start-{self._instance_id(key)}',
                    daemon=True,
                )
                self._start_threads[key] = thread
                thread.start()
            return True

    def stop(self) -> None:
        with self._lifecycle_lock:
            if not self._initialized:
                return

            self._stop_event.set()
            for key, tornado in self._iter_instances():
                self._stop_tornado(tornado)
                self._set_state(
                    key,
                    initialized=getattr(tornado, 'initialized', False),
                    starting=False,
                    started=False,
                )
                self._broadcast(key, 'instance_stopped', self._state_snapshot(key))
            self._started = False

    async def websocket(self,
                        websocket: WebSocket,
                        chain: str,
                        symbol: str,
                        unit: str,
                        operation: str = DEFAULT_OPERATION) -> None:
        await websocket.accept()
        try:
            key, tornado = self._select_instance(chain, symbol, unit)
        except ValueError as e:
            await websocket.send_json(self._error_callback(None, operation, 'invalid_instance', str(e)))
            await websocket.close(code=1008)
            return

        normalized_operation = self._normalize_operation(operation)
        session = _ClientSession(websocket, key, normalized_operation, self._client_queue_size)
        self._add_client(session)

        sender = asyncio.create_task(self._sender(session))
        try:
            await session.send(self._event_message(key, 'connected', {'client_id': session.id}))
            await session.send(self._event_message(key, 'state', self._state_snapshot(key)))

            await self._receiver(session, tornado)
        except WebSocketDisconnect:
            pass
        finally:
            self._remove_client(session)
            sender.cancel()
            try:
                await sender
            except asyncio.CancelledError:
                pass

    def on_blockchain_first_catchup(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit) -> None:
        key = (chain, symbol, unit)
        self._set_state(key, catchup=True)
        self._broadcast(key, 'blockchain_first_catchup', self._state_snapshot(key))

    def on_blockchain_sync(self,
                           chain: ChainID,
                           symbol: Symbol,
                           unit: TornadoUnit,
                           block_from: int,
                           block_to: int,
                           deposits: list[EventDeposit],
                           withdrawals: list[EventWithdraw]) -> None:
        key = (chain, symbol, unit)
        payload = {
            'block_from': block_from,
            'block_to': block_to,
            'deposits': [self._deposit_to_json(e) for e in deposits],
            'withdrawals': [self._withdraw_to_json(e) for e in withdrawals],
        }
        self._set_state(key, last_sync=payload)
        self._broadcast(key, 'blockchain_sync', payload)

    def on_blockchain_latest_block(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit, block_number: int) -> None:
        key = (chain, symbol, unit)
        self._set_state(key, latest_block=block_number)
        self._broadcast(key, 'blockchain_latest_block', {'block_number': block_number})

    def on_merkle_tree_rebuilt_progress(self,
                                        chain: ChainID,
                                        symbol: Symbol,
                                        unit: TornadoUnit,
                                        numerator: int,
                                        denominator: int) -> None:
        key = (chain, symbol, unit)
        payload = {
            'numerator': numerator,
            'denominator': denominator,
            'progress': 0 if denominator == 0 else numerator / denominator,
        }
        self._set_state(key, merkle_tree_rebuilt_progress=payload)
        self._broadcast(key, 'merkle_tree_rebuilt_progress', payload)

    async def _receiver(self, session: _ClientSession, tornado: core.Tornado) -> None:
        while True:
            try:
                raw = await session.websocket.receive_text()
            except WebSocketDisconnect:
                raise

            request_id: Any = None
            try:
                request = json.loads(raw)
                if not isinstance(request, dict):
                    raise ValueError('Request must be a JSON object')
                request_id = request.get('id', request.get('request_id', request.get('callback_id')))
                params = request.get('params', {})
                if params is None:
                    params = {}
                if not isinstance(params, dict):
                    raise ValueError('Request params must be a JSON object')
                await self._dispatch(session, tornado, request_id, params)
            except ValueError as e:
                await session.send(self._error_callback(request_id, session.operation, 'bad_request', str(e)))
            except BaseException as e:
                await session.send(self._error_callback(request_id, session.operation, 'internal_error', str(e)))

    async def _sender(self, session: _ClientSession) -> None:
        while True:
            message = await session.queue.get()
            await session.websocket.send_json(message)

    async def _dispatch(self,
                        session: _ClientSession,
                        tornado: core.Tornado,
                        request_id: Any,
                        params: dict[str, Any]) -> None:
        operation = session.operation
        fn = self._operations.get(operation)
        if fn is None:
            await session.send(self._error_callback(request_id, operation, 'unknown_operation', f'Unsupported operation: {operation}'))
            return

        try:
            result = await asyncio.to_thread(fn, tornado, params)
            await session.send({
                'type': 'callback',
                'id': request_id,
                'operation': operation,
                'ok': True,
                'result': self._json_value(result),
            })
        except ValueError as e:
            await session.send(self._error_callback(request_id, operation, 'bad_request', str(e)))
        except BaseException as e:
            await session.send(self._error_callback(request_id, operation, 'internal_error', str(e)))

    def _op_subscribe(self, _tornado: core.Tornado, _params: dict[str, Any]) -> dict[str, bool]:
        return {'subscribed': True}

    def _op_metadata(self, tornado: core.Tornado, _params: dict[str, Any]) -> dict[str, Any]:
        deployed_address, deployed_block = tornado.meta.deployment[tornado.symbol][tornado.unit]
        return {
            'chain': chain_to_string(tornado.chain),
            'chain_id': tornado.chain.value,
            'symbol': tornado.symbol.value,
            'unit': tornado.unit.value,
            'proxy_address': tornado.proxy_address,
            'deployment_address': deployed_address,
            'deployed_block': deployed_block,
            'decimals': tornado.meta.decimals[tornado.symbol],
        }

    def _select_instance(self, chain_text: str, symbol_text: str, unit_text: str) -> tuple[InstanceKey, core.Tornado]:
        if not self._initialized:
            raise ValueError('Server is not initialized')
        try:
            chain = string_to_chain(chain_text)
            symbol = Symbol(symbol_text.lower())
            unit = TornadoUnit(unit_text)
        except ValueError as e:
            raise ValueError(f'Invalid instance path: {chain_text}/{symbol_text}/{unit_text}') from e
        try:
            tornado = self.instances[chain][symbol][unit]
        except KeyError as e:
            raise ValueError(f'Instance not found: {chain_text}/{symbol_text}/{unit_text}') from e
        return (chain, symbol, unit), tornado

    def _normalize_operation(self, operation: str | None) -> str:
        operation = (operation or self.DEFAULT_OPERATION).strip('/')
        return operation or self.DEFAULT_OPERATION

    def _start_instance(self, key: InstanceKey, tornado: core.Tornado) -> None:
        ok = False
        error: str | None = None
        acquired = False
        try:
            while not self._stop_event.is_set():
                acquired = self._start_semaphore.acquire(timeout=0.2)
                if acquired:
                    break
            if acquired and not self._stop_event.is_set():
                ok = self._start_tornado(tornado)
        except BaseException as e:
            error = str(e)
        finally:
            if acquired:
                self._start_semaphore.release()

        with self._lifecycle_lock:
            self._start_threads.pop(key, None)
            if not self._initialized:
                return
            if self._stop_event.is_set():
                self._stop_tornado(tornado)
                self._set_state(
                    key,
                    initialized=getattr(tornado, 'initialized', False),
                    starting=False,
                    started=False,
                )
                self._broadcast(key, 'instance_stopped', self._state_snapshot(key))
                return
            if ok:
                self._set_state(key, initialized=True, starting=False, started=True, start_error=None)
                self._broadcast(key, 'instance_started', self._state_snapshot(key))
                return
            self._set_state(
                key,
                initialized=getattr(tornado, 'initialized', False),
                starting=False,
                started=False,
                start_error=error or 'Tornado start returned False',
            )
            self._broadcast(key, 'instance_start_failed', self._state_snapshot(key))

    def _start_tornado(self, tornado: core.Tornado) -> bool:
        if self._is_tornado_started(tornado):
            return True

        if self._stop_event.is_set():
            return False

        # Newer Tornado implementations may expose start(sync_only=False);
        # the current one uses init(sync_only=False) followed by start_sync().
        start = getattr(tornado, 'start', None)
        if callable(start):
            try:
                result = start(sync_only=False)
            except TypeError:
                try:
                    result = start(False)
                except TypeError:
                    tornado.sync_only = False
                    result = start()
            return True if result is None else bool(result)

        if getattr(tornado, 'initialized', False) and getattr(tornado, 'sync_only', False):
            tornado.un_init()
        if not getattr(tornado, 'initialized', False):
            if not tornado.init(sync_only=False):
                return False
        if self._stop_event.is_set():
            return False
        return tornado.start_sync()

    def _stop_tornado(self, tornado: core.Tornado) -> None:
        stop = getattr(tornado, 'stop', None)
        if callable(stop):
            stop()
            return
        if self._is_tornado_started(tornado):
            tornado.stop_sync()

    def _is_tornado_started(self, tornado: core.Tornado) -> bool:
        is_started = getattr(tornado, 'is_started', None)
        if callable(is_started):
            return bool(is_started())
        poller = getattr(tornado, 'poller', None)
        return bool(poller is not None and poller.is_started())

    def _destroy_instances(self) -> None:
        for _, tornado in self._iter_instances():
            try:
                tornado.un_init()
            finally:
                tornado.remove_all_handlers()
        for connection in self.connections.values():
            connection.stop()
        self.instances.clear()
        self.connections.clear()
        with self._state_lock:
            self.states.clear()
        self._start_threads.clear()
        self._stop_event.clear()
        self._started = False

    def _iter_instances(self) -> list[tuple[InstanceKey, core.Tornado]]:
        items: list[tuple[InstanceKey, core.Tornado]] = []
        for chain, by_symbol in self.instances.items():
            for symbol, by_unit in by_symbol.items():
                for unit, tornado in by_unit.items():
                    items.append(((chain, symbol, unit), tornado))
        return items

    def _add_client(self, session: _ClientSession) -> None:
        with self._clients_lock:
            if session.key not in self._clients:
                self._clients[session.key] = set()
            self._clients[session.key].add(session)

    def _remove_client(self, session: _ClientSession) -> None:
        with self._clients_lock:
            clients = self._clients.get(session.key)
            if clients is None:
                return
            clients.discard(session)
            if len(clients) == 0:
                del self._clients[session.key]

    def _broadcast(self, key: InstanceKey, event: str, data: dict[str, Any]) -> None:
        message = self._event_message(key, event, data)
        with self._clients_lock:
            clients = list(self._clients.get(key, set()))
        for client in clients:
            client.notify(message)

    def _set_state(self, key: InstanceKey, **updates: Any) -> None:
        with self._state_lock:
            state = self.states.setdefault(key, self._base_state(key))
            state.update({k: self._json_value(v) for k, v in updates.items()})

    def _state_snapshot(self, key: InstanceKey) -> dict[str, Any]:
        with self._state_lock:
            return dict(self.states.get(key, self._base_state(key)))

    def _base_state(self,
                    key: InstanceKey,
                    initialized: bool | None = None,
                    started: bool | None = None) -> dict[str, Any]:
        chain, symbol, unit = key
        return {
            'chain': chain_to_string(chain),
            'chain_id': chain.value,
            'symbol': symbol.value,
            'unit': unit.value,
            'initialized': initialized,
            'starting': False,
            'started': started,
            'start_error': None,
            'catchup': False,
            'latest_block': None,
            'last_sync': None,
            'merkle_tree_rebuilt_progress': None,
        }

    def _event_message(self, key: InstanceKey, event: str, data: dict[str, Any]) -> dict[str, Any]:
        chain, symbol, unit = key
        return {
            'type': 'event',
            'event': event,
            'instance': {
                'chain': chain_to_string(chain),
                'chain_id': chain.value,
                'symbol': symbol.value,
                'unit': unit.value,
            },
            'data': self._json_value(data),
        }

    def _error_callback(self, request_id: Any, operation: str, code: str, message: str) -> dict[str, Any]:
        return {
            'type': 'callback',
            'id': request_id,
            'operation': operation,
            'ok': False,
            'error': {
                'code': code,
                'message': message,
            },
        }

    def _instance_id(self, key: InstanceKey) -> str:
        chain, symbol, unit = key
        return f'{chain_to_string(chain)}/{symbol.value}/{unit.value}'

    def _deposit_to_json(self, event: EventDeposit) -> dict[str, Any]:
        return {
            'timestamp': event.timestamp,
            'blk_num': event.blk_num,
            'tx_hash': self._json_value(event.tx_hash),
            'commitment': self._json_value(event.commitment),
            'leaf_index': event.leaf_index,
        }

    def _withdraw_to_json(self, event: EventWithdraw) -> dict[str, Any]:
        return {
            'blk_num': event.blk_num,
            'tx_hash': self._json_value(event.tx_hash),
            'nullifier_hash': self._json_value(event.nullifier_hash),
            'recipient': event.recipient,
            'fee': int(event.fee) if event.fee is not None else None,
        }

    def _json_value(self, value: Any) -> Any:
        if isinstance(value, HexBytes):
            return value.to_0x_hex()
        if isinstance(value, bytes):
            return '0x' + value.hex()
        if isinstance(value, (ChainID, Symbol, TornadoUnit)):
            if isinstance(value, ChainID):
                return chain_to_string(value)
            return value.value
        if isinstance(value, list):
            return [self._json_value(v) for v in value]
        if isinstance(value, tuple):
            return [self._json_value(v) for v in value]
        if isinstance(value, dict):
            return {str(self._json_value(k)): self._json_value(v) for k, v in value.items()}
        return value
