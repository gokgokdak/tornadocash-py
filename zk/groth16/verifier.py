"""Groth16 verifier for the deployed Tornado BN254 circuit."""

from __future__ import annotations

import json
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from py_ecc.optimized_bn128 import (
    FQ12,
    add,
    b,
    b2,
    curve_order,
    final_exponentiate,
    is_inf,
    is_on_curve,
    multiply,
    neg,
    pairing,
)

from .serialization import (
    G1Point,
    G2Point,
    PUBLIC_INPUT_COUNT,
    ParsedProof,
    parse_g1,
    parse_g2,
    parse_proof,
    validate_solidity_block,
)
from .constants import TORNADO_VERIFICATION_KEY_SHA256


DEFAULT_VERIFICATION_KEY_PATH = (
    Path(__file__).resolve().parent.parent
    / "tornado"
    / "verification_key.json"
)


@dataclass(frozen=True, slots=True)
class VerificationKey:
    alpha_1: G1Point
    beta_2: G2Point
    gamma_2: G2Point
    delta_2: G2Point
    ic: tuple[G1Point, ...]
    alpha_beta_miller: FQ12


def _valid_g1(point: G1Point) -> bool:
    return not is_inf(point) and is_on_curve(point, b)


def _in_g2_subgroup(point: G2Point) -> bool:
    return is_inf(multiply(point, curve_order))


def _valid_g2(point: G2Point) -> bool:
    return (
        not is_inf(point)
        and is_on_curve(point, b2)
        and _in_g2_subgroup(point)
    )


def _parse_verification_key(value: Any) -> VerificationKey:
    if not isinstance(value, Mapping):
        raise ValueError("verification key must be an object")
    if value.get("protocol") != "groth":
        raise ValueError("verification key protocol must be groth")

    n_public = value.get("nPublic")
    if isinstance(n_public, bool) or n_public != PUBLIC_INPUT_COUNT:
        raise ValueError(f"verification key must declare {PUBLIC_INPUT_COUNT} inputs")

    raw_ic = value.get("IC")
    if (
        not isinstance(raw_ic, Sequence)
        or isinstance(raw_ic, (str, bytes, bytearray))
        or len(raw_ic) != PUBLIC_INPUT_COUNT + 1
    ):
        raise ValueError("verification key has an invalid IC table")

    alpha_1 = parse_g1(value.get("vk_alfa_1"), label="vk_alfa_1")
    beta_2 = parse_g2(value.get("vk_beta_2"), label="vk_beta_2")
    gamma_2 = parse_g2(value.get("vk_gamma_2"), label="vk_gamma_2")
    delta_2 = parse_g2(value.get("vk_delta_2"), label="vk_delta_2")
    ic = tuple(parse_g1(point, label=f"IC[{index}]") for index, point in enumerate(raw_ic))

    if not _valid_g1(alpha_1) or not all(_valid_g1(point) for point in ic):
        raise ValueError("verification key contains an invalid G1 point")
    if not all(_valid_g2(point) for point in (beta_2, gamma_2, delta_2)):
        raise ValueError("verification key contains an invalid G2 point")

    return VerificationKey(
        alpha_1=alpha_1,
        beta_2=beta_2,
        gamma_2=gamma_2,
        delta_2=delta_2,
        ic=ic,
        alpha_beta_miller=pairing(
            beta_2,
            neg(alpha_1),
            final_exponentiate=False,
        ),
    )


@lru_cache(maxsize=1)
def _load_verification_key() -> VerificationKey:
    raw = DEFAULT_VERIFICATION_KEY_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != TORNADO_VERIFICATION_KEY_SHA256:
        raise ValueError("Tornado verification-key SHA-256 mismatch")
    return _parse_verification_key(json.loads(raw))


def _validate_proof_points(proof: ParsedProof) -> None:
    if not _valid_g1(proof.a) or not _valid_g1(proof.c):
        raise ValueError("proof contains an invalid G1 point")
    if not _valid_g2(proof.b):
        raise ValueError("proof contains an invalid or non-subgroup G2 point")


def verify(proof: Any) -> bool:
    """Verify a Tornado proof; malformed or invalid inputs always return ``False``."""

    try:
        parsed = parse_proof(proof)
        _validate_proof_points(parsed)
        validate_solidity_block(proof, parsed)
        verification_key = _load_verification_key()

        public_key = verification_key.ic[0]
        for ic_point, signal in zip(
            verification_key.ic[1:],
            parsed.public_signals,
            strict=True,
        ):
            public_key = add(public_key, multiply(ic_point, signal))

        # Move all terms to the left side of the Groth16 equation.  Each
        # pairing below performs only a Miller loop; one final exponentiation
        # is applied to their product.
        miller_product = pairing(
            parsed.b,
            parsed.a,
            final_exponentiate=False,
        )
        miller_product *= pairing(
            verification_key.gamma_2,
            neg(public_key),
            final_exponentiate=False,
        )
        miller_product *= pairing(
            verification_key.delta_2,
            neg(parsed.c),
            final_exponentiate=False,
        )
        miller_product *= verification_key.alpha_beta_miller

        return final_exponentiate(miller_product) == FQ12.one()
    except Exception:
        return False
