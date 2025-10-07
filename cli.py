import argparse
import os
import threading
import traceback
from datetime import datetime
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxReceipt

import config
import log
import util
from blockchain import EventDeposit, EventWithdraw
from core import Tornado
from mytype import ChainID, Key, Metadata, Note, Second, Symbol, TornadoUnit, chain_to_string, string_to_chain


tag: str = 'cli'


def get_option() -> tuple[str, argparse.Namespace] | None:
    class MyFormatter(argparse.RawTextHelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, indent_increment=4, max_help_position=8)
    parser = argparse.ArgumentParser(description='TornadoCash-py CLI', formatter_class=MyFormatter)
    parser.add_argument(
        '--sync',
        required=False,
        nargs=3,
        metavar=("<chain>", "<symbol>", "<unit>"),
        help="Sync events from the blockchain\n"
             "<chain> : Supported values: ethereum, optimism, bsc, polygon, arbitrum, avalanche. Case insensitive\n"
             "<symbol>: Coin symbol, eg: eth, bnb, avac, dai, etc. Case insensitive\n"
             "<unit>  : Tornado unit of coins, eg: 0.1, 1, 10, etc."
    )
    parser.add_argument(
        '--sync_all',
        required=False,
        action='store_true',
        help="Sync events from all supported blockchain\n"
    )
    parser.add_argument(
        '--keep',
        required=False,
        action='store_true',
        help="Used with '--sync' or '--sync_all'"
             "eg: '--sync <chain> <symbol> <unit> --keep'\n"
             "eg: '--sync_all --keep'\n"
             "Optional, keep syncing events from the blockchain after catching up."
    )
    parser.add_argument(
        '--deposit',
        required=False,
        nargs=4,
        metavar=("<key>", "<chain>", "<symbol>", "<unit>"),
        help="Make a deposit\n"
             "<key>   : Private key in Hex string, '0x' prefix is optional\n"
             "<chain> : Supported values: ethereum, optimism, bsc, polygon, arbitrum, avalanche. Case insensitive\n"
             "<symbol>: Coin symbol, eg: eth, bnb, avax, dai, etc. Case insensitive\n"
             "<unit>  : Tornado unit of coins, eg: 0.1, 1, 10, etc."
    )
    parser.add_argument(
        '--deposit_batch',
        required=False,
        nargs=2,
        metavar=("<key>", "<json>"),
        help="Make deposit in batch\n"
             "<key> : Private key in Hex string, '0x' prefix is optional\n"
             "<json>: JSON string to describe a batch, eg: \n"
             "        '{\"ethereum\": {\"eth\": {\"10\": 100, \"100\": 20}}, \"polygon\": {\"pol\": {\"100000\": 1000}}}'\n"
    )
    parser.add_argument(
        '--withdraw',
        required=False,
        nargs=3,
        metavar=("<note>", "<recipient>", "<key>"),
        help="Make a withdrawal\n"
             "<note>     : Tornado note text created by deposit\n"
             "<recipient>: Recipient address\n"
             "<key>      : Private key in Hex string, '0x' prefix is optional\n"
    )
    parser.add_argument(
        '--note_deposited',
        required=False,
        metavar="<note>",
        help="Check if the note has been deposited\n"
             "<note>: Tornado note text created by deposit"
    )
    parser.add_argument(
        '--note_withdrawn',
        required=False,
        metavar="<note>",
        help="Check if the note has been withdrawn\n"
             "<note>: Tornado note text created by deposit"
    )
    parser.add_argument(
        '--note_detail',
        required=False,
        metavar="<note>",
        help="Print nullifier hash and commitment of the note\n"
             "<note>: Tornado note text created by deposit"
    )
    args = parser.parse_args()

    # Check and get enabled option
    enabled_args: list[str] = []
    for arg in vars(args):
        arg_val: any = getattr(args, arg)
        if arg == 'sync_all' and arg_val is False:
            continue
        elif arg_val is not None:
            if arg == 'keep' or arg == 'relayer_url':
                continue
            enabled_args.append(arg)
    if len(enabled_args) == 0:
        parser.print_help()
        return None
    elif len(enabled_args) > 1:
        print(f'Error: Only one option can be specified at a time, your options: {enabled_args}')
        return None
    enabled_arg = enabled_args[0]
    return enabled_arg, args


