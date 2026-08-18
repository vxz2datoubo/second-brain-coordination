"""R142 adversarial coverage for retrospective Signal intake and durable read-back."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import yaml

from global_signal_gateway.gateway import SignalIntakeGateway
from global_signal_gateway.retrospective_intake import (
    DISPOSITIONS, REQUIRED_SCAN_SURFACES, RetrospectiveSignalIntakeBridge,
    reconcile_package, stage_import_package, validate_import_package,
)
from global_signal_plane.ledger import DurableSignalLedger

MAIN = "a" * 40
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
        "expected_canonical_main": "UNKNOWN", "candidates": list(items or (candidate(),)),
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


def snapshot(candidate_evidence=None, *, main=MAIN):
    candidate_evidence = candidate_evidence or {"C-001": evidence()}
    return {
        "schema_version": "CurrentCanonicalSnapshot/v1", "snapshot_id": f"snapshot:{main[:12]}",
        "canonical_main": main, "observed_at": "2026-08-18T12:01:00+08:00",
        "source_provenance_refs": [f"git://canonical@{main}"],
        "scan_coverage": {
            surface: {"status": "SCANNED", "evidence_refs": [f"canonical-scan://{surface}@{main}"]}
            for surface in REQUIRED_SCAN_SURFACES
        },
        "candidate_evidence": candidate_evidence,
    }


class LedgerCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = DurableSignalLedger(Path(self.temp.name) / "signals.sqlite")

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def bridge(self, gateway=None):
        return RetrospectiveSignalIntakeBridge(self.ledger, gateway=gateway)

    def test_true_new_is_durably_persisted_and_read_back(self):
        result = self.bridge().process(package(candidate()), snapshot(), expected_canonical_main=MAIN)
        receipt = result["receipts"][0]
        self.assertEqual("NEW_DURABLE_SIGNAL", receipt["disposition"])
        self.assertEqual("PERSISTED", receipt["write_status"])
        self.assertEqual("ADMITTED", receipt["durable_ledger_identity_or_receipt"]["status"])
        self.assertTrue(receipt["current_projection_result"]["signal_present"])
        self.assertEqual(1, len(self.ledger.history()))
        self.assertFalse(result["automatic_task_created"])
        self.assertFalse(result["automatic_work_claim_created"])
        self.assertFalse(result["domain_or_w3_written"])
        self.assertFalse(result["second_signal_truth_created"])

    def test_duplicate_retry_is_idempotent(self):
        p, s = package(candidate()), snapshot()
        self.bridge().process(p, s, expected_canonical_main=MAIN)
        second = self.bridge().process(p, s, expected_canonical_main=MAIN)["receipts"][0]
        self.assertEqual("PERSISTED", second["write_status"])
        self.assertEqual("IDEMPOTENT_DUPLICATE", second["durable_ledger_identity_or_receipt"]["status"])
        self.assertEqual(1, len(self.ledger.history()))

    def test_same_id_different_body_collision_fails_closed(self):
        self.bridge().process(package(candidate(), batch_id="A"), snapshot(), expected_canonical_main=MAIN)
        result = self.bridge().process(
            package(candidate(public_safe_summary="Different semantic body"), batch_id="B"),
            snapshot(), expected_canonical_main=MAIN,
        )["receipts"][0]
        self.assertEqual("NOT_PERSISTED", result["write_status"])
        self.assertIn(result["durable_ledger_identity_or_receipt"]["error_code"], {"IDEMPOTENCY_KEY_COLLISION", "EVENT_ID_COLLISION"})
        self.assertEqual(1, len(self.ledger.history()))

    def test_omission_is_not_revocation(self):
        self.bridge().process(package(candidate()), snapshot(), expected_canonical_main=MAIN)
        signal_id = self.ledger.history()[0]["signal_id"]
        before = deepcopy(self.ledger.history())
        receipt = SignalIntakeGateway(self.ledger).omission(signal_id)
        self.assertEqual("OMISSION_NOOP", receipt["status"])
        self.assertFalse(receipt["revoked"])
        self.assertEqual(before, self.ledger.history())

    def test_signal_is_not_task(self):
        result = self.bridge().process(package(candidate()), snapshot(), expected_canonical_main=MAIN)
        event = self.ledger.history()[0]
        self.assertEqual("NOT_STARTED", event["execution_state"])
        self.assertEqual([], event["authority_targets"])
        self.assertFalse(result["automatic_task_created"])
        self.assertFalse(result["automatic_work_claim_created"])

    def test_stable_replay_checksum(self):
        self.bridge().process(package(candidate()), snapshot(), expected_canonical_main=MAIN)
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
        receipt = self.bridge(GhostGateway()).process(package(candidate()), snapshot(), expected_canonical_main=MAIN)["receipts"][0]
        self.assertEqual("NOT_PERSISTED", receipt["write_status"])
        self.assertEqual("DURABLE_READBACK_MISSING", receipt["durable_ledger_identity_or_receipt"]["error_code"])
        self.assertEqual([], self.ledger.history())

    def test_closed_task_desired_effect_unmet_is_new_signal_not_task_resurrection(self):
        s = snapshot({"C-001": evidence(closed_task_refs=["github://issue/old-closed"])})
        result = self.bridge().process(package(candidate()), s, expected_canonical_main=MAIN)
        self.assertEqual("NEW_DURABLE_SIGNAL", result["receipts"][0]["disposition"])
        self.assertEqual("PERSISTED", result["receipts"][0]["write_status"])
        self.assertFalse(result["automatic_task_created"])

    def test_current_task_dependency_is_preserved_without_auto_task(self):
        s = snapshot({"C-001": evidence(active_dependency_refs=["mission://CURRENT-DEP"])})
        rec = reconcile_package(package(candidate()), s, expected_canonical_main=MAIN)
        self.assertEqual(["mission://CURRENT-DEP"], rec["results"][0]["dependency_refs"])
        result = self.bridge().process(package(candidate()), s, expected_canonical_main=MAIN)
        self.assertEqual("PERSISTED", result["receipts"][0]["write_status"])
        self.assertFalse(result["automatic_task_created"])


class ReconciliationCase(unittest.TestCase):
    def decision(self, ev, cand=None):
        c = cand or candidate()
        return reconcile_package(package(c), snapshot({c["candidate_id"]: ev}), expected_canonical_main=MAIN)["results"][0]

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
        result = reconcile_package(package(c), snapshot({"C-001": evidence()}, main="b" * 40), expected_canonical_main=MAIN)["results"][0]
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
        c = candidate()
        c["raw_source_body"] = "private conversation body must never enter public repo"
        result = reconcile_package(package(c), snapshot({"C-001": evidence()}), expected_canonical_main=MAIN)["results"][0]
        self.assertEqual("REJECT_PRIVATE_OR_UNSAFE", result["disposition"])

    def test_disposition_matrix_is_complete(self):
        self.assertEqual({
            "NEW_DURABLE_SIGNAL", "ALREADY_CANONICAL", "ALREADY_SATISFIED", "DUPLICATE",
            "EXTENDS", "REINFORCES", "CONTRADICTS", "SUPERSEDED", "DOMAIN_CANONICAL_ONLY",
            "NEEDS_REVALIDATION", "REJECT_PRIVATE_OR_UNSAFE", "INSUFFICIENT_PROVENANCE",
        }, set(DISPOSITIONS))


class PackageContractCase(unittest.TestCase):
    def test_deterministic_canonicalization_digest(self):
        p = package(candidate())
        reordered = dict(reversed(list(p.items())))
        self.assertEqual(validate_import_package(p)["package_digest"], validate_import_package(reordered)["package_digest"])

    def test_batch_duplicate_and_same_id_collision(self):
        same = candidate()
        parsed = validate_import_package(package(same, deepcopy(same)))
        self.assertEqual("DUPLICATE_CANDIDATE_IN_BATCH", parsed["candidate_errors"][0]["code"])
        changed = deepcopy(same); changed["desired_effect"] = "different"
        parsed = validate_import_package(package(same, changed))
        self.assertEqual("CANDIDATE_ID_COLLISION", parsed["candidate_errors"][0]["code"])

    def test_real_retrospective_case_is_honestly_unavailable(self):
        path = Path(__file__).resolve().parents[1] / "R142" / "REAL-RETROSPECTIVE-STATUS.yaml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual("REAL_RETROSPECTIVE_SOURCE_UNAVAILABLE", payload["status"])
        self.assertTrue(payload["historical_handoff"]["available"])
        self.assertFalse(payload["enumerated_candidate_package"]["available"])
        self.assertTrue(payload["synthetic_corpus_is_not_real_case"])


if __name__ == "__main__":
    unittest.main()
