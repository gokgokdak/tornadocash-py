"""Developer-only AOT compiler for the fixed Tornado Circom-1 witness code.

This script is never imported by the runtime.  It converts the generated
function bodies embedded in the authenticated production ``circuit.json`` to
ordinary Python functions and embeds only the component/signal routing data.

The optional development dependency is deliberately not a runtime dependency::

    python -m pip install esprima==4.0.1
    python -m zk.groth16.generate_witness_program --check

Run without ``--check`` to regenerate ``_witness_program.py`` atomically.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any
import zlib

try:
    import esprima
except ImportError as error:  # pragma: no cover - developer setup failure
    raise SystemExit(
        "generate_witness_program requires the dev-only dependency "
        "esprima==4.0.1"
    ) from error


EXPECTED_ESPRIMA_VERSION = "4.0.1"
EXPECTED_CIRCUIT_SHA256 = (
    "3ddd61dbff09caeec82d8edde95c674a3c34f9e66b1fe9f2c8783e72fe536f98"
)
DEFAULT_CIRCUIT = Path(__file__).resolve().parents[1] / "tornado" / "circuit.json"
DEFAULT_OUTPUT = Path(__file__).with_name("_witness_program.py")

_METHOD_NAMES = {"and": "band", "assert": "assert_"}
_IDENTIFIERS = {"bigInt": "F", "__P__": "P", "__MASK__": "MASK"}


def _expression(node: Any) -> str:
    kind = node.type
    if kind == "Identifier":
        return _IDENTIFIERS.get(node.name, node.name)
    if kind == "Literal":
        return repr(node.value)
    if kind == "ArrayExpression":
        return "[" + ", ".join(_expression(item) for item in node.elements) + "]"
    if kind == "MemberExpression":
        if node.computed:
            raise ValueError("computed member expressions are not supported")
        name = _METHOD_NAMES.get(node.property.name, node.property.name)
        return f"{_expression(node.object)}.{name}"
    if kind == "CallExpression":
        arguments = ", ".join(_expression(item) for item in node.arguments)
        return f"{_expression(node.callee)}({arguments})"
    if kind == "ConditionalExpression":
        return (
            f"({_expression(node.consequent)} if "
            f"truthy({_expression(node.test)}) else {_expression(node.alternate)})"
        )
    if kind == "LogicalExpression":
        operators = {"||": "or", "&&": "and"}
        try:
            operator = operators[node.operator]
        except KeyError as error:
            raise ValueError(f"unsupported logical operator: {node.operator}") from error
        return f"({_expression(node.left)} {operator} {_expression(node.right)})"
    raise ValueError(f"unsupported expression: {kind}")


def _body(node: Any) -> list[Any]:
    return node.body if node.type == "BlockStatement" else [node]


def _statements(nodes: list[Any], indentation: int = 1) -> list[str]:
    result: list[str] = []
    prefix = "    " * indentation
    for node in nodes:
        kind = node.type
        if kind == "ExpressionStatement":
            result.append(prefix + _expression(node.expression))
        elif kind == "ReturnStatement":
            result.append(prefix + "return " + _expression(node.argument))
        elif kind == "EmptyStatement":
            continue
        elif kind == "BlockStatement":
            result.extend(_statements(node.body, indentation))
        elif kind == "ForStatement":
            result.append(prefix + _expression(node.init))
            result.append(prefix + "while truthy(" + _expression(node.test) + "):")
            translated = _statements(_body(node.body), indentation + 1)
            translated.append("    " * (indentation + 1) + _expression(node.update))
            result.extend(translated)
        elif kind == "WhileStatement":
            result.append(prefix + "while truthy(" + _expression(node.test) + "):")
            result.extend(
                _statements(_body(node.body), indentation + 1)
                or [prefix + "    pass"]
            )
        elif kind == "IfStatement":
            result.append(prefix + "if truthy(" + _expression(node.test) + "):")
            result.extend(
                _statements(_body(node.consequent), indentation + 1)
                or [prefix + "    pass"]
            )
            if node.alternate is not None:
                result.append(prefix + "else:")
                result.extend(
                    _statements(_body(node.alternate), indentation + 1)
                    or [prefix + "    pass"]
                )
        else:
            raise ValueError(f"unsupported statement: {kind}")
    return result


def _function_source(name: str, javascript: str, prefix: str) -> str:
    parsed = esprima.parseScript("(" + javascript + ")")
    function = parsed.body[0].expression
    body = _statements(function.body.body)
    return "\n".join(
        [f"def {prefix}_{name}(ctx):", *(body or ["    pass"]), ""]
    )


def _metadata(circuit: dict[str, Any]) -> str:
    compact = {
        "components": [
            [item["name"], item["params"], item["template"], item["inputSignals"]]
            for item in circuit["components"]
        ],
        "signals": [
            [item["names"], item["triggerComponents"]] for item in circuit["signals"]
        ],
    }
    canonical = json.dumps(compact, separators=(",", ":")).encode()
    encoded = base64.b85encode(zlib.compress(canonical, 9)).decode("ascii")
    return "\n".join(
        "    " + repr(encoded[offset : offset + 100])
        for offset in range(0, len(encoded), 100)
    )


def generate_source(circuit: dict[str, Any], circuit_digest: str) -> str:
    """Translate an authenticated circuit, compressing metadata with local zlib."""

    header = f'''# Generated from the production Tornado Cash Circom-1 circuit.
# Do not edit by hand. Runtime code never reads or evaluates the embedded JavaScript.

from .constants import FR_MODULUS

CIRCUIT_SHA256 = "{circuit_digest}"
N_SIGNALS = {circuit["nSignals"]}
N_VARS = {circuit["nVars"]}
N_INPUTS = {circuit["nInputs"]}


class F(int):
    """Small compatibility value for legacy snarkjs big-integer expressions."""

    def __new__(cls, value=0):
        if isinstance(value, bytes):
            value = int.from_bytes(value, "big")
        return int.__new__(cls, int(value))

    def add(self, other):
        return F(int(self) + int(other))

    def sub(self, other):
        return F(int(self) - int(other))

    def mul(self, other):
        return F(int(self) * int(other))

    def div(self, other):
        divisor = int(other)
        if divisor == 0:
            raise ZeroDivisionError("division by zero")
        quotient = abs(int(self)) // abs(divisor)
        return F(-quotient if (int(self) < 0) != (divisor < 0) else quotient)

    def mod(self, other):
        modulus = int(other)
        value = abs(int(self)) % abs(modulus)
        return F(-value if int(self) < 0 else value)

    def modPow(self, exponent, modulus):
        return F(pow(int(self), int(exponent), int(modulus)))

    def inverse(self, modulus):
        return F(pow(int(self), -1, int(modulus)))

    def eq(self, other):
        return int(self) == int(other)

    def neq(self, other):
        return int(self) != int(other)

    def lt(self, other):
        return int(self) < int(other)

    def gt(self, other):
        return int(self) > int(other)

    def greater(self, other):
        return int(self) > int(other)

    def band(self, other):
        return F(int(self) & int(other))

    def shr(self, bits):
        return F(int(self) >> int(bits))

    def shl(self, bits):
        return F(int(self) << int(bits))


P = F(FR_MODULUS)
MASK = F("28948022309329048855892746252171976963317496166410141009864396001978282409983")


def truthy(value):
    return bool(value)


METADATA_B85 = (\n{_metadata(circuit)}\n)\n\n'''
    templates = [
        _function_source(name, javascript, "template")
        for name, javascript in circuit["templates"].items()
    ]
    functions = [
        _function_source(name, definition["func"], "function")
        for name, definition in circuit["functions"].items()
    ]
    template_map = "TEMPLATES = {\n" + "".join(
        f"    {name!r}: template_{name},\n" for name in circuit["templates"]
    ) + "}\n\n"
    function_map = "FUNCTIONS = {\n" + "".join(
        f"    {name!r}: ({definition['params']!r}, function_{name}),\n"
        for name, definition in circuit["functions"].items()
    ) + "}\n"
    source = header + "\n".join(templates + functions) + template_map + function_map
    compile(source, str(DEFAULT_OUTPUT), "exec")
    return source


def _source_contents(source: str) -> tuple[bytes, bytes]:
    """Compare metadata contents without depending on zlib's compressed bytes.

    Windows Python 3.14 uses zlib-ng, which may encode the same metadata
    differently. Keep every byte outside the metadata assignment significant,
    and inspect its literal without importing or executing the generated code.
    """

    assignments = [
        node for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "METADATA_B85"
                for target in node.targets)
    ]
    if len(assignments) != 1:
        raise ValueError("expected exactly one METADATA_B85 assignment")
    assignment = assignments[0]
    if (len(assignment.targets) != 1
            or not isinstance(assignment.value, ast.Constant)
            or not isinstance(assignment.value.value, str)):
        raise ValueError("METADATA_B85 must be a string literal")
    metadata = zlib.decompress(base64.b85decode(assignment.value.value))

    # AST columns are UTF-8 byte offsets. Preserve even code after the literal
    # on the same line so metadata normalization cannot hide other changes.
    encoded = source.encode("utf-8")
    lines = encoded.splitlines(keepends=True)
    start = sum(map(len, lines[:assignment.lineno - 1])) + assignment.col_offset
    end = sum(map(len, lines[:assignment.end_lineno - 1])) + assignment.end_col_offset
    return encoded[:start] + b"METADATA_B85 = ..." + encoded[end:], metadata


def _version() -> str:
    version = getattr(esprima, "__version__", "")
    if isinstance(version, tuple):
        return ".".join(str(item) for item in version)
    return str(version)


def _load(circuit_path: Path) -> tuple[dict[str, Any], str]:
    raw = circuit_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_CIRCUIT_SHA256:
        raise ValueError(
            "refusing to generate from an unauthenticated circuit: "
            f"expected {EXPECTED_CIRCUIT_SHA256}, got {digest}"
        )
    return json.loads(raw), digest


def _write_atomic(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as temporary:
        temporary.write(source)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--circuit", type=Path, default=DEFAULT_CIRCUIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that the committed AOT module is current without writing it",
    )
    args = parser.parse_args(argv)

    if _version() != EXPECTED_ESPRIMA_VERSION:
        parser.error(
            f"esprima=={EXPECTED_ESPRIMA_VERSION} is required for deterministic output; "
            f"found {_version() or 'unknown'}"
        )
    try:
        circuit, digest = _load(args.circuit.resolve())
        source = generate_source(circuit, digest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    output = args.output.resolve()
    if args.check:
        try:
            committed = output.read_text(encoding="utf-8")
            matches = _source_contents(committed) == _source_contents(source)
        except (OSError, ValueError, SyntaxError, zlib.error) as error:
            print(f"witness AOT check failed: {error}", file=sys.stderr)
            return 1
        if not matches:
            expected = hashlib.sha256(source.encode()).hexdigest()
            actual = hashlib.sha256(committed.encode()).hexdigest()
            print(
                "witness AOT module is stale: "
                f"expected sha256 {expected}, found {actual}",
                file=sys.stderr,
            )
            return 1
        print(f"witness AOT module is current ({digest})")
        return 0

    _write_atomic(output, source)
    print(f"generated {output} from circuit {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
