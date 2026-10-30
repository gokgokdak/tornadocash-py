import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

from hexbytes import HexBytes
import pytest
from websockets.asyncio.client import ClientConnection, connect
from websockets.asyncio.server import ServerConnection, serve

import webui
from components.mytype import ChainID, Second, Symbol, TornadoUnit


INSTANCE = 'ethereum-dai-1'
ACCOUNT = '0x' + '11' * 20
RECIPIENT = '0x' + '22' * 20
HASH = '0x' + '33' * 32
PARAMS = {'instance': INSTANCE, 'account': ACCOUNT, 'note': 'note',
          'recipient': RECIPIENT, 'relayer': 'https://relayer.example', 'hash': HASH}


def test_http_logs_access_as_info_and_failures_as_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                       capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / 'index.html').write_text('webui')
    info, error = Mock(), Mock()
    monkeypatch.setattr(webui.log, 'info', info)
    monkeypatch.setattr(webui.log, 'error', error)
    with webui.ThreadingHTTPServer(('127.0.0.1', 0), partial(webui.HTTPHandler, directory=str(tmp_path))) as server:
        worker: threading.Thread = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        client: HTTPConnection = HTTPConnection(*server.server_address, timeout=2)
        try:
            client.request('GET', '/')
            response = client.getresponse()
            modified: str | None = response.getheader('Last-Modified')
            assert response.status == 200 and response.read() == b'webui'
            assert modified is not None
            client.request('GET', '/', headers={'If-Modified-Since': modified})
            response = client.getresponse()
            assert response.status == 304 and response.read() == b''
            assert info.call_count == 2
            error.assert_not_called()
            for code, call in zip(('200', '304'), info.call_args_list):
                assert call.args[0] == 'HTTP' and f' {code} ' in call.args[1]
                assert '127.0.0.1' in call.args[1]
            client.request('GET', '/missing')
            response = client.getresponse()
            assert response.status == 404
            response.read()
            assert error.call_args.args[0] == 'HTTP'
            assert '127.0.0.1' in error.call_args.args[1] and '404' in error.call_args.args[1]
        finally:
            client.close()
            server.shutdown()
            worker.join(2)
    assert capsys.readouterr().err == ''


@pytest.mark.parametrize(('method', 'level'), [('log_message', 'info'), ('log_error', 'error')])
def test_http_log_escapes_control_characters(monkeypatch: pytest.MonkeyPatch, method: str, level: str) -> None:
    logged: Mock = Mock()
    monkeypatch.setattr(webui.log, level, logged)
    handler: webui.HTTPHandler = object.__new__(webui.HTTPHandler)
    handler.client_address = ('127.0.0.1', 12345)
    getattr(handler, method)('path %s', '/\x1b[31m\n')
    assert logged.call_args.args == ('HTTP', r'127.0.0.1 path /\x1b[31m\x0a')


class FakePoller:

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.wait_sync: Mock = Mock(return_value=True)
        self.state: dict[str, Any] = {
            'running': True, 'start_block': 10, 'synced_block': 99, 'latest_block': 99,
            'remaining_blocks': 0, 'progress': 1, 'synchronized': True,
            'last_check_sec': time.time(), 'error': None, 'deposits': 2, 'withdrawals': 1,
        }

    def status(self) -> dict[str, Any]:
        state: dict[str, Any] = self.state.copy()
        if not state['running']:
            phase: str = 'error' if state['error'] else 'stopped'
        elif state['error']:
            phase = 'retrying'
        elif state['synchronized']:
            phase = 'ready'
        else:
            phase = 'connecting' if state['latest_block'] is None else 'syncing'
        state.setdefault('phase', phase)
        state.setdefault('activity', 'idle' if phase == 'ready' else 'fetching_events')
        if state['latest_block'] is None or state['error']:
            state['progress'] = None
        return state


class FakeTornado:

    def __init__(self) -> None:
        self.poller          : FakePoller      = FakePoller()
        self.last_update_sec : Second | None   = None
        self.mutex           : threading.Lock  = threading.Lock()
        self.init            : Mock            = Mock(return_value=True)
        self.un_init         : Mock            = Mock()
        self.connection      : SimpleNamespace = SimpleNamespace(transaction_receipt=Mock(return_value={'status': 1}))
        self.note_deposited  : Mock            = Mock(return_value=True)
        self.note_withdrawn  : Mock            = Mock(return_value=False)
        self.note_age        : Mock            = Mock(return_value=(7, 3))
        self.prepare_withdraw: Mock            = Mock(return_value=(object(), {'proof': 'proof'}))
        self.withdraw        : Mock            = Mock(return_value=HexBytes(HASH))
        for method in ('approve_tx', 'deposit_tx', 'withdraw_tx'):
            setattr(self, method, Mock(return_value={'from': ACCOUNT}))


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> webui.Backend:
    meta = SimpleNamespace(deployment={Symbol.DAI: {
        TornadoUnit.UNIT_1: (ACCOUNT, 10), TornadoUnit.UNIT_10: (RECIPIENT, 10),
    }}, decimals={Symbol.DAI: 18})
    monkeypatch.setattr(webui.util, 'load_metadata', lambda: {ChainID.ETHEREUM: meta})
    monkeypatch.setattr(webui.log, 'get_recent', lambda after_id=0: [])
    backend = webui.Backend({ChainID.ETHEREUM})
    for item in backend.instances.values():
        item.totals = (100, 30)
        item.tornado = FakeTornado()
    return backend


@pytest.fixture
def waiting_poller(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch) -> tuple[webui.EventPoller, threading.Event]:
    poller: webui.EventPoller = webui.EventPoller(ChainID.ETHEREUM, SimpleNamespace())
    poller.off, poller.current, poller.latest_block = False, 99, 99
    poller.last_check_sec = time.time()
    poller.activity = webui.EventPoller.Activity.FETCHING_EVENTS
    backend.instances[INSTANCE].tornado.poller = poller
    entered: threading.Event = threading.Event()
    wait = poller.cond.wait

    def waiting(timeout: float | None = None) -> bool:
        entered.set()
        return wait(timeout)

    monkeypatch.setattr(poller.cond, 'wait', waiting)
    return poller, entered


