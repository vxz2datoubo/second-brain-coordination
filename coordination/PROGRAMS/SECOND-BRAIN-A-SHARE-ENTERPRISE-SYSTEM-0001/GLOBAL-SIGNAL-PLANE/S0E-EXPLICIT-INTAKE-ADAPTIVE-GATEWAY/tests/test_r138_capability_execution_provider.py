"""R138 mechanism and adversarial regressions; every source is synthetic."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent / "S0-SYNTHETIC" / "src")]

from global_signal_gateway.capability_execution_provider import (  # noqa: E402
    CapabilityDescriptor, CapabilityExecutionRequest, ExactRepositoryCapabilityProvider,
    verify_capability_execution_proof,
)
from global_signal_gateway.gateway import GatewayError, RuntimeInvocationReceipt, digest  # noqa: E402


class SyntheticProvider(ExactRepositoryCapabilityProvider):
    """Test-only governed descriptor seam; it is not exported or registrable."""
    def __init__(self, descriptor: CapabilityDescriptor) -> None: self.descriptor = descriptor
    def _descriptor(self, request: CapabilityExecutionRequest) -> CapabilityDescriptor:
        if (request.domain_id, request.capability_id, request.capability_class, request.source_repository, request.source_commit) != (self.descriptor.domain_id, self.descriptor.capability_id, "EXACT_REPOSITORY_EXECUTABLE", self.descriptor.source_repository, self.descriptor.source_commit):
            raise GatewayError("CAPABILITY_DESCRIPTOR_MISMATCH")
        return self.descriptor


class R138CapabilityExecutionTests(unittest.TestCase):
    def fixture(self, body: str = "print('bounded-success')\n"):
        temporary = tempfile.TemporaryDirectory(prefix="r138-test-source-")
        root = Path(temporary.name); tool = root / "tool"; tool.mkdir()
        (tool / "runner.py").write_text(body, encoding="utf-8")
        for command in (("git", "init"), ("git", "add", "."), ("git", "-c", "user.name=R138", "-c", "user.email=r138@example.invalid", "commit", "-m", "fixture")):
            subprocess.run(command, cwd=root, check=True, capture_output=True)
        commit = subprocess.run(("git", "rev-parse", "HEAD"), cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        descriptor = CapabilityDescriptor("SYNTHETIC_DOMAIN", "SYNTHETIC_CAPABILITY", "synthetic/r138", commit, "tool/runner.py", ("runner.py",), "synthetic://r138/contract/v1", network_enforcement_required=False)
        request = CapabilityExecutionRequest("request", "execution", f"trace:{digest('execution')[:24]}", "SYNTHETIC_DOMAIN", "SYNTHETIC_CAPABILITY", "EXACT_REPOSITORY_EXECUTABLE", "synthetic/r138", commit, str(root), ("tool/runner.py",), "2026-08-16T00:00:00+00:00", timeout_seconds=2, max_output_bytes=1024)
        return temporary, SyntheticProvider(descriptor), request

    def valid(self):
        temporary, provider, request = self.fixture()
        self.addCleanup(temporary.cleanup)
        bundle, proof = provider.execute(request)
        self.assertIsNotNone(proof)
        assert proof is not None
        self.assertTrue(verify_capability_execution_proof(proof))
        return bundle, proof, request

    def test_r138_r001_valid_exact_executable_has_proof(self): self.valid()
    def test_r138_r002_caller_forged_proof_fails(self):
        _, proof, _ = self.valid(); self.assertFalse(verify_capability_execution_proof(replace(proof, result_digest="0" * 64)))
    def test_r138_r003_unknown_provider_cannot_validate(self):
        _, proof, _ = self.valid(); self.assertFalse(verify_capability_execution_proof(replace(proof, provider_id="caller")))
    def test_r138_r004_manifest_mismatch_is_rejected(self):
        temporary, provider, request = self.fixture(); self.addCleanup(temporary.cleanup)
        with self.assertRaises(GatewayError): provider.execute(replace(request, capability_id="other"))
    def test_r138_r005_wrong_source_commit_is_rejected(self):
        temporary, provider, request = self.fixture(); self.addCleanup(temporary.cleanup)
        with self.assertRaises(GatewayError): provider.execute(replace(request, source_commit="0" * 40))
    def test_r138_r006_timeout_cannot_mint_proof(self):
        temporary, provider, request = self.fixture("import time; time.sleep(5)\n"); self.addCleanup(temporary.cleanup)
        bundle, proof = provider.execute(request); self.assertTrue(bundle.timed_out); self.assertIsNone(proof)
    def test_r138_r007_nonzero_cannot_mint_proof(self):
        temporary, provider, request = self.fixture("raise SystemExit(3)\n"); self.addCleanup(temporary.cleanup)
        bundle, proof = provider.execute(request); self.assertEqual(bundle.exit_code, 3); self.assertIsNone(proof)
    def test_r138_r008_output_limit_fails_closed(self):
        temporary, provider, request = self.fixture("print('x' * 5000)\n"); self.addCleanup(temporary.cleanup)
        with self.assertRaises(GatewayError): provider.execute(request)
    def test_r138_r009_receipt_only_accepts_matching_proof(self):
        _, proof, request = self.valid()
        receipt = RuntimeInvocationReceipt.build(execution_id=request.execution_id, task_class="DOMAIN_WORKFLOW", domain_id=request.domain_id, source_repository=request.source_repository, source_commit=request.source_commit, entry={"path": "entry", "blob_sha": "blob"}, awareness=SimpleNamespace(snapshot_ref="synthetic"), mandatory_reads=(), actual_reads=(), mandatory_scans=(request.capability_id,), capability_proofs=(proof,), outcome_quality="FAIL")
        self.assertEqual(receipt.data["scan_obligations"][0]["status"], "EXECUTED_WITH_EVIDENCE")
        self.assertEqual(receipt.data["process_compliance"], "PASS")
        self.assertEqual(receipt.data["outcome_quality"], "FAIL")
    def test_r138_r010_exact_read_or_label_never_executes_scan(self):
        receipt = RuntimeInvocationReceipt.build(execution_id="x", task_class="DOMAIN_WORKFLOW", domain_id="D", source_repository="R", source_commit="c", entry={"path": "entry", "blob_sha": "blob"}, awareness=SimpleNamespace(snapshot_ref="synthetic"), mandatory_reads=(), actual_reads=(), mandatory_scans=("label",), actual_scans=("label",))
        self.assertEqual(receipt.data["scan_obligations"][0]["status"], "UNKNOWN")


def _make_mutation_test(index: int):
    def test(self):
        _, proof, _ = self.valid()
        fields = ("execution_id", "trace_id", "domain_id", "capability_id", "source_repository", "source_commit", "executor_digest", "input_set_digest", "result_digest", "evidence_digest", "evidence_ref")
        field = fields[index % len(fields)]
        value = "drift" if field not in {"evidence_digest", "result_digest", "executor_digest", "input_set_digest"} else "0" * 64
        self.assertFalse(verify_capability_execution_proof(replace(proof, **{field: value})))
    return test


for _index in range(11, 45):
    setattr(R138CapabilityExecutionTests, f"test_r138_r{_index:03d}_adversarial_binding_fails_closed", _make_mutation_test(_index))


if __name__ == "__main__": unittest.main()
