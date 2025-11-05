import threading
from abc import ABC, abstractmethod
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from web3.types import LogReceipt, Wei

import config
import log
import rpc
import util
from mytype import ChainID


class LogEvent(ABC):

    def __init__(self, signature: str) -> None:
        self.signature: str = signature

    def __str__(self) -> str:
        raise NotImplementedError

    def __dict__(self) -> dict:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load(cls, _dict: dict):
        pass

    @classmethod
    @abstractmethod
    def event_name(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def event_hash(cls) -> HexBytes:
        pass


class EventDeposit(LogEvent):

    def __init__(self, timestamp : int = None,
                       blk_num   : int = None,
                       tx_hash   : HexBytes = None,
                       commitment: HexBytes = None,
                       leaf_index: int = None) -> None:
        super().__init__('Deposit(bytes32,uint32,uint256)')
        self.timestamp : int      = timestamp
        self.blk_num   : int      = blk_num
        self.tx_hash   : HexBytes = tx_hash
        self.commitment: HexBytes = commitment
        self.leaf_index: int      = leaf_index

    def __str__(self) -> str:
        return (f'timestamp={self.timestamp}, '
                f'blk_num={self.blk_num}, '
                f'tx_hash={self.tx_hash}, '
                f'commitment={self.commitment}, '
                f'leaf_index={self.leaf_index}')

    def __dict__(self) -> dict:
        return {
            'timestamp' : self.timestamp,
            'blk_num'   : self.blk_num,
            'tx_hash'   : self.tx_hash,
            'commitment': self.commitment,
            'leaf_index': self.leaf_index,
        }

    @classmethod
    def load(cls, _dict: dict) -> 'EventDeposit':
        return EventDeposit(
            _dict['timestamp'],
            _dict['blk_num'],
            _dict['tx_hash'],
            _dict['commitment'],
            _dict['leaf_index'])

    @classmethod
    def event_name(cls) -> str:
        return 'Deposit'

    @classmethod
    def event_hash(cls) -> HexBytes:
        return Web3.keccak(text='Deposit(bytes32,uint32,uint256)')


class EventWithdraw(LogEvent):

    def __init__(self, blk_num       : int = None,
                       tx_hash       : HexBytes = None,
                       nullifier_hash: HexBytes = None,
                       recipient     : ChecksumAddress = None,
                       fee           : Wei = None) -> None:
        super().__init__('Withdrawal(address,bytes32,address,uint256)')
        self.blk_num       : int             = blk_num
        self.tx_hash       : HexBytes        = tx_hash
        self.nullifier_hash: HexBytes        = nullifier_hash
        self.recipient     : ChecksumAddress = recipient
        self.fee           : Wei             = fee

    def __str__(self) -> str:
        return (f'blk_num={self.blk_num}, '
                f'tx_hash={self.tx_hash}, '
                f'nullifier_hash={self.nullifier_hash}, '
                f'recipient={self.recipient}, '
                f'fee={self.fee}')

    def __dict__(self) -> dict:
        return {
            'blk_num'       : self.blk_num,
            'tx_hash'       : self.tx_hash,
            'nullifier_hash': self.nullifier_hash,
            'recipient'     : self.recipient,
            'fee'           : self.fee,
        }

    @classmethod
    def load(cls, _dict: dict) -> 'EventWithdraw':
        return EventWithdraw(
            _dict['blk_num'],
            _dict['tx_hash'],
            _dict['nullifier_hash'],
            _dict['recipient'],
            _dict['fee'])

    @classmethod
    def event_name(cls) -> str:
        return 'Withdraw'

    @classmethod
    def event_hash(cls) -> HexBytes:
        return Web3.keccak(text='Withdrawal(address,bytes32,address,uint256)')


class EventPoller(object):

    class Handler(object):

        def on_first_catchup(self) -> None:
            """Called when the first catchup is done."""
            pass

        def on_sync(self, block_from: int, block_to: int, deposits: list[EventDeposit], withdrawals: list[EventWithdraw]) -> None:
            """Called when a sync is done."""
            pass

        def on_latest_block(self, block_number: int) -> None:
            """Called when the latest block number is updated."""
            pass

    def __init__(self, chain: ChainID, connection: rpc.Interface | None = None) -> None:
        self.tag        : str                       = f'{__class__.__name__}'
        self.off        : bool                      = True
        self.chain      : ChainID                   = chain
        self.connection : rpc.Interface | None      = connection  # If True, the RPC connection is managed outside
        self.external   : bool                      = connection is not None
        self.meta       : util.Metadata             = util.load_metadata()[chain]
        self.contract   : ChecksumAddress | None    = None
        self.events     : list[LogEvent]            = [EventDeposit(), EventWithdraw()]
        self.current    : int                       = 0
        self.cond       : threading.Condition       = threading.Condition()
        self.worker     : threading.Thread | None   = None
        self.handlers    : list[EventPoller.Handler] = []
        if self.connection is None:
            self.connection = rpc.Connection(self.chain, config.RPC_URLS[self.chain])

    '''
    Start polling
    @param contract     Contract addresses
    @param start_block  Start from which block number (inclusive)
    '''
    def start(self, contract: ChecksumAddress, start_block: int) -> bool:
        if not self.off:
            log.warn(self.tag, 'start() already started')
            return False
        if not self.external:
            if not self.connection.start():
                log.error(self.tag, f'Failed to start RPC connection for {self.chain}')
                return False
        elif not self.connection.started():
            log.error(self.tag, 'The external RPC connection is not started')
            return False
        self.off      = False
        self.contract = contract
        self.current  = start_block
        self.worker   = threading.Thread(target=self._loop)
        self.worker.start()
        log.debug(self.tag, f'start(contract={contract}, start_block={start_block}, events={[e.event_name() for e in self.events]})')
        return True

    def stop(self) -> None:
        if self.off:
            log.warn(self.tag, 'stop() already stopped')
            return
        log.debug(self.tag, 'stop() shutting down')
        self.off = True
        with self.cond:
            self.cond.notify_all()
        self.worker.join()
        if not self.external:
            if self.connection.started():
                self.connection.stop()
        self.worker     = None
        self.contract   = None
        log.debug(self.tag, 'stop() done')

    def is_started(self) -> bool:
        return not self.off

    def add_handler(self, handler: Handler) -> None:
        with self.cond:
            self.handlers.append(handler)

    def remove_all_handlers(self) -> None:
        with self.cond:
            self.handlers.clear()

    def _loop(self) -> None:
        first_loop: bool = True
        while not self.off:
            latest: int | rpc.Error = 0
            # Get latest block number
            while not self.off:
                latest = self.connection.latest_block_number()
                if not rpc.IsError(latest):
                    break
                log.error(self.tag, f'Failed to get latest block number, error: {latest.msg}')
                log.info(self.tag, f'Wait {config.RPC_RETRY_INTERVAL_SEC}s and retry')
                util.wait(config.RPC_RETRY_INTERVAL_SEC, self.cond)
            count_block: int = latest - self.current + 1

            # Notify latest block number
            for h in self.handlers:
                h.on_latest_block(latest)
            # Log how many blocks behind
            if first_loop:
                log.info(self.tag, f'{count_block} blocks behind, latest block number: {latest}')

            # Split into N blocks per request
            batch_size : int = config.BLOCKCHAIN_LOG_EVENT_POLL_BLOCKS_PER_REQUEST[self.chain]
            batch_count: int = count_block // batch_size
            residual   : int = count_block  % batch_size
            chunks     : list[tuple[int, int]] = [(self.current + i * batch_size, self.current + (i + 1) * batch_size - 1) for i in range(batch_count)]
            if residual > 0:
                chunks.append((self.current + batch_count * batch_size, self.current + batch_count * batch_size + residual - 1))

            # Process each chunk
            break_early : bool = False
            for chunk in chunks:
                deposits      : list[EventDeposit]  = []
                withdrawals   : list[EventWithdraw] = []
                count_deposit : int = 0
                count_withdraw: int = 0
                if self.off:
                    break_early = True
                    break
                # Get event logs
                event_logs: list[LogReceipt] = []
                for expected in self.events:
                    result: list[LogReceipt] | rpc.Error = self.connection.log_receipt(ChecksumAddress(self.contract), chunk[0], chunk[1], [expected.event_hash()])
                    while not self.off:
                        if not rpc.IsError(result):
                            break
                        log.error(self.tag, f'Failed to get logs for event {expected.event_hash().to_0x_hex()}, error: {result.msg}')
                        log.info(self.tag, f'Wait {config.RPC_RETRY_INTERVAL_SEC}s and retry')
                        util.wait(config.RPC_RETRY_INTERVAL_SEC, self.cond)
                        result = self.connection.log_receipt(ChecksumAddress(self.contract), chunk[0], chunk[1], [expected.event_hash()])
                    if not rpc.IsError(result):
                        event_logs.extend(result if result is not None else [])
                    if self.off:
                        break
                    util.wait(config.RPC_RETRY_INTERVAL_SEC, self.cond)
                if self.off:
                    break_early = True
                    break

                # Process event logs
                for event in event_logs:
                    if EventDeposit.event_hash() == event['topics'][0]:
                        deposits.append(EventDeposit(
                            int.from_bytes(event['data'][32:64], byteorder='big'),  # timestamp
                            event['blockNumber'],                                   # blk_num
                            event['transactionHash'],                               # tx_hash
                            event['topics'][1],                                     # commitment
                            int.from_bytes(event['data'][:32], byteorder='big'),    # leaf_index
                        ))
                        count_deposit += 1
                    elif EventWithdraw.event_hash() == event['topics'][0]:
                        withdrawals.append(EventWithdraw(
                            event['blockNumber'],                                        # blk_num
                            event['transactionHash'],                                    # tx_hash
                            event['data'][32:64],                                        # nullifier_hash
                            Web3.to_checksum_address(event['data'][12:32].to_0x_hex()),  # recipient
                            Wei(int.from_bytes(event['data'][64:96], byteorder='big')),  # fee
                        ))
                        count_withdraw += 1

                # Prevent reach the rate limit
                util.wait(config.RPC_RETRY_INTERVAL_SEC, self.cond)

                # Log and notify
                log.debug(self.tag, f'Polled {chunk[1] - chunk[0] + 1} blocks, from {chunk[0]} to {chunk[1]}, '
                                    f'contract {self.contract}, deposit: {count_deposit}, withdraw: {count_withdraw}')

                # Callback and update
                for h in self.handlers:
                    h.on_sync(chunk[0], chunk[1], deposits, withdrawals)
            # Update current block number
            if not break_early:
                self.current = latest + 1
                # Notify latest block number
                for h in self.handlers:
                    h.on_latest_block(latest)
                # Notify first catchup
                if first_loop:
                    first_loop = False
                    log.info(self.tag, f'Synced to block {latest}')
                    for h in self.handlers:
                        h.on_first_catchup()
                # Sleep interval if no new block
                if not self.off:
                    util.wait(config.BLOCKCHAIN_LOG_EVENT_POLL_INTERVAL_SEC, self.cond)
