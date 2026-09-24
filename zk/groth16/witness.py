"""Pure-Python witness generation for the fixed Tornado Cash Circom-1 circuit.

The circuit's generated template functions and routing metadata are compiled
ahead of time in :mod:`_witness_program`.  This module deliberately contains no
JavaScript parser, evaluator, Node subprocess, or runtime dependency on
``circuit.json``.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import sys
import threading
from typing import Any
import zlib

from ._witness_program import (
    FUNCTIONS,
    METADATA_B85,
    N_INPUTS,
    N_SIGNALS,
    N_VARS,
    F,
    TEMPLATES,
)


REQUIRED_INPUTS = (
    "root",
    "nullifierHash",
    "recipient",
    "relayer",
    "fee",
    "refund",
    "nullifier",
    "secret",
    "pathElements",
    "pathIndices",
)

# Circom 1 calculates child components synchronously: assigning the final child
# input triggers its template before the parent immediately reads that child's
# output.  The fixed Pedersen circuit contains a deterministic chain of roughly
# 2,025 Python frames.  Replacing it with a queue would change those read-after-
# trigger semantics unless every generated template became a resumable
# continuation.  Raise the process limit lazily with conservative headroom.
_MIN_WITNESS_RECURSION_LIMIT = 3_000
_RECURSION_LIMIT_LOCK = threading.Lock()


class WitnessError(ValueError):
    """The supplied input cannot produce a valid Tornado witness."""


def _ensure_recursion_budget() -> None:
    """Monotonically install the stack budget needed by the fixed AOT graph.

    ``sys.setrecursionlimit`` is process-wide.  Restoring a previous value is
    unsafe when another thread may still be evaluating a witness, so this is a
    lazy, locked, idempotent increase and never a temporary decrease.
    """

    if sys.getrecursionlimit() >= _MIN_WITNESS_RECURSION_LIMIT:
        return
    with _RECURSION_LIMIT_LOCK:
        if sys.getrecursionlimit() < _MIN_WITNESS_RECURSION_LIMIT:
            sys.setrecursionlimit(_MIN_WITNESS_RECURSION_LIMIT)


@dataclass(frozen=True, slots=True)
class _Component:
    name: str
    params: Mapping[str, Any]
    template: str
    input_signals: int


def _decode_metadata():
    compressed = base64.b85decode(METADATA_B85.encode("ascii"))
    raw = json.loads(zlib.decompress(compressed))
    components = tuple(
        _Component(name, params, template, input_signals)
        for name, params, template, input_signals in raw["components"]
    )
    signal_names = tuple(tuple(item[0]) for item in raw["signals"])
    trigger_components = tuple(tuple(item[1]) for item in raw["signals"])
    signal_name_to_index = {
        name: index for index, names in enumerate(signal_names) for name in names
    }
    if len(components) != 2_342 or len(signal_names) != N_SIGNALS:
        raise RuntimeError("corrupt static Tornado witness metadata")
    return components, signal_names, trigger_components, signal_name_to_index


(
    _COMPONENTS,
    _SIGNAL_NAMES,
    _TRIGGER_COMPONENTS,
    _SIGNAL_NAME_TO_INDEX,
) = _decode_metadata()


def _selector(value: Any) -> int:
    index = int(value)
    if index < 0:
        raise WitnessError(f"negative array selector: {index}")
    return index


def _select(value: Any, selectors: Sequence[Any]) -> Any:
    for selector in selectors:
        value = value[_selector(selector)]
    return value


def _set_array(value: list[Any], selectors: Sequence[Any], item: Any) -> None:
    current = value
    for selector in selectors[:-1]:
        index = _selector(selector)
        while len(current) <= index:
            current.append(None)
        if current[index] is None:
            current[index] = []
        current = current[index]
    index = _selector(selectors[-1])
    while len(current) <= index:
        current.append(None)
    current[index] = item


def _suffix(selectors: Sequence[Any]) -> str:
    return "".join(f"[{int(selector)}]" for selector in selectors)


class _RuntimeContext:
    """Compatibility runtime for Circom 1's generated component graph."""

    __slots__ = (
        "currentComponent",
        "notInitSignals",
        "scopes",
        "witness",
    )

    def __init__(self) -> None:
        self.currentComponent: str | None = None
        self.scopes: list[dict[str, Any]] = []
        self.witness: list[F | None] = [None] * N_SIGNALS
        self.notInitSignals = [component.input_signals for component in _COMPONENTS]

    def setPin(
        self,
        component_name: str,
        component_selectors: Sequence[Any],
        signal_name: str,
        signal_selectors: Sequence[Any],
        value: Any,
    ) -> F:
        if component_name == "one":
            full_name = "one"
        else:
            full_name = f"{self.currentComponent}.{component_name}"
        full_name += _suffix(component_selectors)
        full_name += f".{signal_name}{_suffix(signal_selectors)}"
        return self.setSignalFullName(full_name, value)

    def setSignal(self, name: str, selectors: Sequence[Any], value: Any) -> F:
        full_name = f"{self.currentComponent}.{name}" if self.currentComponent else name
        return self.setSignalFullName(full_name + _suffix(selectors), value)

    def triggerComponent(self, component_index: int) -> None:
        # Legacy snarkjs decremented once more at entry.  Besides matching its
        # state machine, this prevents a fully initialized component from being
        # triggered again through an aliased signal.
        self.notInitSignals[component_index] -= 1
        component = _COMPONENTS[component_index]
        previous_component = self.currentComponent
        previous_scopes = self.scopes
        self.currentComponent = component.name
        global_scope = previous_scopes[0] if previous_scopes else {}
        self.scopes = [global_scope, dict(component.params)]
        try:
            TEMPLATES[component.template](self)
        finally:
            self.scopes = previous_scopes
            self.currentComponent = previous_component

    def callFunction(self, function_name: str, params: Sequence[Any]) -> Any:
        try:
            names, function = FUNCTIONS[function_name]
        except KeyError as error:
            raise WitnessError(f"unknown circuit helper: {function_name}") from error
        if len(names) != len(params):
            raise WitnessError(
                f"helper {function_name} expects {len(names)} arguments, got {len(params)}"
            )
        previous_scopes = self.scopes
        global_scope = previous_scopes[0] if previous_scopes else {}
        self.scopes = [global_scope, dict(zip(names, params, strict=True))]
        try:
            return function(self)
        finally:
            self.scopes = previous_scopes

    def setSignalFullName(self, full_name: str, value: Any) -> F:
        try:
            signal_index = _SIGNAL_NAME_TO_INDEX[full_name]
        except KeyError as error:
            raise WitnessError(f"invalid signal identifier: {full_name}") from error
        first_initialization = self.witness[signal_index] is None
        normalized = F(value)
        self.witness[signal_index] = normalized
        components = _TRIGGER_COMPONENTS[signal_index]
        if first_initialization:
            for component_index in components:
                self.notInitSignals[component_index] -= 1
        for component_index in components:
            if self.notInitSignals[component_index] == 0:
                self.triggerComponent(component_index)
        return normalized

    def setVar(self, name: str, selectors: Sequence[Any], value: Any) -> Any:
        scope = self.scopes[-1]
        if not selectors:
            scope[name] = value
        else:
            if name not in scope or scope[name] is None:
                scope[name] = []
            _set_array(scope[name], selectors, value)
        return value

    def getVar(self, name: str, selectors: Sequence[Any]) -> Any:
        for scope in reversed(self.scopes):
            if name in scope and scope[name] is not None:
                try:
                    return _select(scope[name], selectors)
                except (IndexError, TypeError) as error:
                    raise WitnessError(
                        f"variable selector is not initialized: {name}{_suffix(selectors)}"
                    ) from error
        raise WitnessError(f"variable not defined: {name}")

    def getSignal(self, name: str, selectors: Sequence[Any]) -> F:
        full_name = "one" if name == "one" else f"{self.currentComponent}.{name}"
        return self.getSignalFullName(full_name + _suffix(selectors))

    def getPin(
        self,
        component_name: str,
        component_selectors: Sequence[Any],
        signal_name: str,
        signal_selectors: Sequence[Any],
    ) -> F:
        if component_name == "one":
            full_name = "one"
        else:
            full_name = f"{self.currentComponent}.{component_name}"
        full_name += _suffix(component_selectors)
        full_name += f".{signal_name}{_suffix(signal_selectors)}"
        return self.getSignalFullName(full_name)

    def getSignalFullName(self, full_name: str) -> F:
        try:
            signal_index = _SIGNAL_NAME_TO_INDEX[full_name]
        except KeyError as error:
            raise WitnessError(f"invalid signal identifier: {full_name}") from error
        value = self.witness[signal_index]
        if value is None:
            raise WitnessError(f"signal not initialized: {full_name}")
        return value

    def assert_(self, left: Any, right: Any, source: str) -> None:
        if F(left) != F(right):
            raise WitnessError(
                f"constraint does not match {self.currentComponent}: {source}: "
                f"{int(F(left))} != {int(F(right))}"
            )


