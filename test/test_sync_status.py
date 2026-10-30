import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any, Callable, Iterator
from unittest.mock import Mock

import pytest
from hexbytes import HexBytes

from components import blockchain, rpc
from components.mytype import ChainID


@pytest.fixture
def poller(monkeypatch: pytest.MonkeyPatch) -> blockchain.EventPoller:
    connection: SimpleNamespace = SimpleNamespace(
        started=lambda: True,
        latest_block_number=lambda: 5,
        log_receipt=lambda *args: [],
    )
    value: blockchain.EventPoller = blockchain.EventPoller(ChainID.ETHEREUM, connection, poll_interval=15)
    value.off = False
    value.contract = '0x0000000000000000000000000000000000000001'
    monkeypatch.setitem(blockchain.config.BLOCKCHAIN_LOG_EVENT_POLL_BLOCKS_PER_REQUEST, value.chain, 2)
    monkeypatch.setattr(blockchain.util, 'wait', lambda *args: None)
    return value


@pytest.mark.parametrize(('activity', 'value'), [
    (blockchain.EventPoller.Activity.IDLE, 'idle'),
    (blockchain.EventPoller.Activity.FETCHING_HEAD, 'fetching_head'),
    (blockchain.EventPoller.Activity.FETCHING_EVENTS, 'fetching_events'),
    (blockchain.EventPoller.Activity.RETRY_WAIT, 'retry_wait'),
    (blockchain.EventPoller.Activity.PERSISTING, 'persisting'),
])
def test_activity_status_serializes_as_string(poller: blockchain.EventPoller, activity: blockchain.EventPoller.Activity, value: str) -> None:
    poller.activity = activity
    assert json.loads(json.dumps(poller.status()))['activity'] == value
    assert poller.activity is activity


@pytest.fixture
def waiter(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[ThreadPoolExecutor, threading.Event]]:
    entered: threading.Event = threading.Event()
    original_wait = poller.cond.wait

    def wait(timeout: float | None = None) -> bool:
        if threading.current_thread().name.startswith('wait-sync-test'):
            entered.set()
        return original_wait(timeout)

    monkeypatch.setattr(poller.cond, 'wait', wait)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='wait-sync-test') as worker:
        try:
            yield worker, entered
        finally:
            with poller.cond:
                poller.off = True
                poller.cond.notify_all()


@pytest.fixture
def idle_poll(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch) -> Iterator[threading.Event]:
    sleeping: threading.Event = threading.Event()
    original_wait = poller.cond.wait_for
    poller.poll_interval = 600

    def wait(predicate: Callable[[], bool], timeout: float | None = None) -> bool:
        assert timeout == 600
        sleeping.set()
        return original_wait(predicate, timeout)

    monkeypatch.setattr(poller.cond, 'wait_for', wait)
    try:
        yield sleeping
    finally:
        if poller.worker is not None:
            poller.stop()


@pytest.mark.parametrize(('age', 'refresh', 'calls'), [(0, False, 1), (61, False, 2), (0, True, 2)])
def test_wait_sync_refreshes_long_idle_only_when_needed(poller: blockchain.EventPoller, idle_poll: threading.Event,
                                                      waiter: tuple[ThreadPoolExecutor, threading.Event],
                                                      age: int, refresh: bool, calls: int) -> None:
    head: Mock = Mock(side_effect=[5, 7])
    poller.connection.latest_block_number = head
    poller.off = True
    assert poller.start(poller.contract, 4)
    assert idle_poll.wait(1)
    with poller.cond:
        poller.last_check_sec = time.time() - age
    worker, _ = waiter
    assert worker.submit(poller.wait_sync, refresh=refresh).result(timeout=1) is True
    assert head.call_count == calls
    assert poller.status()['synced_block'] == (5 if calls == 1 else 7)
    assert poller.poll_interval == 600


