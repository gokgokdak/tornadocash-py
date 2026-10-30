from threading import Event, Lock
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

from hexbytes import HexBytes
import pytest

from components import core, merkle_tree
from components.mytype import ChainID, CircuitInput, Key, MerkleProof, Note, Second, Symbol, TornadoUnit


ACCOUNT = '0x' + '11' * 20
RECIPIENT = '0x' + '22' * 20
HASH = HexBytes('0x' + '44' * 32)


@pytest.fixture
def note() -> Note:
    return Note(bytearray.fromhex('11' * 31), bytearray.fromhex('22' * 31))


@pytest.fixture
def tornado(monkeypatch: pytest.MonkeyPatch) -> core.Tornado:
    instance: core.Tornado = object.__new__(core.Tornado)
    instance.external: bool = True
    instance.tag     : str  = 'test'
    instance.chain, instance.symbol, instance.unit = ChainID.ETHEREUM, Symbol.ETH, TornadoUnit.UNIT_1
    instance.note_deposited, instance.note_withdrawn = Mock(return_value=False), Mock(return_value=False)
    instance.token_contract, instance.deployment_contract, instance.proxy_contract = object(), object(), object()
    instance.proxy_address, instance.deployment_address = RECIPIENT, ACCOUNT
    instance.meta = SimpleNamespace(decimals={Symbol.ETH: 18, Symbol.DAI: 18})
    instance.mutex, instance.sync_only, instance.handlers, instance.initialized = Lock(), False, [], True
    instance.last_update_sec = None
    instance.db = SimpleNamespace(get_commitments=Mock(return_value=[]), add_synchronized=Mock(return_value=True), close=Mock())
    instance.tree = SimpleNamespace(get_index=Mock(return_value=0), add=Mock(),
                                    get_merkle_proof=Mock(return_value=MerkleProof(HexBytes('0x' + '33' * 32))))
    proof: dict[str, Any] = {'solidity': {'proof': '0x01', 'publicSignals': ['0x00'] * 6}}
    instance.zksnark = SimpleNamespace(prove=Mock(return_value=proof), verify=Mock(return_value=True))
    instance.connection = SimpleNamespace(nonce=Mock(return_value=0), gas_price=Mock(return_value=1),
                                          sign_transaction=Mock(), send_transaction=Mock())
    monkeypatch.setattr(core.rpc, 'contract_build_tx', Mock(side_effect=lambda contract, method, tx, *args:
                        {**tx, 'to': RECIPIENT, 'data': b'\x01'}))
    monkeypatch.setattr(core.rpc, 'contract_call', Mock(return_value=True))
    return instance


def test_deposit_builds_an_unsigned_native_transaction(tornado: core.Tornado, note: Note) -> None:
    tx = tornado.deposit_tx(note.commitment, ACCOUNT)
    assert tx == {'from': ACCOUNT, 'to': RECIPIENT, 'chainId': 1, 'nonce': 0, 'value': 10 ** 18, 'data': b'\x01'}
    tornado.note_deposited.assert_not_called()
    core.rpc.contract_call.assert_not_called()
    tornado.connection.sign_transaction.assert_not_called()
    tornado.connection.send_transaction.assert_not_called()


def test_deposit_reports_only_the_steps_it_runs(tornado: core.Tornado, note: Note) -> None:
    messages: list[str] = []
    tornado.handlers = [SimpleNamespace(on_progress=messages.append)]

    assert tornado.deposit_tx(note.commitment, ACCOUNT) is not None
    assert messages == ['Fetching deposit transaction nonce', 'Building deposit transaction']
    messages.clear()
    assert tornado.deposit_tx(note.commitment, ACCOUNT, nonce=7) is not None
    assert messages == ['Building deposit transaction']
    tornado.connection.nonce.assert_called_once_with(ACCOUNT)