def _iterate_input(value: Any, selectors: list[int]):
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            selectors.append(index)
            yield from _iterate_input(item, selectors)
            selectors.pop()
    else:
        yield selectors, value


def _validate_iden3math(inputs: Mapping[str, Any], commitment: int) -> None:
    """Cross-check circuit-domain results with iden3math's native APIs."""

    import iden3math
    from iden3math import ec, hash

    nullifier = int(inputs["nullifier"])
    secret = int(inputs["secret"])
    try:
        nullifier_bytes = bytearray(nullifier.to_bytes(31, "little"))
        secret_bytes = bytearray(secret.to_bytes(31, "little"))
    except OverflowError as error:
        raise WitnessError("nullifier and secret must each fit in 248 bits") from error

    def pedersen_x(preimage: bytearray) -> int:
        compressed = hash.pedersen(preimage)
        point = ec.babyjub.decompress(compressed, iden3math.Endian.LE)
        return point.x()

    expected_nullifier_hash = pedersen_x(nullifier_bytes)
    expected_commitment = pedersen_x(nullifier_bytes + secret_bytes)
    if expected_nullifier_hash != int(inputs["nullifierHash"]):
        raise WitnessError("iden3math nullifierHash cross-check failed")
    if expected_commitment != commitment:
        raise WitnessError("iden3math commitment cross-check failed")

    current = commitment
    path_elements = inputs["pathElements"]
    path_indices = inputs["pathIndices"]
    if len(path_elements) != 20 or len(path_indices) != 20:
        raise WitnessError("Tornado circuit requires exactly 20 Merkle path levels")
    for sibling, index in zip(path_elements, path_indices, strict=True):
        if int(index) not in (0, 1):
            raise WitnessError("Merkle path indices must be zero or one")
        pair = (current, int(sibling)) if int(index) == 0 else (int(sibling), current)
        current = int.from_bytes(
            hash.mimc_sponge(
                [item.to_bytes(32, "big") for item in pair], 1, b""
            )[0],
            "big",
        )
    if current != int(inputs["root"]):
        raise WitnessError("iden3math Merkle root cross-check failed")


