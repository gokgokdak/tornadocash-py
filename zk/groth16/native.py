"""Validated adapters for the required BN254 batch API."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from iden3math import ec, field, polynomial

from .constants import FQ_MODULUS, FR_MODULUS


def _load() -> tuple[Any, Any]:
    field_api = field.bn254
    ec_api = ec.bn254
    polynomial_api = polynomial.bn254
    required = (
        (field_api, ("fr_modulus", "fq_modulus")),
        (ec_api, ("prepare_g1", "prepare_g2", "MsmExecutor")),
        (polynomial_api, ("ntt_fr",)),
    )
    if any(
        not all(callable(getattr(module, name, None)) for name in names)
        for module, names in required
    ):
        raise RuntimeError("Python ZK backend requires the BN254 batch API")
    if int(field_api.fr_modulus()) != FR_MODULUS:
        raise RuntimeError("BN254 scalar field is incompatible")
    if int(field_api.fq_modulus()) != FQ_MODULUS:
        raise RuntimeError("BN254 base field is incompatible")
    return ec_api, polynomial_api


_EC, _POLYNOMIAL = _load()


def pack_fr(values: Sequence[int]) -> bytearray:
    output = bytearray(32 * len(values))
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"scalar[{index}] is not an integer")
        if not 0 <= value < FR_MODULUS:
            raise ValueError(f"scalar[{index}] is outside Fr")
        offset = 32 * index
        output[offset : offset + 32] = value.to_bytes(32, "little")
    return output


def unpack_fr(values: bytes | bytearray | memoryview) -> list[int]:
    view = memoryview(values)
    try:
        if view.ndim != 1 or view.itemsize != 1 or not view.c_contiguous:
            raise ValueError("Fr buffer must be contiguous bytes")
        if view.nbytes % 32:
            raise ValueError("Fr buffer length is not a multiple of 32")
        result = [
            int.from_bytes(view[offset : offset + 32], "little")
            for offset in range(0, view.nbytes, 32)
        ]
        if any(value >= FR_MODULUS for value in result):
            raise ValueError("Fr output contains a non-canonical value")
        return result
    finally:
        view.release()


def validate_msm_result(value: Any, *, g2: bool) -> bytes | None:
    if value is None:
        return None
    raw = bytes(value)
    expected = 128 if g2 else 64
    if len(raw) != expected:
        raise RuntimeError(f"MSM returned {len(raw)} bytes, expected {expected}")
    if any(
        int.from_bytes(raw[offset : offset + 32], "little") >= FQ_MODULUS
        for offset in range(0, expected, 32)
    ):
        raise RuntimeError("MSM returned a non-canonical coordinate")
    return raw


def prepare_msm(
    points: bytes | bytearray | memoryview,
    *,
    g2: bool,
) -> Any:
    prepared = (_EC.prepare_g2 if g2 else _EC.prepare_g1)(
        points,
        points_montgomery=True,
        validation="none",
    )
    group = "g2" if g2 else "g1"
    if getattr(prepared, "group", None) != group:
        raise RuntimeError("prepared MSM returned the wrong group")
    with memoryview(points) as view:
        width = 128 if g2 else 64
        if view.nbytes % width:
            raise ValueError("packed point buffer has an invalid length")
        count = view.nbytes // width
    if getattr(prepared, "point_count", None) != count:
        raise RuntimeError("prepared MSM changed the point count")
    return prepared


def create_msm_executor(threads: int) -> Any:
    if isinstance(threads, bool) or not isinstance(threads, int):
        raise ValueError("MSM threads must be an integer")
    if threads <= 0:
        raise ValueError("MSM threads must be positive")
    executor = _EC.MsmExecutor(threads=threads)
    if getattr(executor, "threads", None) != threads:
        raise RuntimeError("MSM executor changed the thread count")
    return executor


def msm_batch(
    executor: Any,
    requests: Sequence[tuple[Any, bytes | bytearray | memoryview]],
) -> list[bytes | None]:
    results = executor.msm_batch(requests)
    if len(results) != len(requests):
        raise RuntimeError("MSM batch changed the request count")
    normalized = []
    for index, ((prepared, _), result) in enumerate(zip(requests, results, strict=True)):
        group = getattr(prepared, "group", None)
        if group not in ("g1", "g2"):
            raise RuntimeError(f"MSM request {index} has an invalid group")
        normalized.append(validate_msm_result(result, g2=group == "g2"))
    return normalized


def ntt(
    values: Sequence[int],
    *,
    inverse: bool,
    root: int,
    coset: int = 1,
) -> list[int]:
    for label, value in (("root", root), ("coset", coset)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"NTT {label} is not an integer")
        if not 0 <= value < FR_MODULUS:
            raise ValueError(f"NTT {label} is outside Fr")
    raw = _POLYNOMIAL.ntt_fr(
        pack_fr(values),
        inverse=inverse,
        root=root.to_bytes(32, "little"),
        coset=coset.to_bytes(32, "little"),
    )
    result = unpack_fr(raw)
    if len(result) != len(values):
        raise RuntimeError("NTT changed the batch length")
    return result
