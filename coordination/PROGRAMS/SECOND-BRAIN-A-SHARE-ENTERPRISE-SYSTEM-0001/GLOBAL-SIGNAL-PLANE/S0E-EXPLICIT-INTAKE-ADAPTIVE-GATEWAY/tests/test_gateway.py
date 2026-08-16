from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest

ROOT = Path(__file__).resolve().parents[1]
S0C = ROOT.parent / "S0-SYNTHETIC" / "src"
sys.path[:0] = [str(ROOT / "src"), str(S0C)]

from global_signal_gateway.gateway import (  # noqa: E402
    GatewayError, RuntimeInvocationReceipt, SignalIntakeGateway, SystemAwarenessProjection,
    classify, exact_git_read_records, semantic_capture, validate_envelope,
)
from global_signal_plane.ledger import DurableSignalLedger  # noqa: E402
from global_signal_plane.models import SignalPlaneError  # noqa: E402


def envelope(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "envelope_id": "synthetic-r136-001", "source_ref": "opaque://synthetic/r136", "source_type": "SYNTHETIC_FIXTURE",
        "source_project": "second-brain-synthetic", "source_actor": "synthetic-owner", "source_window_ref": "window://synthetic",
        "captured_at": "2026-08-16T00:00:00+00:00", "original_intent_ref": "intent://synthetic/r136",
        "public_safe_summary": "synthetic feature request", "desired_effect": "synthetic outcome", "problem_to_solve": "synthetic problem",
        "success_condition": "synthetic test passes", "expected_problems": ["UNKNOWN"], "risks": ["UNKNOWN"], "assumptions": [], "unknowns": ["UNKNOWN"],
        "dependencies": [], "evidence_refs": ["evidence://synthetic"], "counterevidence_refs": [], "privacy_scope_ref": "PUBLIC_SAFE",
        "proposed_primary_domain": "W8", "proposed_related_domains": [], "persistence_class": "DURABLE_SIGNAL",
        "execution_class": "GOVERNED_MISSION", "materiality_class": "MATERIAL", "epistemic_state": "USER_EXPLICIT",
    }
    data.update(overrides)
    return data


def sources(revision: str = "main-1") -> dict[str, dict[str, object]]:
    return {"coordination/ACTIVE-CODEX-TASK.yaml": {"revision": revision, "component_id": "control-plane", "component_kind": "CONTROL", "authority_owner": "GPT", "canonical_entrypoints": ["ACTIVE-CODEX-TASK"], "read_set_refs": [], "route_set_refs": [], "dependency_refs": [], "interface_refs": [], "capability_refs": [], "read_boundary_refs": ["public"], "write_boundary_refs": ["locked"], "regression_refs": [], "unknown_refs": [], "relevant_open_signal_refs": []}}


class GatewayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = DurableSignalLedger(Path(self.temp.name) / "ledger.sqlite")
        self.gateway = SignalIntakeGateway(self.ledger)

    def tearDown(self) -> None:
        self.ledger.close(); self.temp.cleanup()

    def awareness(self, revision: str = "main-1") -> SystemAwarenessProjection:
        projection = self.ledger.current_projection() or self.ledger.rebuild_projection(expected_version=self.ledger.current_projection_version())
        return SystemAwarenessProjection.build(sources(revision), projection)

    def test_r136_r001_to_r008_explicit_capture_and_axes(self) -> None:
        self.assertTrue(semantic_capture("请记录这个需求"))
        self.assertTrue(semantic_capture("capture this request"))
        self.assertFalse(semantic_capture("请记录这个，但不要记录"))
        self.assertFalse(semantic_capture("ordinary conversation"))
        self.assertEqual(classify(envelope(persistence_class="TRACE_ONLY", execution_class="DIRECT", materiality_class="LOW"))["execution_class"], "DIRECT")
        high = classify(envelope(persistence_class="TRACE_ONLY", execution_class="DIRECT", materiality_class="HIGH_RISK"))
        self.assertEqual(high, {"persistence_class": "DURABLE_SIGNAL", "execution_class": "GOVERNED_MISSION", "materiality_class": "HIGH_RISK"})
        with self.assertRaises(GatewayError) as invalid:
            classify(envelope(materiality_class="MAGIC_SCORE"))
        self.assertEqual(invalid.exception.code, "INVALID_CLASSIFICATION_AXIS")
        self.assertEqual(self.gateway.intake(envelope(), request_text="不要记录这个" )["status"], "NOT_CAPTURED")

    def test_r136_r009_to_r015_envelope_fails_closed_and_trace_routes(self) -> None:
        for change, code in (({"captured_at": "not-time"}, "INVALID_TIMESTAMP"), ({"captured_at": "2026-08-16T00:00:00"}, "NAIVE_TIMESTAMP_FORBIDDEN"), ({"raw_source_body": "x"}, "PRIVATE_OR_SECRET_FIELD_FORBIDDEN"), ({"desired_effect": "sk-test"}, "PRIVATE_OR_SECRET_VALUE_FORBIDDEN")):
            with self.subTest(change=change), self.assertRaises(GatewayError) as raised:
                validate_envelope(envelope(**change))
            self.assertEqual(raised.exception.code, code)
        missing = envelope(); del missing["success_condition"]
        with self.assertRaises(GatewayError) as raised:
            validate_envelope(missing)
        self.assertEqual(raised.exception.code, "MISSING_REQUIRED_FIELD")
        trace = self.gateway.intake(envelope(persistence_class="TRACE_ONLY", execution_class="DOMAIN_WORKFLOW"), request_text="记住这个")
        self.assertEqual(trace["status"], "TRACE_ONLY")
        self.assertEqual(len(self.ledger.history()), 0)

    def test_r136_r016_to_r022_durable_idempotency_collision_and_replay(self) -> None:
        first = self.gateway.intake(envelope(), request_text="记录这个")
        second = self.gateway.intake(envelope(), request_text="记录这个")
        self.assertEqual(first["status"], "ADMITTED")
        self.assertEqual(second["status"], "IDEMPOTENT_DUPLICATE")
        self.assertEqual(len(self.ledger.history()), 1)
        conflicting = envelope(public_safe_summary="different", desired_effect="different")
        with self.assertRaises(SignalPlaneError) as collision:
            self.gateway.intake(conflicting, request_text="记录这个")
        self.assertEqual(collision.exception.code, "IDEMPOTENCY_KEY_COLLISION")
        before = self.ledger.current_projection()["checksum"]
        self.assertTrue(self.ledger.observe_replay())
        self.assertEqual(self.ledger.current_projection()["checksum"], before)
        self.assertEqual(self.gateway.relate(signal_ref=first["signal_id"], target_ref="signal:old", relation="SUPERSEDES", at="2026-08-16T00:01:00+00:00")["status"], "ADMITTED")
        self.assertEqual(self.gateway.relate(signal_ref=first["signal_id"], target_ref="signal:old", relation="SUPERSEDES", at="2026-08-16T00:01:00+00:00")["status"], "IDEMPOTENT_DUPLICATE")

    def test_durable_concurrent_same_delivery_has_one_append_and_one_recovery(self) -> None:
        db = Path(self.temp.name) / "race.sqlite"
        def worker() -> str:
            ledger = DurableSignalLedger(db)
            try:
                return SignalIntakeGateway(ledger).intake(envelope(), request_text="capture this")["status"]
            finally:
                ledger.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: worker(), range(2)))
        inspect = DurableSignalLedger(db)
        try:
            self.assertCountEqual(outcomes, ["ADMITTED", "IDEMPOTENT_DUPLICATE"])
            self.assertEqual(len(inspect.history()), 1)
        finally:
            inspect.close()

    def test_r136_r023_to_r029_awareness_is_derived_and_stale_is_blocked(self) -> None:
        awareness = self.awareness()
        self.assertTrue(awareness.derived_only); self.assertFalse(awareness.authority_granted)
        self.assertTrue(awareness.is_current(sources()))
        self.assertFalse(awareness.is_current(sources("main-2")))
        stale = self.gateway.preflight(awareness=awareness, sources=sources("main-2"), reconciliation_receipt={"status": "VALID", "ledger_checksum": awareness.ledger_checksum}, material_conflicts=[])
        self.assertEqual(stale["code"], "STALE_SYSTEM_AWARENESS")
        missing = self.gateway.preflight(awareness=awareness, sources=sources(), reconciliation_receipt=None, material_conflicts=[])
        self.assertEqual(missing["code"], "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT")
        bad_checksum = self.gateway.preflight(awareness=awareness, sources=sources(), reconciliation_receipt={"status": "VALID", "ledger_checksum": "wrong"}, material_conflicts=[])
        self.assertEqual(bad_checksum["code"], "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT")
        conflicts = self.gateway.preflight(awareness=awareness, sources=sources(), reconciliation_receipt={"status": "VALID", "ledger_checksum": awareness.ledger_checksum}, material_conflicts=["conflict://1"])
        self.assertEqual(conflicts["code"], "MATERIAL_CONFLICT_UNRESOLVED")

    def test_r136_r030_to_r034_release_packet_cannot_authorize_itself(self) -> None:
        awareness = self.awareness()
        receipt = {"status": "VALID", "ledger_checksum": awareness.ledger_checksum, "receipt_ref": "reconciliation://1"}
        preflight = self.gateway.preflight(awareness=awareness, sources=sources(), reconciliation_receipt=receipt, material_conflicts=[])
        packet = self.gateway.release(preflight=preflight, included_signal_refs=["signal:a"], awareness=awareness)
        self.assertTrue(preflight["can_release"])
        self.assertTrue(packet["control_tower_required"])
        self.assertFalse(packet["execution_authorized"])
        with self.assertRaises(GatewayError) as blocked:
            self.gateway.release(preflight={"can_release": False}, included_signal_refs=[], awareness=awareness)
        self.assertEqual(blocked.exception.code, "FORMAL_RELEASE_PRECHECK_FAILED")
        self.assertIn("CONTROL_TOWER_AUTHORIZATION_REQUIRED", packet["unknowns"])

    def test_r136_r035_to_r040_runtime_receipt_requires_exact_actual_reads(self) -> None:
        awareness = self.awareness()
        entry = {"path": "PROJECT_INDEX.yaml", "blob_sha": "a" * 40}
        declared = RuntimeInvocationReceipt.build(execution_id="exec-1", source_repository="vxz2datoubo/eustia-ai-film", source_commit="c" * 40, entry=entry, awareness=awareness, mandatory_reads=["PROJECT_INDEX.yaml"], actual_reads=[{"path": "PROJECT_INDEX.yaml"}])
        self.assertEqual(declared.data["process_compliance"], "UNVERIFIED")
        actual = {"repository": "vxz2datoubo/eustia-ai-film", "commit": "c" * 40, "path": "PROJECT_INDEX.yaml", "blob_sha_or_equivalent_content_identity": "a" * 40, "content_sha256_or_equivalent_digest": hashlib.sha256(b"index").hexdigest(), "execution_id": "exec-1"}
        verified = RuntimeInvocationReceipt.build(execution_id="exec-1", source_repository="vxz2datoubo/eustia-ai-film", source_commit="c" * 40, entry=entry, awareness=awareness, mandatory_reads=["PROJECT_INDEX.yaml"], actual_reads=[actual], outcome_quality="FAIL")
        self.assertEqual(verified.data["process_compliance"], "PASS")
        self.assertEqual(verified.data["outcome_quality"], "FAIL")
        drift = dict(actual); drift["commit"] = "d" * 40
        self.assertEqual(RuntimeInvocationReceipt.build(execution_id="exec-1", source_repository="vxz2datoubo/eustia-ai-film", source_commit="c" * 40, entry=entry, awareness=awareness, mandatory_reads=["PROJECT_INDEX.yaml"], actual_reads=[drift]).data["validation_result"], "UNVERIFIED")
        self.assertEqual(verified.data["writeback_decision"], "TRACE_ONLY")

    def test_actual_git_read_proof_rejects_drift_and_records_object_identity(self) -> None:
        source = Path(self.temp.name) / "exact-source"; source.mkdir()
        subprocess.run(["git", "init", "-q", str(source)], check=True)
        subprocess.run(["git", "-C", str(source), "config", "user.email", "synthetic@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(source), "config", "user.name", "Synthetic"], check=True)
        (source / "PROJECT_INDEX.yaml").write_text("source_authority: this_file\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(source), "add", "PROJECT_INDEX.yaml"], check=True)
        subprocess.run(["git", "-C", str(source), "commit", "-qm", "synthetic"], check=True)
        commit = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        reads = exact_git_read_records(source, repository="synthetic/repo", commit=commit, paths=["PROJECT_INDEX.yaml"], execution_id="exec-2")
        self.assertEqual(reads[0]["commit"], commit); self.assertEqual(len(reads[0]["content_sha256_or_equivalent_digest"]), 64)
        (source / "PROJECT_INDEX.yaml").write_text("changed\n", encoding="utf-8")
        with self.assertRaises(GatewayError) as changed:
            exact_git_read_records(source, repository="synthetic/repo", commit=commit, paths=["PROJECT_INDEX.yaml"], execution_id="exec-2")
        self.assertEqual(changed.exception.code, "SOURCE_WORKTREE_PAYLOAD_MISMATCH")

    def test_r136_r041_to_r044_closure_preserves_history_and_no_promotion(self) -> None:
        partial = self.gateway.assess_closure(signal_ref="signal:a", state="PARTIALLY_SATISFIED", effect_evidence_refs=[], task_done=True)
        self.assertTrue(partial["append_only"]); self.assertTrue(partial["history_retained"])
        with self.assertRaises(GatewayError) as missing:
            self.gateway.assess_closure(signal_ref="signal:a", state="SATISFIED", effect_evidence_refs=[], task_done=True)
        self.assertEqual(missing.exception.code, "SATISFACTION_EFFECT_EVIDENCE_REQUIRED")
        satisfied = self.gateway.assess_closure(signal_ref="signal:a", state="SATISFIED", effect_evidence_refs=["evidence://effect"], task_done=True)
        self.assertFalse(satisfied["authorizes_promotion"])
        self.assertEqual(self.gateway.assess_closure(signal_ref="signal:a", state="REVOKED", effect_evidence_refs=[], task_done=False)["state"], "REVOKED")
