import os
import platform

from mytype import ChainID, Second, Symbol, TornadoUnit, chain_to_string


# ============================================== User Configurations ===================================================

# RPC URLs for different chains, modify as needed
RPC_URLS: dict[ChainID, str] = {
    ChainID.ETHEREUM : 'https://ethereum-rpc.publicnode.com',
    ChainID.OPTIMISM : 'https://optimism-rpc.publicnode.com',
    ChainID.BSC      : 'https://bsc-rpc.publicnode.com',
    ChainID.POLYGON  : 'https://polygon-bor-rpc.publicnode.com',
    ChainID.ARBITRUM : 'https://arbitrum-one-rpc.publicnode.com',
    ChainID.AVALANCHE: 'https://avalanche-c-chain-rpc.publicnode.com',
    ChainID.SEPOLIA  : 'https://ethereum-sepolia-rpc.publicnode.com',
}

# Time interval in seconds to retry RPC calls if they fail
RPC_RETRY_INTERVAL_SEC: Second = Second(0.5)

# Time interval in seconds to sync Deposit and Withdrawal events from the blockchain RPC
# Consider to increase or decrease based on your network quality
BLOCKCHAIN_LOG_EVENT_POLL_INTERVAL_SEC: Second = Second(600)

# Use Node.js runtime bundled in './zk/bin/' directory
# Change to `False` if you want to use a system-installed Node.js
# If `False`, please make sure command `node` is available in your PATH environment
BUNDLED_NODE_JS: bool = True

# Relayer fee rate in percentage, e.g., '1.8' means 1.8%
# Increase this value manually if relayer rejects your request
RELAYER_FEE_RATE: str = '1.8'


# ================================================== Constants =========================================================

MERKLE_TREE_HEIGHT: int = 20

LOG_DIR: str = os.path.join(os.path.dirname(__file__), 'logs').replace('\\', '/')

METADATA_PATH: str = os.path.join(os.path.dirname(__file__), 'metadata.json').replace('\\', '/')

BUNDLED_NODE_JS_EXE: str = os.path.join(
    os.path.dirname(__file__),
    f'zk/bin/node-{platform.system().lower()}-{platform.machine().lower()}{'.exe' if 'window' in platform.system().lower() else ''}'
).replace('\\', '/')

DATABASE_PATHS: dict[ChainID, dict[Symbol, dict[TornadoUnit, str]]] = {
    chain: {
        symbol: {
            unit: os.path.join(
                os.path.dirname(__file__), f'db/{chain_to_string(chain)}_{symbol.value}_{unit.value}.sqlite'
            ).replace('\\', '/') for unit in TornadoUnit
        } for symbol in Symbol
    } for chain in ChainID
}

TORNADO_CIRCUIT_PATH: str = os.path.join(os.path.dirname(__file__), 'zk/tornado/circuit.json').replace('\\', '/')

TORNADO_PROVING_KEY_PATH: str = os.path.join(os.path.dirname(__file__), 'zk/tornado/proving_key.bin').replace('\\', '/')

TORNADO_VERIFICATION_KEY_PATH: str = os.path.join(os.path.dirname(__file__), 'zk/tornado/verification_key.json').replace('\\', '/')

TORNADO_ABI_PATH: str = os.path.join(os.path.dirname(__file__), 'abi/tornado.json').replace('\\', '/')

TORNADO_PROXY_ABI_PATH: str = os.path.join(os.path.dirname(__file__), 'abi/tornado_proxy.json').replace('\\', '/')

ERC20_ABI_PATH: str = os.path.join(os.path.dirname(__file__), 'abi/erc20.json').replace('\\', '/')

BACKUP_DIR: str = os.path.join(os.path.dirname(__file__), 'backup').replace('\\', '/')