def test_refresh_before_idle_predicate_is_not_lost(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch,
                                                 idle_poll: threading.Event, waiter: tuple[ThreadPoolExecutor, threading.Event]) -> None:
    head: Mock = Mock(side_effect=[5, 7])
    poller.connection.latest_block_number = head
    worker, entered = waiter
    original_wait = poller.cond.wait_for

    def wait(predicate: Callable[[], bool], timeout: float | None = None) -> bool:
        if head.call_count == 1:
            idle_poll.set()
            poller.cond.release()
            try:
                assert entered.wait(1)
            finally:
                poller.cond.acquire()
        return original_wait(predicate, timeout)

    monkeypatch.setattr(poller.cond, 'wait_for', wait)
    poller.off = True
    assert poller.start(poller.contract, 4)
    assert idle_poll.wait(1)
    result = worker.submit(poller.wait_sync, refresh=True)
    assert result.result(timeout=1) is True
    assert head.call_count == 2


def test_concurrent_refreshes_share_one_pending_head(poller: blockchain.EventPoller, idle_poll: threading.Event) -> None:
    fetching: threading.Event = threading.Event()
    release : threading.Event = threading.Event()
    calls: list[int] = []

    def head() -> int:
        calls.append(1)
        if len(calls) == 2:
            fetching.set()
            assert release.wait(2)
        return 5

    poller.connection.latest_block_number = head
    poller.off = True
    assert poller.start(poller.contract, 4)
    assert idle_poll.wait(1)
    try:
        with ThreadPoolExecutor(max_workers=3) as workers:
            first = workers.submit(poller.wait_sync, refresh=True)
            assert fetching.wait(1)
            entered: list[threading.Event] = [threading.Event(), threading.Event()]

            def cancel(index: int) -> bool:
                entered[index].set()
                return False

            others = [workers.submit(poller.wait_sync, lambda index=index: cancel(index), True) for index in range(2)]
            assert all(event.wait(1) for event in entered)
            assert not poller.status()['synchronized']
            release.set()
            assert all(result.result(timeout=1) for result in [first, *others])
    finally:
        release.set()
    assert len(calls) == 3


def test_refresh_during_inflight_head_requires_a_new_request(poller: blockchain.EventPoller, idle_poll: threading.Event,
                                                          waiter: tuple[ThreadPoolExecutor, threading.Event]) -> None:
    fetching: threading.Event = threading.Event()
    release : threading.Event = threading.Event()
    calls: list[int] = []

    def head() -> int:
        calls.append(1)
        if len(calls) == 1:
            fetching.set()
            assert release.wait(2)
            return 5
        return 7

    poller.connection.latest_block_number = head
    poller.off = True
    assert poller.start(poller.contract, 4)
    try:
        assert fetching.wait(1)
        worker, entered = waiter
        result = worker.submit(poller.wait_sync, refresh=True)
        assert entered.wait(1)
        release.set()
        assert result.result(timeout=1) is True
        assert len(calls) == 2
        assert poller.status()['synced_block'] == 7
    finally:
        release.set()


def test_stale_waiter_reuses_a_slow_refresh_instead_of_requeuing(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch,
                                                              idle_poll: threading.Event, waiter: tuple[ThreadPoolExecutor, threading.Event]) -> None:
    fetching: threading.Event = threading.Event()
    cycled  : threading.Event = threading.Event()
    release : threading.Event = threading.Event()
    calls: list[int] = []
    waits: list[float | None] = []
    original_wait = poller.cond.wait

    def head() -> int:
        calls.append(1)
        if len(calls) == 2:
            fetching.set()
            assert release.wait(2)
        return 5

    def wait(timeout: float | None = None) -> bool:
        if threading.current_thread().name.startswith('wait-sync-test'):
            waits.append(timeout)
            if len(waits) == 2:
                cycled.set()
        return original_wait(timeout)

    monkeypatch.setattr(poller.cond, 'wait', wait)
    poller.connection.latest_block_number = head
    poller.off = True
    assert poller.start(poller.contract, 4)
    try:
        assert idle_poll.wait(1)
        with poller.cond:
            poller.last_check_sec = time.time() - 61
        worker, _ = waiter
        result = worker.submit(poller.wait_sync)
        assert fetching.wait(1) and cycled.wait(1)
        release.set()
        assert result.result(timeout=1) is True
        assert len(calls) == 2
    finally:
        release.set()


