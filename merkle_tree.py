from enum import Enum
from hexbytes import HexBytes
from iden3math import Fp1
from iden3math import hash
from iden3math import prime
import threading

import log
from mytype import MerkleProof


class ImplType(Enum):
    MEMORY = 'memory'


class Interface(object):

    # dec: 21888242871839275222246405745257275088548364400416034343698204186575808495617
    # hex: 30644E72E131A029B85045B68181585D2833E84879B9709143E1F593F0000001
    FILED_SIZE: HexBytes = prime.bn254().to_bytes(32, byteorder='big')

    # dec: 21663839004416932945382355908790599225266501822907911457504978515578255421292
    # hex: 2FE54C60D3ACABF3343A35B6EBA15DB4821B340F76E741E2249685ED4899AF6C
    # zero = keccak256('tornado') % FILED_SIZE
    fp1 = Fp1(prime.bn254())
    digest = int.from_bytes(hash.keccak256('tornado'.encode('ascii')))
    ZERO_VALUE: HexBytes = HexBytes(fp1.mod_reduce(digest).to_bytes(32, byteorder='big'))

    def __init__(self, _type: ImplType) -> None:
        self._type: ImplType = _type

    @staticmethod
    def is_left(node_index: int) -> bool:
        return node_index % 2 == 0

    def implementation(self) -> ImplType:
        return self._type

    def size(self):
        raise NotImplementedError

    '''
    Get root value
    @return HexBytes of root value
            None if tree is empty
    '''
    def root(self) -> HexBytes | None:
        raise NotImplementedError

    '''
    Get index of leaf in the tree
    @param  leaf    The leaf value to search for
    @return The index of the leaf in the tree, None if leaf is not found
    '''
    def get_index(self, leaf: HexBytes) -> int | None:
        raise NotImplementedError

    '''
    Get leaf value by index
    @param  leaf_index  The index of the leaf in the tree, starts from 0, minus N for the last N leafs
    @return None if index is out of range
    '''
    def leaf(self, leaf_index: int) -> HexBytes | None:
        raise NotImplementedError

    '''
    Get path to root from leaf
    @param  leaf_index  The index of the leaf in the tree, starts from 0, minus N for the last N leafs
    @return ([leaf_0, leaf_1, ...], [index_0, index_1, ...])
            None if HexBytes is exists
    '''
    def path(self, leaf_index: int) -> tuple[list[HexBytes], list[int]] | None:
        raise NotImplementedError

    '''
    Add a leaf to the tree
    @return True on succeed
            False if leaf value is out of range
    '''
    def add(self, leaf: HexBytes) -> bool:
        raise NotImplementedError

    def get_merkle_proof(self, leaf_index: int) -> MerkleProof | None:
        raise NotImplementedError