def handle_option(enabled_arg: str, args: argparse.Namespace) -> None:
    if enabled_arg == 'sync':
        try:
            chain : ChainID     = string_to_chain(args.sync[0].lower())
            symbol: Symbol      = Symbol(args.sync[1].lower())
            unit  : TornadoUnit = TornadoUnit(args.sync[2])
        except ValueError as e:
            log.error(tag, f'Invalid arguments for --sync: {args.sync}, exception: {e}')
            return
        try:
            keep: bool | None = False if args.keep is None else bool(args.keep)
        except ValueError as e:
            log.error(tag, f'Invalid arguments for --keep: {args.keep}, exception: {e}')
            return
        sync_events(chain, symbol, unit, keep)
    elif enabled_arg == 'sync_all':
        try:
            keep: bool | None = False if args.keep is None else bool(args.keep)
        except ValueError as e:
            log.error(tag, f'Invalid arguments for --keep: {args.keep}, exception: {e}')
            return
        sync_all_events(keep)
    elif enabled_arg == 'deposit':
        try:
            key   : Key         = Key(args.deposit[0])
            chain : ChainID     = string_to_chain(args.deposit[1].lower())
            symbol: Symbol      = Symbol(args.deposit[2].lower())
            unit  : TornadoUnit = TornadoUnit(args.deposit[3])
        except ValueError as e:
            log.error(tag, f'Invalid arguments for --deposit: {args.deposit}, exception: {e}')
            return
        deposit(key, chain, symbol, unit)
    elif enabled_arg == 'deposit_batch':
        try:
            key  : Key = Key(args.deposit_batch[0])
            batch: str = str(args.deposit_batch[1]).lower()
        except ValueError as e:
            log.error(tag, f'Invalid arguments for --deposit_batch: {args.deposit_batch}, exception: {e}')
            return
        deposit_batch(key, batch)
    elif enabled_arg == 'withdraw':
        try:
            note_text: str             = str(args.withdraw[0])
            recipient: ChecksumAddress = Web3.to_checksum_address(args.withdraw[1])
            fee_payer: str             = str(args.withdraw[2])
        except ValueError as e:
            log.error(tag, f'Invalid arguments for --withdraw: {args.withdraw}, exception: {e}')
            return
        key    : Key | None = None
        relayer: str        = fee_payer
        try:
            key = Key(fee_payer)
        except:
            pass
        if key is not None:
            withdraw(note_text, recipient, key)
        else:
            withdraw(note_text, recipient, relayer)
    elif enabled_arg == 'note_deposited':
        note_deposited(str(args.note_deposited))
    elif enabled_arg == 'note_withdrawn':
        note_withdrawn(str(args.note_withdrawn))
    elif enabled_arg == 'note_detail':
        parsed: tuple[ChainID, Symbol, TornadoUnit, Note] | None = Note.from_text(str(args.note_detail))
        if parsed is None:
            log.error(f'Failed to parse note: "{args.note_detail}"')
            return
        chain, symbol, unit, note = parsed
        log.info(tag, f'Note detail:\n'
                      f'  Chain         : {util.upper_first_char(chain_to_string(chain))}({hex(chain.value)})\n'
                      f'  Symbol        : {symbol.value.upper()}\n'
                      f'  Unit          : {unit.value}\n'
                      f'  Nullifier     : 0x{note.nullifier.hex().zfill(62)}\n'
                      f'  Secret        : 0x{note.secret.hex().zfill(62)}\n'
                      f'  Nullifier Hash: 0x{note.nullifier_hash.hex().zfill(64)}\n'
                      f'  Commitment    : 0x{note.commitment.hex().zfill(64)}')


