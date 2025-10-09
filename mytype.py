from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from enum import Enum
from eth_keys.datatypes import PrivateKey, PublicKey
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from iden3math import ec
from iden3math import hash
from iden3math import random
from typing import Union
from web3 import Web3
from web3.types import Wei
import iden3math


class MBytes(int):
    def __new__(cls, value):
        return super().__new__(cls, value)


class Second(float):
    def __new__(cls, value):
        return super().__new__(cls, value)


class ChainID(Enum):
    ETHEREUM  = 0x01        # 1
    BSC       = 0x38        # 56
    OPTIMISM  = 0x0a        # 10
    POLYGON   = 0x89        # 137
    ARBITRUM  = 0xa4b1      # 42161
    AVALANCHE = 0xa86a      # 43114
    SEPOLIA   = 0xaa36a7    # 11155111


def chain_to_string(chain: ChainID) -> str:
    if chain == ChainID.ETHEREUM:
        return 'ethereum'
    elif chain == ChainID.OPTIMISM:
        return 'optimism'
    elif chain == ChainID.BSC:
        return 'bsc'
    elif chain == ChainID.POLYGON:
        return 'polygon'
    elif chain == ChainID.ARBITRUM:
        return 'arbitrum'
    elif chain == ChainID.AVALANCHE:
        return 'avalanche'
    elif chain == ChainID.SEPOLIA:
        return 'sepolia'
    raise ValueError(f'Unsupported chain: {chain}')


# Case-insensitive
def string_to_chain(text: str) -> ChainID:
    if text.strip().lower() == 'ethereum':
        return ChainID.ETHEREUM
    elif text.strip().lower() == 'bsc':
        return ChainID.BSC
    elif text.strip().lower() == 'optimism':
        return ChainID.OPTIMISM
    elif text.strip().lower() == 'polygon':
        return ChainID.POLYGON
    elif text.strip().lower() == 'arbitrum':
        return ChainID.ARBITRUM
    elif text.strip().lower() == 'avalanche':
        return ChainID.AVALANCHE
    elif text.strip().lower() == 'sepolia':
        return ChainID.SEPOLIA
    raise ValueError(f'Unsupported chain: {text}')


class Symbol(Enum):
    ETH  = 'eth'
    BNB  = 'bnb'
    POL  = 'pol'
    AVAX = 'avax'
    DAI  = 'dai'
    CDAI = 'cdai'
    USDC = 'usdc'
    USDT = 'usdt'
    WBTC = 'wbtc'


class SymbolType(Enum):
    NATIVE = 'native'
    ERC20  = 'erc20'


class TornadoUnit(Enum):
    UNIT_0_1     = '0.1'
    UNIT_1       = '1'
    UNIT_10      = '10'
    UNIT_100     = '100'
    UNIT_500     = '500'
    UNIT_1000    = '1000'
    UNIT_10000   = '10000'
    UNIT_100000  = '100000'
    UNIT_5000    = '5000'
    UNIT_50000   = '50000'
    UNIT_500000  = '500000'
    UNIT_5000000 = '5000000'


class Metadata(object):

    def __init__(self):
        self.proxy_address    : ChecksumAddress | None = None
        self.multicall_address: ChecksumAddress | None = None
        self.token_address    : dict[Symbol, ChecksumAddress] | None = {}
        self.decimals         : dict[Symbol, int] = {}
        self.deployment       : dict[Symbol, dict[TornadoUnit, tuple[ChecksumAddress, int]]] = {}  # {symbol: {unit: (deployed_address, deployed_block)}}
        self.flatten          : dict[ChecksumAddress, tuple[Symbol, TornadoUnit, int]] = {}  # {deployed_address: (symbol, unit, deployed_block)}


