"""Groth16 prover for Tornado's legacy WebSnark proving key."""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from typing import Any

import config
from py_ecc.optimized_bn128 import (
    FQ,
    FQ2,
    Z1,
    Z2,
    add,
    curve_order,
    multiply,
    neg,
)

from .artifacts import (
    G1Affine,
    G2Affine,
    LegacyProvingKey,
    SparseTerm,
    open_tornado_proving_key,
)
from .constants import FR_MODULUS
from .msm import query_msms
from .ntt import fft, ifft
from .serialization import G1Point, G2Point, proof_to_dict


def _g1(point: G1Affine) -> G1Point:
    # Legacy WebSnark encodes affine infinity as (0, 1).
    if point.x == 0 and point.y == 1:
        return Z1
    return FQ(point.x), FQ(point.y), FQ.one()


def _g2(point: G2Affine) -> G2Point:
    # FQ2 coefficients stay in c0,c1 order until Solidity serialization.
    if point.x == (0, 0) and point.y == (1, 0):
        return Z2
    return FQ2(point.x), FQ2(point.y), FQ2.one()


def _construct_evaluations(
    witness: Sequence[int],
    polynomials: Sequence[tuple[SparseTerm, ...]],
    domain_size: int,
) -> list[int]:
    if len(witness) != len(polynomials):
        raise ValueError("witness and sparse polynomial tables differ in length")
    evaluations = [0] * domain_size
    for signal, terms in zip(witness, polynomials, strict=True):
        scalar = int(signal) % FR_MODULUS
        if scalar == 0:
            continue
        for term in terms:
            evaluations[term.index] = (
                evaluations[term.index] + scalar * term.coefficient
            ) % FR_MODULUS
    return evaluations


def calculate_h(
    witness: Sequence[int],
    polynomials_a: Sequence[tuple[SparseTerm, ...]],
    polynomials_b: Sequence[tuple[SparseTerm, ...]],
    domain_size: int,
) -> list[int]:
    """Calculate the H coefficients using WebSnark's interleaved coset flow."""

    evaluations_a = _construct_evaluations(witness, polynomials_a, domain_size)
    evaluations_b = _construct_evaluations(witness, polynomials_b, domain_size)

    coefficients_a = ifft(evaluations_a)
    coefficients_b = ifft(evaluations_b)
    odd_a = fft(coefficients_a, odd=True)
    odd_b = fft(coefficients_b, odd=True)

    product_evaluations = [0] * (2 * domain_size)
    for index in range(domain_size):
        product_evaluations[2 * index] = (
            evaluations_a[index] * evaluations_b[index]
        ) % FR_MODULUS
        product_evaluations[2 * index + 1] = odd_a[index] * odd_b[index] % FR_MODULUS

    product_coefficients = ifft(product_evaluations)
    return product_coefficients[domain_size:]


def _validate_witness(witness: Sequence[int], key: LegacyProvingKey) -> list[int]:
    if len(witness) != key.header.n_signals:
        raise ValueError(
            f"witness must contain exactly {key.header.n_signals} values"
        )
    normalized: list[int] = []
    for index, value in enumerate(witness):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"witness[{index}] is not an integer")
        if not 0 <= value < FR_MODULUS:
            raise ValueError(f"witness[{index}] is outside Fr")
        normalized.append(value)
    if normalized[0] != 1:
        raise ValueError("witness[0] must be one")
    return normalized


def _random_scalar() -> int:
    # Avoid the degenerate zero case; entropy failures still come from the OS.
    while True:
        scalar = secrets.randbelow(FR_MODULUS)
        if scalar:
            return scalar


def _worker_count() -> int:
    workers = config.ZK_WORKERS
    if isinstance(workers, bool) or not isinstance(workers, int):
        raise ValueError("ZK_WORKERS must be an integer")
    if not 1 <= workers <= 8:
        raise ValueError("ZK_WORKERS must be between 1 and 8")
    return workers


def prove_with_key(
    witness: Sequence[int],
    key: LegacyProvingKey,
) -> dict[str, Any]:
    """Create a proof with fresh cryptographically secure randomness."""

    scalars = _validate_witness(witness, key)
    random_r = _random_scalar()
    random_s = _random_scalar()

    h = calculate_h(
        scalars,
        key.pols_a,
        key.pols_b,
        key.header.domain_size,
    )
    if len(h) != key.header.domain_size or h[-1] != 0:
        raise ValueError("witness does not produce a valid Groth16 H polynomial")

    private_scalars = scalars[key.header.n_public + 1 :]
    h_scalars = h[: len(key.points_h)]
    queries = query_msms(
        key,
        scalars,
        private_scalars,
        h_scalars,
        workers=_worker_count(),
    )

    a_query, b1_query, b2_query, c_query, h_query = (
        queries[name] for name in ("a", "b1", "b2", "c", "h")
    )

    alpha1 = _g1(key.alpha1)
    beta1 = _g1(key.beta1)
    delta1 = _g1(key.delta1)
    beta2 = _g2(key.beta2)
    delta2 = _g2(key.delta2)

    pi_a = add(add(alpha1, a_query), multiply(delta1, random_r))
    pi_b = add(add(beta2, b2_query), multiply(delta2, random_s))
    b1 = add(add(beta1, b1_query), multiply(delta1, random_s))

    pi_c = add(c_query, h_query)
    pi_c = add(pi_c, multiply(pi_a, random_s))
    pi_c = add(pi_c, multiply(b1, random_r))
    pi_c = add(
        pi_c,
        neg(multiply(delta1, random_r * random_s % curve_order)),
    )

    return proof_to_dict(
        pi_a,
        pi_b,
        pi_c,
        scalars[1 : key.header.n_public + 1],
    )


def prove(
    witness: Sequence[int],
) -> dict[str, Any]:
    """Create a proof using the authenticated bundled Tornado proving key."""

    with open_tornado_proving_key() as key:
        return prove_with_key(witness, key)