@pytest.fixture
def operations(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    note      : SimpleNamespace = SimpleNamespace(commitment=HexBytes('0x01'), nullifier_hash=HexBytes('0x02'))
    parse_note: Mock            = Mock(return_value=(ChainID.ETHEREUM, Symbol.DAI, TornadoUnit.UNIT_1, note))
    monkeypatch.setattr(webui.Note, 'from_text', parse_note)
    tornado = backend.instances[INSTANCE].tornado
    methods = {method: getattr(tornado, method) for method in (
        'approve_tx', 'deposit_tx', 'prepare_withdraw', 'withdraw_tx', 'withdraw',
    )}
    methods['parse_note'] = parse_note
    methods['create_note'] = Mock(wraps=webui.Note.create)
    monkeypatch.setattr(webui.Note, 'create', methods['create_note'])
    return methods


async def receive(socket: ClientConnection, message_type: str | None = None,
                  request_id: int | str | None = None) -> dict[str, Any]:
    async def read() -> dict[str, Any]:
        while True:
            message: dict[str, Any] = json.loads(await socket.recv())
            if message_type is not None:
                if message.get('type') == message_type and (request_id is None or message.get('id') == request_id):
                    return message
            elif 'id' in message and message['id'] == request_id and message.get('type') != 'progress':
                return message
    return await asyncio.wait_for(read(), 2)


@pytest.fixture
def log_history(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch) -> tuple[list[dict], Mock]:
    entries: list[dict] = []

    def recent(after_id: int = 0) -> list[dict]:
        return [entry.copy() for entry in entries if entry['id'] > after_id]

    recent_logs: Mock = Mock(side_effect=recent)
    monkeypatch.setattr(webui.log, 'get_recent', recent_logs)
    return entries, recent_logs


@pytest.mark.parametrize(('change', 'ready'), [
    ({'synchronized': False}, False),
    ({'synchronized': False, 'latest_block': None, 'last_check_sec': None}, False),
    ({'last_check_sec': None}, True), ({'last_check_sec': time.time() - 61}, True),
    ({'running': False}, False), ({'error': 'RPC failed'}, False),
])
def test_sync_readiness_is_informational(backend: webui.Backend, change: dict[str, Any], ready: bool) -> None:
    assert backend.status()['ready']
    backend.instances['ethereum-dai-10'].tornado.poller.state.update(change)
    status = backend.status()
    assert status['ready'] is ready and not status['stopping']
    assert status['instances'][0]['state'] == 'ready'
    assert (status['instances'][1]['state'] == 'ready') is ready
    assert backend.dispatch('approve', PARAMS) == {'from': ACCOUNT}
    assert backend.dispatch('approve', {**PARAMS, 'instance': 'ethereum-dai-10'}) == {'from': ACCOUNT}


@pytest.mark.parametrize('phase', ['starting', 'error', 'proving'])
def test_another_instance_startup_failure_or_work_does_not_block(backend: webui.Backend, phase: str) -> None:
    item: webui.Instance = backend.instances['ethereum-dai-10']
    if phase == 'proving':
        item.activity = phase
        item.lock.acquire()
    else:
        item.tornado = None
        item.phase = phase
        item.error = 'Initialization failed' if phase == 'error' else None
    try:
        assert backend.dispatch('approve', PARAMS) == {'from': ACCOUNT}
    finally:
        if phase == 'proving':
            item.lock.release()


@pytest.mark.parametrize('phase', ['starting', 'connecting', 'initializing'])
def test_startup_phases_have_unknown_progress(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    monkeypatch.setattr(webui.util, 'load_metadata', Mock(side_effect=AssertionError('Status must use the loaded metadata')))
    for item in backend.instances.values():
        item.tornado = None
        item.phase = phase
    status: dict[str, Any] = backend.status()
    assert not status['ready']
    for row in status['instances']:
        assert row['state'] == row['sync_state'] == phase
        assert not row['ready']
        assert row['message']
        assert row['address'] == (ACCOUNT if row['id'] == INSTANCE else RECIPIENT)
        assert row['decimals'] == 18
        assert all(row[field] is None for field in ('synced_block', 'latest_block', 'remaining_blocks', 'progress', 'last_update_sec'))


@pytest.mark.parametrize('updated', [None, Second(1234)])
def test_status_reports_tornado_update_time(backend: webui.Backend, updated: Second | None) -> None:
    tornado: FakeTornado = backend.instances[INSTANCE].tornado
    tornado.last_update_sec = updated
    assert backend.status()['instances'][0]['last_update_sec'] == updated
    tornado.poller.state['last_check_sec'] = time.time() + 10
    assert backend.status()['instances'][0]['last_update_sec'] == updated
    tornado.last_update_sec = Second(5678)
    assert backend.status()['instances'][0]['last_update_sec'] == Second(5678)


def test_rpc_retry_shows_failure_without_locking_operations(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    backend.instances[INSTANCE].tornado.poller.state.update(error='RPC_CALL_RATE_LIMIT', synchronized=False)
    status: dict[str, Any] = backend.status()
    row: dict[str, Any] = status['instances'][0]
    assert row['state'] == row['sync_state'] == 'retrying'
    assert not status['ready'] and not row['ready']
    assert row['progress'] is None and row['message']
    assert backend.dispatch('approve', PARAMS) == {'from': ACCOUNT}
    operations['approve_tx'].assert_called_once_with(ACCOUNT)


@pytest.mark.parametrize('age', [61, 600])
def test_ready_instance_keeps_progress_between_polls(backend: webui.Backend, operations: dict[str, Mock], age: int) -> None:
    backend.instances[INSTANCE].tornado.poller.state['last_check_sec'] = time.time() - age
    status: dict[str, Any] = backend.status()
    row: dict[str, Any] = status['instances'][0]
    assert row['state'] == row['sync_state'] == 'ready'
    assert row['ready'] and status['ready']
    assert row['synced_block'] == row['latest_block'] == 99
    assert row['progress'] == 1 and row['remaining_blocks'] == 0
    assert row['message'] == webui.STATUS_MESSAGES['ready'] and row['activity'] == ''
    assert backend.dispatch('approve', PARAMS) == {'from': ACCOUNT}


@pytest.mark.parametrize('method', ['create_note', 'approve', 'deposit', 'note_status', 'receipt'])
def test_non_proof_operations_do_not_wait_for_sync(backend: webui.Backend, operations: dict[str, Mock], method: str) -> None:
    tornado: FakeTornado = backend.instances[INSTANCE].tornado
    tornado.poller.state['synchronized'] = False
    assert not backend.status()['ready']
    assert backend.dispatch(method, PARAMS)
    tornado.poller.wait_sync.assert_not_called()


@pytest.mark.parametrize('method', ['create_note', 'approve', 'deposit', 'withdraw', 'relay_withdraw', 'note_status'])
def test_ready_instance_works_while_another_is_unsynchronized(backend: webui.Backend, operations: dict[str, Mock], method: str) -> None:
    backend.instances['ethereum-dai-10'].tornado.poller.state['synchronized'] = False
    assert not backend.status()['ready']
    assert backend.dispatch(method, PARAMS)


@pytest.mark.parametrize('method', ['withdraw', 'relay_withdraw', 'note_status'])
def test_note_selects_its_instance_instead_of_the_form_selection(backend: webui.Backend, operations: dict[str, Mock], method: str) -> None:
    backend.instances['ethereum-dai-10'].tornado.poller.state['synchronized'] = False
    assert backend.dispatch(method, {**PARAMS, 'instance': 'ethereum-dai-10'})
    chain, symbol, _, note = operations['parse_note'].return_value
    operations['parse_note'].return_value = (chain, symbol, TornadoUnit.UNIT_10, note)
    assert backend.dispatch(method, PARAMS)
    tornado: FakeTornado = backend.instances['ethereum-dai-10'].tornado
    if method == 'note_status':
        tornado.note_deposited.assert_called_once_with(note.commitment)
    else:
        tornado.init.assert_called_once_with(sync_only=False)


def test_create_note_matches_selected_instance_without_transactions(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch) -> None:
    create: Mock = Mock(wraps=webui.Note.create)
    wallet: Mock = Mock()
    monkeypatch.setattr(webui.Note, 'create', create)
    monkeypatch.setattr(webui, 'encode_wallet_format_tx', wallet)
    result = backend.dispatch('create_note', {'instance': 'ethereum-dai-10'})
    create.assert_called_once_with()
    assert set(result) == {'note', 'invoice'}
    chain, symbol, unit, note = webui.Note.from_text(result['note'])
    assert (chain, symbol, unit) == (ChainID.ETHEREUM, Symbol.DAI, TornadoUnit.UNIT_10)
    assert webui.Note.to_text(chain, symbol, unit, note) == result['note']
    assert webui.Note.to_invoice(chain, symbol, unit, note) == result['invoice']
    wallet.assert_not_called()
    for item in backend.instances.values():
        tornado = item.tornado
        for method in ('approve_tx', 'deposit_tx', 'prepare_withdraw', 'withdraw_tx', 'withdraw'):
            getattr(tornado, method).assert_not_called()
        tornado.connection.transaction_receipt.assert_not_called()


def test_create_note_rejects_unavailable_instance(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch) -> None:
    create = Mock()
    monkeypatch.setattr(webui.Note, 'create', create)
    with pytest.raises(ValueError, match='unavailable'):
        backend.dispatch('create_note', {'instance': 'ethereum-dai-100'})
    create.assert_not_called()


def test_create_note_does_not_require_tornado_initialization(backend: webui.Backend) -> None:
    backend.instances[INSTANCE].tornado = None
    result: dict[str, str] = backend.dispatch('create_note', {'instance': INSTANCE})
    assert webui.Note.from_text(result['note'])[:3] == (ChainID.ETHEREUM, Symbol.DAI, TornadoUnit.UNIT_1)


@pytest.mark.parametrize('method', ['approve', 'deposit', 'withdraw', 'relay_withdraw'])
def test_dispatch_routes_arguments(backend: webui.Backend, operations: dict[str, Mock], method: str) -> None:
    result = backend.dispatch(method, PARAMS)
    note = operations['parse_note'].return_value[3]
    tornado = backend.instances[INSTANCE].tornado
    if method in ('withdraw', 'relay_withdraw'):
        tornado.init.assert_called_once_with(sync_only=False)
    else:
        tornado.init.assert_not_called()
    if method == 'approve':
        operations['approve_tx'].assert_called_once_with(ACCOUNT)
    elif method == 'deposit':
        operations['deposit_tx'].assert_called_once_with(note.commitment, ACCOUNT)
    elif method == 'withdraw':
        operations['prepare_withdraw'].assert_called_once_with(note, RECIPIENT)
        operations['withdraw_tx'].assert_called_once_with(
            note, ACCOUNT, RECIPIENT, *operations['prepare_withdraw'].return_value,
        )
    else:
        assert operations['withdraw'].call_args.args == (note, RECIPIENT, 'https://relayer.example')
        can_submit = operations['withdraw'].call_args.kwargs['can_submit']
        assert can_submit()
        backend.stopping = True
        assert not can_submit()
    assert result == ({'hash': HASH} if method == 'relay_withdraw' else {'from': ACCOUNT})
    assert not backend.instances[INSTANCE].lock.locked()


@pytest.mark.parametrize('method', ['withdraw', 'relay_withdraw'])
def test_proof_waits_before_and_after_tree_building_without_blocking_sync(backend: webui.Backend, operations: dict[str, Mock],
                                                                        waiting_poller: tuple[webui.EventPoller, threading.Event], method: str) -> None:
    poller, entered = waiting_poller
    tornado: FakeTornado = backend.instances[INSTANCE].tornado
    other: FakeTornado = backend.instances['ethereum-dai-10'].tornado
    other.poller.state['synchronized'] = False
    rebuilt, cancelled = threading.Event(), threading.Event()

    def build(*args: Any, **kwargs: Any) -> bool:
        with poller.cond:
            poller.caught_up = False
            entered.clear()
        rebuilt.set()
        return True

    def synchronize() -> None:
        assert tornado.mutex.acquire(blocking=False)
        try:
            with poller.cond:
                poller.current, poller.caught_up = 100, True
                poller.refresh_needed = False
                poller.last_check_sec = time.time()
                poller.cond.notify_all()
        finally:
            tornado.mutex.release()

    tornado.init.side_effect = build
    with ThreadPoolExecutor(max_workers=1) as workers:
        pending = workers.submit(backend.dispatch, method, PARAMS, cancelled)
        try:
            assert entered.wait(1)
            row: dict[str, Any] = backend.status()['instances'][0]
            assert row['state'] == row['sync_state'] == 'syncing'
            assert row['message'] == webui.ACTIVITY_MESSAGES['syncing']
            assert row['sync_activity'] == webui.ACTIVITY_MESSAGES['fetching_events']
            assert not row['ready']
            tornado.init.assert_not_called()
            assert backend.dispatch('approve', {**PARAMS, 'instance': 'ethereum-dai-10'}) == {'from': ACCOUNT}
            synchronize()
            assert rebuilt.wait(1) and entered.wait(1)
            operations['prepare_withdraw'].assert_not_called()
            operations['withdraw'].assert_not_called()
            synchronize()
            assert pending.result(2) == ({'hash': HASH} if method == 'relay_withdraw' else {'from': ACCOUNT})
            other.poller.wait_sync.assert_not_called()
        finally:
            cancelled.set()
            with poller.cond:
                poller.cond.notify_all()
    assert not backend.instances[INSTANCE].lock.locked()


@pytest.mark.parametrize('method', ['withdraw', 'relay_withdraw'])
@pytest.mark.parametrize('age', [0, 61])
def test_withdrawal_wakes_idle_poller_before_proving(backend: webui.Backend, operations: dict[str, Mock],
                                                   monkeypatch: pytest.MonkeyPatch, method: str, age: int) -> None:
    monkeypatch.setattr(webui.config, 'BLOCKCHAIN_LOG_EVENT_POLL_INTERVAL_SEC', 600)
    monkeypatch.setattr(webui.util, 'wait', lambda *args: None)
    head, persisted = [100], []
    idle, writing, release, cancelled = (threading.Event() for _ in range(4))
    connection: SimpleNamespace = SimpleNamespace(started=lambda: True, latest_block_number=lambda: head[0], log_receipt=lambda *args: [])
    poller: webui.EventPoller = webui.EventPoller(ChainID.ETHEREUM, connection)
    backend.instances[INSTANCE].tornado.poller = poller
    original_wait = poller.cond.wait

    def wait(timeout: float | None = None) -> bool:
        if threading.current_thread() is poller.worker and timeout is not None and timeout > 60:
            idle.set()
        return original_wait(timeout)

    class Storage(webui.EventPoller.Handler):

        def on_sync(self, start: int, end: int, deposits: list, withdrawals: list) -> None:
            if end == 101:
                writing.set()
                assert release.wait(2)
            persisted.append(end)

    operation: Mock = operations['prepare_withdraw' if method == 'withdraw' else 'withdraw']
    proof = operation.return_value

    def prove(*args: Any, **kwargs: Any) -> Any:
        assert persisted[-1] == 101 and poller.status()['synchronized']
        return proof

    operation.side_effect = prove
    monkeypatch.setattr(poller.cond, 'wait', wait)
    poller.add_handler(Storage())
    assert poller.poll_interval == 600
    assert poller.start(ACCOUNT, 100)
    try:
        assert idle.wait(1), poller.status()
        with poller.cond:
            head[0] = 101
            poller.last_check_sec = time.time() - age
        row: dict[str, Any] = backend.status()['instances'][0]
        assert row['state'] == row['sync_state'] == 'ready' and row['ready']
        with ThreadPoolExecutor(max_workers=1) as workers:
            pending = workers.submit(backend.dispatch, method, PARAMS, cancelled)
            try:
                assert writing.wait(1)
                assert not pending.done()
                row = backend.status()['instances'][0]
                assert row['state'] == row['sync_state'] == 'syncing' and not row['ready']
                assert row['message'] == webui.ACTIVITY_MESSAGES['syncing']
                backend.instances[INSTANCE].tornado.init.assert_not_called()
                operation.assert_not_called()
                release.set()
                assert pending.result(2) == ({'hash': HASH} if method == 'relay_withdraw' else {'from': ACCOUNT})
                operation.assert_called_once()
                row = backend.status()['instances'][0]
                assert row['state'] == row['sync_state'] == 'ready' and row['ready']
            finally:
                cancelled.set()
                release.set()
                with poller.cond:
                    poller.cond.notify_all()
    finally:
        cancelled.set()
        release.set()
        poller.stop()


@pytest.mark.parametrize('method', ['withdraw', 'relay_withdraw'])
def test_stopped_sync_cannot_start_proof(backend: webui.Backend, operations: dict[str, Mock],
                                       waiting_poller: tuple[webui.EventPoller, threading.Event], method: str) -> None:
    poller, _ = waiting_poller
    poller.off = True
    with pytest.raises(RuntimeError, match='Synchronization has stopped'):
        backend.dispatch(method, PARAMS)
    backend.instances[INSTANCE].tornado.init.assert_not_called()
    operations['prepare_withdraw'].assert_not_called()
    operations['withdraw'].assert_not_called()
    assert not backend.instances[INSTANCE].lock.locked()


@pytest.mark.parametrize(('method', 'callbacks'), [
    ('approve', {'approve_tx': 'approving'}),
    ('deposit', {'deposit_tx': 'depositing'}),
    ('withdraw', {'init': 'building_tree', 'prepare_withdraw': 'proving'}),
    ('relay_withdraw', {'init': 'building_tree', 'withdraw': 'relaying'}),
])
def test_operation_activity_does_not_change_sync_readiness(backend: webui.Backend, operations: dict[str, Mock],
                                                           method: str, callbacks: dict[str, str]) -> None:
    tornado: FakeTornado = backend.instances[INSTANCE].tornado
    observed: list[str] = []

    def check_activity(state: str, result: Any, *args: Any, **kwargs: Any) -> Any:
        status: dict[str, Any] = backend.status()
        row: dict[str, Any] = status['instances'][0]
        assert status['ready'] and row['ready']
        assert row['sync_state'] == 'ready'
        assert row['state'] == (state if state in ('building_tree', 'proving', 'relaying') else 'working')
        assert row['activity'] == webui.ACTIVITY_MESSAGES[state]
        assert row['message'] == row['operation_progress']
        observed.append(state)
        return result

    for callback, state in callbacks.items():
        operation: Mock = getattr(tornado, callback)
        result: Any = operation.return_value
        operation.side_effect = lambda *args, state=state, result=result, **kwargs: check_activity(state, result, *args, **kwargs)
    backend.dispatch(method, PARAMS)
    assert observed == list(callbacks.values())
    row: dict[str, Any] = backend.status()['instances'][0]
    assert row['state'] == row['sync_state'] == 'ready'
    assert row['activity'] == webui.ACTIVITY_MESSAGES['idle']


@pytest.mark.parametrize('outcome', ['success', 'error', 'cancelled', 'callback_error'])
def test_operation_progress_cleanup_and_request_isolation(backend: webui.Backend, operations: dict[str, Mock], outcome: str) -> None:
    item: webui.Instance = backend.instances[INSTANCE]
    counter: webui.Counters = webui.Counters(item)
    cancelled: threading.Event = threading.Event()
    stages, saved = [], []

    def progress(message: str) -> None:
        assert backend.status()['instances'][0]['operation_progress'] == message
        stages.append(message)
        if outcome == 'callback_error' and message == 'First request stage':
            raise RuntimeError('Viewer failed')

    def operation(*args: Any) -> dict[str, str]:
        saved.append(item.progress_callback)
        counter.on_progress('First request stage')
        webui.Counters(backend.instances['ethereum-dai-10']).on_progress('Other instance stage')
        if outcome == 'error':
            raise RuntimeError('Operation failed')
        if outcome == 'cancelled':
            cancelled.set()
        return {'from': ACCOUNT}

    operations['approve_tx'].side_effect = operation
    if outcome == 'success':
        assert backend.dispatch('approve', PARAMS, cancelled, progress) == {'from': ACCOUNT}
    else:
        with pytest.raises((ValueError, RuntimeError)):
            backend.dispatch('approve', PARAMS, cancelled, progress)
    assert 'First request stage' in stages and 'Other instance stage' not in stages
    assert item.progress_callback is item.progress is item.activity is None
    assert backend.status()['instances'][0]['operation_progress'] is None
    assert not item.lock.locked()
    prior: list[str] = stages.copy()
    counter.on_progress('After completion')
    saved[0]('Late first request stage')
    assert stages == prior

    def second(*args: Any) -> dict[str, str]:
        saved[0]('Late first request stage')
        counter.on_progress('Second request stage')
        return {'from': ACCOUNT}

    operations['approve_tx'].side_effect = second
    next_stages: list[str] = []
    backend.dispatch('approve', PARAMS, progress=next_stages.append)
    assert 'Second request stage' in next_stages and 'Late first request stage' not in next_stages
    assert stages == prior


def test_sync_failure_stays_visible_during_operation(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    def lose_sync(*args: Any) -> dict[str, str]:
        backend.instances[INSTANCE].tornado.poller.state.update(error='RPC failed', synchronized=False)
        status: dict[str, Any] = backend.status()
        row: dict[str, Any] = status['instances'][0]
        assert row['state'] == 'working' and row['sync_state'] == 'retrying'
        assert row['error'] == 'RPC failed'
        assert not row['ready'] and not status['ready']
        return {'from': ACCOUNT}

    operations['approve_tx'].side_effect = lose_sync
    assert backend.dispatch('approve', PARAMS) == {'from': ACCOUNT}
    assert not backend.instances[INSTANCE].lock.locked()


@pytest.mark.parametrize(('method', 'callback'), [
    ('create_note', 'create_note'), ('approve', 'approve_tx'), ('deposit', 'deposit_tx'),
    ('withdraw', 'withdraw_tx'), ('note_status', 'note_age'),
])
@pytest.mark.parametrize('changed_instance', [INSTANCE, 'ethereum-dai-10'])
def test_sync_change_does_not_discard_the_result(backend: webui.Backend, operations: dict[str, Mock],
                                                  method: str, callback: str, changed_instance: str) -> None:
    operation: Mock = operations['create_note'] if method == 'create_note' else getattr(backend.instances[INSTANCE].tornado, callback)
    result: Any = webui.Note.create() if method == 'create_note' else operation.return_value

    def lose_sync(*args: Any) -> Any:
        backend.instances[changed_instance].tornado.poller.state.update(error='RPC failed', synchronized=False)
        return result

    operation.side_effect = lose_sync
    assert backend.dispatch(method, PARAMS)
    assert not backend.instances[INSTANCE].lock.locked()


@pytest.mark.parametrize('changed_instance', [INSTANCE, 'ethereum-dai-10'])
def test_relayer_submission_remains_valid_when_sync_changes(backend: webui.Backend, operations: dict[str, Mock], changed_instance: str) -> None:
    def relay(*args: Any, **kwargs: Any) -> HexBytes | None:
        backend.instances[changed_instance].tornado.poller.state.update(error='RPC failed', synchronized=False)
        can_submit = kwargs['can_submit']
        assert can_submit()
        return HexBytes(HASH)

    operations['withdraw'].side_effect = relay
    assert backend.dispatch('relay_withdraw', PARAMS) == {'hash': HASH}


def test_cancellation_is_rechecked_after_acquiring_the_instance_lock(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    item: webui.Instance = backend.instances[INSTANCE]
    original_lock = item.lock
    cancelled: threading.Event = threading.Event()

    def acquire(*args: Any, **kwargs: Any) -> bool:
        cancelled.set()
        return original_lock.acquire(*args, **kwargs)

    item.lock = Mock(wraps=original_lock)
    item.lock.acquire.side_effect = acquire
    with pytest.raises(ValueError, match='cancelled'):
        backend.dispatch('approve', PARAMS, cancelled)
    operations['approve_tx'].assert_not_called()
    assert not original_lock.locked()


@pytest.mark.parametrize('method', ['create_note', 'approve', 'deposit'])
def test_cancelled_request_does_not_create_note_or_build_transaction(backend: webui.Backend, operations: dict[str, Mock], method: str) -> None:
    cancelled: threading.Event = threading.Event()
    cancelled.set()
    with pytest.raises(ValueError, match='cancelled'):
        backend.dispatch(method, PARAMS, cancelled)
    for operation in operations.values():
        operation.assert_not_called()


def test_cancellation_after_proving_prevents_transaction_building(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    cancelled: threading.Event = threading.Event()
    proof = operations['prepare_withdraw'].return_value

    def prove(*args: Any) -> Any:
        cancelled.set()
        return proof

    operations['prepare_withdraw'].side_effect = prove
    with pytest.raises(ValueError, match='cancelled'):
        backend.dispatch('withdraw', PARAMS, cancelled)
    operations['withdraw_tx'].assert_not_called()


def test_cancelled_relayer_request_cannot_submit(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    cancelled: threading.Event = threading.Event()

    def relay(*args: Any, **kwargs: Any) -> None:
        cancelled.set()
        assert not kwargs['can_submit']()

    operations['withdraw'].side_effect = relay
    with pytest.raises(ValueError, match='cancelled'):
        backend.dispatch('relay_withdraw', PARAMS, cancelled)


def test_shutdown_locks_all_instances_including_receipts(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    backend.stopping = True
    status: dict[str, Any] = backend.status()
    assert status['stopping'] and not status['ready']
    for name in backend.instances:
        for method in ('create_note', 'approve', 'deposit', 'withdraw', 'relay_withdraw', 'note_status', 'receipt'):
            with pytest.raises(ValueError, match='shutting down'):
                backend.dispatch(method, {**PARAMS, 'instance': name})


def test_withdrawal_tree_failure_does_not_prove_or_submit(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    backend.instances[INSTANCE].tornado.init.return_value = False
    with pytest.raises(RuntimeError, match='withdrawal tree'):
        backend.dispatch('withdraw', PARAMS)
    operations['prepare_withdraw'].assert_not_called()
    operations['withdraw_tx'].assert_not_called()
    assert backend.status()['instances'][0]['state'] == 'ready'


def test_deposit_rejects_note_for_another_instance(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    with pytest.raises(ValueError, match='different instance'):
        backend.dispatch('deposit', {**PARAMS, 'instance': 'ethereum-dai-10'})
    for item in backend.instances.values():
        item.tornado.deposit_tx.assert_not_called()


def test_encode_wallet_format_tx_encodes_nested_quantities_and_bytes() -> None:
    assert webui.encode_wallet_format_tx({
        'from': ACCOUNT, 'to': RECIPIENT, 'value': 0, 'gas': 21000, 'chainId': 1,
        'data': HexBytes('0x1234'), 'accessList': [(ACCOUNT, [bytes.fromhex('ff')])],
    }) == {
        'from': ACCOUNT, 'to': RECIPIENT, 'value': '0x0', 'gas': '0x5208', 'chainId': '0x1',
        'data': '0x1234', 'accessList': [[ACCOUNT, ['0xff']]],
    }


def test_encode_wallet_format_tx_rejects_failed_transaction_build() -> None:
    with pytest.raises(RuntimeError, match='Could not build transaction'):
        webui.encode_wallet_format_tx(None)


def test_note_status_and_historical_counts(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    assert backend.dispatch('note_status', PARAMS) == {
        'instance': INSTANCE, 'deposited': True, 'spent': False,
        'deposits_after': 7, 'withdrawals_after': 3,
    }
    row = backend.status()['instances'][0]
    assert (row['deposits'], row['withdrawals']) == (2, 1)
    assert (row['deposits_total'], row['withdrawals_total'], row['anonymity_set']) == (100, 30, 100)
    counter: webui.Counters = webui.Counters(backend.instances[INSTANCE])
    for deposits, withdrawals, expected in [
        (3, 1, (103, 31, 103)), (1, 1, (104, 32, 104)), (0, 1, (104, 33, 104)),
    ]:
        counter.on_sync(100, 101, [object()] * deposits, [object()] * withdrawals)
        row = backend.status()['instances'][0]
        assert (row['deposits_total'], row['withdrawals_total'], row['anonymity_set']) == expected


def test_start_runs_connection_off_event_loop_and_loads_counts_before_sync(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch) -> None:
    main_thread: int             = threading.get_ident()
    order      : list[str]       = []

    def start_connection() -> bool:
        assert threading.get_ident() != main_thread
        rows: list[dict[str, Any]] = backend.status()['instances']
        assert all(row['state'] == 'connecting' and row['progress'] is None for row in rows)
        return True

    connection: SimpleNamespace = SimpleNamespace(start=Mock(side_effect=start_connection), stop=Mock())
    pollers: Mock = Mock(side_effect=FakePoller)
    monkeypatch.setattr(webui.rpc, 'Connection', Mock(return_value=connection))
    monkeypatch.setattr(webui, 'EventPoller', pollers)

    class FakeTornado:

        def __init__(self, *args: Any) -> None:
            self.name           : str             = f'ethereum-dai-{args[2].value}'
            self.last_update_sec: Second | None   = None
            self.db             : SimpleNamespace = SimpleNamespace(get_event_counts=lambda: order.append('counts') or (50, 20))
            self.un_init        : Mock            = Mock()

        def init(self, sync_only: bool) -> bool:
            assert sync_only
            row: dict[str, Any] = next(row for row in backend.status()['instances'] if row['id'] == self.name)
            assert row['state'] == 'initializing' and row['progress'] is None
            order.append('init')
            return True

        def add_handler(self, handler: webui.Counters) -> None:
            self.handler: webui.Counters = handler
            order.append('handler')

        def start_sync(self) -> bool:
            order.append('sync')
            assert self.handler.item.totals == (50, 20)
            return True

    monkeypatch.setattr(webui, 'Tornado', FakeTornado)

    async def scenario() -> None:
        for item in backend.instances.values():
            item.tornado = None
        await backend.start()
        for item in backend.instances.values():
            assert item.error is None
            assert item.totals == (50, 20)
        await backend.close()

    asyncio.run(scenario())
    assert order.count('init') == order.count('sync') == 2
    assert pollers.call_count == 2
    assert all(call.args == (ChainID.ETHEREUM, connection) and not call.kwargs for call in pollers.call_args_list)
    connection.start.assert_called_once()
    connection.stop.assert_called_once()


def test_failed_connection_marks_all_instances_and_closes(backend: webui.Backend, monkeypatch: pytest.MonkeyPatch) -> None:
    connection = SimpleNamespace(start=Mock(return_value=False), stop=Mock())
    monkeypatch.setattr(webui.rpc, 'Connection', Mock(return_value=connection))

    async def scenario() -> None:
        for item in backend.instances.values():
            item.tornado = None
        await backend.start()
        assert not backend.status()['ready']
        assert all(row['state'] == 'error' for row in backend.status()['instances'])
        await backend.close()

    asyncio.run(scenario())
    connection.stop.assert_called_once()


def test_close_waits_for_active_operation_and_rejects_new_work(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    entered, release = threading.Event(), threading.Event()

    def slow(*args: Any) -> dict[str, str]:
        entered.set()
        assert release.wait(3)
        return {'from': ACCOUNT}

    operations['approve_tx'].side_effect = slow
    tornado = backend.instances[INSTANCE].tornado

    async def scenario() -> None:
        operation = asyncio.create_task(asyncio.to_thread(backend.dispatch, 'approve', PARAMS))
        assert await asyncio.to_thread(entered.wait, 1)
        with pytest.raises(ValueError, match='busy'):
            backend.dispatch('approve', PARAMS)
        closing = asyncio.create_task(backend.close())
        try:
            await asyncio.sleep(0.03)
            tornado.un_init.assert_not_called()
            with pytest.raises(ValueError, match='locked'):
                backend.dispatch('approve', PARAMS)
        finally:
            release.set()
        result, _ = await asyncio.gather(operation, closing, return_exceptions=True)
        assert isinstance(result, ValueError)
        tornado.un_init.assert_called_once()

    asyncio.run(scenario())


def test_shutdown_cancels_sync_wait_and_releases_the_instance(backend: webui.Backend, operations: dict[str, Mock],
                                                             waiting_poller: tuple[webui.EventPoller, threading.Event]) -> None:
    poller, entered = waiting_poller
    item: webui.Instance = backend.instances[INSTANCE]

    async def scenario() -> None:
        operation = asyncio.create_task(asyncio.to_thread(backend.dispatch, 'withdraw', PARAMS))
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            results = await asyncio.wait_for(asyncio.gather(operation, backend.close(), return_exceptions=True), 2)
            assert isinstance(results[0], ValueError) and 'shutting down' in str(results[0])
            assert not item.lock.locked()
            item.tornado.un_init.assert_called_once()
            operations['prepare_withdraw'].assert_not_called()
        finally:
            backend.stopping = True
            with poller.cond:
                poller.cond.notify_all()
            await asyncio.gather(operation, return_exceptions=True)

    asyncio.run(scenario())


def test_close_finishes_all_instances_before_stopping_rpc_after_an_error(backend: webui.Backend) -> None:
    slow_done = threading.Event()

    def slow_close() -> None:
        time.sleep(0.03)
        slow_done.set()

    backend.instances[INSTANCE].tornado.un_init.side_effect = RuntimeError('failed')
    backend.instances['ethereum-dai-10'].tornado.un_init.side_effect = slow_close
    stop = Mock(side_effect=lambda: slow_done.is_set() or pytest.fail('RPC stopped before every instance finished'))
    backend.connections[ChainID.ETHEREUM] = SimpleNamespace(stop=stop)
    asyncio.run(backend.close())
    stop.assert_called_once()


def test_websocket_survives_invalid_json_and_routes_requests(backend: webui.Backend, operations: dict[str, Mock]) -> None:
    async def scenario() -> None:
        async with serve(lambda socket: webui.handle_client(socket, backend), '127.0.0.1', 0) as server:
            async with connect(f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}') as socket:
                assert (await receive(socket, 'status'))['ready']
                for invalid in ('{', '[]', '{"id":true,"method":"status"}'):
                    await socket.send(invalid)
                    response: dict[str, Any] = await receive(socket)
                    assert response['id'] is None and 'error' in response
                await socket.send(json.dumps({'id': 7, 'method': 'approve', 'params': PARAMS}))
                response = await receive(socket, request_id=7)
                assert response == {'id': 7, 'result': {'from': ACCOUNT}}

    asyncio.run(scenario())


def test_websocket_routes_create_note_to_python_backend(backend: webui.Backend) -> None:
    async def scenario() -> None:
        async with serve(lambda socket: webui.handle_client(socket, backend), '127.0.0.1', 0) as server:
            async with connect(f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}') as socket:
                assert (await receive(socket, 'status'))['ready']
                await socket.send(json.dumps({'id': 8, 'method': 'create_note', 'params': {'instance': INSTANCE}}))
                response: dict[str, Any] = await receive(socket, request_id=8)
                assert response['id'] == 8
                result = response['result']
                chain, symbol, unit, note = webui.Note.from_text(result['note'])
                assert (chain, symbol, unit) == (ChainID.ETHEREUM, Symbol.DAI, TornadoUnit.UNIT_1)
                assert webui.Note.to_invoice(chain, symbol, unit, note) == result['invoice']

    asyncio.run(scenario())


@pytest.mark.parametrize('failure', [False, True])
def test_websocket_drains_progress_when_dispatch_finishes_without_yielding(backend: webui.Backend,
                                                                         monkeypatch: pytest.MonkeyPatch, failure: bool) -> None:
    def dispatch(method: str, params: dict, cancelled: threading.Event, progress: Any) -> dict:
        progress('First stage')
        progress('Last stage')
        if failure:
            raise RuntimeError('Fast operation failed')
        return {'from': ACCOUNT}

    async def completed(function: Any, *args: Any, **kwargs: Any) -> Any:
        return function(*args, **kwargs)

    monkeypatch.setattr(backend, 'dispatch', dispatch)
    monkeypatch.setattr(asyncio, 'to_thread', completed)

    async def scenario() -> None:
        async with serve(lambda socket: webui.handle_client(socket, backend), '127.0.0.1', 0) as server:
            async with connect(f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}') as socket:
                await socket.send(json.dumps({'id': 7, 'method': 'approve', 'params': PARAMS}))

                async def read() -> list[dict]:
                    messages: list[dict] = []
                    while True:
                        message: dict = json.loads(await socket.recv())
                        if message.get('id') == 7:
                            messages.append(message)
                            if message.get('type') != 'progress':
                                return messages

                assert await asyncio.wait_for(read(), 2) == [
                    {'id': 7, 'type': 'progress', 'message': 'First stage'},
                    {'id': 7, 'type': 'progress', 'message': 'Last stage'},
                    {'id': 7, 'error': 'Fast operation failed'} if failure else {'id': 7, 'result': {'from': ACCOUNT}},
                ]

    asyncio.run(scenario())


@pytest.mark.parametrize('failure', [False, True])
def test_websocket_progress_is_live_isolated_and_drained_before_result(backend: webui.Backend, operations: dict[str, Mock], failure: bool) -> None:
    release: threading.Event = threading.Event()
    first: str = 'Fetching deposit transaction nonce'
    last: str = 'Building deposit transaction'
    other: str = 'Other instance approval'
    secret: str = 'private-note-do-not-send-in-progress'

    def deposit(*args: Any) -> dict[str, str]:
        counter: webui.Counters = webui.Counters(backend.instances[INSTANCE])
        counter.on_progress(first)
        assert release.wait(3)
        counter.on_progress(last)
        if failure:
            raise RuntimeError('Deposit failed')
        return {'from': ACCOUNT}

    def approve(*args: Any) -> dict[str, str]:
        webui.Counters(backend.instances['ethereum-dai-10']).on_progress(other)
        return {'from': ACCOUNT}

    operations['deposit_tx'].side_effect = deposit
    backend.instances['ethereum-dai-10'].tornado.approve_tx.side_effect = approve

    async def result(socket: ClientConnection, request_id: int) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        async def read() -> list[dict[str, Any]]:
            while True:
                message: dict[str, Any] = json.loads(await socket.recv())
                if 'id' not in message:
                    continue
                messages.append(message)
                if message['id'] == request_id and message.get('type') != 'progress':
                    return messages
        return await asyncio.wait_for(read(), 2)

    async def scenario() -> None:
        async with serve(lambda socket: webui.handle_client(socket, backend), '127.0.0.1', 0) as server:
            url: str = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            async with connect(url) as socket, connect(url) as unrelated:
                await receive(socket, 'status')
                await receive(unrelated, 'status')
                try:
                    await socket.send(json.dumps({'id': 7, 'method': 'deposit', 'params': {**PARAMS, 'note': secret}}))
                    stages: list[dict[str, Any]] = []
                    while True:
                        phase: dict[str, Any] = await receive(socket, 'progress', 7)
                        stages.append(phase)
                        if phase['message'] == first:
                            break
                    assert not release.is_set()
                    await unrelated.send(json.dumps({'id': 7, 'method': 'approve', 'params': {**PARAMS, 'instance': 'ethereum-dai-10'}}))
                    independent: list[dict[str, Any]] = await result(unrelated, 7)
                    assert any(message.get('message') == other for message in independent)
                    assert all(message.get('message') not in (first, last) for message in independent)
                    release.set()
                    completed: list[dict[str, Any]] = await result(socket, 7)
                    phases: list[dict[str, Any]] = stages + completed[:-1]
                    assert any(message['message'] == last for message in phases)
                    assert all(set(message) == {'id', 'type', 'message'} and message['id'] == 7 for message in phases)
                    assert all(message['message'] != other for message in phases)
                    assert secret not in json.dumps(phases)
                    assert completed[-1] == ({'id': 7, 'error': 'Deposit failed'} if failure else {'id': 7, 'result': {'from': ACCOUNT}})
                    await socket.send(json.dumps({'id': 8, 'method': 'status'}))
                    assert len(await result(socket, 8)) == 1
                finally:
                    release.set()
            async with connect(url) as reconnected:
                status: dict[str, Any] = await receive(reconnected, 'status')
                assert all(row['operation_progress'] is None for row in status['instances'])
                webui.Counters(backend.instances[INSTANCE]).on_progress('Old operation after reconnect')
                await reconnected.send(json.dumps({'id': 9, 'method': 'status'}))
                assert len(await result(reconnected, 9)) == 1
        assert not any(task.get_coro().__qualname__.endswith('publish_progress') for task in asyncio.all_tasks())

    asyncio.run(scenario())


def test_websocket_disconnect_cancels_sync_wait_and_releases_the_instance(backend: webui.Backend, operations: dict[str, Mock],
                                                                        waiting_poller: tuple[webui.EventPoller, threading.Event],
                                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    poller, entered = waiting_poller
    released: threading.Event = threading.Event()
    dispatch = backend.dispatch

    def request(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return dispatch(*args, **kwargs)
        finally:
            released.set()

    monkeypatch.setattr(backend, 'dispatch', request)

    async def scenario() -> None:
        try:
            async with serve(lambda socket: webui.handle_client(socket, backend), '127.0.0.1', 0) as server:
                async with connect(f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}') as socket:
                    await socket.send(json.dumps({'id': 1, 'method': 'withdraw', 'params': PARAMS}))
                    assert await asyncio.to_thread(entered.wait, 1)
                    assert backend.instances[INSTANCE].lock.locked()
                assert await asyncio.to_thread(released.wait, 2)
                assert not backend.instances[INSTANCE].lock.locked()
                item: webui.Instance = backend.instances[INSTANCE]
                assert item.progress_callback is item.progress is item.activity is None
                operations['prepare_withdraw'].assert_not_called()
        finally:
            backend.stopping = True
            with poller.cond:
                poller.cond.notify_all()
        assert not any(task.get_coro().__qualname__.endswith('publish_progress') for task in asyncio.all_tasks())

    asyncio.run(scenario())


def test_websocket_keeps_publishing_during_work_and_cleans_up_on_disconnect(backend: webui.Backend, operations: dict[str, Mock],
                                                                            log_history: tuple[list[dict], Mock]) -> None:
    entered, release = threading.Event(), threading.Event()
    entries, recent_logs = log_history

    def slow(*args: Any) -> dict[str, str]:
        entered.set()
        assert release.wait(6)
        return {'from': ACCOUNT}

    operations['approve_tx'].side_effect = slow

    async def scenario() -> None:
        finished = asyncio.Event()

        async def handle(socket: ServerConnection) -> None:
            try:
                await webui.handle_client(socket, backend)
            finally:
                finished.set()

        try:
            async with serve(handle, '127.0.0.1', 0) as server:
                async with connect(f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}') as socket:
                    assert (await receive(socket, 'status'))['ready']
                    assert await receive(socket, 'logs') == {'type': 'logs', 'reset': True, 'entries': []}
                    await socket.send(json.dumps({'id': 1, 'method': 'approve', 'params': PARAMS}))
                    assert await asyncio.to_thread(entered.wait, 1)
                    entries.append({'id': 9, 'level': 'I', 'text': 'working'})
                    status: dict[str, Any] = await receive(socket, 'status')
                    assert status['ready'] and status['instances'][0]['state'] == 'working'
                    assert await receive(socket, 'logs') == {'type': 'logs', 'reset': False, 'entries': entries}
                await asyncio.wait_for(finished.wait(), 0.5)
                reads_after_disconnect: int = recent_logs.call_count
                await asyncio.sleep(0.03)
                assert recent_logs.call_count == reads_after_disconnect
        finally:
            release.set()
            await backend.close()

    asyncio.run(scenario())


def test_websocket_history_and_id_based_increments_work_while_unsynchronized(backend: webui.Backend,
                                                                             log_history: tuple[list[dict], Mock]) -> None:
    entries, _ = log_history
    entries.extend([{'id': 5, 'level': 'I', 'text': 'same'}, {'id': 11, 'level': 'I', 'text': 'same'}])
    backend.instances[INSTANCE].tornado.poller.state.update(error='RPC failed', synchronized=False)

    async def scenario() -> None:
        async with serve(lambda socket: webui.handle_client(socket, backend), '127.0.0.1', 0) as server:
            url: str = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            async with connect(url) as socket:
                assert not (await receive(socket, 'status'))['ready']
                assert await receive(socket, 'logs') == {'type': 'logs', 'reset': True, 'entries': entries}
                entries.append({'id': 20, 'level': 'I', 'text': 'same'})
                assert await receive(socket, 'logs') == {'type': 'logs', 'reset': False, 'entries': entries[-1:]}
                entries.append({'id': 29, 'level': 'I', 'text': 'same'})
                assert await receive(socket, 'logs') == {'type': 'logs', 'reset': False, 'entries': entries[-1:]}
                await socket.send(json.dumps({'id': 3, 'method': 'approve', 'params': PARAMS}))
                assert (await receive(socket, request_id=3))['result'] == {'from': ACCOUNT}
            async with connect(url) as socket:
                assert not (await receive(socket, 'status'))['ready']
                assert await receive(socket, 'logs') == {'type': 'logs', 'reset': True, 'entries': entries}

    asyncio.run(scenario())
