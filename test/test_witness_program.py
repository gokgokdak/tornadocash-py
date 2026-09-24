import base64
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib


if importlib.util.find_spec("esprima") is not None:
    from zk.groth16 import generate_witness_program as generator
else:
    generator = None


@unittest.skipIf(generator is None, "AOT compiler requires dev-only esprima")
class TestWitnessProgram(unittest.TestCase):
    METADATA = b'{"components":[],"signals":[["input",[]]]}'

    @classmethod
    def _source(cls, metadata=None, level=9):
        if metadata is None:
            metadata = cls.METADATA
        encoded = base64.b85encode(zlib.compress(metadata, level)).decode("ascii")
        return (
            "N_SIGNALS = 1\n"
            f"METADATA_B85 = ({encoded!r})\n"
            "\ndef witness(ctx):\n"
            "    return ctx\n"
        )

    def _check(self, committed, expected_result):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "witness.py"
            original = committed.encode("utf-8")
            output.write_bytes(original)
            with (
                patch.object(generator, "_load", return_value=({}, "test-digest")),
                patch.object(generator, "generate_source", return_value=self._source()),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                result = generator.main(["--check", "--output", str(output)])
            self.assertEqual(expected_result, result)
            self.assertEqual(original, output.read_bytes(), "--check must not write")

    def test_check_accepts_equivalent_compression(self):
        recompressed = self._source(level=0)
        self.assertNotEqual(self._source(), recompressed)
        self._check(recompressed, 0)

    def test_check_accepts_crlf_checkout(self):
        self._check(self._source().replace("\n", "\r\n"), 0)

    def test_check_rejects_changed_metadata(self):
        self._check(self._source(metadata=b'{"components":[],"signals":[]}'), 1)

    def test_check_rejects_changed_source(self):
        source = self._source()
        for changed in (
            source.replace("N_SIGNALS = 1", "N_SIGNALS = 2"),
            source.replace("return ctx", "return None"),
            source.replace(
                ")\n\ndef witness", "); raise AssertionError('must not execute')\n\ndef witness"
            ),
        ):
            with self.subTest(source=changed):
                self._check(changed, 1)

    def test_check_rejects_invalid_metadata(self):
        invalid_stream = base64.b85encode(b"not a zlib stream").decode("ascii")
        for value in (repr("/"), repr(invalid_stream), "42", "str('not literal')"):
            with self.subTest(value=value):
                self._check(f"METADATA_B85 = {value}\n", 1)

    def test_check_rejects_missing_or_duplicate_metadata(self):
        for source in ("N_SIGNALS = 1\n", self._source() + self._source()):
            with self.subTest(source=source):
                self._check(source, 1)

    def test_check_rejects_invalid_python(self):
        self._check(self._source() + "def unfinished(\n", 1)
