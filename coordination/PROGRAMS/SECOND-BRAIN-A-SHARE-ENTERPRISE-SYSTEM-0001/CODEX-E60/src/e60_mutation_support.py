"""E60 test-only attack runner outside the verifier runtime package.

It produces an isolated temporary copy and routes its one child process through
the E60 whole-task lease.  It never edits the working-tree runtime sources.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Mapping

from e60_runtime.execution import ExecutionReceipt, WholeTaskResourceLease
from e60_runtime.resource_tree import ProcessLifecycleError


@dataclass(frozen=True, slots=True)
class MutationOutcome:
    mutation_id: str
    expected_rejection: str
    observed_rejection: str
    receipt: ExecutionReceipt


def run_legacy_bootstrap_injection(
    lease: WholeTaskResourceLease,
    *,
    attestation_payload: Mapping[str, object],
) -> MutationOutcome:
    """Attempt the frozen E59 private-harness injection against a package copy.

    Adding ``authority_client.py`` changes the package identity manifest.  The
    child must observe the exact identity-mismatch error before it can consume
    the injected raw-evidence helper.  Exit 0 means the attack failed closed.
    """

    runtime_root = Path(__file__).resolve().parent / "e60_runtime"
    with tempfile.TemporaryDirectory(prefix="e60-bootstrap-mutation-") as temporary:
        copied_root = Path(temporary) / "e60_runtime"
        shutil.copytree(runtime_root, copied_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (copied_root / "authority_client.py").write_text(
            "class _SyntheticAuthorityHarness:\n"
            "    @staticmethod\n"
            "    def bootstrap_raw_evidence():\n"
            "        return b'caller-controlled-raw-evidence'\n",
            encoding="utf-8",
        )
        payload_path = Path(temporary) / "attestation.json"
        payload_path.write_text(json.dumps(dict(attestation_payload), sort_keys=True), encoding="utf-8")
        result_path = Path(temporary) / "mutation-result.txt"
        child = """
import json
import sys
from e60_runtime.attestation import AttestationError, CanonicalVerifier, ExternalAttestation
from e60_runtime.authority_client import _SyntheticAuthorityHarness

payload_path, result_path = sys.argv[1:3]
payload = json.load(open(payload_path, encoding="utf-8"))
raw = _SyntheticAuthorityHarness.bootstrap_raw_evidence()
if raw != b"caller-controlled-raw-evidence":
    open(result_path, "w", encoding="ascii").write("HARNESS_RAW_VALUE_UNEXPECTED")
    raise SystemExit(21)
try:
    CanonicalVerifier(ExternalAttestation.from_mapping(payload))
except AttestationError as error:
    observed = str(error)
else:
    observed = "ATTACK_UNEXPECTEDLY_ACCEPTED"
open(result_path, "w", encoding="ascii").write(observed)
raise SystemExit(0 if observed == "EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH" else 22)
"""
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPATH"] = temporary
        try:
            receipt = lease.execute(
                [os.sys.executable, "-c", child, str(payload_path), str(result_path)],
                purpose="legacy-bootstrap-injection-mutation",
                timeout_seconds=5.0,
                env=environment,
            )
        except ProcessLifecycleError as exc:
            observed = result_path.read_text(encoding="ascii") if result_path.exists() else "NO_CHILD_RESULT"
            raise RuntimeError(f"LEGACY_BOOTSTRAP_MUTATION_FAILED:{observed}") from exc
        observed = result_path.read_text(encoding="ascii") if result_path.exists() else "NO_CHILD_RESULT"
    if receipt.exit_code != 0:
        raise RuntimeError(f"LEGACY_BOOTSTRAP_MUTATION_UNEXPECTED_EXIT:{receipt.exit_code}")
    if observed != "EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH":
        raise RuntimeError(f"LEGACY_BOOTSTRAP_MUTATION_UNEXPECTED_RESULT:{observed}")
    return MutationOutcome(
        mutation_id="E60-MUT-LEGACY-BOOTSTRAP-INJECTION-001",
        expected_rejection="EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH",
        observed_rejection=observed,
        receipt=receipt,
    )
