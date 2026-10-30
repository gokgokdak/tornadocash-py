from pathlib import Path

from hexbytes import HexBytes
import pytest

import config
from components.blockchain import EventDeposit, EventWithdraw
from components.database import SQLite
from components.mytype import ChainID, Symbol, TornadoUnit


def test_event_counts_use_persisted_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chain, symbol, unit = ChainID.SEPOLIA, Symbol.ETH, TornadoUnit.UNIT_0_1
    monkeypatch.setitem(config.DATABASE_PATHS[chain][symbol], unit, str(tmp_path / 'events.sqlite'))
    db: SQLite = SQLite()
    try:
        assert db.open(chain, symbol, unit)
        assert db.get_event_counts() == (0, 0)
        deposit   : EventDeposit  = EventDeposit(1, 1, HexBytes('01' * 32), HexBytes('02' * 32), 0)
        withdrawal: EventWithdraw = EventWithdraw(2, HexBytes('03' * 32), HexBytes('04' * 32), '0x' + '00' * 20, 0)
        assert db.add_synchronized(2, [deposit], [withdrawal])
        assert db.get_event_counts() == (1, 1)
        # Re-reading a block must not inflate the UI's historical totals.
        assert db.add_synchronized(2, [deposit], [withdrawal])
        assert db.get_event_counts() == (1, 1)
    finally:
        db.close()
