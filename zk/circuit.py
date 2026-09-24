import json
import os
import subprocess
from enum import Enum
from hexbytes import HexBytes

from components import log
from components.mytype import CircuitInput
from zk.groth16.input import prepare_circuit_input
from zk.groth16.prover import prove as prove_witness
from zk.groth16.serialization import SOLIDITY_PROOF_SIZE, parse_proof, solidity_proof_bytes
from zk.groth16.verifier import verify as verify_proof
from zk.groth16.witness import calculate_witness


class ImplType(Enum):
    PYTHON     = 'python'
    JAVASCRIPT = 'javascript'


class Interface(object):

    def __init__(self, _type: ImplType) -> None:
        self._type: ImplType = _type
        self.TAG  : str      = type(self).__name__

    def prove(self, ctx: CircuitInput) -> dict | None:
        raise NotImplementedError

    def verify(self, proof: dict) -> bool:
        raise NotImplementedError


class Javascript(Interface):

    def __init__(self):
        super().__init__(ImplType.JAVASCRIPT)
        self.TAG: str = __class__.__name__
        self.node: str = 'node'
        self.prover_path  : str = os.path.join(os.path.dirname(__file__), 'js/prover.js').replace('\\', '/')
        self.verifier_path: str = os.path.join(os.path.dirname(__file__), 'js/verifier.js').replace('\\', '/')

    def prove(self, ctx: CircuitInput) -> dict | None:
        # Prepare input for the prover
        try:
            js_input: str = json.dumps({
                # Public Inputs
                'root'         : str(int.from_bytes(ctx.merkle_proof.root, byteorder='big')),
                'nullifierHash': str(int.from_bytes(ctx.note.nullifier_hash, byteorder='big')),
                'recipient'    : str(int.from_bytes(HexBytes.fromhex(ctx.recipient[2:] if ctx.recipient.startswith('0x') else ctx.recipient.strip('0x')), byteorder='big')),
                'relayer'      : str(int.from_bytes(HexBytes.fromhex(ctx.relayer[2:] if ctx.relayer.startswith('0x') else ctx.relayer.strip('0x')), byteorder='big')),
                'fee'          : str(ctx.fee),
                'refund'       : str(ctx.refund),
                # Private Inputs
                'nullifier'   : str(int.from_bytes(ctx.note.nullifier[::-1], byteorder='big')),  # Reverse the byte order, little-endian buffer to big-endian integer
                'secret'      : str(int.from_bytes(ctx.note.secret[::-1], byteorder='big')),     # Reverse the byte order, little-endian buffer to big-endian integer
                'pathElements': [str(int.from_bytes(node, byteorder='big')) for node in ctx.merkle_proof.path_nodes],
                'pathIndices' : ctx.merkle_proof.path_indices,
            }, indent=4)
        except Exception as e:
            log.error(self.TAG, f"Error preparing input for prover: {e}")
            return None
        # Run the prover using Node.js
        try:
            result: subprocess.CompletedProcess = subprocess.run(
                [self.node, self.prover_path, js_input],
                capture_output=True,
                text=True
            )
        except Exception as e:
            log.error(self.TAG, f"Error running prover: {e}")
            return None
        # Parse the output from the prover
        try:
            parsed_result: dict = json.loads(result.stdout)
        except Exception as e:
            log.error(self.TAG, f"Error parsing prover output: {e}")
            log.error(self.TAG, f"Prover stdout: {result.stdout}")
            log.error(self.TAG, f"Prover stderr: {result.stderr}")
            return None
        # Check
        try:
            hexstr: str = parsed_result['solidity']['proof'][2:] if parsed_result['solidity']['proof'].startswith('0x') else parsed_result['solidity']['proof']
            proof: HexBytes = HexBytes.fromhex(hexstr)
        except Exception as e:
            log.error(self.TAG, f"Error parsing solidity output: {e}")
            log.error(self.TAG, f"Prover stdout: {result.stdout}")
            log.error(self.TAG, f"Prover stderr: {result.stderr}")
            return None
        if len(proof) != 256:
            log.error(self.TAG, f"Invalid proof length: {len(proof)}. Expected 256 bytes.")
            return None
        return parsed_result

    def verify(self, proof: dict) -> bool:
        # Prepare input for the verifier
        try:
            js_input: str = json.dumps(proof, indent=4)
        except Exception as e:
            log.error(self.TAG, f"Error preparing input for verifier: {e}")
            return False
        # Run the verifier using Node.js
        try:
            result: subprocess.CompletedProcess = subprocess.run(
                [self.node, self.verifier_path, js_input],
                capture_output=True,
                text=True
            )
        except Exception as e:
            log.error(self.TAG, f"Error running verifier: {e}")
            return False
        if result.returncode != 0:
            log.error(self.TAG, f"Error verifying proof")
            log.error(self.TAG, f"Verifier stdout: {result.stdout}")
            log.error(self.TAG, f"Verifier stderr: {result.stderr}")
            return False
        return True


class Python(Interface):
    """In-process implementation of the fixed Tornado Groth16 circuit."""

    def __init__(self) -> None:
        super().__init__(ImplType.PYTHON)

    def prove(self, ctx: CircuitInput) -> dict | None:
        try:
            witness = calculate_witness(prepare_circuit_input(ctx))
            result = prove_witness(witness)
            parsed = parse_proof(result)
            if len(solidity_proof_bytes(parsed)) != SOLIDITY_PROOF_SIZE:
                raise ValueError("invalid Solidity proof length")
            if not verify_proof(result):
                raise ValueError("generated proof failed self-verification")
            return result
        except Exception as error:
            log.error(self.TAG, f"Error generating proof: {error}")
            return None

    def verify(self, proof: dict) -> bool:
        try:
            return verify_proof(proof)
        except Exception as error:
            log.error(self.TAG, f"Error verifying proof: {error}")
            return False


def create(impl: ImplType) -> Interface:
    if impl == ImplType.PYTHON:
        return Python()
    if impl == ImplType.JAVASCRIPT:
        return Javascript()
    else:
        raise NotImplementedError
