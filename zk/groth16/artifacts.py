"""Bounds-checked reader for legacy WebSnark binary proving keys.

The format has no magic number or version field.  Consequently the production
Tornado artifact is identified by both its exact structural header and SHA-256
digest.  Query points and sparse polynomial terms are decoded lazily from a
read-only memory map, so opening the 14 MiB key does not duplicate it in memory.
"""

from __future__ import annotations

import hashlib
import mmap
import os
import struct
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

from .constants import (
    FIELD_ELEMENT_BYTES,
    FQ_MODULUS,
    FR_MODULUS,
    FR_TWO_ADICITY,
    TORNADO_PROVING_KEY_HEADER,
    TORNADO_PROVING_KEY_SHA256,
    TORNADO_PROVING_KEY_SIZE,
    TORNADO_SPARSE_A_TERMS,
    TORNADO_SPARSE_B_TERMS,
)
from .field import decode_fq_montgomery, decode_fr_montgomery


_UINT32 = struct.Struct("<I")
_HEADER = struct.Struct("<10I")
_HEADER_SIZE = _HEADER.size
_G1_BYTES = 2 * FIELD_ELEMENT_BYTES
_G2_BYTES = 4 * FIELD_ELEMENT_BYTES
_FIXED_POINTS_SIZE = 3 * _G1_BYTES + 2 * _G2_BYTES
_FIXED_SECTION_END = _HEADER_SIZE + _FIXED_POINTS_SIZE
_SPARSE_TERM_BYTES = _UINT32.size + FIELD_ELEMENT_BYTES


class ArtifactFormatError(ValueError):
    """Raised when a proving key is truncated, corrupt, or incompatible."""


@dataclass(frozen=True, slots=True)
class ProvingKeyHeader:
    n_signals: int
    n_public: int
    domain_size: int
    pols_a_offset: int
    pols_b_offset: int
    points_a_offset: int
    points_b1_offset: int
    points_b2_offset: int
    points_c_offset: int
    points_h_offset: int

    def as_tuple(self) -> tuple[int, ...]:
        return (
            self.n_signals,
            self.n_public,
            self.domain_size,
            self.pols_a_offset,
            self.pols_b_offset,
            self.points_a_offset,
            self.points_b1_offset,
            self.points_b2_offset,
            self.points_c_offset,
            self.points_h_offset,
        )


@dataclass(frozen=True, slots=True)
class G1Affine:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class G2Affine:
    x: tuple[int, int]
    y: tuple[int, int]


@dataclass(frozen=True, slots=True)
class SparseTerm:
    index: int
    coefficient: int


class _PointQuery:
    __slots__ = ("_key", "_offset", "_length", "_g2")

    def __init__(
        self,
        key: "LegacyProvingKey",
        offset: int,
        length: int,
        *,
        g2: bool,
    ) -> None:
        self._key = key
        self._offset = offset
        self._length = length
        self._g2 = g2

    def __len__(self) -> int:
        return self._length

    def encoded_bytes(self) -> bytes:
        width = _G2_BYTES if self._g2 else _G1_BYTES
        size = self._length * width
        self._key._require_range(self._offset, size)
        return bytes(self._key._ensure_open()[self._offset : self._offset + size])


class _SparsePolynomials(Sequence[tuple[SparseTerm, ...]]):
    __slots__ = ("_key", "_entries", "term_count")

    def __init__(
        self,
        key: "LegacyProvingKey",
        entries: tuple[tuple[int, int], ...],
        term_count: int,
    ) -> None:
        self._key = key
        self._entries = entries
        self.term_count = term_count

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(
        self,
        index: int | slice,
    ) -> tuple[SparseTerm, ...] | tuple[tuple[SparseTerm, ...], ...]:
        if isinstance(index, slice):
            return tuple(self[item] for item in range(*index.indices(len(self))))
        normalized = index + len(self) if index < 0 else index
        if not 0 <= normalized < len(self):
            raise IndexError("sparse polynomial index out of range")
        return tuple(self.iter_terms(normalized))

    def iter_terms(self, index: int) -> Iterator[SparseTerm]:
        normalized = index + len(self) if index < 0 else index
        if not 0 <= normalized < len(self):
            raise IndexError("sparse polynomial index out of range")
        offset, count = self._entries[normalized]
        for _ in range(count):
            term_index = self._key._read_u32(offset)
            coefficient = self._key._read_fr(offset + _UINT32.size)
            yield SparseTerm(term_index, coefficient)
            offset += _SPARSE_TERM_BYTES


