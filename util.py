import inspect
import json
import os
import signal
import threading
import time
from typing import Any, Callable
from web3.types import Wei

import config
from mytype import ChainID, Metadata, Second, Symbol, SymbolType, TornadoUnit, string_to_chain


def unix_timestamp() -> Second:
    return Second(time.time_ns() / 1000.0 / 1000.0 / 1000.0)


def signal_interrupt() -> None:
    os.kill(os.getpid(), signal.SIGINT)


# Decorator to capture caller's filename and line number
def caller_location(func: Callable) -> Any:
    def wrapper(*args, **kwargs) -> Any:
        stack       = inspect.currentframe().f_back
        filename    = os.path.basename(stack.f_code.co_filename)
        line_number = stack.f_lineno
        kwargs['filename']    = filename
        kwargs['line_number'] = line_number
        return func(*args, **kwargs)
    return wrapper


# Waits for a duration in seconds or until interrupted by Ctrl-C.
# If `wakeup` is provided, it will be used to wait, and can be notified to wake up early.
def wait(duration: Second, wakeup: threading.Condition | None = None, interruptable: bool = True) -> None:
    stop = False
    if wakeup is None:
        wakeup = threading.Condition()
    def _():
        nonlocal stop
        nonlocal duration
        nonlocal wakeup
        nonlocal interruptable
        with wakeup:
            if duration <= 0:
                while True:
                    try:
                        wakeup.wait()
                        break
                    except KeyboardInterrupt:
                        if interruptable:
                            break
            else:
                eta: Second = Second(unix_timestamp() + duration)
                while unix_timestamp() < eta:
                    try:
                        nap: Second = eta - unix_timestamp()
                        if nap <= 0:
                            break
                        wakeup.wait(nap)
                        break
                    except KeyboardInterrupt:
                        if interruptable:
                            break
        stop = True
    if threading.current_thread() is not threading.main_thread():
        _()
        return
    t = threading.Thread(target=_)
    t.start()
    while not stop:
        try:
            t.join(timeout=0.001)
        except KeyboardInterrupt:
            if interruptable:
                with wakeup:
                    wakeup.notify_all()


def get_chain_native_symbol(chain: ChainID) -> Symbol:
    if chain == ChainID.ETHEREUM:
        return Symbol.ETH
    elif chain == ChainID.BSC:
        return Symbol.BNB
    elif chain == ChainID.OPTIMISM:
        return Symbol.ETH
    elif chain == ChainID.POLYGON:
        return Symbol.POL
    elif chain == ChainID.ARBITRUM:
        return Symbol.ETH
    elif chain == ChainID.AVALANCHE:
        return Symbol.AVAX
    else:
        raise ValueError(f"Unknown chain: {chain}")


def load_metadata() -> dict[ChainID, Metadata]:
    meta_list: dict[ChainID, Metadata] = {}
    f = open(config.METADATA_PATH, 'r')
    try:
        loaded: dict = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f'Failed to load metadata.json from {config.METADATA_PATH}: {e}')
    try:
        for chain_str, params in loaded.items():
            chain: ChainID = string_to_chain(chain_str)
            if chain not in meta_list:
                meta_list[chain] = Metadata()
            meta_list[chain].proxy_address     = params['proxy_address']
            meta_list[chain].multicall_address = params['multicall_address']
            for symbol in Symbol:
                if symbol.value not in params:
                    continue
                is_native: bool = symbol == get_chain_native_symbol(chain)
                param_symbol: dict = params[symbol.value]
                meta_list[chain].deployment[symbol] = {}
                meta_list[chain].decimals[symbol] = params[symbol.value]['decimals']
                for unit, address in param_symbol['deployed_address'].items():
                    meta_list[chain].deployment[symbol][TornadoUnit(unit)] = (address, param_symbol['deployed_block_number'][unit])
                    meta_list[chain].flatten[address] = (symbol, TornadoUnit(unit), param_symbol['deployed_block_number'][unit])
                if not is_native:
                    meta_list[chain].token_address[symbol] = params[symbol.value]['token_address']
    except Exception as e:
        raise ValueError(f'Failed to parse {loaded}, exception: {e}')
    f.close()
    return meta_list


def unit_to_wei(unit: TornadoUnit, decimals: int) -> Wei:
    return {
        TornadoUnit.UNIT_0_1    : 1       * (10 ** max(0, decimals - 1)),
        TornadoUnit.UNIT_1      : 1       * (10 ** decimals),
        TornadoUnit.UNIT_10     : 10      * (10 ** decimals),
        TornadoUnit.UNIT_100    : 100     * (10 ** decimals),
        TornadoUnit.UNIT_500    : 500     * (10 ** decimals),
        TornadoUnit.UNIT_1000   : 1000    * (10 ** decimals),
        TornadoUnit.UNIT_10000  : 10000   * (10 ** decimals),
        TornadoUnit.UNIT_100000 : 100000  * (10 ** decimals),
        TornadoUnit.UNIT_5000   : 5000    * (10 ** decimals),
        TornadoUnit.UNIT_50000  : 50000   * (10 ** decimals),
        TornadoUnit.UNIT_500000 : 500000  * (10 ** decimals),
        TornadoUnit.UNIT_5000000: 5000000 * (10 ** decimals),
    }[unit]


def get_symbol_type(symbol: Symbol) -> SymbolType:
    return {
        Symbol.ETH : SymbolType.NATIVE,
        Symbol.BNB : SymbolType.NATIVE,
        Symbol.POL : SymbolType.NATIVE,
        Symbol.AVAX: SymbolType.NATIVE,
        Symbol.DAI : SymbolType.ERC20,
        Symbol.CDAI: SymbolType.ERC20,
        Symbol.USDC: SymbolType.ERC20,
        Symbol.USDT: SymbolType.ERC20,
    }[symbol]

def upper_first_char(s: str) -> str:
    if len(s) == 0:
        return s
    return s[0].upper() + s[1:]
