"""BN254 Montgomery decoding for legacy WebSnark artifacts."""

from __future__ import annotations

from .constants import (
    FQ_MODULUS,
    FQ_MONTGOMERY_FACTOR_INVERSE,
    FR_MODULUS,
    FR_MONTGOMERY_FACTOR_INVERSE,
)


def decode_fr_montgomery(value: int) -> int:
    """Decode a canonical WebSnark Montgomery Fr integer."""

    encoded = int(value)
    if not 0 <= encoded < FR_MODULUS:
        raise ValueError("non-canonical Montgomery Fr value")
    return encoded * FR_MONTGOMERY_FACTOR_INVERSE % FR_MODULUS
def decode_fq_montgomery(value: int) -> int:
    """Decode a canonical WebSnark Montgomery Fq integer."""

    encoded = int(value)
    if not 0 <= encoded < FQ_MODULUS:
        raise ValueError("non-canonical Montgomery Fq value")
    return encoded * FQ_MONTGOMERY_FACTOR_INVERSE % FQ_MODULUS
