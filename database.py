import os
import sqlite3
import threading
from enum import Enum
from hexbytes import HexBytes
from typing import Any

import blockchain
import config
import log
import util
from executor import Job, Queue
from mytype import ChainID, Metadata, Symbol, TornadoUnit


TABLE_STRUCTURE: dict = {
    't_event_deposit' : {
        'columns': ['timestamp', 'blk_num', 'tx_hash', 'commitment', 'leaf_index'],
        'types'  : ['INTEGER', 'INTEGER', 'TEXT', 'TEXT', 'INTEGER'],
    },
    't_event_withdraw': {
        'columns': ['blk_num', 'tx_hash', 'nullifier_hash', 'recipient', 'fee'],
        'types'  : ['INTEGER', 'TEXT', 'TEXT', 'TEXT', 'TEXT'],
    },
    't_info': {
        'columns': ['latest_blk_num', 'latest_leaf_index', 'unspent_count'],
        'types'  : ['INTEGER', 'INTEGER', 'INTEGER'],
    }
}


class Backend(Enum):
    SQLITE = 'sqlite'


class Interface(object):

    def __init__(self, backend: Backend) -> None:
        self.backend: Backend = backend

    '''
    Open or Create a database if not exists
    '''
    def open(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def check_integrity(self) -> bool:
        raise NotImplementedError

    '''
    Get latest block number
    @return Latest synced block number
            None if error occurred
    '''
    def get_latest_block_number(self) -> int | None:
        raise NotImplementedError

    '''
    Get latest leaf index
    @return Latest synced leaf index
            None if error occurred
    '''
    def get_latest_leaf_index(self) -> int | None:
        raise NotImplementedError

    '''
    Get how many deposit remain unspent
    @return Number of unspent deposits
            None if error occurred
    '''
    def get_unspent_count(self) -> int | None:
        raise NotImplementedError

    '''
    Get commitments by leaf index range
    @return List of commitments
            None if error occurred
    '''
    def get_commitments(self) -> list[HexBytes] | None:
        raise NotImplementedError

    '''
    Add synchronized events in batch
    @param  block_number    Latest synced block number, will not be updated if less or equal to current value
    @param  deposits        List of deposit events, existing events (by tx_hash and commitment) will be ignored
    @param  withdrawals     List of withdraw events, existing events (by tx_hash and nullifier_hash) will be ignored
    @return True if succeed, False otherwise
    '''
    def add_synchronized(self, block_number: int, deposits: list[blockchain.EventDeposit], withdrawals: list[blockchain.EventWithdraw]) -> bool:
        raise NotImplementedError


class SQLite(Interface):

    def __init__(self):
        super().__init__(Backend.SQLITE)
        self.TAG: str = __class__.__name__
        self.mutex      : threading.Lock            = threading.Lock()
        self.opened     : bool                      = False
        self.taskq      : Queue                     = Queue()
        self.connection : sqlite3.Connection | None = None
        self.cursor     : sqlite3.Cursor | None     = None

    def open(self, chain: ChainID, symbol: Symbol, unit: TornadoUnit) -> bool:
        meta: Metadata = util.load_metadata()[chain]
        with self.mutex:
            # Create directory recursively if not exists
            url: str = config.DATABASE_PATHS[chain][symbol][unit]
            directory: str = os.path.dirname(url)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Start worker threads
            if self.opened:
                log.warn(self.TAG, f'Already opened')
                return True
            else:
                self.taskq.start()

            # Create and open database
            def _() -> None:
                try:
                    self.connection = sqlite3.connect(url)
                    self.connection.execute('PRAGMA synchronous=NORMAL;')  # Or 'OFF' for less safety but faster
                    self.connection.execute('PRAGMA journal_mode=WAL;')
                    self.connection.execute('PRAGMA temp_store=MEMORY;')
                    for table_name, table_structure in TABLE_STRUCTURE.items():
                        sql: str = f'CREATE TABLE IF NOT EXISTS {table_name} ('
                        for column, type_ in zip(table_structure['columns'], table_structure['types']):
                            sql += f'{column} {type_}, '
                        sql = sql[:-2] + ');'
                        self.connection.execute(sql)
                    # latest_blk_num, latest_leaf_index, unspent_count
                    self.connection.execute(f'INSERT INTO t_info(latest_blk_num, latest_leaf_index, unspent_count) SELECT {meta.deployment[symbol][unit][1]}, 0, 0 WHERE NOT EXISTS (SELECT 1 FROM t_info);')
                    self.connection.commit()
                    self.cursor = self.connection.cursor()
                except Exception as e_:
                    log.error(self.TAG, f'Open database exception, error: {e_}')
                self.opened = True
            self.taskq.run_sync(Job('open', _))

            return self.opened

    def close(self) -> None:
        with self.mutex:
            if not self.opened:
                log.warn(self.TAG, f'Already closed')
                return
            def _() -> None:
                try:
                    self.cursor.close()
                    self.connection.close()
                except Exception as e:
                    log.error(self.TAG, f'Close database exception, error: {e}')
                self.opened     = False
                self.cursor     = None
                self.connection = None
            self.taskq.run_sync(Job('close', _))
            self.taskq.stop()

    def check_integrity(self) -> bool:
        sql: str = f'SELECT (COALESCE(MAX(leaf_index), -1) + 1 = COUNT(*)) AS result FROM t_event_deposit;'
        with self.mutex:
            result: list[tuple] | None = self._query(sql)
            if result is None:
                return False
            return True if 1 == result[0][0] else False

    def get_latest_block_number(self) -> int | None:
        sql: str = f'SELECT latest_blk_num FROM t_info;'
        with self.mutex:
            result: list[tuple] | None = self._query(sql)
            if result is None:
                return None
            return result[0][0]

    def get_latest_leaf_index(self) -> int | None:
        sql: str = f'SELECT latest_leaf_index FROM t_info;'
        with self.mutex:
            result: list[tuple] | None = self._query(sql)
            if result is None:
                return None
            return result[0][0]

    def get_unspent_count(self) -> int | None:
        sql: str = f'SELECT unspent_count FROM t_info;'
        with self.mutex:
            result: list[tuple] | None = self._query(sql)
            if result is None:
                return None
            return result[0][0]

    # Get commitments by leaf index range
    # @return List of commitments ordered by leaf index
    def get_commitments(self) -> list[HexBytes] | None:
        sql: str = f'SELECT commitment FROM t_event_deposit ORDER BY leaf_index ASC;'
        with self.mutex:
            result: list[tuple[str]] | None = self._query(sql)
            if result is None:
                return None
            return [HexBytes.fromhex(x[0][2:] if x[0].startswith('0x') else x[0]) for x in result]

    def add_synchronized(self, block_number: int, deposits: list[blockchain.EventDeposit], withdrawals: list[blockchain.EventWithdraw]) -> bool:
        sql: list[str] = [
            f'UPDATE t_info SET latest_blk_num = {block_number} WHERE latest_blk_num < {block_number};',
            f'UPDATE t_info SET unspent_count = unspent_count + {len(deposits)} - {len(withdrawals)};',
        ]
        leaf_index: int = -1
        for e in deposits:
            if e.leaf_index > leaf_index:
                leaf_index = e.leaf_index
            sql.append(f'INSERT INTO t_event_deposit(timestamp, blk_num, tx_hash, commitment, leaf_index) SELECT {e.timestamp}, {e.blk_num}, "{e.tx_hash.to_0x_hex()}", "{e.commitment.to_0x_hex()}", {e.leaf_index} WHERE NOT EXISTS (SELECT 1 FROM t_event_deposit WHERE tx_hash="{e.tx_hash.to_0x_hex()}" AND commitment="{e.commitment.to_0x_hex()}");')
        for e in withdrawals:
            sql.append(f'INSERT INTO t_event_withdraw(blk_num, tx_hash, nullifier_hash, recipient, fee) SELECT {e.blk_num}, "{e.tx_hash.to_0x_hex()}", "{e.nullifier_hash.to_0x_hex()}", "{e.recipient}", "{str(e.fee)}" WHERE NOT EXISTS (SELECT 1 FROM t_event_withdraw WHERE tx_hash="{e.tx_hash.to_0x_hex()}" AND nullifier_hash="{e.nullifier_hash.to_0x_hex()}");')
        if leaf_index >= 0:
            sql.append(f'UPDATE t_info SET latest_leaf_index = {leaf_index} WHERE latest_leaf_index < {leaf_index};')
        with self.mutex:
            return self._insert(sql)

    def _query(self, sql: str) -> list[Any] | None:
        if not self.opened:
            log.error(self.TAG, f'Database not opened')
            return None

        result: list[Any] | None = None
        def _() -> None:
            nonlocal result
            try:
                self.cursor.execute(sql)
                result = self.cursor.fetchall()
            except Exception as e:
                log.error(self.TAG, f'Query exception, sql: {sql}, error: {e}')
        self.taskq.run_sync(Job('Query', _))

        return result

    def _insert(self, sql: list[str]) -> bool:
        if not self.opened:
            log.error(self.TAG, f'Database not opened')
            return False

        succeed: bool = True
        def _() -> None:
            nonlocal succeed
            try:
                for q in sql:
                    self.cursor.execute(q)
                self.connection.commit()
            except Exception as e:
                log.error(self.TAG, f'Insert exception, sql: {sql}, error: {e}')
                self.connection.rollback()
                succeed = False
        self.taskq.run_sync(Job('Insert', _))

        return succeed


def create(backend: Backend) -> Interface:
    if backend == Backend.SQLITE:
        return SQLite()
    else:
        raise NotImplementedError
