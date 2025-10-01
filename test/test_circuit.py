import unittest
from web3 import Web3
from web3.types import Wei

import merkle_tree
from mytype import CircuitInput, Note, MerkleProof
from zk import circuit


class TestCircuit(unittest.TestCase):

    def setUp(self):
        self.notes0: list[Note] = [
            Note.from_text('ethereum-eth-100-0118a532d30fa512ce8286ec6c4f9f5ecf742d30c053db416a57600e80af39-fc6193cc565df5bb583d92f27cd18308bbcfae9c4e72b035c53f34a9b90c91')[-1],
            Note.from_text('ethereum-eth-100-2b28d2cc359c2f883d4eef646da15c525ad6c9e491d046674ae6744d4f2a7a-f08e1d8873b54aec0266e7d980aa29bfdf1df4abb3209922f993b7dca05f7a')[-1],
            Note.from_text('ethereum-eth-100-dfbcbc9c22b1394e2d3a1b17ecb1497835357ac51f50398ee6b951e0b1bd31-fb68d3817340b73e0a018cb827e441b0af5fd3add690e2c172f8079c100162')[-1],
            Note.from_text('ethereum-eth-100-acaf46e33323a0f20f661cb22b071e0bce6cf37d3f03b1ca00304be17bd4bb-13a30438f561592e0cd7ed4698ad025f8cba7274aa198b2891e877df304990')[-1],
            Note.from_text('ethereum-eth-100-9a9e01e7196b7e5994c6b7cbfd07ef94e3d4045975dbe67ffee8e52d78091e-8a7cb67ad861adfd0f85f70b22bf852d77f0bfa92c625be896f56626b78248')[-1],
            Note.from_text('ethereum-eth-100-da1d131bb200dae4fafa130971a313ff0559faaa7046b08ba565a33ac7d69a-e5dd6fef0845d1703570dfa8bca05382d7eda02d990a3da8d7f9944c950ff6')[-1],
            Note.from_text('ethereum-eth-100-ea5014762f35647e25ee18510c4490553a60dcb38cd62b3c3f29c656bb2c22-5a18e28aa7e6d8d0b3d3ef597e13200e01485a655740585292e02ad7083e67')[-1],
            Note.from_text('ethereum-eth-100-c1fdafbbc63813b1e1966ac5c14e48c1bc111ba4c2fd7e851f1ee059b1e14f-36208c0060e6bdf7d45c7c200b494b480db344f7f9a82f2dbd2b933f49d805')[-1],
        ]
        self.notes1: list[Note] = [
            Note.from_text('ethereum-eth-100-0118a532d30fa512ce8286ec6c4f9f5ecf742d30c053db416a57600e80af39-fc6193cc565df5bb583d92f27cd18308bbcfae9c4e72b035c53f34a9b90c91')[-1],
            Note.from_text('ethereum-eth-100-2b28d2cc359c2f883d4eef646da15c525ad6c9e491d046674ae6744d4f2a7a-f08e1d8873b54aec0266e7d980aa29bfdf1df4abb3209922f993b7dca05f7a')[-1],
            Note.from_text('ethereum-eth-100-dfbcbc9c22b1394e2d3a1b17ecb1497835357ac51f50398ee6b951e0b1bd31-fb68d3817340b73e0a018cb827e441b0af5fd3add690e2c172f8079c100162')[-1],
            Note.from_text('ethereum-eth-100-acaf46e33323a0f20f661cb22b071e0bce6cf37d3f03b1ca00304be17bd4bb-13a30438f561592e0cd7ed4698ad025f8cba7274aa198b2891e877df304990')[-1],
            Note.from_text('ethereum-eth-100-9a9e01e7196b7e5994c6b7cbfd07ef94e3d4045975dbe67ffee8e52d78091e-8a7cb67ad861adfd0f85f70b22bf852d77f0bfa92c625be896f56626b78248')[-1],
            Note.from_text('ethereum-eth-100-da1d131bb200dae4fafa130971a313ff0559faaa7046b08ba565a33ac7d69a-e5dd6fef0845d1703570dfa8bca05382d7eda02d990a3da8d7f9944c950ff6')[-1],
            Note.from_text('ethereum-eth-100-ea5014762f35647e25ee18510c4490553a60dcb38cd62b3c3f29c656bb2c22-5a18e28aa7e6d8d0b3d3ef597e13200e01485a655740585292e02ad7083e67')[-1],
        ]

    def test_prove_and_verify_notes0(self):
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY)
        for note in self.notes0:
            tree.add(note.commitment)
        merkle_proof: MerkleProof = tree.get_merkle_proof(-1)
        circuit_input = CircuitInput(
            merkle_proof=merkle_proof,
            note=self.notes0[-1],
            recipient=Web3.to_checksum_address('0x02395233b8175b0a04D5A0AD0F62Eaf7aFE55d5c'),
            relayer=Web3.to_checksum_address('0x36B290b60bf8aecd244Ef53E387e7602229aF19E'),
            fee=Wei(3000000000000000),
            refund=Wei(0)
        )
        snark: circuit.Interface = circuit.create(circuit.ImplType.JAVASCRIPT)
        proof: dict | None = snark.prove(circuit_input)
        self.assertNotEqual(proof, None)
        self.assertTrue(snark.verify(proof))

    def test_prove_and_verify_notes1(self):
        tree: merkle_tree.Interface = merkle_tree.create(merkle_tree.ImplType.MEMORY)
        for note in self.notes1:
            tree.add(note.commitment)
        merkle_proof: MerkleProof = tree.get_merkle_proof(-1)
        circuit_input = CircuitInput(
            merkle_proof=merkle_proof,
            note=self.notes1[-1],
            recipient=Web3.to_checksum_address('0x02395233b8175b0a04D5A0AD0F62Eaf7aFE55d5c'),
            relayer=Web3.to_checksum_address('0x36B290b60bf8aecd244Ef53E387e7602229aF19E'),
            fee=Wei(3000000000000000),
            refund=Wei(0)
        )
        snark: circuit.Interface = circuit.create(circuit.ImplType.JAVASCRIPT)
        proof: dict | None = snark.prove(circuit_input)
        self.assertNotEqual(proof, None)
        self.assertTrue(snark.verify(proof))
