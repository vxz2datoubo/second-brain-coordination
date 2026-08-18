"""R142 adversarial coverage for retrospective Signal intake and durable read-back."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

import global_signal_gateway.gateway as gateway_module
from global_signal_gateway.gateway import (
    AuthorityBoundLiveObservationProof, GatewayError, SignalIntakeGateway, exact_git_read_proofs,
)
from global_signal_gateway.retrospective_intake import (
    CANONICAL_REPOSITORY, DISPOSITIONS, REQUIRED_NEW_EXACT_PATHS, REQUIRED_SCAN_SURFACES,
    RetrospectiveSignalIntakeBridge, _r136_envelope, governed_snapshot_refs,
    reconcile_package, stage_import_package, validate_import_package,
)
from global_signal_plane.ledger import DurableSignalLedger
from global_signal_plane.models import SignalPlaneError

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[4]
MAIN = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
AT = "2026-08-15T12:00:00+08:00"


def candidate(candidate_id="C-001", **overrides):
    value = {
        "candidate_id": candidate_id,
        "source_window_ref": "chatgpt://window/historical-signal-tower",
        "source_message_ref": f"chatgpt://message/{candidate_id}",
        "source_project": "SECOND_BRAIN_COGNITIVE_OS",
        "source_time_range": {"start": AT, "end": AT},
        "public_safe_summary": f"Public-safe retrospective candidate {candidate_id}",
        "original_intent_ref": f"opaque://intent/{candidate_id}",
        "signal_kind": "REQUIREMENT",
        "epistemic_state": "USER_EXPLICIT",
        "desired_effect": f"Durable desired effect {candidate_id}",
        "problem_to_solve": f"Governed system problem {candidate_id}",
        "success_condition": f"Verified success condition {candidate_id}",
        "expected_problems": [], "risks": [], "assumptions": [], "unknowns": [],
        "dependencies": [], "evidence_refs": [f"opaque://evidence/{candidate_id}"],
        "counterevidence_refs": [], "proposed_primary_domain": "SHARED_COGNITIVE_OS",
        "related_domains": [], "privacy_scope": "PUBLIC_SAFE_METADATA_ONLY",
        "historical_status": "NEW", "candidate_relations": [],
        "model_tool_version_work_item_refs": {
            "model_ref": "GPT-5.6 Sol", "tool_ref": "historical-chat-window",
            "version_ref": "UNKNOWN", "work_item_ref": "R142",
        },
    }
    value.update(overrides)
    return value


def package(*items, batch_id="BATCH-001"):
    return {
        "schema_version": "SignalImportPackage/v1", "import_batch_id": batch_id,
        "generated_at": "2026-08-18T12:00:00+08:00",
        "source_window_ref": "chatgpt://window/historical-signal-tower",
        "expected_canonical_main": MAIN, "candidates": list(items or (candidate(),)),
        "package_metadata": {"transport": "PUBLIC_SAFE_REFERENCE_ONLY"},
    }


def evidence(**overrides):
    value = {
        "current_signal_refs": [], "historical_signal_refs": [], "satisfied_refs": [],
        "duplicate_refs": [], "extends_refs": [], "reinforces_refs": [], "contradicts_refs": [],
        "superseded_refs": [], "domain_canonical_refs": [], "needs_revalidation_refs": [],
        "active_dependency_refs": [], "closed_task_refs": [],
        "issue_pr_review_refs": ["github://issue/393"], "capability_refs": ["canonical://R136-R141"],
        "provenance_complete": True, "desired_effect_unmet": True,
    }
    value.update(overrides)
    return value


def caller_snapshot(candidate_evidence=None, *, main=MAIN):
    candidate_evidence = candidate_evidence or {"C-001": evidence()}
    return {
        "schema_version": "CurrentCanonicalSnapshot/v1", "snapshot_id": f"snapshot:{main[:12]}",
        "canonical_main": main, "observed_at": "2026-08-18T12:01:00+08:00",
        "source_provenance_refs": [f"git://canonical@{main}"],
        "scan_coverage": {
            surface: {"status": "SCANNED", "evidence_refs": [f"caller-asserted://{surface}@{main}"]}
            for surface in REQUIRED_SCAN_SURFACES
        },
        "candidate_evidence": candidate_evidence,
    }


@contextmanager
def synthetic_governed_provider():
    """Test-only sealed provider seam already supported by R136; never production registration."""
    provider_id = "test-only-r142-governed-provider"
    now = datetime.now(timezone.utc)
    bindings = {
        "head_sha": MAIN, "base_sha": MAIN, "current_main_sha": MAIN,
        "review_state_ref": "review-r142", "merged": False, "merge_commit_sha": None,
        "route_fingerprint": "route-r142", "claim_fingerprint": "claim-r142",
        "lane_fingerprint": "lane-r142", "lease_fingerprint": "lease-r142",
        "domain_freshness_ref": "domain-r142", "pending_approval_ref": "approval-r142",
    }
    exact_refs = ("provider://synthetic/r142/pr", "provider://synthetic/r142/control-plane")
    observed_at = (now - timedelta(seconds=5)).isoformat()
    fresh_until = (now + timedelta(minutes=5)).isoformat()
    evidence_digest = gateway_module.digest({"provider": provider_id, "bindings": bindings, "exact_refs": exact_refs, "observed_at": observed_at, "fresh_until": fresh_until})

    def verifier(proof, checked_at):
        del checked_at
        return proof.evidence_digest == evidence_digest and proof.exact_refs == exact_refs and all(getattr(proof, field) == value for field, value in bindings.items())

    prior = gateway_module._LIVE_OBSERVATION_VERIFIERS.get(provider_id)
    gateway_module._LIVE_OBSERVATION_VERIFIERS[provider_id] = verifier
    try:
        yield AuthorityBoundLiveObservationProof(
            CANONICAL_REPOSITORY, 400, "open", bindings["head_sha"], bindings["base_sha"], bindings["current_main_sha"],
            bindings["merged"], bindings["merge_commit_sha"], bindings["review_state_ref"], observed_at,
            bindings["route_fingerprint"], bindings["claim_fingerprint"], bindings["lane_fingerprint"], bindings["lease_fingerprint"],
            bindings["domain_freshness_ref"], bindings["pending_approval_ref"], exact_refs, provider_id,
            "provider://synthetic/r142/attestation", evidence_digest, fresh_until, dict(bindings),
            gateway_module._LIVE_OBSERVATION_ISSUER_SEAL,
        )
    finally:
        if prior is None:
            gateway_module._LIVE_OBSERVATION_VERIFIERS.pop(provider_id, None)
        else:
            gateway_module._LIVE_OBSERVATION_VERIFIERS[provider_id] = prior


def exact_current_reads(execution_id="r142-test-exact"):
    return exact_git_read_proofs(
        REPO, repository=CANONICAL_REPOSITORY, commit=MAIN,
        paths=REQUIRED_NEW_EXACT_PATHS, execution_id=execution_id,
    )


def bound_snapshot(ledger, proof, exact_proofs, candidate_evidence=None):
    candidate_evidence = candidate_evidence or {"C-001": evidence()}
    binding = governed_snapshot_refs(
        expected_canonical_main=MAIN, live_observation_proof=proof,
        exact_read_proofs=exact_proofs, ledger=ledger,
    )
    assert binding["valid"], binding
    exact_by_path = binding["exact_refs_by_path"]
    s0c_ref = binding["s0c_projection_ref"]
    provider_ref = proof.provider_attribution_ref
    coverage = {}
    for surface in REQUIRED_SCAN_SURFACES:
        if surface in {"current_signals", "historical_signals"}:
            refs = [s0c_ref]
        elif surface in {"issues_pr_reviews", "domain_canonical"}:
            refs = [provider_ref]
        elif surface == "current_tasks":
            refs = [exact_by_path["coordination/ACTIVE-CODEX-TASK.yaml"]]
        elif surface == "current_missions":
            refs = [exact_by_path["coordination/ACTIVE-PROGRAM-LANES.yaml"], exact_by_path["coordination/PROGRAM-CONTROL-TOWER.md"]]
        elif surface == "r136_r141_capabilities":
            refs = [exact_by_path[next(path for path in REQUIRED_NEW_EXACT_PATHS if path.endswith("gateway.py"))]]
        else:
            refs = [exact_by_path["coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"]]
        coverage[surface] = {"status": "SCANNED", "evidence_refs": refs}
    return {
        "schema_version": "CurrentCanonicalSnapshot/v1", "snapshot_id": f"bound:{MAIN[:12]}",
        "canonical_main": MAIN, "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_provenance_refs": [provider_ref, s0c_ref, *binding["exact_read_refs"]],
        "scan_coverage": coverage, "candidate_evidence": candidate_evidence,
    }


class LedgerCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = DurableSignalLedger(Path(self.temp.name) / "signals.sqlite")

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def governed_process(self, p=None, candidate_evidence=None, gateway=None):
        p = p or package(candidate())
        with synthetic_governed_provider() as proof:
            exacts = exact_current_reads(f"r142-test-{id(self)}")
            snap = bound_snapshot(self.ledger, proof, exacts, candidate_evidence)
            bridge = RetrospectiveSignalIntakeBridge(
                self.ledger, gateway=gateway, live_observation_proof=proof, exact_read_proofs=exacts,
            )
            return bridge.process(p, snap, expected_canonical_main=MAIN)

    def test_true_new_is_durably_persisted_and_read_back(self):
        result = self.governed_process()
        receipt = result["receipts"][0]
        self.assertEqual((receipt["disposition"], receipt["write_status"]), ("NEW_DURABLE_SIGNAL", "PERSISTED"))
        self.assertEqual("ADMITTED", receipt["durable_ledger_identity_or_receipt"]["status"])
        self.assertTrue(receipt["current_projection_result"]["signal_present"])
        self.assertEqual("REQUIREMENT", receipt["current_projection_result"]["signal_kind"])
        self.assertEqual("S0C-3", receipt["current_projection_result"]["reducer_version"])
        self.assertEqual(1, len(self.ledger.history()))
        self.assertFalse(result["automatic_task_created"])
        self.assertFalse(result["automatic_work_claim_created"])
        self.assertFalse(result["domain_or_w3_written"])
        self.assertFalse(result["second_signal_truth_created"])

    def test_non_requirement_kinds_survive_gateway_history_projection_and_replay(self):
        items = [candidate(f"KIND-{i}", signal_kind=kind) for i, kind in enumerate(("RISK", "FINDING", "OPPORTUNITY", "CORRECTION"), 1)]
        ev = {item["candidate_id"]: evidence() for item in items}
        result = self.governed_process(package(*items, batch_id="KINDS"), ev)
        self.assertEqual(4, len(result["receipts"]))
        self.assertTrue(all(item["write_status"] == "PERSISTED" for item in result["receipts"]))
        history_kinds = {item["signal_kind"] for item in self.ledger.history()}
        self.assertEqual({"RISK", "FINDING", "OPPORTUNITY", "CORRECTION"}, history_kinds)
        projection = self.ledger.current_projection()
        projected = {item["signal_kind"] for item in projection["signals"]}
        self.assertEqual(history_kinds, projected)
        self.assertTrue(self.ledger.observe_replay())
        replayed = {item["signal_kind"] for item in self.ledger.current_projection()["signals"]}
        self.assertEqual(history_kinds, replayed)

    def test_r136_legacy_default_remains_requirement_and_invalid_kind_fails_closed(self):
        gateway = SignalIntakeGateway(self.ledger)
        env = _r136_envelope(candidate("LEGACY-001"))
        first = gateway.intake(env, request_text="governed system signal", explicit_capture=True)
        self.assertEqual("REQUIREMENT", first["signal_kind"])
        self.assertEqual("REQUIREMENT", self.ledger.history()[0]["signal_kind"])
        bad = _r136_envelope(candidate("LEGACY-002"))
        with self.assertRaises(GatewayError) as got:
            gateway.intake(bad, request_text="governed system signal", explicit_capture=True, signal_kind="NOT_A_KIND")
        self.assertEqual("INVALID_SIGNAL_KIND", got.exception.code)

    def test_repeat_same_candidate_is_current_canonical_not_rewritten(self):
        self.governed_process()
        second = self.governed_process()["receipts"][0]
        self.assertEqual("ALREADY_CANONICAL", second["disposition"])
        self.assertEqual("NOT_PERSISTED", second["write_status"])
        self.assertEqual(1, len(self.ledger.history()))

    def test_omission_is_not_revocation(self):
        self.governed_process()
        signal_id = self.ledger.history()[0]["signal_id"]
        before = deepcopy(self.ledger.history())
        receipt = SignalIntakeGateway(self.ledger).omission(signal_id)
        self.assertEqual("OMISSION_NOOP", receipt["status"])
        self.assertFalse(receipt["revoked"])
        self.assertEqual(before, self.ledger.history())

    def test_signal_is_not_task(self):
        result = self.governed_process()
        event = self.ledger.history()[0]
        self.assertEqual("NOT_STARTED", event["execution_state"])
        self.assertEqual([], event["authority_targets"])
        self.assertFalse(result["automatic_task_created"])
        self.assertFalse(result["automatic_work_claim_created"])

    def test_stable_replay_checksum(self):
        self.governed_process()
        before = self.ledger.current_projection()["checksum"]
        self.assertTrue(self.ledger.observe_replay())
        self.assertEqual(before, self.ledger.current_projection()["checksum"])

    def test_transport_cannot_mutate_effective_truth(self):
        before = self.ledger.history()
        staged = stage_import_package(package(candidate()))
        self.assertEqual(before, self.ledger.history())
        self.assertFalse(staged["effective_truth_authority"])
        self.assertEqual("NOT_PERSISTED", staged["write_status"])

    def test_no_durable_readback_means_not_persisted(self):
        class GhostGateway:
            def intake(self, *args, **kwargs):
                return {"event_id": "ghost", "signal_id": "ghost-signal", "ledger_receipt": {"status": "ADMITTED"}}
        receipt = self.governed_process(gateway=GhostGateway())["receipts"][0]
        self.assertEqual("NOT_PERSISTED", receipt["write_status"])
        self.assertEqual("DURABLE_READBACK_MISSING", receipt["durable_ledger_identity_or_receipt"]["error_code"])
        self.assertEqual([], self.ledger.history())

    def test_closed_task_desired_effect_unmet_can_be_new_signal_without_task_resurrection(self):
        result = self.governed_process(candidate_evidence={"C-001": evidence(closed_task_refs=["github://issue/old-closed"])})
        self.assertEqual("NEW_DURABLE_SIGNAL", result["receipts"][0]["disposition"])
        self.assertEqual("PERSISTED", result["receipts"][0]["write_status"])
        self.assertFalse(result["automatic_task_created"])

    def test_current_task_dependency_preserved_without_auto_task(self):
        result = self.governed_process(candidate_evidence={"C-001": evidence(active_dependency_refs=["mission://CURRENT-DEP"])})
        self.assertEqual("PERSISTED", result["receipts"][0]["write_status"])
        self.assertFalse(result["automatic_task_created"])


class ReconciliationCase(unittest.TestCase):
    def decision(self, ev, cand=None):
        c = cand or candidate()
        return reconcile_package(package(c), caller_snapshot({c["candidate_id"]: ev}), expected_canonical_main=MAIN)["results"][0]

    def test_structurally_complete_caller_fabricated_snapshot_cannot_authorize_new(self):
        result = self.decision(evidence())
        self.assertEqual("NEEDS_REVALIDATION", result["disposition"])
        self.assertEqual("AUTHORITY_BOUND_LIVE_OBSERVATION_REQUIRED", result["reason"])

    def test_real_sealed_observation_and_exact_reads_bind_new(self):
        with tempfile.TemporaryDirectory() as directory, synthetic_governed_provider() as proof:
            ledger = DurableSignalLedger(Path(directory) / "ledger.sqlite")
            try:
                exacts = exact_current_reads("r142-positive-binding")
                snap = bound_snapshot(ledger, proof, exacts)
                result = reconcile_package(package(candidate()), snap, expected_canonical_main=MAIN, live_observation_proof=proof, exact_read_proofs=exacts, ledger=ledger)["results"][0]
                self.assertEqual("NEW_DURABLE_SIGNAL", result["disposition"])
                self.assertTrue(result["authority_evidence_refs"])
            finally:
                ledger.close()

    def test_one_real_proof_cannot_be_reused_as_fake_all_surface_refs(self):
        with tempfile.TemporaryDirectory() as directory, synthetic_governed_provider() as proof:
            ledger = DurableSignalLedger(Path(directory) / "ledger.sqlite")
            try:
                exacts = exact_current_reads("r142-bad-binding")
                snap = bound_snapshot(ledger, proof, exacts)
                snap["scan_coverage"]["current_tasks"]["evidence_refs"] = [proof.provider_attribution_ref]
                result = reconcile_package(package(candidate()), snap, expected_canonical_main=MAIN, live_observation_proof=proof, exact_read_proofs=exacts, ledger=ledger)["results"][0]
                self.assertEqual("NEEDS_REVALIDATION", result["disposition"])
                self.assertEqual("CANONICAL_SCAN_EVIDENCE_NOT_BOUND", result["reason"])
            finally:
                ledger.close()

    def test_old_new_current_already_satisfied(self):
        self.assertEqual("ALREADY_SATISFIED", self.decision(evidence(satisfied_refs=["canonical://done"]))["disposition"])

    def test_old_window_new_is_overridden(self):
        c = candidate(historical_status="NEW")
        result = self.decision(evidence(current_signal_refs=["signal://current"]), c)
        self.assertEqual("ALREADY_CANONICAL", result["disposition"])
        self.assertEqual("NEW", result["historical_status"])

    def test_cross_window_duplicate(self):
        self.assertEqual("DUPLICATE", self.decision(evidence(duplicate_refs=["signal://other-window"]))["disposition"])

    def test_superseded_historical_requirement(self):
        self.assertEqual("SUPERSEDED", self.decision(evidence(superseded_refs=["signal://replacement"]))["disposition"])

    def test_contradictory_lessons_do_not_overwrite(self):
        self.assertEqual("CONTRADICTS", self.decision(evidence(contradicts_refs=["signal://counterlesson"]))["disposition"])

    def test_domain_only_knowledge(self):
        self.assertEqual("DOMAIN_CANONICAL_ONLY", self.decision(evidence(domain_canonical_refs=["domain://canonical"]))["disposition"])

    def test_missing_provenance(self):
        self.assertEqual("INSUFFICIENT_PROVENANCE", self.decision(evidence(), candidate(evidence_refs=[]))["disposition"])

    def test_stale_snapshot(self):
        c = candidate()
        result = reconcile_package(package(c), caller_snapshot({"C-001": evidence()}, main="b" * 40), expected_canonical_main=MAIN)["results"][0]
        self.assertEqual("NEEDS_REVALIDATION", result["disposition"])
        self.assertEqual("STALE_CANONICAL_SNAPSHOT", result["reason"])

    def test_extends_and_reinforces(self):
        for field, expected in (("extends_refs", "EXTENDS"), ("reinforces_refs", "REINFORCES")):
            with self.subTest(field=field):
                self.assertEqual(expected, self.decision(evidence(**{field: [f"signal://{field}"]}))["disposition"])

    def test_needs_revalidation_evidence_beats_old_new(self):
        c = candidate(historical_status="NEW")
        self.assertEqual("NEEDS_REVALIDATION", self.decision(evidence(needs_revalidation_refs=["canonical://gap"]), c)["disposition"])

    def test_private_raw_candidate_is_rejected(self):
        c = candidate(); c["raw_source_body"] = "private conversation body must never enter public repo"
        result = reconcile_package(package(c), caller_snapshot({"C-001": evidence()}), expected_canonical_main=MAIN)["results"][0]
        self.assertEqual("REJECT_PRIVATE_OR_UNSAFE", result["disposition"])

    def test_disposition_matrix_is_complete(self):
        self.assertEqual({
            "NEW_DURABLE_SIGNAL", "ALREADY_CANONICAL", "ALREADY_SATISFIED", "DUPLICATE",
            "EXTENDS", "REINFORCES", "CONTRADICTS", "SUPERSEDED", "DOMAIN_CANONICAL_ONLY",
            "NEEDS_REVALIDATION", "REJECT_PRIVATE_OR_UNSAFE", "INSUFFICIENT_PROVENANCE",
        }, set(DISPOSITIONS))


class PackageContractCase(unittest.TestCase):
    def test_deterministic_canonicalization_digest(self):
        p = package(candidate()); reordered = dict(reversed(list(p.items())))
        self.assertEqual(validate_import_package(p)["package_digest"], validate_import_package(reordered)["package_digest"])

    def test_batch_duplicate_and_same_id_collision(self):
        same = candidate(); parsed = validate_import_package(package(same, deepcopy(same)))
        self.assertEqual("DUPLICATE_CANDIDATE_IN_BATCH", parsed["candidate_errors"][0]["code"])
        changed = deepcopy(same); changed["desired_effect"] = "different"
        parsed = validate_import_package(package(same, changed))
        self.assertEqual("CANDIDATE_ID_COLLISION", parsed["candidate_errors"][0]["code"])

    def test_invalid_signal_kind_is_rejected_before_gateway(self):
        parsed = validate_import_package(package(candidate(signal_kind="NOT_A_KIND")))
        self.assertEqual("INVALID_SIGNAL_KIND", parsed["candidate_errors"][0]["code"])

    def test_historical_source_status_reflects_reconstruction_authorization(self):
        path = ROOT / "R142" / "REAL-RETROSPECTIVE-STATUS.yaml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertIn(payload["status"], {
            "REAL_RETROSPECTIVE_SOURCE_UNAVAILABLE",
            "HISTORICAL_HANDOFF_SOURCE_AVAILABLE / PRE_ENUMERATED_PACKAGE_NOT_RECOVERED",
        })
        self.assertTrue(payload["historical_handoff"]["available"])


if __name__ == "__main__":
    unittest.main()
