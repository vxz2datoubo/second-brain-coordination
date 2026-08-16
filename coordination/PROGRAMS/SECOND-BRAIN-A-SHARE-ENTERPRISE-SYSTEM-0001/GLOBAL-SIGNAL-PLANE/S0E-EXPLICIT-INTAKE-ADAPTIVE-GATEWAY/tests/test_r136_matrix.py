"""One test method per frozen R136 acceptance scenario; no result self-certification."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[4]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent / "S0-SYNTHETIC" / "src")]

from global_signal_gateway.gateway import (  # noqa: E402
    AI_FILM_COMMIT, AI_FILM_REPOSITORY, AuthorityBoundLiveObservationProof, GatewayError, RuntimeInvocationReceipt, SignalIntakeGateway,
    SystemAwarenessProjection, ai_film_directing_read_only_smoke, classify, exact_git_read_proofs, seal_global_reconciliation,
    semantic_capture, temporary_exact_clone, validate_envelope, validate_live_observation_proof,
)
from global_signal_plane.ledger import DurableSignalLedger  # noqa: E402
from global_signal_plane.models import SignalPlaneError  # noqa: E402


def envelope(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "envelope_id": "synthetic-r136-001", "source_ref": "opaque://synthetic/r136", "source_type": "SYNTHETIC_FIXTURE",
        "source_project": "second-brain-synthetic", "source_actor": "synthetic-owner", "source_window_ref": "window://synthetic",
        "captured_at": "2026-08-16T00:00:00+00:00", "original_intent_ref": "intent://synthetic/r136",
        "public_safe_summary": "formal system module request", "desired_effect": "synthetic outcome", "problem_to_solve": "system architecture update",
        "success_condition": "synthetic test passes", "expected_problems": ["UNKNOWN"], "risks": ["UNKNOWN"], "assumptions": ["synthetic"], "unknowns": ["UNKNOWN"],
        "dependencies": ["dependency://synthetic"], "evidence_refs": ["evidence://synthetic"], "counterevidence_refs": ["counter://synthetic"], "privacy_scope_ref": "PUBLIC_SAFE",
        "proposed_primary_domain": "W8", "proposed_related_domains": ["W10"], "epistemic_state": "USER_EXPLICIT",
    }
    data.update(overrides); return data


def source_map(revision: str = "main-1") -> dict[str, dict[str, object]]:
    return {"coordination/ACTIVE-CODEX-TASK.yaml": {"revision": revision, "component_id": "control-plane", "component_kind": "CONTROL", "authority_owner": "GPT", "canonical_entrypoints": ["ACTIVE-CODEX-TASK"], "capability_refs": ["route"], "read_boundary_refs": ["public"], "write_boundary_refs": ["locked"]}}


class R136ScenarioMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.ledger = DurableSignalLedger(Path(self.temp.name) / "ledger.sqlite"); self.gateway = SignalIntakeGateway(self.ledger)

    def tearDown(self) -> None:
        self.ledger.close(); self.temp.cleanup()

    def awareness(self, canonical: bool = False) -> SystemAwarenessProjection:
        projection = self.ledger.current_projection() or self.ledger.rebuild_projection(expected_version=self.ledger.current_projection_version())
        return SystemAwarenessProjection.from_canonical(REPO, projection) if canonical else SystemAwarenessProjection.build(source_map(), projection)

    def admitted(self) -> dict[str, object]:
        return self.gateway.intake(envelope(), request_text="把这个需求记到信号塔")

    def receipt(self, awareness: SystemAwarenessProjection):
        return seal_global_reconciliation(REPO, awareness)

    def _synthetic_proof(self) -> tuple[SystemAwarenessProjection, tuple[object, ...], dict[str, str]]:
        source = Path(self.temp.name) / "source"; source.mkdir(); subprocess.run(["git", "init", "-q", str(source)], check=True)
        subprocess.run(["git", "-C", str(source), "config", "user.email", "synthetic@example.invalid"], check=True); subprocess.run(["git", "-C", str(source), "config", "user.name", "Synthetic"], check=True)
        (source / "PROJECT_INDEX.yaml").write_text("source_authority: this_file\n", encoding="utf-8"); subprocess.run(["git", "-C", str(source), "add", "PROJECT_INDEX.yaml"], check=True); subprocess.run(["git", "-C", str(source), "commit", "-qm", "synthetic"], check=True)
        commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(); proofs = exact_git_read_proofs(source, repository="synthetic/repo", commit=commit, paths=["PROJECT_INDEX.yaml"], execution_id="exec-1")
        return self.awareness(), proofs, {"path": "PROJECT_INDEX.yaml", "blob_sha": proofs[0].blob_sha}


def _case(case_id: str):
    def run(self: R136ScenarioMatrix) -> None:
        if case_id == "R001": self.assertTrue(semantic_capture("把这个需求记到信号塔"))
        elif case_id == "R002": self.assertTrue(all(semantic_capture(text) for text in ("录入信号塔", "登入信号塔", "记到信号塔", "放进信号塔", "把这个想法录入信号塔")))
        elif case_id == "R003": self.assertEqual(self.gateway.intake(envelope(), request_text="录入信号塔，但只是讨论", explicit_capture=True)["status"], "NOT_CAPTURED")
        elif case_id == "R004": self.assertEqual(classify(envelope(problem_to_solve="one off question", public_safe_summary="ordinary"), "ordinary question"), {"persistence_class": "EPHEMERAL", "execution_class": "DIRECT", "materiality_class": "LOW"})
        elif case_id == "R005": self.assertEqual(classify(envelope(problem_to_solve="导演镜头", public_safe_summary="AI Film directing"), "AI Film 导演"), {"persistence_class": "TRACE_ONLY", "execution_class": "DOMAIN_WORKFLOW", "materiality_class": "LOW"})
        elif case_id == "R006": self.assertEqual(classify(envelope(), "正式任务的系统蓝图模块改造")["execution_class"], "GOVERNED_MISSION")
        elif case_id == "R007": self.assertEqual(classify(envelope(), "生产权限高风险事项")["persistence_class"], "DURABLE_SIGNAL")
        elif case_id == "R008":
            with self.assertRaises(GatewayError) as got: validate_envelope(envelope(desired_effect=""), "正式任务")
            self.assertEqual(got.exception.code, "DURABLE_INTENT_FIELD_REQUIRED")
        elif case_id == "R009":
            with self.assertRaises(GatewayError) as got: validate_envelope(envelope(success_condition=""), "正式任务")
            self.assertEqual(got.exception.code, "DURABLE_INTENT_FIELD_REQUIRED")
        elif case_id == "R010": self.assertEqual(validate_envelope(envelope(risks=["UNKNOWN"]), "正式任务")["risks"], ["UNKNOWN"])
        elif case_id == "R011":
            result = self.admitted(); stored = self.ledger.history()[0]["public_safe_metadata"]["intent_envelope"]; self.assertEqual(stored["source_window_ref"], "window://synthetic"); self.assertEqual(result["status"], "ADMITTED")
        elif case_id == "R012":
            with self.assertRaises(GatewayError) as got: validate_envelope(envelope(raw_source_body="x"), "正式任务")
            self.assertEqual(got.exception.code, "PRIVATE_OR_SECRET_FIELD_FORBIDDEN")
        elif case_id == "R013": self.assertEqual(self.admitted()["status"], "ADMITTED")
        elif case_id == "R014":
            self.admitted()
            with self.assertRaises(SignalPlaneError) as got: self.gateway.intake(envelope(public_safe_summary="mutated"), request_text="录入信号塔")
            self.assertEqual(got.exception.code, "IDEMPOTENCY_KEY_COLLISION")
        elif case_id == "R015": self.admitted(); self.assertEqual(self.admitted()["status"], "IDEMPOTENT_DUPLICATE")
        elif case_id == "R016":
            self.admitted()
            with self.assertRaises(SignalPlaneError): self.gateway.intake(envelope(desired_effect="other"), request_text="录入信号塔")
        elif case_id == "R017": result = self.admitted(); before = len(self.ledger.history()); self.assertFalse(self.gateway.omission(result["signal_id"])["revoked"]); self.assertEqual(len(self.ledger.history()), before)
        elif case_id == "R018": result = self.admitted(); self.gateway.revoke(result["signal_id"], evidence_refs=["evidence://revoke"], at="2026-08-16T00:01:00+00:00"); self.assertEqual(self.ledger.history()[-1]["revokes_refs"], [result["signal_id"]])
        elif case_id == "R019": self.admitted(); self.assertTrue(self.ledger.observe_replay())
        elif case_id == "R020": self.assertEqual(set(self.gateway.__dict__), {"ledger"})
        elif case_id == "R021": awareness = self.awareness(canonical=True); self.assertEqual(awareness.source_mode, "CANONICAL_TARGETED_READ"); self.assertGreaterEqual(len(awareness.nodes), 8)
        elif case_id == "R022": awareness = self.awareness(canonical=True); proof = self.receipt(awareness); self.assertEqual(self.gateway.preflight(awareness=awareness, canonical_root=REPO, reconciliation_proof=proof)["code"], "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT")
        elif case_id == "R023": self.assertFalse(self.awareness(canonical=True).authority_granted)
        elif case_id == "R024": self.assertIn("UNKNOWN", [node["authority_owner"] for node in SystemAwarenessProjection.build({"x": {"revision": "1"}}, {"checksum": "x"}).nodes])
        elif case_id == "R025": self.assertEqual(classify(envelope(problem_to_solve="one off", public_safe_summary="ordinary"), "one off" )["execution_class"], "DIRECT")
        elif case_id == "R026": self.assertEqual(classify(envelope(problem_to_solve="directing camera", public_safe_summary="AI Film directing"), "directing camera" )["execution_class"], "DOMAIN_WORKFLOW")
        elif case_id == "R027": self.assertEqual(classify(envelope(), "正式任务模块" )["execution_class"], "GOVERNED_MISSION")
        elif case_id == "R028": self.assertEqual(self.gateway.intake(envelope(problem_to_solve="directing camera", public_safe_summary="AI Film directing"), request_text="AI Film directing", explicit_capture=True)["status"], "TRACE_ONLY")
        elif case_id in {"R029", "R030", "R031", "R032", "R033", "R034", "R035"}:
            left = self.admitted(); right = self.gateway.intake(envelope(envelope_id="synthetic-r136-002", source_ref="opaque://two", original_intent_ref="intent://synthetic/r136", proposed_primary_domain="W8"), request_text="录入信号塔")
            awareness = self.awareness(); proof = self.receipt(awareness); preflight = self.gateway.preflight(awareness=awareness, canonical_root=None, reconciliation_proof=proof)
            if case_id == "R029": self.assertIn("DUPLICATE", [item["relation"] for item in preflight["relations"]])
            elif case_id == "R030":
                self.gateway.link_relation(left["signal_id"], right["signal_id"], "CONTRADICTS", evidence_refs=["evidence://contradiction"], at="2026-08-16T00:01:00+00:00"); proof = self.receipt(self.awareness()); preflight = self.gateway.preflight(awareness=self.awareness(), canonical_root=None, reconciliation_proof=proof); self.assertEqual(preflight["code"], "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT"); self.assertIn("CONTRADICTS", [item["relation"] for item in preflight["relations"]])
            elif case_id == "R031":
                self.gateway.link_relation(left["signal_id"], right["signal_id"], "DEPENDS_ON", evidence_refs=["evidence://dependency"], at="2026-08-16T00:01:00+00:00"); proof = self.receipt(self.awareness()); self.assertTrue(self.gateway.preflight(awareness=self.awareness(), canonical_root=None, reconciliation_proof=proof)["decisions"]["must_serialize_refs"])
            elif case_id == "R032": self.assertIn("merge_keep_separate_rationale", preflight["decisions"])
            elif case_id == "R033": self.assertIn("REVIEWER_CANDIDATE", preflight["decisions"]["reviewer_or_challenger_requirements"])
            elif case_id == "R034": self.assertFalse(preflight["can_release"])
            else:
                fake = {"status": "VALID", "repository_state_digest": "matching-fabrication"}
                self.assertEqual(self.gateway.preflight(awareness=awareness, canonical_root=None, reconciliation_proof=fake)["code"], "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT")
        elif case_id == "R036":
            awareness, proofs, entry = self._synthetic_proof(); receipt = RuntimeInvocationReceipt.build(execution_id="exec-1", task_class="DOMAIN_WORKFLOW", domain_id="SYNTHETIC", source_repository="synthetic/repo", source_commit=proofs[0].commit, entry=entry, awareness=awareness, mandatory_reads=["PROJECT_INDEX.yaml"], actual_reads=proofs); self.assertEqual(receipt.data["process_compliance"], "PASS")
        elif case_id == "R037":
            awareness, proofs, entry = self._synthetic_proof(); fake = proofs[0].public_dict(); self.assertEqual(RuntimeInvocationReceipt.build(execution_id="exec-1", task_class="DOMAIN_WORKFLOW", domain_id="SYNTHETIC", source_repository="synthetic/repo", source_commit=proofs[0].commit, entry=entry, awareness=awareness, mandatory_reads=["PROJECT_INDEX.yaml"], actual_reads=[fake]).data["validation_result"], "UNVERIFIED")
        elif case_id == "R038":
            awareness, proofs, entry = self._synthetic_proof(); receipt = RuntimeInvocationReceipt.build(execution_id="exec-1", task_class="DOMAIN_WORKFLOW", domain_id="SYNTHETIC", source_repository="synthetic/repo", source_commit=proofs[0].commit, entry=entry, awareness=awareness, mandatory_reads=["PROJECT_INDEX.yaml"], actual_reads=proofs, outcome_quality="FAIL"); self.assertEqual((receipt.data["process_compliance"], receipt.data["outcome_quality"]), ("PASS", "FAIL"))
        elif case_id == "R039":
            signal = self.admitted()["signal_id"]; result = self.gateway.assess_closure(signal_id=signal, state="PARTIALLY_SATISFIED", effect_evidence_refs=[], task_done=True, at="2026-08-16T00:01:00+00:00"); self.assertEqual(result["state"], "PARTIALLY_SATISFIED")
        elif case_id == "R040":
            signal = self.admitted()["signal_id"]; result = self.gateway.assess_closure(signal_id=signal, state="SATISFIED", effect_evidence_refs=["evidence://effect"], task_done=True, at="2026-08-16T00:01:00+00:00"); self.assertFalse(result["active_projection_contains_signal"]); self.assertTrue(result["history_retained"])
        elif case_id == "R041":
            awareness = self.awareness(canonical=True); source = os.environ.get("R136_AI_FILM_SOURCE_ROOT")
            if source: smoke = ai_film_directing_read_only_smoke(source, awareness=awareness, fixture={"symptoms": ["左右反了"], "spatial": True, "feedback": True, "formal_scene_pixels": True})
            else:
                with temporary_exact_clone("https://github.com/vxz2datoubo/eustia-ai-film.git", AI_FILM_COMMIT) as root: smoke = ai_film_directing_read_only_smoke(root, awareness=awareness, fixture={"symptoms": ["左右反了"], "spatial": True, "feedback": True, "formal_scene_pixels": True})
            self.assertEqual(smoke["receipt"]["process_compliance"], "UNVERIFIED"); self.assertTrue(smoke["matched_routes"]); self.assertFalse(smoke["receipt"]["actual_scans"]); self.assertFalse(smoke["receipt"]["capability_invocations"]); self.assertTrue(all(item["status"] == "UNKNOWN" for item in smoke["receipt"]["scan_obligations"]))
            if source: rejected = ai_film_directing_read_only_smoke(source, awareness=awareness, fixture={"symptoms": ["左右反了"], "spatial": True, "formal_scene_pixels": True, "withhold_scans": ["map_authority"]})
            else:
                with temporary_exact_clone("https://github.com/vxz2datoubo/eustia-ai-film.git", AI_FILM_COMMIT) as root: rejected = ai_film_directing_read_only_smoke(root, awareness=awareness, fixture={"symptoms": ["左右反了"], "spatial": True, "formal_scene_pixels": True, "withhold_scans": ["map_authority"]})
            self.assertEqual(rejected["receipt"]["validation_result"], "UNVERIFIED")
        elif case_id == "R042":
            source = os.environ.get("R136_AI_FILM_SOURCE_ROOT")
            if source:
                before = subprocess.check_output(["git", "-C", source, "status", "--porcelain"], text=True); smoke = ai_film_directing_read_only_smoke(source, awareness=self.awareness(canonical=True), fixture={"symptoms": ["左右反了"], "spatial": True, "formal_scene_pixels": True}); self.assertEqual(subprocess.check_output(["git", "-C", source, "status", "--porcelain"], text=True), before)
            else:
                with temporary_exact_clone("https://github.com/vxz2datoubo/eustia-ai-film.git", AI_FILM_COMMIT) as root: smoke = ai_film_directing_read_only_smoke(root, awareness=self.awareness(canonical=True), fixture={"symptoms": ["左右反了"], "spatial": True, "formal_scene_pixels": True})
            self.assertEqual((smoke["source_status_before"], smoke["source_status_after"]), ("CLEAN", "CLEAN"))
        elif case_id == "R043":
            with temporary_exact_clone("https://github.com/vxz2datoubo/eustia-ai-film.git", AI_FILM_COMMIT) as clone: saved = clone; self.assertTrue(clone.exists())
            self.assertFalse(saved.exists())
        elif case_id == "R044":
            text = (ROOT / "src" / "global_signal_gateway" / "gateway.py").read_text(encoding="utf-8").casefold(); self.assertFalse(any(marker in text for marker in ("todo", "fixme", "notimplementederror", "placeholder implementation"))); self.assertTrue(self.ledger.observe_replay())
        else: raise AssertionError(case_id)
    run.__name__ = f"test_r136_{case_id.lower()}"
    return run


for _number in range(1, 45):
    _id = f"R{_number:03d}"; setattr(R136ScenarioMatrix, f"test_r136_{_id.lower()}", _case(_id))


class F01F04AdversarialRegressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = DurableSignalLedger(Path(self.temp.name) / "ledger.sqlite")
        self.gateway = SignalIntakeGateway(self.ledger)
        self.awareness = SystemAwarenessProjection.build(source_map(), self.ledger.rebuild_projection(expected_version=self.ledger.current_projection_version()))

    def tearDown(self) -> None:
        self.ledger.close(); self.temp.cleanup()

    @staticmethod
    def caller_fabricated_proof(*, fresh_until: str = "2099-01-01T00:01:00+00:00") -> AuthorityBoundLiveObservationProof:
        invalidators = {"head_sha": "head", "base_sha": "base", "review_state_ref": "review", "route_fingerprint": "route", "claim_fingerprint": "claim", "lane_fingerprint": "lane", "lease_fingerprint": "lease", "domain_freshness_ref": "fresh", "pending_approval_ref": "approval"}
        return AuthorityBoundLiveObservationProof("synthetic/repo", 1, "OPEN", "head", "base", False, None, "review", "2099-01-01T00:00:00+00:00", "route", "claim", "lane", "lease", "fresh", "approval", ("provider://evidence/one",), "caller", "provider://caller/self-assertion", "a" * 64, fresh_until, invalidators, object())

    def test_f02_caller_supplied_complete_fields_are_not_provider_evidence(self) -> None:
        proof = self.caller_fabricated_proof()
        self.assertFalse(validate_live_observation_proof(proof))
        preflight = self.gateway.preflight(awareness=self.awareness, canonical_root=None, reconciliation_proof=proof)
        self.assertEqual((preflight["status"], preflight["code"], preflight["exact_repository_state_refs"]), ("BLOCKED", "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT", []))

    def test_f02_expired_or_unattributed_proof_is_blocked(self) -> None:
        proof = self.caller_fabricated_proof(fresh_until="2020-01-01T00:01:00+00:00")
        self.assertFalse(validate_live_observation_proof(proof))
        self.assertFalse(self.gateway.preflight(awareness=self.awareness, canonical_root=None, reconciliation_proof=proof)["can_release"])

    def test_f03_blocked_preflight_cannot_release_a_packet(self) -> None:
        blocked = self.gateway.preflight(awareness=self.awareness, canonical_root=None, reconciliation_proof=self.caller_fabricated_proof())
        with self.assertRaises(GatewayError) as got:
            self.gateway.release(preflight=blocked, included_signal_refs=[], awareness=self.awareness)
        self.assertEqual(got.exception.code, "FORMAL_RELEASE_PRECHECK_FAILED")