def _sync(tornado: Tornado, keep: bool, signal: threading.Condition | None = None) -> None:
    catch_up_bool: bool = False
    latest_block : int  = 0
    if not keep and signal is None:
        signal = threading.Condition()
    class Handler(Tornado.Handler):
        def __init__(self, meta: str) -> None:
            super().__init__()
            self.meta = meta
        def on_first_catchup(self, _chain: ChainID, _symbol: Symbol, _unit: TornadoUnit) -> None:
            nonlocal catch_up_bool
            nonlocal signal
            log.info(tag, f'{self.meta}, catch up to the latest blockchain')
            catch_up_bool = True
            if signal is None:
                return
            if not keep:
                with signal:
                    signal.notify_all()
        def on_sync(self, block_from: int, block_to: int, deposits: list[EventDeposit], withdrawals: list[EventWithdraw]) -> None:
            nonlocal latest_block
            log.info(tag, f'{self.meta}, synced {block_to - block_from + 1} blocks from {block_from} to {block_to}, '
                          f'progress: {min(100.0, 100.0 * block_to / latest_block):.2f}%, '
                          f'deposits: {len(deposits)}, withdrawals: {len(withdrawals)}')
        def on_latest_block(self, block_number: int) -> None:
            nonlocal latest_block
            latest_block = block_number
    handler: Handler = Handler(f'{util.upper_first_char(chain_to_string(tornado.chain))}@{tornado.unit.value}{tornado.symbol.value.upper()}')
    tornado.add_handler(handler)
    if tornado.start_sync():
        util.wait(Second(0), signal, True)
        tornado.stop_sync()
    tornado.remove_all_handlers()
    if not catch_up_bool:
        raise KeyboardInterrupt


def sync_events(chain: ChainID, symbol: Symbol, unit: TornadoUnit, keep: bool) -> None:
    tornado: Tornado = Tornado(chain, symbol, unit)
    if not tornado.init(sync_only=True):
        return
    try:
        _sync(tornado, keep)
    except KeyboardInterrupt:
        log.warn(tag, 'Interrupted')
    tornado.un_init()


def sync_all_events(keep: bool) -> None:
    # Load metadata
    meta_data: dict[ChainID, Metadata] = util.load_metadata()
    # Create tornado instances
    instances: list[Tornado] = []
    for chain_id, metadata in meta_data.items():
        for symbol, units in metadata.deployment.items():
            for unit in units.keys():
                instances.append(Tornado(chain_id, symbol, unit))
    # Initialize all instances
    succeed: bool = True
    initialized: list[Tornado] = []
    for tornado in instances:
        if not tornado.init(sync_only=True):
            succeed = False
            log.error(tag, f'Failed to initialize {util.upper_first_char(chain_to_string(tornado.chain))} {tornado.unit.value} {tornado.symbol.value}, skip it')
            break
        initialized.append(tornado)
    # If any instance failed to initialize, un-initialize all and return
    if not succeed:
        for tornado in initialized:
            tornado.un_init()
        return
    if keep:
        # Start threads
        signals: list[threading.Condition] = []
        workers: list[threading.Thread]    = []
        for tornado in initialized:
            def job(_t, _s):
                try:
                    _sync(_t, True, _s)
                except KeyboardInterrupt:
                    log.warn(tag, f'{util.upper_first_char(chain_to_string(_t.chain))}@{_t.unit.value}{_t.symbol.value.upper()}, interrupted')
            signal: threading.Condition = threading.Condition()
            thread: threading.Thread    = threading.Thread(target=lambda t=tornado, s=signal: job(t, s))
            thread.start()
            signals.append(signal)
            workers.append(thread)
        # Wait for all threads to finish or be interrupted
        cond: threading.Condition = threading.Condition()
        try:
            with cond:
                cond.wait()
        except KeyboardInterrupt:
            pass
        for signal in signals:
            with signal:
                signal.notify_all()
        for worker in workers:
            worker.join()
    else:
        for tornado in initialized:
            try:
                _sync(tornado, False)
            except KeyboardInterrupt:
                log.warn(tag, 'Interrupted')
                break
    # Un-initialize all instances
    for tornado in initialized:
        tornado.un_init()


