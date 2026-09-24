"""WebSnark-compatible radix-2 transforms over BN254 Fr."""

from __future__ import annotations

from collections.abc import MutableSequence, Sequence
from functools import lru_cache

from . import native
from .constants import FR_MODULUS, FR_TWO_ADICITY, WEB_SNARK_NON_RESIDUE


def _log2_size(size: int) -> int:
    if size <= 0 or size & (size - 1):
        raise ValueError("NTT size must be a positive power of two")
    bits = size.bit_length() - 1
    if bits > FR_TWO_ADICITY:
        raise ValueError(f"NTT size exceeds Fr's 2^{FR_TWO_ADICITY} domain")
    return bits


@lru_cache(maxsize=FR_TWO_ADICITY + 1)
def root_of_unity(log_size: int) -> int:
    if not 0 <= log_size <= FR_TWO_ADICITY:
        raise ValueError(f"root order must be between 2^0 and 2^{FR_TWO_ADICITY}")
    if log_size == 0:
        return 1
    root = pow(
        WEB_SNARK_NON_RESIDUE,
        (FR_MODULUS - 1) >> log_size,
        FR_MODULUS,
    )
    if pow(root, 1 << log_size, FR_MODULUS) != 1:
        raise RuntimeError("configured root has the wrong order")
    if pow(root, 1 << (log_size - 1), FR_MODULUS) == 1:
        raise RuntimeError("configured root is not primitive")
    return root


def _transform(
    values: MutableSequence[int],
    *,
    inverse: bool,
    odd: bool,
) -> None:
    bits = _log2_size(len(values))
    if odd and bits == FR_TWO_ADICITY:
        raise ValueError("odd transform needs one additional 2-adic root")
    if inverse and odd:
        raise ValueError("legacy odd inverse transform is unsupported")
    values[:] = native.ntt(
        [int(value) % FR_MODULUS for value in values],
        inverse=inverse,
        root=root_of_unity(bits),
        coset=root_of_unity(bits + 1) if odd else 1,
    )


def fft_in_place(values: MutableSequence[int], *, odd: bool = False) -> None:
    _transform(values, inverse=False, odd=odd)


def ifft_in_place(values: MutableSequence[int]) -> None:
    _transform(values, inverse=True, odd=False)


def fft(values: Sequence[int], *, odd: bool = False) -> list[int]:
    result = list(values)
    fft_in_place(result, odd=odd)
    return result


def ifft(values: Sequence[int]) -> list[int]:
    result = list(values)
    ifft_in_place(result)
    return result
