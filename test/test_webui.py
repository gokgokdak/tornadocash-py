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
    async with asyncio.timeout(2):
        while True:
            message: dict[str, Any] = json.loads(await socket.recv())
            if message_type is not None:
                if message.get('type') == message_type and (request_id is None or message.get('id') == request_id):
                    return message
            elif 'id' in message and message['id'] == request_id and message.get('type') != 'progress':
                return message


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
                operations['prepare_withdraw'].assert_not_called()
        finally:
            backend.stopping = True
            with poller.cond:
                poller.cond.notify_all()
        assert not any(task.get_coro().__qualname__.endswith('publish_progress') for task in asyncio.all_tasks())

    asyncio.run(scenario())
