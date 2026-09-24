import shutil
import unittest

from web3 import Web3
from web3.types import Wei

import config
from components import merkle_tree
from components.mytype import CircuitInput, Note
from zk import circuit


NOTE_TEXTS = (
    "ethereum-eth-100-0118a532d30fa512ce8286ec6c4f9f5ecf742d30c053db416a57600e80af39-fc6193cc565df5bb583d92f27cd18308bbcfae9c4e72b035c53f34a9b90c91",
    "ethereum-eth-100-2b28d2cc359c2f883d4eef646da15c525ad6c9e491d046674ae6744d4f2a7a-f08e1d8873b54aec0266e7d980aa29bfdf1df4abb3209922f993b7dca05f7a",
    "ethereum-eth-100-dfbcbc9c22b1394e2d3a1b17ecb1497835357ac51f50398ee6b951e0b1bd31-fb68d3817340b73e0a018cb827e441b0af5fd3add690e2c172f8079c100162",
    "ethereum-eth-100-acaf46e33323a0f20f661cb22b071e0bce6cf37d3f03b1ca00304be17bd4bb-13a30438f561592e0cd7ed4698ad025f8cba7274aa198b2891e877df304990",
    "ethereum-eth-100-9a9e01e7196b7e5994c6b7cbfd07ef94e3d4045975dbe67ffee8e52d78091e-8a7cb67ad861adfd0f85f70b22bf852d77f0bfa92c625be896f56626b78248",
    "ethereum-eth-100-da1d131bb200dae4fafa130971a313ff0559faaa7046b08ba565a33ac7d69a-e5dd6fef0845d1703570dfa8bca05382d7eda02d990a3da8d7f9944c950ff6",
    "ethereum-eth-100-ea5014762f35647e25ee18510c4490553a60dcb38cd62b3c3f29c656bb2c22-5a18e28aa7e6d8d0b3d3ef597e13200e01485a655740585292e02ad7083e67",
    "ethereum-eth-100-c1fdafbbc63813b1e1966ac5c14e48c1bc111ba4c2fd7e851f1ee059b1e14f-36208c0060e6bdf7d45c7c200b494b480db344f7f9a82f2dbd2b933f49d805",
)


class TestCircuit(unittest.TestCase):
    def setUp(self):
        self.notes0 = [Note.from_text(text)[-1] for text in NOTE_TEXTS]
        self.notes1 = self.notes0[:-1]

    @staticmethod
    def _circuit_input(notes: list[Note]) -> CircuitInput:
        tree = merkle_tree.create(merkle_tree.ImplType.MEMORY)
        for note in notes:
            tree.add(note.commitment)
        merkle_proof = tree.get_merkle_proof(-1)
        checksum = Web3.to_checksum_address
        return CircuitInput(
            merkle_proof=merkle_proof,
            note=notes[-1],
            recipient=checksum("0x02395233b8175b0a04D5A0AD0F62Eaf7aFE55d5c"),
            relayer=checksum("0x36B290b60bf8aecd244Ef53E387e7602229aF19E"),
            fee=Wei(3000000000000000),
            refund=Wei(0),
        )

    def _prove_python(self, notes: list[Note]):
        snark = circuit.create(circuit.ImplType.PYTHON)
        proof = snark.prove(self._circuit_input(notes))
        self.assertIsNotNone(proof)
        self.assertTrue(snark.verify(proof))
        return snark, proof

    def test_backend_configuration_defaults_to_python(self):
        self.assertEqual("python", config.ZK_BACKEND)
        backend = circuit.ImplType(config.ZK_BACKEND)
        self.assertIsInstance(circuit.create(backend), circuit.Python)
        self.assertIsInstance(circuit.create(circuit.ImplType.JAVASCRIPT), circuit.Javascript)

    def test_prove_and_verify_notes0(self):
        self._prove_python(self.notes0)

    def test_prove_and_verify_notes1(self):
        self._prove_python(self.notes1)

    @unittest.skipUnless(shutil.which("node"), "legacy backend requires Node.js")
    def test_python_and_javascript_outputs_match(self):
        circuit_input = self._circuit_input(self.notes0)
        python = circuit.create(circuit.ImplType.PYTHON)
        legacy = circuit.create(circuit.ImplType.JAVASCRIPT)

        _, python_proof = self._prove_python(self.notes0)
        self.assertTrue(legacy.verify(python_proof))

        js_proof = legacy.prove(circuit_input)
        self.assertIsNotNone(js_proof)
        self.assertTrue(legacy.verify(js_proof))
        self.assertTrue(python.verify(js_proof))

        # Proof points are random; public outputs must match byte for byte.
        self.assertEqual(python_proof["publicSignals"], js_proof["publicSignals"])
        self.assertEqual(
            python_proof["solidity"]["publicSignals"],
            js_proof["solidity"]["publicSignals"],
        )