def test_progress_uses_a_handler_snapshot(tornado: core.Tornado) -> None:
    observe: Mock = Mock()
    tornado.handlers = [SimpleNamespace(on_progress=lambda _: tornado.handlers.clear()), SimpleNamespace(on_progress=observe)]
    tornado._progress('Building deposit transaction')
    observe.assert_called_once_with('Building deposit transaction')
    assert not tornado.handlers


def test_erc20_builds_without_preflight_queries_or_automatic_approval(tornado: core.Tornado, note: Note) -> None:
    tornado.symbol = Symbol.DAI
    tx = tornado.deposit_tx(note.commitment, ACCOUNT)
    assert 'value' not in tx
    assert core.rpc.contract_build_tx.call_args.args[1] == 'deposit'
    core.rpc.contract_build_tx.assert_called_once()
    core.rpc.contract_call.assert_not_called()
    tornado.note_deposited.assert_not_called()
    tornado.connection.sign_transaction.assert_not_called()
    tornado.connection.send_transaction.assert_not_called()
    assert tornado.approve_tx(ACCOUNT)['chainId'] == 1
    assert core.rpc.contract_build_tx.call_args.args[1] == 'approve'


@pytest.mark.parametrize(('deposited', 'withdrawn'), [(False, False), (True, True), (None, False), (True, None)])
def test_prepare_uses_local_tree_without_chain_queries(tornado: core.Tornado, note: Note, deposited: bool | None, withdrawn: bool | None) -> None:
    tornado.note_deposited.return_value = deposited
    tornado.note_withdrawn.return_value = withdrawn
    core.rpc.contract_call.return_value = core.rpc.Error(core.rpc.ErrorCode.UNKNOWN, ())
    assert tornado.prepare_withdraw(note, RECIPIENT) is not None
    tornado.note_deposited.assert_not_called()
    tornado.note_withdrawn.assert_not_called()
    core.rpc.contract_call.assert_not_called()
    tornado.zksnark.prove.assert_called_once()
    tornado.zksnark.verify.assert_called_once()