@pytest.mark.parametrize(('age', 'refresh'), [(61, False), (0, True)])
def test_refresh_during_persistence_survives_the_old_round(poller: blockchain.EventPoller,
                                                        idle_poll: threading.Event, waiter: tuple[ThreadPoolExecutor, threading.Event],
                                                        age: int, refresh: bool) -> None:
    writing: threading.Event = threading.Event()
    release: threading.Event = threading.Event()
    head: Mock = Mock(side_effect=[5, 7])
    poller.connection.latest_block_number = head

    class Storage(blockchain.EventPoller.Handler):

        def on_sync(self, start: int, end: int, deposits: list[blockchain.EventDeposit], withdrawals: list[blockchain.EventWithdraw]) -> None:
            if start == 4:
                with poller.cond:
                    poller.last_check_sec = time.time() - age
                writing.set()
                assert release.wait(2)

    poller.add_handler(Storage())
    poller.off = True
    assert poller.start(poller.contract, 4)
    try:
        assert writing.wait(1)
        worker, entered = waiter
        result = worker.submit(poller.wait_sync, refresh=refresh)
        assert entered.wait(1)
        assert not result.done()
        release.set()
        assert result.result(timeout=1) is True
        assert head.call_count == 2
        assert poller.status()['synced_block'] == 7
    finally:
        release.set()


def test_refresh_does_not_interrupt_rpc_retry_delay(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch,
                                                  idle_poll: threading.Event, waiter: tuple[ThreadPoolExecutor, threading.Event]) -> None:
    retrying: threading.Event = threading.Event()
    notified: list[bool] = []
    head: Mock = Mock(side_effect=[rpc.Error(rpc.ErrorCode.GATEWAY_TIMEOUT, ()), 5])
    poller.connection.latest_block_number = head

    def wait(interval: float, condition: threading.Condition) -> None:
        if poller.error:
            with condition:
                retrying.set()
                notified.append(condition.wait(0.1))

    monkeypatch.setattr(blockchain.util, 'wait', wait)
    poller.off = True
    assert poller.start(poller.contract, 4)
    assert retrying.wait(1)
    worker, entered = waiter
    result = worker.submit(poller.wait_sync, refresh=True)
    assert entered.wait(1)
    assert result.result(timeout=1) is True
    assert notified == [False]


@pytest.mark.parametrize('state', ['connecting', 'syncing', 'retrying', 'stale'])
def test_wait_sync_resumes_only_when_ready_and_fresh(poller: blockchain.EventPoller,
                                                   waiter: tuple[ThreadPoolExecutor, threading.Event], state: str) -> None:
    poller.current        = 6
    poller.latest_block   = None if state == 'connecting' else 5
    poller.caught_up      = state != 'connecting'
    poller.error          = 'GATEWAY_TIMEOUT' if state == 'retrying' else None
    poller.last_check_sec = time.time() - 61 if state == 'stale' else time.time()
    if state == 'syncing':
        poller.current = 4
    worker, entered = waiter
    result = worker.submit(poller.wait_sync)
    assert entered.wait(1)
    assert not result.done()
    with poller.cond:
        poller.current        = 6
        poller.latest_block   = 5
        poller.caught_up      = True
        poller.error          = None
        poller.last_check_sec = time.time()
        poller.refresh_needed = False
        poller.cond.notify_all()
    assert result.result(timeout=1) is True


def test_wait_sync_cancel_exits_without_a_notification(poller: blockchain.EventPoller,
                                                      waiter: tuple[ThreadPoolExecutor, threading.Event]) -> None:
    worker, entered = waiter
    cancel: threading.Event = threading.Event()
    result = worker.submit(poller.wait_sync, cancel.is_set)
    assert entered.wait(1)
    cancel.set()
    assert result.result(timeout=1) is False


