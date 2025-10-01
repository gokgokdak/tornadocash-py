import json
import os
import subprocess
from enum import Enum
from hexbytes import HexBytes

import config
import log
from mytype import CircuitInput


class ImplType(Enum):
    JAVASCRIPT = 'javascript'


class Interface(object):

    def __init__(self, _type: ImplType) -> None:
        self._type: ImplType = _type

    def prove(self, ctx: CircuitInput) -> dict | None:
        raise NotImplementedError

    def verify(self, proof: dict) -> bool:
        raise NotImplementedError


class Javascript(Interface):

    def __init__(self):
        super().__init__(ImplType.JAVASCRIPT)
        self.TAG: str = __class__.__name__
        if config.BUNDLED_NODE_JS:
            self.node: str = config.BUNDLED_NODE_JS_EXE
        else:
            self.node: str = 'node'
        self.prover_path  : str = os.path.join(os.path.dirname(__file__), 'js/prover.js').replace('\\', '/')
        self.verifier_path: str = os.path.join(os.path.dirname(__file__), 'js/verifier.js').replace('\\', '/')

    def prove(self, ctx: CircuitInput) -> dict | None:
        # Prepare input for the prover
        try:
            js_input: str = json.dumps({
                # Public Inputs
                'root'         : str(int.from_bytes(ctx.merkle_proof.root)),
                'nullifierHash': str(int.from_bytes(ctx.note.nullifier_hash)),
                'recipient'    : str(int.from_bytes(HexBytes.fromhex(ctx.recipient[2:] if ctx.recipient.startswith('0x') else ctx.recipient.strip('0x')))),
                'relayer'      : str(int.from_bytes(HexBytes.fromhex(ctx.relayer[2:] if ctx.relayer.startswith('0x') else ctx.relayer.strip('0x')))),
                'fee'          : str(ctx.fee),
                'refund'       : str(ctx.refund),
                # Private Inputs
                'nullifier'   : str(int.from_bytes(ctx.note.nullifier[::-1])),  # Reverse the byte order, little-endian buffer to big-endian integer
                'secret'      : str(int.from_bytes(ctx.note.secret[::-1])),     # Reverse the byte order, little-endian buffer to big-endian integer
                'pathElements': [str(int.from_bytes(node)) for node in ctx.merkle_proof.path_nodes],
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


def create(impl: ImplType) -> Interface:
    if impl == ImplType.JAVASCRIPT:
        return Javascript()
    else:
        raise NotImplementedError