def _deposit(key: Key, tornado: Tornado) -> HexBytes | None:
    log.info(tag, f'Depositing {util.upper_first_char(chain_to_string(tornado.chain))} {tornado.unit.value} {tornado.symbol.value}')
    # Create and save the note to a file
    note: Note = Note.create()
    try:
        if not os.path.exists(config.BACKUP_DIR):
            os.makedirs(config.BACKUP_DIR, exist_ok=True)
        filename: str = f'{datetime.now().strftime('%Y-%m-%d_%H.%M.%S.%f')[:-3]}_{chain_to_string(tornado.chain)}_{tornado.symbol.value}_{tornado.unit.value}.txt'
        backup_path: str = os.path.join(config.BACKUP_DIR, filename).replace('\\', '/')
        with open(backup_path, 'w') as f:
            f.write(f'{Note.to_text(tornado.chain, tornado.symbol, tornado.unit, note)}\n')
    except Exception as e:
        log.error(tag, f'Failed to save note to file: {e}')
        return None
    # Deposit
    log.info(tag, f'IMPORTANT: Please save the note text below and keep it private', log.Color.YELLOW, log.Style.BOLD)
    log.info(tag, f'IMPORTANT: {Note.to_text(tornado.chain, tornado.symbol, tornado.unit, note)}', log.Color.YELLOW, log.Style.BOLD)
    tx_hash: HexBytes | None = tornado.deposit(note, key)
    if tx_hash is None:
        try:
            os.remove(backup_path)
        except Exception as e:
            log.error(tag, f'Failed to remove failed deposit\'s backup file: {e}')
        return None
    log.info(tag, f'IMPORTANT: Note backup saved to {backup_path}', log.Color.YELLOW, log.Style.BOLD)
    return tx_hash


def deposit(key: Key, chain: ChainID, symbol: Symbol, unit: TornadoUnit) -> None:
    tornado: Tornado = Tornado(chain, symbol, unit)
    if not tornado.init(sync_only=True):
        return
    try:
        _deposit(key, tornado)
    except KeyboardInterrupt:
        log.warn(tag, 'Interrupted')
    tornado.un_init()