def test_explicit_full_init_builds_tree_atomically_and_future_sync_appends(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    tree, tornado.tree = tornado.tree, None
    tornado.sync_only = True
    tornado.db.get_commitments.return_value = [note.commitment]

    def create(*args: Any) -> SimpleNamespace:
        assert tornado.mutex.locked()
        assert args[2] == [note.commitment]
        return tree

    monkeypatch.setattr(core.merkle_tree, 'create', create)
    assert tornado.init(sync_only=False)
    assert tornado.tree is tree and tornado.sync_only is False
    assert tornado.init(sync_only=False) and tornado.init(sync_only=True)
    tornado.db.get_commitments.assert_called_once()
    merkle_proof, proof = tornado.prepare_withdraw(note, RECIPIENT)
    circuit = tornado.zksnark.prove.call_args.args[0]
    assert circuit.recipient == RECIPIENT and circuit.fee == 0 and circuit.refund == 0
    assert circuit.relayer == '0x' + '00' * 20
    tornado.zksnark.verify.assert_called_once_with(proof)
    core.rpc.contract_call.assert_not_called()
    commitment = HexBytes('0x55')
    tornado.on_sync(100, 101, [SimpleNamespace(commitment=commitment)], [])
    tree.add.assert_called_once_with(commitment)
    tx = tornado.withdraw_tx(note, ACCOUNT, RECIPIENT, merkle_proof, proof)
    assert tx['from'] == ACCOUNT
    tornado.connection.sign_transaction.assert_not_called()


def test_tree_initialization_forwards_real_layer_progress(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    tornado.handlers = [SimpleNamespace(on_progress=messages.append)]
    tornado.sync_only, tornado.tree = True, None
    tornado.db.get_commitments.return_value = [note.commitment]
    monkeypatch.setattr(core.config, 'MERKLE_TREE_HEIGHT', 3)
    assert tornado.init(sync_only=False)
    assert messages == ['Reading commitments from database', 'Preparing Merkle tree',
                        'Rebuilding Merkle tree: level 1/3 · 0/1 nodes', 'Rebuilding Merkle tree: level 1/3 · 1/1 nodes',
                        'Rebuilding Merkle tree: level 2/3 · 0/1 nodes', 'Rebuilding Merkle tree: level 2/3 · 1/1 nodes',
                        'Rebuilding Merkle tree: level 3/3 · 0/1 nodes', 'Rebuilding Merkle tree: level 3/3 · 1/1 nodes',
                        'Merkle tree ready']
    assert tornado.tree.size() == 1 and not tornado.sync_only


@pytest.mark.parametrize('with_deposit', [False, True])
def test_sync_records_update_time_before_notifying(tornado: core.Tornado, monkeypatch: pytest.MonkeyPatch, with_deposit: bool) -> None:
    updated: Second = Second(1234)
    clock: Mock = Mock(return_value=updated)
    handler: Mock = Mock(side_effect=lambda *args: observed.append(tornado.last_update_sec))
    observed: list[Second | None] = []
    tornado.handlers = [SimpleNamespace(on_sync=handler)]
    monkeypatch.setattr(core.util, 'unix_timestamp', clock)
    deposits: list = [SimpleNamespace(commitment=HexBytes('0x55'))] if with_deposit else []
    tornado.on_sync(100, 101, deposits, [])
    assert tornado.last_update_sec == updated
    assert observed == [updated]
    clock.assert_called_once_with()
    handler.assert_called_once_with(100, 101, deposits, [])


@pytest.mark.parametrize('failure', ['database', 'tree', 'rejected_append'])
def test_failed_sync_keeps_previous_update_time(tornado: core.Tornado, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    tornado.last_update_sec = Second(1234)
    clock: Mock = Mock(return_value=Second(5678))
    handler: Mock = Mock()
    tornado.handlers = [SimpleNamespace(on_sync=handler)]
    monkeypatch.setattr(core.util, 'unix_timestamp', clock)
    if failure == 'database':
        tornado.db.add_synchronized.return_value = False
    elif failure == 'tree':
        tornado.tree.add.side_effect = RuntimeError('tree update failed')
    else:
        tornado.tree.add.return_value = False
    with pytest.raises(RuntimeError):
        tornado.on_sync(100, 101, [SimpleNamespace(commitment=HexBytes('0x55'))], [])
    assert tornado.last_update_sec == Second(1234)
    clock.assert_not_called()
    handler.assert_not_called()


@pytest.mark.parametrize('failure', [None, ValueError('invalid leaves')])
def test_failed_full_init_keeps_sync_only_mode(tornado: core.Tornado, monkeypatch: pytest.MonkeyPatch, failure: ValueError | None) -> None:
    tornado.sync_only, tornado.tree = True, None
    if failure is None:
        tornado.db.get_commitments.return_value = None
    else:
        monkeypatch.setattr(core.merkle_tree, 'create', Mock(side_effect=failure))
    assert not tornado.init(sync_only=False)
    assert tornado.initialized and tornado.sync_only and tornado.tree is None
    tornado.db.close.assert_not_called()


def test_concurrent_full_init_builds_only_one_tree(tornado: core.Tornado, monkeypatch: pytest.MonkeyPatch) -> None:
    tree, tornado.tree = tornado.tree, None
    tornado.sync_only = True
    create = Mock(return_value=tree)
    monkeypatch.setattr(core.merkle_tree, 'create', create)
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert all(workers.map(lambda _: tornado.init(sync_only=False), range(2)))
    create.assert_called_once()
    assert tornado.tree is tree and not tornado.sync_only


@pytest.mark.parametrize('sync_only', [True, False])
def test_initialization_builds_tree_only_when_explicitly_requested(tornado: core.Tornado, monkeypatch: pytest.MonkeyPatch, sync_only: bool) -> None:
    tree, tornado.tree = tornado.tree, None
    tornado.initialized = False
    tornado.connection.started = Mock(return_value=True)
    tornado.db.open, tornado.db.check_integrity = Mock(return_value=True), Mock(return_value=True)
    tornado.poller = SimpleNamespace(add_handler=Mock())
    create = Mock(return_value=tree)
    monkeypatch.setattr(core.merkle_tree, 'create', create)
    assert tornado.init(sync_only=sync_only)
    assert tornado.sync_only == sync_only
    assert create.call_count == (0 if sync_only else 1)
    assert tornado.init(sync_only=False)
    assert tornado.tree is tree and not tornado.sync_only
    create.assert_called_once()
    tornado.poller.add_handler.assert_called_once_with(tornado)


def test_sync_only_mode_never_prepares_or_submits_withdrawals(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    tornado.sync_only, tornado.tree = True, None
    get = Mock()
    monkeypatch.setattr(core.requests, 'get', get)
    assert tornado.prepare_withdraw(note, RECIPIENT) is None
    assert tornado.withdraw(note, RECIPIENT, 'https://relayer.example') is None
    tornado.db.get_commitments.assert_not_called()
    tornado.zksnark.prove.assert_not_called()
    get.assert_not_called()


@pytest.mark.parametrize('missing', ['index', 'proof'])
def test_prepare_rejects_missing_local_deposit(tornado: core.Tornado, note: Note, missing: str) -> None:
    if missing == 'index':
        tornado.tree.get_index.return_value = None
    else:
        tornado.tree.get_merkle_proof.return_value = None
    assert tornado.prepare_withdraw(note, RECIPIENT) is None
    tornado.zksnark.prove.assert_not_called()


def test_snapshot_excludes_sync_but_proving_allows_sync_to_continue(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    tree: merkle_tree.Memory = merkle_tree.Memory(3, [note.commitment])
    tornado.tree = tree
    taking_snapshot, release_snapshot, sync_started, sync_done = Event(), Event(), Event(), Event()
    snapshots: list[tuple[MerkleProof, tuple]] = []
    original_snapshot = tree.get_merkle_proof
    proof: dict[str, Any] = tornado.zksnark.prove.return_value

    def snapshot(index: int) -> MerkleProof:
        assert tornado.mutex.locked()
        taking_snapshot.set()
        assert release_snapshot.wait(2)
        merkle_proof: MerkleProof = original_snapshot(index)
        snapshots.append((merkle_proof, (merkle_proof.root, tuple(merkle_proof.path_nodes), tuple(merkle_proof.path_indices))))
        return merkle_proof

    def sync() -> None:
        sync_started.set()
        tornado.on_sync(100, 101, [SimpleNamespace(commitment=HexBytes((1).to_bytes(32, 'big')))], [])
        sync_done.set()

    def prove(circuit: CircuitInput) -> dict[str, Any]:
        assert sync_done.wait(2)
        merkle_proof, before = snapshots[0]
        assert circuit.merkle_proof is merkle_proof
        assert (merkle_proof.root, tuple(merkle_proof.path_nodes), tuple(merkle_proof.path_indices)) == before
        assert tree.root() != merkle_proof.root
        return proof

    monkeypatch.setattr(tree, 'get_merkle_proof', snapshot)
    tornado.zksnark.prove.side_effect = prove
    with ThreadPoolExecutor(max_workers=2) as workers:
        preparing = workers.submit(tornado.prepare_withdraw, note, RECIPIENT)
        assert taking_snapshot.wait(1)
        synchronizing = workers.submit(sync)
        try:
            assert sync_started.wait(1)
            assert not sync_done.wait(0.03)
            tornado.db.add_synchronized.assert_not_called()
        finally:
            release_snapshot.set()
        assert preparing.result(timeout=3) == (snapshots[0][0], proof)
        synchronizing.result(timeout=1)
    assert tree.size() == 2
    tornado.note_withdrawn.assert_not_called()
    core.rpc.contract_call.assert_not_called()


def test_prepare_rejects_invalid_proof(tornado: core.Tornado, note: Note) -> None:
    tornado.zksnark.verify.return_value = False
    assert tornado.prepare_withdraw(note, RECIPIENT) is None
    core.rpc.contract_call.assert_not_called()


@pytest.mark.parametrize('proof_available', [True, False])
def test_proof_progress_precedes_work_and_stops_on_failure(tornado: core.Tornado, note: Note, proof_available: bool) -> None:
    messages: list[str] = []
    tornado.handlers = [SimpleNamespace(on_progress=messages.append)]
    proof: dict[str, Any] = tornado.zksnark.prove.return_value

    def prove(circuit: CircuitInput) -> dict[str, Any] | None:
        assert messages[-1] == 'Generating zero-knowledge proof'
        assert not tornado.mutex.locked()
        return proof if proof_available else None

    def verify(value: dict[str, Any]) -> bool:
        assert messages[-1] == 'Verifying zero-knowledge proof'
        return value is proof

    tornado.zksnark.prove.side_effect = prove
    tornado.zksnark.verify.side_effect = verify
    prepared = tornado.prepare_withdraw(note, RECIPIENT)
    assert (prepared is not None) == proof_available
    expected: list[str] = ['Reading Merkle path', 'Generating zero-knowledge proof']
    if proof_available:
        expected += ['Verifying zero-knowledge proof']
    else:
        tornado.zksnark.verify.assert_not_called()
    assert messages == expected


def test_withdraw_rejects_invalid_key_or_relayer_type(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    get = Mock()
    monkeypatch.setattr(core.requests, 'get', get)
    assert tornado.withdraw(note, RECIPIENT, None) is None
    get.assert_not_called()


def relayer_requests(tornado: core.Tornado, monkeypatch: pytest.MonkeyPatch, reward_account: str = RECIPIENT) -> tuple[Mock, Mock]:
    status: dict[str, Any] = {'netId': 1, 'rewardAccount': reward_account,
              'instances': {'eth': {'instanceAddress': {'1': ACCOUNT}}}}
    get : Mock = Mock(side_effect=[
        SimpleNamespace(status_code=200, json=lambda: status),
        SimpleNamespace(status_code=200, json=lambda: {'status': 'CONFIRMED', 'txHash': HASH.to_0x_hex()}),
    ])
    post: Mock = Mock(return_value=SimpleNamespace(status_code=200, json=lambda: {'id': 'job'}))
    monkeypatch.setattr(core.requests, 'get', get)
    monkeypatch.setattr(core.requests, 'post', post)
    monkeypatch.setattr(core, 'wait', lambda seconds: None)
    return get, post


def test_relayer_reuses_preparation_after_explicit_full_init(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    get, post = relayer_requests(tornado, monkeypatch)
    tornado.sync_only = True
    assert tornado.init(sync_only=False)
    assert tornado.withdraw(note, RECIPIENT, 'https://relayer.example', can_submit=lambda: True) == HASH
    assert tornado.sync_only is False
    tornado.zksnark.prove.assert_called_once()
    assert all('timeout' not in call.kwargs for call in get.call_args_list + post.call_args_list)
    tornado.connection.send_transaction.assert_not_called()


@pytest.mark.parametrize('url', ['http://user:password@relayer.example', 'httpx://relayer.example'])
def test_relayer_url_is_passed_to_requests(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    get, post = relayer_requests(tornado, monkeypatch)
    assert tornado.withdraw(note, RECIPIENT, url) == HASH
    assert get.call_args_list[0].args == (url + '/status',)
    assert get.call_args_list[1].args == (url + '/v1/jobs/job',)
    assert post.call_args.kwargs['url'] == url + '/v1/tornadoWithdraw'


def test_relayer_reward_account_is_used_as_returned(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    reward_account: str = '0x' + 'ab' * 20
    get, post = relayer_requests(tornado, monkeypatch, reward_account)
    assert tornado.withdraw(note, RECIPIENT, 'https://relayer.example') == HASH
    assert tornado.zksnark.prove.call_args.args[0].relayer == reward_account
    assert post.call_args.kwargs['json']['args'][3] == reward_account


@pytest.mark.parametrize('failure', ['status_http', 'instance', 'status_format', 'submit_http', 'job_http', 'tx_hash'])
def test_relayer_errors_keep_response_details(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    get, post = relayer_requests(tornado, monkeypatch)
    responses: list = list(get.side_effect)
    response: Any = post.return_value if failure == 'submit_http' else responses[1 if failure in ('job_http', 'tx_hash') else 0]
    if failure.endswith('_http'):
        response.status_code, response.text = 503, 'relayer diagnostic details'
        details: str = response.text
    else:
        result: dict = response.json()
        del result[{'instance': 'instances', 'status_format': 'rewardAccount', 'tx_hash': 'txHash'}[failure]]
        response.json = lambda: result
        details = str(result)
    get.side_effect = responses
    error: Mock = Mock()
    monkeypatch.setattr(core.log, 'error', error)
    assert tornado.withdraw(note, RECIPIENT, 'https://relayer.example') is None
    assert any('response: ' + details in call.args[1] for call in error.call_args_list)


def test_direct_withdraw_still_signs_and_sends(tornado: core.Tornado, note: Note) -> None:
    key: Key = Key('11' * 32)
    tornado.connection.send_transaction.return_value = HASH
    assert tornado.withdraw(note, RECIPIENT, key) == HASH
    tornado.connection.nonce.assert_called_once_with(key.eth_address())
    tornado.connection.sign_transaction.assert_called_once()
    tornado.connection.send_transaction.assert_called_once_with(tornado.connection.sign_transaction.return_value)
    tornado.zksnark.prove.assert_called_once()
    tornado.zksnark.verify.assert_called_once()
    tornado.note_deposited.assert_not_called()
    tornado.note_withdrawn.assert_not_called()
    core.rpc.contract_call.assert_not_called()


def test_relayer_reports_submission_and_job_stages(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    get, post = relayer_requests(tornado, monkeypatch)
    messages: list[str] = []
    tornado.handlers = [SimpleNamespace(on_progress=messages.append)]
    response: Any = post.return_value

    def submit(*args: Any, **kwargs: Any) -> Any:
        assert messages[-1] == 'Submitting withdrawal to relayer'
        return response

    post.side_effect = submit
    assert tornado.withdraw(note, RECIPIENT, 'https://relayer.example') == HASH
    assert messages[:2] == ['Fetching relayer status', 'Calculating relayer fee']
    assert messages[-4:] == ['Submitting withdrawal to relayer', 'Waiting for relayer job',
                             'Checking relayer job: attempt 1/10', 'Relayer job: confirmed']
    assert all(RECIPIENT not in message and 'relayer.example' not in message for message in messages)


def test_relayer_checks_cancellation_after_reporting_submission(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    get, post = relayer_requests(tornado, monkeypatch)
    ready: list[bool] = [True]

    def progress(message: str) -> None:
        if message == 'Submitting withdrawal to relayer':
            ready[0] = False

    tornado.handlers = [SimpleNamespace(on_progress=progress)]
    assert tornado.withdraw(note, RECIPIENT, 'https://relayer.example', can_submit=lambda: ready[0]) is None
    post.assert_not_called()


def test_relayer_cannot_submit_after_proving_changes_sync_state(tornado: core.Tornado, note: Note, monkeypatch: pytest.MonkeyPatch) -> None:
    get, post = relayer_requests(tornado, monkeypatch)
    ready = [True]
    proof = tornado.zksnark.prove.return_value

    def prove(circuit: CircuitInput) -> dict[str, Any]:
        ready[0] = False
        return proof

    tornado.zksnark.prove.side_effect = prove
    assert tornado.withdraw(note, RECIPIENT, 'https://relayer.example', can_submit=lambda: ready[0]) is None
    tornado.zksnark.verify.assert_called_once()
    get.assert_called_once_with('https://relayer.example/status')
    post.assert_not_called()
