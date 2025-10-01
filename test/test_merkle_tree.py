import unittest
from hexbytes import HexBytes

import merkle_tree


class TestMerkleTree(unittest.TestCase):

    def setUp(self):
        self.leafs: list[HexBytes] = [
            HexBytes.fromhex('159dd798020ef2810bdfdb58f278014610f63f47f0bf731050a59741d223c6ae'),
            HexBytes.fromhex('602d086c140e1d288c5c1a2578e68d62168b91e41fd4a20fe0508a5fc7702b27'),
            HexBytes.fromhex('245f8050bf8f2e2bd42922f481150dc37a845a476cc3c31ae7fd500e83058a1d'),
            HexBytes.fromhex('064767fef5c0b362cfcbbfc76fae617e568900475afff8ce6d526d08c3442c1c'),
            HexBytes.fromhex('9a3cee9b6634e96de73de98c23369bf5e9478641cff1008093b5984470055f04'),
            HexBytes.fromhex('8426b3b6d26a179286d139b2dd755e0a5a6a59b13d0d5f440f8953281633662b'),
        ]

    def test_construct_with_1_leaf(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('18a98fa1a3c14ddcba71f0186347225e40a33449fd364c74ed3b0368689b39b4')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('2fe54c60d3acabf3343a35b6eba15db4821b340f76e741e2249685ed4899af6c'),
            HexBytes.fromhex('256a6135777eee2fd26f54b8b7037a25439d5235caee224154186d2b8a52e31d'),
            HexBytes.fromhex('1151949895e82ab19924de92c40a3d6f7bcb60d92b00504b8199613683f0c200'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20, self.leafs[:1])
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(0)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_construct_with_2_leafs(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('1f87aae6a7caa396e7fcd88bdce00565583cafef3557c1b50a5a0e1d4cd8022a')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('159dd798020ef2810bdfdb58f278014610f63f47f0bf731050a59741d223c6ae'),
            HexBytes.fromhex('256a6135777eee2fd26f54b8b7037a25439d5235caee224154186d2b8a52e31d'),
            HexBytes.fromhex('1151949895e82ab19924de92c40a3d6f7bcb60d92b00504b8199613683f0c200'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20, self.leafs[:2])
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(1)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_construct_with_3_leafs(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('1abd6e1b335717c6237575116deb5fec5fbeff12f48d7cc513bfc5d3a157a3b5')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('2fe54c60d3acabf3343a35b6eba15db4821b340f76e741e2249685ed4899af6c'),
            HexBytes.fromhex('1c98197f76d0205e45bbad23332dc3db89d1ad8c5c099d0c8e1d02f413e40a1b'),
            HexBytes.fromhex('1151949895e82ab19924de92c40a3d6f7bcb60d92b00504b8199613683f0c200'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20, self.leafs[:3])
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(2)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_construct_with_4_leafs(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('2c16093a2dfadf9a11d96629661b5a57cb0db1b8b3fc75664818a7323ea860bb')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('245f8050bf8f2e2bd42922f481150dc37a845a476cc3c31ae7fd500e83058a1d'),
            HexBytes.fromhex('1c98197f76d0205e45bbad23332dc3db89d1ad8c5c099d0c8e1d02f413e40a1b'),
            HexBytes.fromhex('1151949895e82ab19924de92c40a3d6f7bcb60d92b00504b8199613683f0c200'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20, self.leafs[:4])
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(3)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_construct_with_5_leafs(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('0eab44a0c5899a23fcb4d16cc4b418fa4a818f3cdcf486ac5009707272f912eb')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('2fe54c60d3acabf3343a35b6eba15db4821b340f76e741e2249685ed4899af6c'),
            HexBytes.fromhex('256a6135777eee2fd26f54b8b7037a25439d5235caee224154186d2b8a52e31d'),
            HexBytes.fromhex('113283c51ae499e24027551379961922de969f8201a79dcbd204cd4362ef4e6d'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20, self.leafs[:5])
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(4)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_construct_with_6_leafs_path_at_0(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('0901882c62511e32020fcf8ab02bff3fe86042c3e46d4c960ade73277feea11b')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('602d086c140e1d288c5c1a2578e68d62168b91e41fd4a20fe0508a5fc7702b27'),
            HexBytes.fromhex('004bed8becaaa4c9a15483a4e186cde201b739b17e0b4305cad4dd9d723a0108'),
            HexBytes.fromhex('2793557e8ca20f9a25e339e9603d11707d8cfeea329635d24a205c93e2536527'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20, self.leafs[:6])
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(0)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_construct_with_6_leafs_path_at_5(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('0901882c62511e32020fcf8ab02bff3fe86042c3e46d4c960ade73277feea11b')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('9a3cee9b6634e96de73de98c23369bf5e9478641cff1008093b5984470055f04'),
            HexBytes.fromhex('256a6135777eee2fd26f54b8b7037a25439d5235caee224154186d2b8a52e31d'),
            HexBytes.fromhex('113283c51ae499e24027551379961922de969f8201a79dcbd204cd4362ef4e6d'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20, self.leafs[:6])
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(5)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_add_6_leafs_one_by_one_path_at_0(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('0901882c62511e32020fcf8ab02bff3fe86042c3e46d4c960ade73277feea11b')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('602d086c140e1d288c5c1a2578e68d62168b91e41fd4a20fe0508a5fc7702b27'),
            HexBytes.fromhex('004bed8becaaa4c9a15483a4e186cde201b739b17e0b4305cad4dd9d723a0108'),
            HexBytes.fromhex('2793557e8ca20f9a25e339e9603d11707d8cfeea329635d24a205c93e2536527'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20)
        for leaf in self.leafs[:6]:
            tree.add(leaf)
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(0)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_add_6_leafs_one_by_one_path_at_2(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('0901882c62511e32020fcf8ab02bff3fe86042c3e46d4c960ade73277feea11b')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('064767fef5c0b362cfcbbfc76fae617e568900475afff8ce6d526d08c3442c1c'),
            HexBytes.fromhex('1c98197f76d0205e45bbad23332dc3db89d1ad8c5c099d0c8e1d02f413e40a1b'),
            HexBytes.fromhex('2793557e8ca20f9a25e339e9603d11707d8cfeea329635d24a205c93e2536527'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20)
        for leaf in self.leafs[:6]:
            tree.add(leaf)
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(2)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_add_6_leafs_one_by_one_path_at_3(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('0901882c62511e32020fcf8ab02bff3fe86042c3e46d4c960ade73277feea11b')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('245f8050bf8f2e2bd42922f481150dc37a845a476cc3c31ae7fd500e83058a1d'),
            HexBytes.fromhex('1c98197f76d0205e45bbad23332dc3db89d1ad8c5c099d0c8e1d02f413e40a1b'),
            HexBytes.fromhex('2793557e8ca20f9a25e339e9603d11707d8cfeea329635d24a205c93e2536527'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20)
        for leaf in self.leafs[:6]:
            tree.add(leaf)
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(3)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])

    def test_add_6_leafs_one_by_one_path_at_5(self):
        ground_truth_root: HexBytes = HexBytes.fromhex('0901882c62511e32020fcf8ab02bff3fe86042c3e46d4c960ade73277feea11b')
        ground_truth_path: list[HexBytes] = [
            HexBytes.fromhex('9a3cee9b6634e96de73de98c23369bf5e9478641cff1008093b5984470055f04'),
            HexBytes.fromhex('256a6135777eee2fd26f54b8b7037a25439d5235caee224154186d2b8a52e31d'),
            HexBytes.fromhex('113283c51ae499e24027551379961922de969f8201a79dcbd204cd4362ef4e6d'),
            HexBytes.fromhex('20121ee811489ff8d61f09fb89e313f14959a0f28bb428a20dba6b0b068b3bdb'),
            HexBytes.fromhex('0a89ca6ffa14cc462cfedb842c30ed221a50a3d6bf022a6a57dc82ab24c157c9'),
            HexBytes.fromhex('24ca05c2b5cd42e890d6be94c68d0689f4f21c9cec9c0f13fe41d566dfb54959'),
            HexBytes.fromhex('1ccb97c932565a92c60156bdba2d08f3bf1377464e025cee765679e604a7315c'),
            HexBytes.fromhex('19156fbd7d1a8bf5cba8909367de1b624534ebab4f0f79e003bccdd1b182bdb4'),
            HexBytes.fromhex('261af8c1f0912e465744641409f622d466c3920ac6e5ff37e36604cb11dfff80'),
            HexBytes.fromhex('0058459724ff6ca5a1652fcbc3e82b93895cf08e975b19beab3f54c217d1c007'),
            HexBytes.fromhex('1f04ef20dee48d39984d8eabe768a70eafa6310ad20849d4573c3c40c2ad1e30'),
            HexBytes.fromhex('1bea3dec5dab51567ce7e200a30f7ba6d4276aeaa53e2686f962a46c66d511e5'),
            HexBytes.fromhex('0ee0f941e2da4b9e31c3ca97a40d8fa9ce68d97c084177071b3cb46cd3372f0f'),
            HexBytes.fromhex('1ca9503e8935884501bbaf20be14eb4c46b89772c97b96e3b2ebf3a36a948bbd'),
            HexBytes.fromhex('133a80e30697cd55d8f7d4b0965b7be24057ba5dc3da898ee2187232446cb108'),
            HexBytes.fromhex('13e6d8fc88839ed76e182c2a779af5b2c0da9dd18c90427a644f7e148a6253b6'),
            HexBytes.fromhex('1eb16b057a477f4bc8f572ea6bee39561098f78f15bfb3699dcbb7bd8db61854'),
            HexBytes.fromhex('0da2cb16a1ceaabf1c16b838f7a9e3f2a3a3088d9e0a6debaa748114620696ea'),
            HexBytes.fromhex('24a3b3d822420b14b5d8cb6c28a574f01e98ea9e940551d2ebd75cee12649f9d'),
            HexBytes.fromhex('198622acbd783d1b0d9064105b1fc8e4d8889de95c4c519b3f635809fe6afc05'),
        ]
        ground_truth_indices: list[int] = [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY, 20)
        for leaf in self.leafs[:6]:
            tree.add(leaf)
        root: HexBytes = tree.root()
        path: tuple[list[HexBytes], list[int]] = tree.path(5)
        self.assertEqual(ground_truth_root, root)
        self.assertEqual(ground_truth_path, path[0])
        self.assertEqual(ground_truth_indices, path[1])