def calculate_witness(inputs: Mapping[str, Any]) -> list[int]:
    """Calculate all 28,300 proving variables for a Tornado withdrawal.

    ``inputs`` uses the same ten logical keys as the legacy snarkjs witness
    calculator. Scalar values may be decimal strings or integers; Merkle path
    values are flat sequences of length 20.
    """

    if not isinstance(inputs, Mapping):
        raise TypeError("witness inputs must be a mapping")
    missing = [name for name in REQUIRED_INPUTS if name not in inputs]
    extra = [name for name in inputs if name not in REQUIRED_INPUTS]
    if missing or extra:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unknown " + ", ".join(extra))
        raise WitnessError("invalid witness inputs: " + "; ".join(details))

    _ensure_recursion_budget()
    context = _RuntimeContext()
    context.setSignalFullName("one", 1)
    for component_index in range(len(_COMPONENTS)):
        if context.notInitSignals[component_index] == 0:
            context.triggerComponent(component_index)

    for name, value in inputs.items():
        context.currentComponent = "main"
        for selectors, item in _iterate_input(value, []):
            if item is None:
                raise WitnessError(f"input signal not defined: {name}{_suffix(selectors)}")
            context.setSignal(name, selectors, item)

    for signal_index in range(1, N_INPUTS + 1):
        if context.witness[signal_index] is None:
            raise WitnessError(
                "input signal not assigned: " + ", ".join(_SIGNAL_NAMES[signal_index])
            )
    for signal_index, value in enumerate(context.witness):
        if value is None:
            raise WitnessError(
                "signal not assigned: " + ", ".join(_SIGNAL_NAMES[signal_index])
            )

    commitment_index = _SIGNAL_NAME_TO_INDEX["main.hasher.commitment"]
    _validate_iden3math(inputs, int(context.witness[commitment_index]))
    return [int(value) for value in context.witness[:N_VARS]]
