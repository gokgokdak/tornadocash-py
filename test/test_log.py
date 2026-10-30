from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import Mock

import pytest

from components import log


@pytest.fixture
def logger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[log.Logger]:
    instance: log.Logger = log.Logger(str(tmp_path), 'test')
    monkeypatch.setattr(log.Instance, 'obj', instance)
    yield instance
    instance.file.close()


def write(logger: log.Logger, message: str | list[str], level: log.Level = log.Level.INFO) -> None:
    logger.log(level, 'test', message, log.Color.CYAN, log.Style.BOLD, 'source.py', 12)


def test_uninitialized_logger_has_no_recent_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(log.Instance, 'obj', None)
    assert log.get_recent() == []


def test_recent_messages_are_ordered_incremental_copies(logger: log.Logger) -> None:
    write(logger, ['first', 'second'])
    write(logger, 'third', log.Level.ERROR)
    records: list[dict] = log.get_recent()
    assert [record['id'] for record in records] == [1, 2, 3]
    assert [record['level'] for record in records] == ['I', 'I', 'E']
    assert all('test] ' in record['text'] and ' (source.py:12)' in record['text'] for record in records)
    assert [record['id'] for record in log.get_recent(1)] == [2, 3]
    assert log.get_recent(3) == []
    records[0]['text'] = 'changed by reader'
    assert 'first' in log.get_recent()[0]['text']


def test_recent_messages_keep_only_the_latest_500(logger: log.Logger) -> None:
    for index in range(600):
        write(logger, str(index))
    records: list[dict] = log.get_recent()
    assert len(records) == 500
    assert [record['id'] for record in records] == list(range(101, 601))
    assert [record['id'] for record in log.get_recent(598)] == [599, 600]


def test_filtered_levels_do_not_enter_recent_messages(logger: log.Logger) -> None:
    logger.set_level(log.Level.WARN)
    write(logger, 'filtered info')
    write(logger, 'filtered debug', log.Level.DEBUG)
    write(logger, 'warning', log.Level.WARN)
    write(logger, 'error', log.Level.ERROR)
    records: list[dict] = log.get_recent()
    assert [(record['id'], record['level']) for record in records] == [(1, 'W'), (2, 'E')]
    assert 'filtered' not in Path(logger.file.name).read_text()


def test_history_limit_preserves_original_console_and_file_output(logger: log.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    console = Mock()
    monkeypatch.setattr(log, 'STDOUT', SimpleNamespace(writelines=console))
    logger.console(True)
    message: str = 'x' * 5000
    write(logger, message)
    record: dict = log.get_recent()[0]
    file_text: str = Path(logger.file.name).read_text()
    console_text: str = ''.join(console.call_args.args[0])
    assert len(record['text']) == 4096
    assert record['text'] == file_text[:4096]
    assert '\x1b[' not in record['text'] and '\x1b[' not in file_text
    assert file_text.endswith(message + ' (source.py:12)\n')
    assert '\x1b[1;36m' + message + '\x1b[0m' in console_text
    assert ' (source.py:12)' in console_text


def test_readers_receive_consistent_snapshots_during_concurrent_writes(logger: log.Logger) -> None:
    def write_batch(worker: int) -> None:
        for index in range(50):
            write(logger, f'{worker}:{index}')

    with ThreadPoolExecutor(max_workers=4) as workers:
        writers = [workers.submit(write_batch, worker) for worker in range(4)]
        while any(not writer.done() for writer in writers):
            records: list[dict] = log.get_recent()
            ids: list[int] = [record['id'] for record in records]
            assert ids == list(range(1, len(ids) + 1))
            Event().wait(0.001)
        for writer in writers:
            writer.result()
    assert [record['id'] for record in log.get_recent()] == list(range(1, 201))