class LegacyProvingKey:
    """Authenticate and map the Tornado WebSnark proving key."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path).resolve()
        self._file = self.path.open("rb")
        self._mapping: mmap.mmap | None = None
        self._closed = False
        try:
            file_size = os.fstat(self._file.fileno()).st_size
            if file_size < _FIXED_SECTION_END:
                raise ArtifactFormatError("proving key is truncated before fixed points")
            self._mapping = mmap.mmap(self._file.fileno(), length=0, access=mmap.ACCESS_READ)
            self.file_size = file_size
            self.sha256 = hashlib.sha256(self._mapping).hexdigest()

            self.header = ProvingKeyHeader(*_HEADER.unpack_from(self._mapping, 0))
            self._validate_layout()
            a_entries, a_terms = self._scan_sparse_section(
                self.header.pols_a_offset,
                self.header.pols_b_offset,
                "A",
            )
            b_entries, b_terms = self._scan_sparse_section(
                self.header.pols_b_offset,
                self.header.points_a_offset,
                "B",
            )

            self._validate_tornado(a_terms, b_terms)

            offset = _HEADER_SIZE
            self.alpha1 = self._read_g1(offset)
            offset += _G1_BYTES
            self.beta1 = self._read_g1(offset)
            offset += _G1_BYTES
            self.delta1 = self._read_g1(offset)
            offset += _G1_BYTES
            self.beta2 = self._read_g2(offset)
            offset += _G2_BYTES
            self.delta2 = self._read_g2(offset)

            self.pols_a = _SparsePolynomials(self, a_entries, a_terms)
            self.pols_b = _SparsePolynomials(self, b_entries, b_terms)
            self.points_a = _PointQuery(
                self,
                self.header.points_a_offset,
                self.header.n_signals,
                g2=False,
            )
            self.points_b1 = _PointQuery(
                self,
                self.header.points_b1_offset,
                self.header.n_signals,
                g2=False,
            )
            self.points_b2 = _PointQuery(
                self,
                self.header.points_b2_offset,
                self.header.n_signals,
                g2=True,
            )
            private_count = self.header.n_signals - self.header.n_public - 1
            self.points_c = _PointQuery(
                self,
                self.header.points_c_offset,
                private_count,
                g2=False,
            )
            self.points_h = _PointQuery(
                self,
                self.header.points_h_offset,
                self.header.domain_size - 1,
                g2=False,
            )
        except BaseException:
            self.close()
            raise

    def _ensure_open(self) -> mmap.mmap:
        if self._closed or self._mapping is None:
            raise ValueError("proving key is closed")
        return self._mapping

    def _require_range(self, offset: int, size: int) -> None:
        if offset < 0 or size < 0 or offset + size > self.file_size:
            raise ArtifactFormatError("proving key read is outside the mapped file")

    def _read_u32(self, offset: int) -> int:
        self._require_range(offset, _UINT32.size)
        return _UINT32.unpack_from(self._ensure_open(), offset)[0]

    def _read_encoded(self, offset: int, modulus: int) -> int:
        self._require_range(offset, FIELD_ELEMENT_BYTES)
        encoded = int.from_bytes(
            self._ensure_open()[offset : offset + FIELD_ELEMENT_BYTES],
            byteorder="little",
            signed=False,
        )
        if encoded >= modulus:
            raise ArtifactFormatError("proving key contains a non-canonical field element")
        return encoded

    def _read_fr(self, offset: int) -> int:
        return decode_fr_montgomery(self._read_encoded(offset, FR_MODULUS))

    def _read_fq(self, offset: int) -> int:
        return decode_fq_montgomery(self._read_encoded(offset, FQ_MODULUS))

    def _read_g1(self, offset: int) -> G1Affine:
        return G1Affine(
            self._read_fq(offset),
            self._read_fq(offset + FIELD_ELEMENT_BYTES),
        )

    def _read_g2(self, offset: int) -> G2Affine:
        return G2Affine(
            (
                self._read_fq(offset),
                self._read_fq(offset + FIELD_ELEMENT_BYTES),
            ),
            (
                self._read_fq(offset + 2 * FIELD_ELEMENT_BYTES),
                self._read_fq(offset + 3 * FIELD_ELEMENT_BYTES),
            ),
        )

    def _validate_layout(self) -> None:
        header = self.header
        if header.n_signals <= 0:
            raise ArtifactFormatError("proving key has no signals")
        if not 0 <= header.n_public < header.n_signals:
            raise ArtifactFormatError("invalid public-signal count")
        if (
            header.domain_size <= 0
            or header.domain_size & (header.domain_size - 1)
            or header.domain_size > 1 << FR_TWO_ADICITY
        ):
            raise ArtifactFormatError("invalid Fr evaluation domain")
        if header.pols_a_offset != _FIXED_SECTION_END:
            raise ArtifactFormatError("sparse A section does not follow fixed points")

        offsets = header.as_tuple()[3:]
        if tuple(sorted(offsets)) != offsets or len(set(offsets)) != len(offsets):
            raise ArtifactFormatError("proving-key offsets are not strictly increasing")
        if offsets[-1] > self.file_size:
            raise ArtifactFormatError("proving-key section starts beyond end of file")

        # Validate every fixed-width section before trusting n_signals in a loop.
        expected_b1 = header.points_a_offset + header.n_signals * _G1_BYTES
        expected_b2 = header.points_b1_offset + header.n_signals * _G1_BYTES
        expected_c = header.points_b2_offset + header.n_signals * _G2_BYTES
        private_count = header.n_signals - header.n_public - 1
        expected_h = header.points_c_offset + private_count * _G1_BYTES
        expected_size = header.points_h_offset + (header.domain_size - 1) * _G1_BYTES
        actual = (
            header.points_b1_offset,
            header.points_b2_offset,
            header.points_c_offset,
            header.points_h_offset,
            self.file_size,
        )
        expected = (expected_b1, expected_b2, expected_c, expected_h, expected_size)
        if actual != expected:
            raise ArtifactFormatError("fixed-width proving-key sections have invalid sizes")
        if header.pols_b_offset - header.pols_a_offset < header.n_signals * _UINT32.size:
            raise ArtifactFormatError("sparse A section cannot contain all signal headers")
        if header.points_a_offset - header.pols_b_offset < header.n_signals * _UINT32.size:
            raise ArtifactFormatError("sparse B section cannot contain all signal headers")

    def _scan_sparse_section(
        self,
        start: int,
        end: int,
        name: str,
    ) -> tuple[tuple[tuple[int, int], ...], int]:
        entries: list[tuple[int, int]] = []
        offset = start
        term_total = 0

        for _ in range(self.header.n_signals):
            if offset + _UINT32.size > end:
                raise ArtifactFormatError(f"sparse {name} section is truncated")
            count = self._read_u32(offset)
            offset += _UINT32.size
            payload_size = count * _SPARSE_TERM_BYTES
            if offset + payload_size > end:
                raise ArtifactFormatError(f"sparse {name} polynomial exceeds its section")
            entries.append((offset, count))
            for term_offset in range(offset, offset + payload_size, _SPARSE_TERM_BYTES):
                term_index = self._read_u32(term_offset)
                if term_index >= self.header.domain_size:
                    raise ArtifactFormatError(f"sparse {name} term index exceeds domain")
                # Reject corrupt/non-canonical coefficients while the file is authenticated.
                self._read_encoded(term_offset + _UINT32.size, FR_MODULUS)
            offset += payload_size
            term_total += count

        if offset != end:
            raise ArtifactFormatError(f"sparse {name} section has trailing bytes")
        return tuple(entries), term_total

    def _validate_tornado(self, a_terms: int, b_terms: int) -> None:
        if self.file_size != TORNADO_PROVING_KEY_SIZE:
            raise ArtifactFormatError("unexpected Tornado proving-key size")
        if self.sha256 != TORNADO_PROVING_KEY_SHA256:
            raise ArtifactFormatError("Tornado proving-key SHA-256 mismatch")
        if self.header.as_tuple() != TORNADO_PROVING_KEY_HEADER:
            raise ArtifactFormatError("unexpected Tornado proving-key header")
        if (a_terms, b_terms) != (TORNADO_SPARSE_A_TERMS, TORNADO_SPARSE_B_TERMS):
            raise ArtifactFormatError("unexpected Tornado sparse-polynomial term counts")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._mapping is not None:
            self._mapping.close()
            self._mapping = None
        self._file.close()

    def __enter__(self) -> "LegacyProvingKey":
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except BaseException:
            pass


def tornado_proving_key_path() -> Path:
    """Return the repository's bundled Tornado production key path."""

    return Path(__file__).resolve().parent.parent / "tornado" / "proving_key.bin"


def open_tornado_proving_key() -> LegacyProvingKey:
    """Open and authenticate the bundled Tornado production proving key."""

    return LegacyProvingKey(tornado_proving_key_path())