class Key(object):

    def __init__(self, private_key: str | PrivateKey = None) -> None:
        self.TAG: str = __name__
        if private_key is None:
            ec_key: ec.EllipticCurvePrivateKey  = ec.generate_private_key(ec.SECP256K1(), default_backend())
            self.private_key_bytes : bytes      = ec_key.private_numbers().private_value.to_bytes(32, byteorder='big')
            self.private_key_hexstr: str        = self.private_key_bytes.hex()
            self.private_key_obj   : PrivateKey = PrivateKey(self.private_key_bytes)
        elif isinstance(private_key, str):
            self.private_key_hexstr: str        = private_key[2:] if private_key.startswith('0x') else private_key
            self.private_key_bytes : bytes      = bytes.fromhex(self.private_key_hexstr)
            self.private_key_obj   : PrivateKey = PrivateKey(self.private_key_bytes)
        elif isinstance(private_key, PrivateKey):
            self.private_key_hexstr: str        = private_key.to_hex()
            self.private_key_bytes : bytes      = private_key.to_bytes()
            self.private_key_obj   : PrivateKey = private_key
        self.public_key_obj   : PublicKey       = self.private_key_obj.public_key
        self.public_key_bytes : bytes           = self.public_key_obj.to_bytes()
        self.public_key_hexstr: str             = self.public_key_obj.to_hex()
        self.__eth_address    : ChecksumAddress = Web3.to_checksum_address(self.public_key_obj.to_address())

    def private(self) -> PrivateKey:
        return self.private_key_obj

    def public(self) -> PublicKey:
        return self.public_key_obj

    def eth_address(self) -> ChecksumAddress:
        return self.__eth_address


class Note(object):

    def __init__(self, nullifier: bytearray, secret: bytearray) -> None:
        self.nullifier     : HexBytes = HexBytes(nullifier)
        self.secret        : HexBytes = HexBytes(secret)
        self.nullifier_hash: HexBytes = HexBytes(Note._pedersen(nullifier))
        self.commitment    : HexBytes = HexBytes(Note._pedersen(nullifier + secret))

    @staticmethod
    def create() -> 'Note':
        preimage : bytearray = random.get_bytes(62)  # concat(nullifier, secret) in little-endian
        nullifier: bytearray = preimage[:31]
        secret   : bytearray = preimage[31:]
        return Note(nullifier, secret)

    @staticmethod
    def _pedersen(preimage: bytearray) -> bytearray:
        digest: bytearray = hash.pedersen(preimage)
        point : ec.Point  = ec.babyjub.decompress(digest, iden3math.Endian.LE)
        return bytearray(point.x().to_bytes(32, byteorder='big'))

    @staticmethod
    def to_text(chain: ChainID, symbol: Symbol, unit: TornadoUnit, note: 'Note') -> str:
        return (f'{chain_to_string(chain)}-'
                f'{symbol.value}-'
                f'{unit.value}-'
                f'{note.nullifier.hex().zfill(62)}-'
                f'{note.secret.hex().zfill(62)}')

    @staticmethod
    def from_text(string: str) -> Union[tuple[ChainID, Symbol, TornadoUnit, 'Note'], None]:
        parts = string.split('-')
        if len(parts) != 5:
            return None
        try:
            chain : ChainID     = string_to_chain(parts[0])
            symbol: Symbol      = Symbol(parts[1].lower())
            unit  : TornadoUnit = TornadoUnit(parts[2])
        except ValueError:
            return None
        nullifier: bytearray   = bytearray.fromhex(parts[3]).rjust(31, b'\x00')
        secret   : bytearray   = bytearray.fromhex(parts[4]).rjust(31, b'\x00')
        return chain, symbol, unit, Note(nullifier, secret)


class MerkleProof(object):

    def __init__(self, root: HexBytes | None = None, path_nodes: list[HexBytes] | None = None, path_indices: list[int] | None = None) -> None:
        self.root        : HexBytes | None       = root
        self.path_nodes  : list[HexBytes] | None = path_nodes
        self.path_indices: list[int] | None      = path_indices


class CircuitInput(object):

    def __init__(self,
                 merkle_proof: MerkleProof | None = None,
                 note: Note | None = None,
                 recipient: ChecksumAddress | None = None,
                 relayer: ChecksumAddress | None = None,
                 fee: Wei | None = None,
                 refund: Wei | None = None) -> None:
        self.merkle_proof: MerkleProof | None     = merkle_proof
        self.note        : Note | None            = note
        self.recipient   : ChecksumAddress | None = recipient
        self.relayer     : ChecksumAddress | None = relayer
        self.fee         : Wei | None             = fee
        self.refund      : Wei | None             = refund
