"""Prepared batch MSMs for the Tornado proving key."""

from __future__ import annotations

import atexit
import threading
from collections.abc import Sequence
from typing import Any

from py_ecc.optimized_bn128 import FQ, FQ2, Z1, Z2

from . import native
from .artifacts import LegacyProvingKey


_QUERY_SPECS = (
    ("a", "points_a", False),
    ("b1", "points_b1", False),
    ("b2", "points_b2", True),
    ("c", "points_c", False),
    ("h", "points_h", False),
)
_LOCK = threading.Lock()
_PREPARED: tuple[str, tuple[Any, ...]] | None = None
_EXECUTOR: tuple[int, Any] | None = None


def _point(value: bytes | None, *, g2: bool):
    if value is None:
        return Z2 if g2 else Z1
    coordinates = tuple(
        int.from_bytes(value[offset : offset + 32], "little")
        for offset in range(0, len(value), 32)
    )
    if g2:
        x0, x1, y0, y1 = coordinates
        return FQ2((x0, x1)), FQ2((y0, y1)), FQ2.one()
    x, y = coordinates
    return FQ(x), FQ(y), FQ.one()


def _prepared_queries(key: LegacyProvingKey) -> tuple[Any, ...]:
    global _PREPARED
    with _LOCK:
        if _PREPARED is None or _PREPARED[0] != key.sha256:
            prepared = tuple(
                native.prepare_msm(
                    getattr(key, attribute).encoded_bytes(),
                    g2=g2,
                )
                for _, attribute, g2 in _QUERY_SPECS
            )
            _PREPARED = key.sha256, prepared
        return _PREPARED[1]


def _executor(workers: int):
    global _EXECUTOR
    with _LOCK:
        if _EXECUTOR is None or _EXECUTOR[0] != workers:
            _EXECUTOR = workers, native.create_msm_executor(workers)
        return _EXECUTOR[1]


def query_msms(
    key: LegacyProvingKey,
    witness: Sequence[int],
    private_witness: Sequence[int],
    h: Sequence[int],
    *,
    workers: int,
) -> dict[str, Any]:
    witness_buffer = native.pack_fr(witness)
    requests = tuple(
        zip(
            _prepared_queries(key),
            (witness_buffer,) * 3
            + (native.pack_fr(private_witness), native.pack_fr(h)),
            strict=True,
        )
    )
    results = native.msm_batch(_executor(workers), requests)
    return {
        name: _point(result, g2=g2)
        for (name, _, g2), result in zip(_QUERY_SPECS, results, strict=True)
    }


def clear_cache() -> None:
    global _PREPARED, _EXECUTOR
    with _LOCK:
        resources = _PREPARED, _EXECUTOR
        _PREPARED = _EXECUTOR = None
    del resources


atexit.register(clear_cache)