''' Example of batch
"{
    'ethereum': {
        'eth': {
            '10': 100,
            '100': 20
        }
    },
    'polygon': {
        'pol': {
            '100000': 1000
        }
    }
}"
'''
def deposit_batch(key: Key, batch: str) -> None:
    # Evaluate the batch string to a dictionary
    parsed: dict[ChainID, dict[Symbol, dict[TornadoUnit, int]]] = {}
    try:
        loaded: dict[str, dict] = eval(batch)
        for chain_str, v0 in loaded.items():
            chain: ChainID = string_to_chain(chain_str)
            if chain in parsed:
                log.error(tag, f'Duplicated key "{chain_str}" in the batch')
                return
            parsed[chain] = {}
            for symbol_str, v1 in v0.items():
                symbol: Symbol = Symbol(symbol_str.lower())
                if symbol in parsed[chain]:
                    log.error(tag, f'Duplicated key "{symbol_str}" in the batch')
                    return
                parsed[chain][symbol] = {}
                for unit_str, count in v1.items():
                    unit: TornadoUnit = TornadoUnit(unit_str)
                    if unit in parsed[chain][symbol]:
                        log.error(tag, f'Duplicated key "{unit_str}" in the batch')
                        return
                    parsed[chain][symbol][unit] = int(count)
    except Exception as e:
        stack: str = traceback.format_exc()
        text: str = str(e)
        lines: list[str] = [f'deposit_batch() raised {type(e)} exception: {text}']
        lines.extend(stack.split('\n'))
        log.error(tag, lines)
        return
    # Deposit
    for chain, v0 in parsed.items():
        url: str = config.RPC_URLS[chain]
        if url.startswith('http'):
            w3: Web3 = Web3(Web3.HTTPProvider(url))
        elif url.startswith('ws'):
            w3: Web3 = Web3(Web3.LegacyWebSocketProvider(url))
        else:
            log.error(tag, f'unsupported RPC url: {url}')
            return None
        if not w3.is_connected():
            log.error(tag, f'failed to connect to RPC: {url}')
            return None
        for symbol, v1 in v0.items():
            for unit, count in v1.items():
                tornado: Tornado = Tornado(chain, symbol, unit)
                if not tornado.init(sync_only=False):
                    continue
                for _ in range(count):
                    try:
                        tx_hash: HexBytes = _deposit(key, tornado)
                    except KeyboardInterrupt:
                        log.warn(tag, 'Interrupted')
                        tornado.un_init()
                        return
                    # Wait until the deposit transaction is mined
                    if tx_hash is None:
                        continue
                    util.wait(Second(10))
                    while True:
                        try:
                            receipt: TxReceipt = w3.eth.get_transaction_receipt(tx_hash)
                            if receipt is not None and receipt['blockNumber'] is not None:
                                log.info(tag, f'Deposit transaction mined in block {receipt["blockNumber"]}', log.Color.CYAN, log.Style.BOLD)
                                break
                        except Exception as e:
                            log.error(tag, f'Waiting for deposit transaction to be mined, RPC response: \"{e}\"')
                            util.wait(Second(5))
                            continue
                        log.warn(tag, f'Waiting for deposit transaction to be mined ...')
                        util.wait(Second(5))
                tornado.un_init()


def withdraw(note_text: str, recipient: ChecksumAddress, key_or_relayer: Key | str) -> None:
    parsed: tuple[ChainID, Symbol, TornadoUnit, Note] | None = Note.from_text(note_text)
    if parsed is None:
        log.error(f'Failed to parse note: "{note_text}"')
        return
    chain, symbol, unit, note = parsed
    tornado: Tornado = Tornado(chain, symbol, unit)
    if not tornado.init(sync_only=False):
        return
    _sync(tornado, False)
    tornado.withdraw(note, recipient, key_or_relayer)
    tornado.un_init()


def note_deposited(note_text: str) -> None:
    parsed: tuple[ChainID, Symbol, TornadoUnit, Note] | None = Note.from_text(note_text)
    if parsed is None:
        log.error(f'Failed to parse note: "{note_text}"')
        return
    chain, symbol, unit, note = parsed
    tornado: Tornado = Tornado(chain, symbol, unit)
    deposited: bool | None = tornado.note_deposited(note.commitment)
    if deposited is not None:
        log.info(tag, f'Deposited: {str(deposited)}')


def note_withdrawn(note_text: str) -> None:
    parsed: tuple[ChainID, Symbol, TornadoUnit, Note] | None = Note.from_text(note_text)
    if parsed is None:
        log.error(f'Failed to parse note: "{note_text}"')
        return
    chain, symbol, unit, note = parsed
    tornado: Tornado = Tornado(chain, symbol, unit)
    withdrawn: bool | None = tornado.note_withdrawn(note.nullifier_hash)
    if withdrawn is not None:
        log.info(tag, f'Withdrawn: {str(withdrawn)}')


if __name__ == "__main__":
    option: tuple[str, argparse.Namespace] | None = get_option()
    if option is not None:
        log.init(config.LOG_DIR)
        log.set_level(log.Level.INFO)
        log.set_console_enable(True)
        handle_option(option[0], option[1])
        log.un_init()