def test_wait_sync_stop_wakes_waiter(poller: blockchain.EventPoller,
                                   waiter: tuple[ThreadPoolExecutor, threading.Event]) -> None:
    worker, entered = waiter
    result = worker.submit(poller.wait_sync)
    assert entered.wait(1)
    poller.worker = threading.Thread(target=lambda: None)
    poller.worker.start()
    poller.stop()
    assert result.result(timeout=1) is False


@pytest.mark.parametrize('fail', [False, True])
def test_wait_sync_waits_for_persistence_then_catchup(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch,
                                                   waiter: tuple[ThreadPoolExecutor, threading.Event], fail: bool) -> None:
    writing: threading.Event = threading.Event()
    release: threading.Event = threading.Event()

    class Storage(blockchain.EventPoller.Handler):

        def on_sync(self, start: int, end: int, deposits: list[blockchain.EventDeposit], withdrawals: list[blockchain.EventWithdraw]) -> None:
            writing.set()
            assert release.wait(2)
            if fail:
                raise RuntimeError('database write failed')

    def wait(interval: float, condition: threading.Condition) -> None:
        if interval == poller.poll_interval:
            with condition:
                condition.wait(2)

    monkeypatch.setattr(blockchain.util, 'wait', wait)
    poller.add_handler(Storage())
    poller.off = True
    assert poller.start(poller.contract, 4)
    try:
        assert writing.wait(1)
        worker, entered = waiter
        result = worker.submit(poller.wait_sync)
        assert entered.wait(1)
        assert not result.done()
        assert poller.status()['synced_block'] == 3
        release.set()
        assert result.result(timeout=1) is (not fail)
        assert poller.status()['synced_block'] == (3 if fail else 5)
    finally:
        release.set()
        poller.stop()


def test_wait_sync_survives_rpc_retry_until_recovery(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch,
                                                   waiter: tuple[ThreadPoolExecutor, threading.Event]) -> None:
    retrying: threading.Event = threading.Event()
    release : threading.Event = threading.Event()
    latest = iter([rpc.Error(rpc.ErrorCode.GATEWAY_TIMEOUT, ()), 5])
    poller.connection.latest_block_number = lambda: next(latest)

    def wait(interval: float, condition: threading.Condition) -> None:
        if poller.error:
            retrying.set()
            assert release.wait(2)
        elif interval == poller.poll_interval:
            with condition:
                condition.wait(2)

    monkeypatch.setattr(blockchain.util, 'wait', wait)
    poller.off = True
    assert poller.start(poller.contract, 4)
    try:
        assert retrying.wait(1)
        worker, entered = waiter
        result = worker.submit(poller.wait_sync)
        assert entered.wait(1)
        assert not result.done()
        release.set()
        assert result.result(timeout=1) is True
    finally:
        release.set()
        poller.stop()


@pytest.mark.parametrize('start_block', [0, 516_873_190, 517_143_055])
def test_progress_uses_displayed_heights_independent_of_restart_start(poller: blockchain.EventPoller, start_block: int) -> None:
    poller.start_block  = start_block
    poller.current      = 517_143_056
    poller.latest_block = 517_499_325
    status: dict[str, Any] = poller.status()
    assert status['start_block'] == start_block
    assert status['synced_block'] == 517_143_055
    assert status['latest_block'] == 517_499_325
    assert status['progress'] == pytest.approx(517_143_055 / 517_499_325)
    assert round(status['progress'] * 100, 1) == 99.9


@pytest.mark.parametrize(('latest_block', 'current', 'expected'), [
    (100, 0, 0.0), (100, 101, 1.0), (100, 102, 1.0),
    (0, 0, 0.0), (0, 1, 1.0), (0, 2, 1.0),
])
def test_progress_clamps_known_heights_and_handles_genesis(poller: blockchain.EventPoller, latest_block: int, current: int, expected: float) -> None:
    poller.latest_block = latest_block
    poller.current      = current
    assert poller.status()['progress'] == expected


