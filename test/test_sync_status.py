import json
from types import SimpleNamespace
from typing import Any

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
