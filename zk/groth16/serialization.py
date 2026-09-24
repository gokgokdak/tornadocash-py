"""Strict parsing and Solidity serialization for Tornado Groth16 proofs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

from py_ecc.optimized_bn128 import FQ, FQ2, curve_order, field_modulus, is_inf, normalize


PUBLIC_INPUT_COUNT = 6
SOLIDITY_PROOF_SIZE = 8 * 32

G1Point: TypeAlias = tuple[FQ, FQ, FQ]
G2Point: TypeAlias = tuple[FQ2, FQ2, FQ2]


@dataclass(frozen=True, slots=True)
class ParsedProof:
    """A canonical Groth16 proof converted to ``py_ecc`` field values."""

    a: G1Point
    b: G2Point
    c: G1Point
    public_signals: tuple[int, ...]


def _sequence(value: Any, *, length: int, label: str) -> Sequence[Any]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) != length
    ):
        raise ValueError(f"{label} must contain exactly {length} values")
    return value


def _uint(value: Any, *, modulus: int, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an unsigned integer")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value and value.isascii() and value.isdecimal():
        number = int(value, 10)
    else:
        raise ValueError(f"{label} must be an unsigned decimal integer")
    if number < 0 or number >= modulus:
        raise ValueError(f"{label} is outside its field")
    return number


def parse_g1(value: Any, *, label: str = "G1 point") -> G1Point:
    """Parse a canonical affine G1 point represented as ``[x, y, 1]``."""

    coordinates = _sequence(value, length=3, label=label)
    x = _uint(coordinates[0], modulus=field_modulus, label=f"{label}.x")
    y = _uint(coordinates[1], modulus=field_modulus, label=f"{label}.y")
    z = _uint(coordinates[2], modulus=field_modulus, label=f"{label}.z")
    if z != 1:
        raise ValueError(f"{label} must be an affine, non-infinity point")
    return FQ(x), FQ(y), FQ.one()


def parse_g2(value: Any, *, label: str = "G2 point") -> G2Point:
    """Parse a canonical affine G2 point using FQ2 coefficient order c0,c1."""

    coordinates = _sequence(value, length=3, label=label)
    x = _sequence(coordinates[0], length=2, label=f"{label}.x")
    y = _sequence(coordinates[1], length=2, label=f"{label}.y")
    z = _sequence(coordinates[2], length=2, label=f"{label}.z")

    x0 = _uint(x[0], modulus=field_modulus, label=f"{label}.x.c0")
    x1 = _uint(x[1], modulus=field_modulus, label=f"{label}.x.c1")
    y0 = _uint(y[0], modulus=field_modulus, label=f"{label}.y.c0")
    y1 = _uint(y[1], modulus=field_modulus, label=f"{label}.y.c1")
    z0 = _uint(z[0], modulus=field_modulus, label=f"{label}.z.c0")
    z1 = _uint(z[1], modulus=field_modulus, label=f"{label}.z.c1")
    if (z0, z1) != (1, 0):
        raise ValueError(f"{label} must be an affine, non-infinity point")

    return FQ2((x0, x1)), FQ2((y0, y1)), FQ2.one()


def parse_public_signals(value: Any) -> tuple[int, ...]:
    signals = _sequence(
        value,
        length=PUBLIC_INPUT_COUNT,
        label="publicSignals",
    )
    return tuple(
        _uint(signal, modulus=curve_order, label=f"publicSignals[{index}]")
        for index, signal in enumerate(signals)
    )


def parse_proof(value: Any) -> ParsedProof:
    """Parse the canonical proof fields without accepting field reduction."""

    if not isinstance(value, Mapping):
        raise ValueError("proof must be an object")
    return ParsedProof(
        a=parse_g1(value.get("pi_a"), label="pi_a"),
        b=parse_g2(value.get("pi_b"), label="pi_b"),
        c=parse_g1(value.get("pi_c"), label="pi_c"),
        public_signals=parse_public_signals(value.get("publicSignals")),
    )


def solidity_proof_bytes(proof: ParsedProof) -> bytes:
    """Encode a proof in the eight-word order expected by Tornado contracts."""

    bx0, bx1 = (int(coefficient) for coefficient in proof.b[0].coeffs)
    by0, by1 = (int(coefficient) for coefficient in proof.b[1].coeffs)
    words = (
        int(proof.a[0]),
        int(proof.a[1]),
        bx1,
        bx0,
        by1,
        by0,
        int(proof.c[0]),
        int(proof.c[1]),
    )
    return b"".join(word.to_bytes(32, byteorder="big") for word in words)


def to_solidity(proof: ParsedProof | Mapping[str, Any]) -> dict[str, Any]:
    """Return the Solidity proof/public-input representation used by the JS API."""

    parsed = proof if isinstance(proof, ParsedProof) else parse_proof(proof)
    return {
        "proof": "0x" + solidity_proof_bytes(parsed).hex(),
        "publicSignals": [f"0x{signal:064x}" for signal in parsed.public_signals],
    }


def proof_to_dict(
    a: G1Point,
    b: G2Point,
    c: G1Point,
    public_signals: Sequence[int],
) -> dict[str, Any]:
    """Build the legacy JS-compatible result dictionary from Jacobian points."""

    if is_inf(a) or is_inf(b) or is_inf(c):
        raise ValueError("a Groth16 proof may not contain the point at infinity")
    normalized_a = normalize(a)
    normalized_b = normalize(b)
    normalized_c = normalize(c)
    signals = parse_public_signals(public_signals)

    result: dict[str, Any] = {
        "pi_a": [str(int(normalized_a[0])), str(int(normalized_a[1])), "1"],
        "pi_b": [
            [
                str(int(normalized_b[0].coeffs[0])),
                str(int(normalized_b[0].coeffs[1])),
            ],
            [
                str(int(normalized_b[1].coeffs[0])),
                str(int(normalized_b[1].coeffs[1])),
            ],
            ["1", "0"],
        ],
        "pi_c": [str(int(normalized_c[0])), str(int(normalized_c[1])), "1"],
        "publicSignals": [str(signal) for signal in signals],
    }
    result["solidity"] = to_solidity(result)
    return result


def _hex_bytes(value: Any, *, expected_size: int, label: str) -> bytes:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a hex string")
    payload = value[2:] if value.startswith(("0x", "0X")) else value
    if len(payload) != expected_size * 2 or not payload.isascii():
        raise ValueError(f"{label} must encode exactly {expected_size} bytes")
    try:
        decoded = bytes.fromhex(payload)
    except ValueError as exc:
        raise ValueError(f"{label} is not valid hexadecimal") from exc
    if len(decoded) != expected_size:
        raise ValueError(f"{label} must encode exactly {expected_size} bytes")
    return decoded


def _solidity_signal(value: Any, *, index: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"solidity.publicSignals[{index}] is invalid")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.startswith(("0x", "0X")):
        payload = value[2:]
        if not payload or len(payload) > 64 or not payload.isascii():
            raise ValueError(f"solidity.publicSignals[{index}] is invalid")
        try:
            number = int(payload, 16)
        except ValueError as exc:
            raise ValueError(
                f"solidity.publicSignals[{index}] is invalid"
            ) from exc
    else:
        raise ValueError(f"solidity.publicSignals[{index}] is invalid")
    if number < 0 or number >= curve_order:
        raise ValueError(f"solidity.publicSignals[{index}] is outside Fr")
    return number


def validate_solidity_block(raw_proof: Mapping[str, Any], proof: ParsedProof) -> None:
    """Require an optional Solidity block to agree with canonical proof fields."""

    if "solidity" not in raw_proof:
        return
    solidity = raw_proof["solidity"]
    if not isinstance(solidity, Mapping):
        raise ValueError("solidity must be an object")

    encoded = _hex_bytes(
        solidity.get("proof"),
        expected_size=SOLIDITY_PROOF_SIZE,
        label="solidity.proof",
    )
    if encoded != solidity_proof_bytes(proof):
        raise ValueError("solidity.proof does not match canonical proof points")

    public_signals = _sequence(
        solidity.get("publicSignals"),
        length=PUBLIC_INPUT_COUNT,
        label="solidity.publicSignals",
    )
    parsed_signals = tuple(
        _solidity_signal(signal, index=index)
        for index, signal in enumerate(public_signals)
    )
    if parsed_signals != proof.public_signals:
        raise ValueError(
            "solidity.publicSignals do not match canonical publicSignals"
        )