def test_progress_waits_for_persistence(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch) -> None:
    before_commit: list[dict[str, Any]] = []
    caught_up    : list[dict[str, Any]] = []

    class Storage(blockchain.EventPoller.Handler):

        def on_sync(self, start: int, end: int, deposits: list[blockchain.EventDeposit], withdrawals: list[blockchain.EventWithdraw]) -> None:
            before_commit.append(poller.status())

    def wait(interval: float, *args: Any) -> None:
        if interval == poller.poll_interval:
            caught_up.append(poller.status())
            poller.off = True

    poller.add_handler(Storage())
    monkeypatch.setattr(blockchain.util, 'wait', wait)
    monkeypatch.setattr(poller.cond, 'wait_for', lambda predicate, timeout: wait(timeout, poller.cond))
    poller._loop()
    assert [status['synced_block'] for status in before_commit] == [-1, 1, 3]
    assert all(not status['synchronized'] for status in before_commit)
    assert all(status['phase'] == 'syncing' and status['activity'] == 'persisting' for status in before_commit)
    assert caught_up[0]['synchronized']
    assert caught_up[0]['progress'] == 1
    assert caught_up[0]['remaining_blocks'] == 0
    assert caught_up[0]['last_check_sec'] is not None
    assert caught_up[0]['phase'] == 'ready' and caught_up[0]['activity'] == 'idle'
    assert not poller.status()['running']
    assert poller.status()['phase'] == 'stopped'


def test_initial_head_retry_has_no_progress_until_recovery(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch) -> None:
    initial: dict[str, Any] = poller.status()
    assert initial['running'] and initial['error'] is None
    assert initial['phase'] == 'connecting'
    assert initial['progress'] is initial['latest_block'] is initial['synced_block'] is None
    assert initial['remaining_blocks'] is None
    latest = iter([rpc.Error(rpc.ErrorCode.UNKNOWN, ('private request argument',), 'upstream unavailable ' + 'x' * 400), 5])
    poller.connection.latest_block_number = lambda: next(latest)
    retrying: list[dict[str, Any]] = []
    recovered: list[dict[str, Any]] = []

    class Storage(blockchain.EventPoller.Handler):

        def on_latest_block(self, block_number: int) -> None:
            recovered.append(poller.status())

    def wait(interval: float, *args: Any) -> None:
        status: dict[str, Any] = poller.status()
        if status['error']:
            retrying.append(status)
        if interval == poller.poll_interval:
            recovered.append(status)
            poller.off = True

    poller.add_handler(Storage())
    monkeypatch.setattr(blockchain.util, 'wait', wait)
    monkeypatch.setattr(poller.cond, 'wait_for', lambda predicate, timeout: wait(timeout, poller.cond))
    poller._loop()
    assert len(retrying) == 1
    assert retrying[0]['running'] and not retrying[0]['synchronized']
    assert retrying[0]['phase'] == 'retrying' and retrying[0]['activity'] == 'retry_wait'
    assert retrying[0]['progress'] is retrying[0]['latest_block'] is retrying[0]['synced_block'] is None
    assert retrying[0]['error'].startswith('UNKNOWN: upstream unavailable')
    assert len(retrying[0]['error']) == 300
    assert 'private request argument' not in retrying[0]['error']
    assert recovered[0]['error'] is None and recovered[0]['progress'] == 0
    assert recovered[0]['phase'] == 'syncing'
    assert not recovered[0]['synchronized']
    assert recovered[-1]['progress'] == 1 and recovered[-1]['synchronized']
    assert recovered[-1]['phase'] == 'ready'


