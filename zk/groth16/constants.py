"""Constants pinned to the Tornado Cash v2.1 BN254 artifacts.

The proving-key layout is the legacy WebSnark layout produced by
``tools/buildpkey.js`` at commit
``4c0af6a8b65aabea3c09f377f63c44e7a58afa6d``.
"""

from __future__ import annotations

from iden3math import field


# BN254 scalar field (Fr) and base field (Fq).
_EXPECTED_FR_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617
_EXPECTED_FQ_MODULUS = 21888242871839275222246405745257275088696311157297823662689037894645226208583
FR_MODULUS = int(field.bn254.fr_modulus())
if FR_MODULUS != _EXPECTED_FR_MODULUS:
    raise RuntimeError("iden3math returned an incompatible BN254 scalar field")
FQ_MODULUS = int(field.bn254.fq_modulus())
if FQ_MODULUS != _EXPECTED_FQ_MODULUS:
    raise RuntimeError("iden3math returned an incompatible BN254 base field")
FIELD_ELEMENT_BYTES = 32
MONTGOMERY_RADIX = 1 << (FIELD_ELEMENT_BYTES * 8)
FR_MONTGOMERY_FACTOR_INVERSE = pow(MONTGOMERY_RADIX, -1, FR_MODULUS)
FQ_MONTGOMERY_FACTOR_INVERSE = pow(MONTGOMERY_RADIX, -1, FQ_MODULUS)

# WebSnark explicitly overrides the FFT quadratic non-residue with seven.
WEB_SNARK_NON_RESIDUE = 7
FR_TWO_ADICITY = 28

# Exact Tornado Cash production proving-key identity and structure.
TORNADO_PROVING_KEY_SIZE = 14_522_256
TORNADO_PROVING_KEY_SHA256 = "8e2d2f22beafb5a9666daebca57b13f8029c3656c65fcfbcc86e2418fa16a3af"
TORNADO_VERIFICATION_KEY_SHA256 = "3eedcf6ec6b5c24219ed19c7a33966fbfa6a03ae7c84124270589091e87cf8d3"
TORNADO_N_SIGNALS = 28_300
TORNADO_N_PUBLIC = 6
TORNADO_DOMAIN_SIZE = 32_768
TORNADO_PROVING_KEY_OFFSETS = (
    488,         # sparse A polynomials
    1_506_204,   # sparse B polynomials
    3_369_616,   # A G1 query
    5_180_816,   # B1 G1 query
    6_992_016,   # B2 G2 query
    10_614_416,  # C G1 query
    12_425_168,  # H G1 query
)
TORNADO_PROVING_KEY_HEADER = (
    TORNADO_N_SIGNALS,
    TORNADO_N_PUBLIC,
    TORNADO_DOMAIN_SIZE,
    *TORNADO_PROVING_KEY_OFFSETS,
)
TORNADO_SPARSE_A_TERMS = 38_681
TORNADO_SPARSE_B_TERMS = 48_617
