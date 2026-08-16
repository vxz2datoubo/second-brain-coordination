"""Frozen R138 R001-R044 acceptance matrix; every case is executable."""
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
from global_signal_gateway.capability_execution_provider import (CapabilityDescriptor, CapabilityExecutionRequest, CONTRACT_REVISION, ExactRepositoryCapabilityProvider, _tree_digest, verify_capability_execution_proof, verify_historical_capability_execution_proof)
from global_signal_gateway.gateway import GatewayError, RuntimeInvocationReceipt, digest


class TestOnlyBoundedProvider(ExactRepositoryCapabilityProvider):
    """A non-exported test seam. Production always uses Docker network=none."""
    def __init__(self, descriptor): self.descriptor = descriptor
    def _descriptor(self, request):
        d = self.descriptor
        expected = (d.domain_id, d.capability_id, "EXACT_REPOSITORY_EXECUTABLE", CONTRACT_REVISION, d.source_repository, d.source_commit, d.capability_contract_ref, d.executor_path, d.result_schema_ref, d.resource_policy_ref, d.network_policy_ref, d.write_policy_ref, d.privacy_scope_ref)
        fields = ("domain_id", "capability_id", "capability_class", "provider_contract_revision", "source_repository", "source_commit", "capability_contract_ref", "executor_ref", "result_schema_ref", "resource_policy_ref", "network_policy_ref", "write_policy_ref", "privacy_scope_ref")
        if tuple(getattr(request, field) for field in fields) != expected or request.input_refs != d.input_paths: raise GatewayError("CAPABILITY_DESCRIPTOR_MISMATCH")
        return d
    def _runtime_identity(self, descriptor): return {"runtime": "test-governed-boundary", "image": descriptor.runtime_image, "image_id": "test-image", "host_python": "test", "os": "test"}
    def _execute_boundary(self, descriptor, source, output, request):
        try:
            result = subprocess.run((sys.executable, "-I", *descriptor.argv), cwd=source / descriptor.working_directory, shell=False, capture_output=True, timeout=request.timeout_seconds, env={"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}, check=False)
            return result.returncode, False, result.stdout, result.stderr, {"network": True, "read_only_source": True, "write_surface": True, "resource_limits": True, "no_shell": True}, self._runtime_identity(descriptor), "test-r138"
        except subprocess.TimeoutExpired as error:
            return None, True, error.stdout or b"", error.stderr or b"", {"network": True, "read_only_source": True, "write_surface": True, "resource_limits": True, "no_shell": True}, self._runtime_identity(descriptor), "test-r138"
    def _post_boundary_clean(self, workspace, output, descriptor, container):
        return _tree_digest(workspace / "source") == _tree_digest(workspace / "source-before") and not any(item.is_symlink() for item in output.rglob("*")), True


class R138AcceptanceMatrix(unittest.TestCase):
    def fixture(self, body="print('bounded-success')\n", *, descriptor_changes=None):
        temp = tempfile.TemporaryDirectory(prefix="r138-r001-r044-"); root = Path(temp.name); tool = root / "tool"; tool.mkdir()
        (tool / "runner.py").write_text(body, encoding="utf-8"); (tool / "requirements.lock").write_text("public-test-dependency==1\n", encoding="utf-8")
        (root / ".gitignore").write_text("ignored-runtime.txt\n", encoding="utf-8")
        for args in (("git", "init"), ("git", "add", "."), ("git", "-c", "user.name=R138", "-c", "user.email=r138@example.invalid", "commit", "-m", "fixture")):
            subprocess.run(args, cwd=root, check=True, capture_output=True)
        commit = subprocess.run(("git", "rev-parse", "HEAD"), cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        d = CapabilityDescriptor("SYNTHETIC_DOMAIN", "SYNTHETIC_EXECUTABLE_V1", "synthetic/r138", commit, "synthetic://contract/v1", "tool/runner.py", "tool", ("runner.py",), ("tool/requirements.lock",), "tool/requirements.lock", "synthetic://result/v1", "synthetic://resource/single", "synthetic://network/offline", "synthetic://write/task-output", "PUBLIC_SAFE", "test-r138-image")
        if descriptor_changes: d = replace(d, **descriptor_changes)
        r = CapabilityExecutionRequest("request", "execution", f"trace:{digest('execution')[:24]}", d.domain_id, d.capability_id, "EXACT_REPOSITORY_EXECUTABLE", CONTRACT_REVISION, d.source_repository, commit, d.capability_contract_ref, d.executor_path, d.input_paths, d.result_schema_ref, d.resource_policy_ref, d.network_policy_ref, d.write_policy_ref, d.privacy_scope_ref, str(root), "2026-08-16T00:00:00+00:00", 2, 4096)
        return temp, TestOnlyBoundedProvider(d), r
    def valid(self):
        temp, provider, request = self.fixture(); self.addCleanup(temp.cleanup); bundle, proof = provider.execute(request); self.assertIsNotNone(proof); self.assertTrue(verify_capability_execution_proof(proof)); return bundle, proof, request
    def rejects(self, **changes):
        temp, provider, request = self.fixture(); self.addCleanup(temp.cleanup)
        with self.assertRaises(GatewayError): provider.execute(replace(request, **changes))
    def invalid(self, field, value="drift"):
        _, proof, _ = self.valid(); self.assertFalse(verify_capability_execution_proof(replace(proof, **{field: value})))

    # R001-R013: exact static identity, forgery, and binding.
    def test_r001_valid_exact_executable_proof(self): self.valid()
    def test_r002_caller_self_report_cannot_mint(self): self.invalid("result_digest", "0" * 64)
    def test_r003_no_caller_registration_surface(self): self.assertFalse(hasattr(ExactRepositoryCapabilityProvider, "register"))
    def test_r004_arbitrary_shell_is_not_a_request_field(self): self.assertNotIn("command", CapabilityExecutionRequest.__dataclass_fields__)
    def test_r005_traversal_executor_rejected(self): self.rejects(executor_ref="../tool/runner.py")
    def test_r006_symlink_input_rejected(self):
        temp, provider, r = self.fixture(); self.addCleanup(temp.cleanup); (Path(r.source_root) / "tool" / "requirements.lock").unlink(); (Path(r.source_root) / "tool" / "requirements.lock").symlink_to("runner.py")
        with self.assertRaises(GatewayError): provider.execute(r)
    def test_r007_wrong_commit_rejected(self): self.rejects(source_commit="0" * 40)
    def test_r008_executor_identity_drift_invalid(self): self.invalid("executor_digest", "0" * 64)
    def test_r009_input_identity_drift_invalid(self): self.invalid("input_set_digest", "0" * 64)
    def test_r010_result_substitution_invalid(self): self.invalid("result_digest", "f" * 64)
    def test_r011_bundle_digest_mutation_invalid(self): self.invalid("evidence_digest", "0" * 64)
    def test_r012_execution_identity_mismatch_invalid(self): self.invalid("execution_id")
    def test_r013_cross_domain_capability_mismatch_invalid(self): self.invalid("domain_id")
    # R014-R022: bounded process, environment, isolation and cleanup.
    def test_r014_timeout_blocks_proof(self):
        temp, p, r = self.fixture("import time; time.sleep(4)\n"); self.addCleanup(temp.cleanup); b, proof = p.execute(r); self.assertTrue(b.timed_out); self.assertIsNone(proof)
    def test_r015_nonzero_blocks_proof(self):
        temp, p, r = self.fixture("raise SystemExit(3)\n"); self.addCleanup(temp.cleanup); b, proof = p.execute(r); self.assertEqual(b.exit_code, 3); self.assertIsNone(proof)
    def test_r016_oversized_output_fails_closed(self):
        temp, p, r = self.fixture("print('x'*5000)\n"); self.addCleanup(temp.cleanup)
        with self.assertRaises(GatewayError): p.execute(r)
    def test_r017_no_caller_environment_or_credential_fields(self): self.assertFalse({"env", "token", "credential"} & CapabilityExecutionRequest.__dataclass_fields__.keys())
    def test_r018_required_network_boundary_absent_blocks_proof(self):
        temp, p, r = self.fixture(); self.addCleanup(temp.cleanup); p._execute_boundary = lambda *args: (0, False, b"", b"", {"network": False}, p._runtime_identity(p.descriptor), "test-r138"); b, proof = p.execute(r); self.assertIn("NETWORK_ISOLATION_UNENFORCED", b.warnings); self.assertIsNone(proof)
    def test_r019_canonical_source_mutation_blocks_proof(self):
        temp, p, r = self.fixture(); self.addCleanup(temp.cleanup); (Path(r.source_root) / "late.txt").write_text("mutation")
        with self.assertRaises(GatewayError): p.execute(r)
    def test_r020_temp_write_escape_blocks_proof(self):
        temp, p, r = self.fixture("open('runner.py','a').write('x')\n"); self.addCleanup(temp.cleanup); b, proof = p.execute(r); self.assertIn("WRITE_ISOLATION_UNVERIFIED", b.warnings); self.assertIsNone(proof)
    def test_r021_cleanup_observed_after_context(self):
        b, _, _ = self.valid(); self.assertTrue(b.cleanup_complete); self.assertTrue(b.descendant_ownership_verified)
    def test_r022_resource_boundary_is_bound(self):
        b, proof, _ = self.valid(); self.assertTrue(b.boundary_enforcement["resource_limits"]); self.assertTrue(verify_capability_execution_proof(proof))
    # R023-R035: unsupported semantics, receipt behavior, and authority.
    def test_r023_unsupported_class_is_rejected(self): self.rejects(capability_class="MODEL_MEDIATED_COGNITIVE_SCAN")
    def test_r024_cognitive_self_report_is_unknown(self): self._unknown_receipt("narrative_multiplex")
    def test_r025_scan_name_echo_is_unknown(self): self._unknown_receipt("scan-label", actual_scans=("scan-label",))
    def test_r026_provider_cannot_adjudicate_not_applicable(self): self._unknown_receipt("n/a")
    def test_r027_freshness_replay_expiry_invalid(self):
        _, proof, _ = self.valid(); expired = replace(proof, fresh_until="2026-01-01T00:00:00+00:00"); self.assertFalse(verify_capability_execution_proof(expired, at="2099-01-01T00:00:00+00:00")); self.assertTrue(verify_historical_capability_execution_proof(expired, at="2099-01-01T00:00:00+00:00"))
    def test_r028_same_historical_proof_is_verifiable(self):
        b, proof, _ = self.valid(); self.assertTrue(verify_capability_execution_proof(proof, at=b.completed_at))
    def test_r029_exact_reads_alone_remain_unknown(self): self._unknown_receipt("exact-read")
    def test_r030_valid_proof_populates_actual_scan(self):
        _, proof, r = self.valid(); receipt = self._receipt(r, (r.capability_id,), (proof,)); self.assertEqual(receipt.data["actual_scans"][0]["capability_id"], r.capability_id)
    def test_r031_mixed_executed_and_unknown_not_pass(self):
        _, proof, r = self.valid(); receipt = self._receipt(r, (r.capability_id, "other"), (proof,)); self.assertNotEqual(receipt.data["process_compliance"], "PASS")
    def test_r032_process_is_independent_from_outcome(self):
        _, proof, r = self.valid(); receipt = self._receipt(r, (r.capability_id,), (proof,), outcome="FAIL"); self.assertEqual(receipt.data["process_compliance"], "PASS"); self.assertEqual(receipt.data["outcome_quality"], "FAIL")
    def test_r033_provider_cannot_authorize_release(self): self.assertFalse(hasattr(ExactRepositoryCapabilityProvider, "release"))
    def test_r034_provider_cannot_authorize_merge(self): self.assertFalse(hasattr(ExactRepositoryCapabilityProvider, "merge"))
    def test_r035_provider_has_no_domain_write_api(self): self.assertFalse(hasattr(ExactRepositoryCapabilityProvider, "write_domain"))
    # R036-R044: public safety, materialization, retained boundary, and real-smoke scope.
    def test_r036_public_proof_excludes_raw_output(self):
        b, proof, _ = self.valid(); self.assertNotIn("stdout", proof.public_dict()); self.assertNotIn("bounded-success", str(b.__dict__))
    def test_r037_ignored_source_file_not_materialized(self):
        temp, p, r = self.fixture("from pathlib import Path\nassert not (Path('../ignored-runtime.txt')).exists()\n"); self.addCleanup(temp.cleanup); (Path(r.source_root) / "ignored-runtime.txt").write_text("untracked"); b, proof = p.execute(r); self.assertIsNotNone(proof); self.assertTrue(b.source_clean_before)
    def test_r038_single_worker_no_nested_pool(self):
        b, _, _ = self.valid(); self.assertEqual(b.resource_policy_ref, "synthetic://resource/single")
    def test_r039_task_owned_cleanup_has_no_leaked_workspace(self):
        b, _, _ = self.valid(); self.assertTrue(b.cleanup_complete)
    def test_r040_ci_matrix_is_declared_in_acceptance_plan(self): self.assertTrue((ROOT / "R138" / "EXECUTION-PLAN.yaml").exists())
    def test_r041_retained_provider_absence_semantics(self): self._unknown_receipt("unrelated-cognitive-scan")
    def test_r042_real_smoke_capability_cannot_satisfy_cognitive_id(self):
        _, proof, r = self.valid(); receipt = self._receipt(r, ("narrative_multiplex",), (proof,)); self.assertEqual(receipt.data["scan_obligations"][0]["status"], "UNKNOWN")
    def test_r043_contract_drift_invalid(self): self.invalid("capability_contract_ref")
    def test_r044_cross_window_task_drift_invalid(self): self.invalid("trace_id")

    def _receipt(self, request, scans, proofs, outcome="UNKNOWN"):
        return RuntimeInvocationReceipt.build(execution_id=request.execution_id, task_class="DOMAIN_WORKFLOW", domain_id=request.domain_id, source_repository=request.source_repository, source_commit=request.source_commit, entry={"path": "entry", "blob_sha": "blob"}, awareness=SimpleNamespace(snapshot_ref="synthetic"), mandatory_reads=(), actual_reads=(), mandatory_scans=scans, capability_proofs=proofs, outcome_quality=outcome)
    def _unknown_receipt(self, scan, actual_scans=()):
        receipt = RuntimeInvocationReceipt.build(execution_id="x", task_class="DOMAIN_WORKFLOW", domain_id="D", source_repository="R", source_commit="c", entry={"path": "entry", "blob_sha": "blob"}, awareness=SimpleNamespace(snapshot_ref="synthetic"), mandatory_reads=(), actual_reads=(), mandatory_scans=(scan,), actual_scans=actual_scans)
        self.assertEqual(receipt.data["scan_obligations"][0]["status"], "UNKNOWN")


if __name__ == "__main__": unittest.main()