def test_log_retry_pauses_progress_and_recovers_after_success(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch) -> None:
    logs = iter([rpc.Error(rpc.ErrorCode.GATEWAY_TIMEOUT, (), 'log request timed out')])
    poller.connection.log_receipt = lambda *args: next(logs, [])
    retrying: list[dict[str, Any]] = []
    recovered: list[dict[str, Any]] = []

    class Storage(blockchain.EventPoller.Handler):

        def on_sync(self, start: int, end: int, deposits: list[blockchain.EventDeposit], withdrawals: list[blockchain.EventWithdraw]) -> None:
            recovered.append(poller.status())

    def wait(interval: float, *args: Any) -> None:
        status: dict[str, Any] = poller.status()
        if status['error']:
            retrying.append(status)
        if interval == poller.poll_interval:
            poller.off = True

    poller.add_handler(Storage())
    monkeypatch.setattr(blockchain.util, 'wait', wait)
    monkeypatch.setattr(poller.cond, 'wait_for', lambda predicate, timeout: wait(timeout, poller.cond))
    poller._loop()
    assert len(retrying) == 1
    assert retrying[0]['running'] and not retrying[0]['synchronized']
    assert retrying[0]['phase'] == 'retrying' and retrying[0]['activity'] == 'retry_wait'
    assert retrying[0]['error'] == 'GATEWAY_TIMEOUT: log request timed out'
    assert retrying[0]['progress'] is None
    assert retrying[0]['latest_block'] == 5
    assert retrying[0]['synced_block'] == -1
    assert all(status['error'] is None and status['progress'] is not None for status in recovered)
    assert all(status['phase'] == 'syncing' and status['activity'] == 'persisting' for status in recovered)
    assert [status['synced_block'] for status in recovered] == [-1, 1, 3]


def test_failed_write_keeps_last_committed_block(poller: blockchain.EventPoller) -> None:
    def logs(contract: str, start: int, end: int, topics: list[HexBytes]) -> list[dict[str, Any]]:
        if topics != [blockchain.EventDeposit.event_hash()]:
            return []
        return [{
            'topics': topics + [HexBytes(bytes(32))],
            'data': HexBytes(bytes(64)),
            'blockNumber': start,
            'transactionHash': HexBytes(bytes(32)),
        }]

    poller.connection.log_receipt = logs

    class Storage(blockchain.EventPoller.Handler):

        def on_sync(self, start: int, end: int, deposits: list[blockchain.EventDeposit], withdrawals: list[blockchain.EventWithdraw]) -> None:
            if start == 2:
                raise RuntimeError('database write failed')

    poller.add_handler(Storage())
    poller._loop()
    status = poller.status()
    assert status['synced_block'] == 1
    assert status['remaining_blocks'] == 4
    assert status['error'] == 'database write failed'
    assert status['deposits'] == 1
    assert status['withdrawals'] == 0
    assert status['progress'] is None
    assert not status['synchronized']
    assert not status['running']
    assert status['phase'] == 'error' and status['activity'] == 'idle'


def test_rpc_failure_revokes_synchronized_status(poller: blockchain.EventPoller, monkeypatch: pytest.MonkeyPatch) -> None:
    latest = iter([5, rpc.Error(rpc.ErrorCode.GATEWAY_TIMEOUT, ())])
    poller.connection.latest_block_number = lambda: next(latest)
    statuses: list[dict[str, Any]] = []

    def wait(interval: float, *args: Any) -> None:
        status = poller.status()
        if interval == poller.poll_interval:
            statuses.append(status)
        elif status['error']:
            statuses.append(status)
            poller.off = True

    monkeypatch.setattr(blockchain.util, 'wait', wait)
    monkeypatch.setattr(poller.cond, 'wait_for', lambda predicate, timeout: wait(timeout, poller.cond))
    poller._loop()
    assert statuses[0]['synchronized']
    assert not statuses[1]['synchronized']
    assert statuses[1]['error'] == 'GATEWAY_TIMEOUT'
    assert statuses[1]['progress'] is None


def test_failed_catchup_callback_is_visible(poller: blockchain.EventPoller) -> None:
    class Storage(blockchain.EventPoller.Handler):

        def on_first_catchup(self) -> None:
            raise RuntimeError('catchup failed')

    poller.add_handler(Storage())
    poller._loop()
    assert poller.status()['synced_block'] == 5
    assert poller.status()['error'] == 'catchup failed'
    assert not poller.status()['synchronized']
