import unittest
from hexbytes import HexBytes

from mytype import ChainID, Note, Symbol, TornadoUnit


class TestNote(unittest.TestCase):

    def test_backup_and_restore(self):
        note1 : Note = Note.create()
        backup: str  = Note.to_text(ChainID.ETHEREUM, Symbol.ETH, TornadoUnit.UNIT_1, note1)
        chain, symbol, unit, note2 = Note.from_text(backup)
        self.assertEqual(chain, ChainID.ETHEREUM)
        self.assertEqual(symbol, Symbol.ETH)
        self.assertEqual(unit, TornadoUnit.UNIT_1)
        self.assertEqual(note1.nullifier, note2.nullifier)
        self.assertEqual(note1.secret, note2.secret)
        self.assertEqual(note1.nullifier_hash, note2.nullifier_hash)
        self.assertEqual(note1.commitment, note2.commitment)

    def test_hash_correctness(self):
        ground_truth_nullifier     : bytearray = bytearray.fromhex('3d5d309ff14f0b3def05060870c6f1815f2b5420624c262d90575aa6a49389')
        ground_truth_secret        : bytearray = bytearray.fromhex('8faed9f0c6f71cc14b57cacc22b1eab246fb8351ac0f8af035ad42b6c5baae')
        ground_truth_nullifier_hash: bytearray = bytearray.fromhex('097107f7c6d252a02f007694c5948b379860f8773e22a2bef15eab1c61eeeae7')
        ground_truth_commitment    : bytearray = bytearray.fromhex('16efa3228ed5a0ba54c580fe8438b4c53b851dc5dd9be0c3a354c1f14f2854bb')
        note: Note = Note(ground_truth_nullifier, ground_truth_secret)
        self.assertEqual(HexBytes(ground_truth_nullifier), note.nullifier)
        self.assertEqual(HexBytes(ground_truth_secret), note.secret)
        self.assertEqual(HexBytes(ground_truth_nullifier_hash), note.nullifier_hash)
        self.assertEqual(HexBytes(ground_truth_commitment), note.commitment)
