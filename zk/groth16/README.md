# Tornado Groth16 Python backend

This package proves and verifies the fixed Tornado Cash v2.1 BN254 circuit without a JavaScript or Node.js runtime.  
The Python backend is selected by default in `config.py`; the legacy JavaScript backend remains available for compatibility checks.

## Design

- `_witness_program.py` is an AOT translation of the bundled Circom-1 circuit.
- `witness.py` executes the translated circuit and validates its outputs.
- `artifacts.py` authenticates and reads the proving key.
- `prover.py` builds randomized Groth16 proofs.
- `verifier.py` strictly parses and verifies proofs and public signals.

The circuit, proving key, and verification key are pinned by SHA-256. Unknown or modified artifacts are rejected.  
Both backends use the same artifacts, six public signals, and 256-byte Solidity proof encoding.

Proof generation uses fresh randomness, so valid proofs for identical inputs normally differ.
Proving arithmetic is variable-time and intended for local execution.

Set `ZK_WORKERS` in `config.py` to an integer from `1` to `8` to control
prover parallelism.

## Verification

Run the complete test suite from the repository root:

```shell
python -m unittest discover -s test -p "test_*.py"
# Or
pytest -q
```

To verify that the checked-in AOT witness program matches the bundled circuit:

```shell
python -m zk.groth16.generate_witness_program --check
```

The check compares decompressed routing metadata and the remaining generated
source, so differences between zlib and zlib-ng compression do not mark an
otherwise identical program as stale.

Regenerate the AOT module only when intentionally replacing the pinned circuit.