class Memory(Interface):

    def __init__(self, height: int, leafs: list[HexBytes] | None = None) -> None:
        super().__init__(ImplType.MEMORY)
        self.TAG      : str                  = f'MerkleTree.{__class__.__name__}'
        self.mutex    : threading.RLock      = threading.RLock()
        self.height   : int                  = height
        self.layers   : list[list[HexBytes]] = [[] for _ in range(height)]  # [[leafs], [parents]]
        self.zeros    : list[HexBytes]       = [Interface.ZERO_VALUE]
        self.root_node: HexBytes | None      = None
        self.capacity : int                  = 2 ** height
        self._size    : int                  = 0
        for i in range(1, self.height):
            self.zeros.append(HexBytes(hash.mimc_sponge([self.zeros[i - 1], self.zeros[i - 1]], 1, b'')[0]))
        if leafs is not None and len(leafs) > 0:
            if not self._bulk_initialize(leafs):
                raise ValueError(f'Illegal leafs')

    # Do not call this function directly, use constructor instead
    def _bulk_initialize(self, leafs: list[HexBytes]) -> bool:
        if len(leafs) > self.capacity:
            log.error(self.TAG, f'Tree capacity exceeded: {len(leafs)} > {self.capacity}')
            return False
        self.layers[0] = leafs
        for level in range(self.height):
            for node in range(len(self.layers[level])):
                if not Interface.is_left(node):
                    continue
                left: HexBytes = self.layers[level][node]
                if node + 1 < len(self.layers[level]):
                    right: HexBytes = self.layers[level][node + 1]
                else:
                    right: HexBytes = self.zeros[level]
                parent: HexBytes = HexBytes(hash.mimc_sponge([left, right], 1, b'')[0])
                if level == self.height - 1:  # No more upper layers, set the root
                    self.root_node = parent
                    if len(self.layers[level]) > 2:  # The top level should only have two nodes
                        log.error(self.TAG, f'Illegal top level size: {len(self.layers[level])}')
                        return False
                else:
                    self.layers[level + 1].append(parent)
            log.info(self.TAG, f'Level {level} rebuilt, size: {len(self.layers[level])}')
        self._size = len(leafs)
        return True

    def size(self):
        with self.mutex:
            return self._size

    def root(self) -> HexBytes | None:
        with self.mutex:
            if 0 == self._size:
                return None
            return self.root_node

    def get_index(self, leaf: HexBytes) -> int | None:
        with self.mutex:
            if leaf not in self.layers[0]:
                log.error(self.TAG, f'Leaf not found: {leaf.hex()}')
                return None
            return self.layers[0].index(leaf)

    def leaf(self, leaf_index: int) -> HexBytes | None:
        with self.mutex:
            # Check
            if leaf_index > len(self.layers[0]) - 1:
                log.error(self.TAG, f'Leaf index out of range: {leaf_index}')
                return None
            elif leaf_index < 0:
                leaf_index = len(self.layers[0]) + leaf_index
                if leaf_index < 0:
                    log.error(self.TAG, f'Leaf index out of range: {leaf_index}')
                    return None
            return self.layers[0][leaf_index] if 0 <= leaf_index < len(self.layers[0]) else None

    def path(self, leaf_index: int) -> tuple[list[HexBytes], list[int]] | None:
        with self.mutex:
            # Check
            if 0 == len(self.layers[0]):
                log.error(self.TAG, f'Tree is empty')
                return None
            elif leaf_index > len(self.layers[0]) - 1:
                log.error(self.TAG, f'Leaf index out of range: {leaf_index}')
                return None
            elif leaf_index < 0:
                leaf_index = len(self.layers[0]) + leaf_index
                if leaf_index < 0:
                    log.error(self.TAG, f'Leaf index out of range: {leaf_index}')
                    return None
            # Prepare path
            path_node : list[HexBytes] = []
            path_index: list[int]      = []
            for i in range(self.height):
                path_index.append(leaf_index % 2)
                if leaf_index ^ 1 < len(self.layers[i]):
                    node: HexBytes = self.layers[i][leaf_index ^ 1]
                else:
                    node: HexBytes = self.zeros[i]
                path_node.append(node)
                leaf_index //= 2
            return path_node, path_index

    def add(self, leaf: HexBytes) -> bool:
        with self.mutex:
            # Check if legal
            if len(self.layers[0]) >= self.capacity:
                log.error(self.TAG, f'Tree is full')
                return False

            # Prepare left leaf, right leaf and their parent
            self.layers[0].append(leaf)
            node_index: int = len(self.layers[0]) - 1
            if Interface.is_left(node_index):
                add_parent: bool     = True
                node_left : HexBytes = leaf
                node_right: HexBytes = self.zeros[0]
            else:
                add_parent: bool     = False  # Update parent instead of add a new one
                node_left : HexBytes = self.leaf(node_index - 1)
                node_right: HexBytes = leaf
            parent: HexBytes = HexBytes(hash.mimc_sponge([node_left, node_right], 1, b'')[0])

            # Re-build merkle tree
            for level in range(1, self.height):
                node_index //= 2
                if add_parent:
                    self.layers[level].append(parent)
                else:
                    self.layers[level][node_index] = parent
                if Interface.is_left(node_index):
                    node_left  = self.layers[level][node_index]
                    node_right = self.zeros[level]
                else:
                    add_parent = False
                    node_left  = self.layers[level][node_index - 1]
                    node_right = self.layers[level][node_index]
                parent = HexBytes(hash.mimc_sponge([node_left, node_right], 1, b'')[0])
            self.root_node = parent
            self._size += 1

            return True

    def get_merkle_proof(self, leaf_index: int) -> MerkleProof | None:
        root: HexBytes | None = self.root()
        path: tuple[list[HexBytes], list[int]] | None = self.path(leaf_index)
        if root is None or path is None:
            return None
        return MerkleProof(
            root=root,
            path_nodes=path[0],
            path_indices=path[1]
        )

def create(impl: ImplType, height: int = 20, leafs: list[HexBytes] | None = None) -> Interface:
    if impl == ImplType.MEMORY:
        return Memory(height, leafs)
    else:
        raise NotImplementedError
