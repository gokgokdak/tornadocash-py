"""Conversion of application objects to the fixed Tornado circuit inputs."""

from __future__ import annotations

from typing import TypeAlias

from hexbytes import HexBytes

from components.mytype import CircuitInput


WitnessValue: TypeAlias = int | list[int]


def _address_to_int(value: str) -> int:
    raw = value[2:] if value.startswith(("0x", "0X")) else value
    encoded = HexBytes.fromhex(raw)
    if len(encoded) != 20:
        raise ValueError("recipient and relayer must be 20-byte addresses")
    return int.from_bytes(encoded, byteorder="big")


def prepare_circuit_input(ctx: CircuitInput) -> dict[str, WitnessValue]:
    """Return integer inputs in the exact order/endianness of the old JS API."""

    path_nodes = list(ctx.merkle_proof.path_nodes)
    path_indices = [int(index) for index in ctx.merkle_proof.path_indices]
    if len(path_nodes) != len(path_indices):
        raise ValueError("Merkle path nodes and indices must have the same length")

    return {
        "root": int.from_bytes(ctx.merkle_proof.root, byteorder="big"),
        "nullifierHash": int.from_bytes(ctx.note.nullifier_hash, byteorder="big"),
        "recipient": _address_to_int(ctx.recipient),
        "relayer": _address_to_int(ctx.relayer),
        "fee": int(ctx.fee),
        "refund": int(ctx.refund),
        # Note buffers are defined by the existing API as little-endian values.
        "nullifier": int.from_bytes(ctx.note.nullifier, byteorder="little"),
        "secret": int.from_bytes(ctx.note.secret, byteorder="little"),
        "pathElements": [int.from_bytes(node, byteorder="big") for node in path_nodes],
        "pathIndices": path_indices,
    }
