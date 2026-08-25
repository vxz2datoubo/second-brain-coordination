from __future__ import annotations

import copy
import unittest

from global_signal_gateway.retrospective_intake import validate_import_package
from project_retrospective_sweep import (
    SOURCE_SCHEMA,
    ProjectRetrospectiveSweepError,
    build_r147_requests,
    execute_r147_admissions,
    finalize_sweep_receipt,
    prepare_project_sweep,
    reconcile_project_sweep,
    validate_source_snapshot,
)


MAIN = "71c70f6bc3683eff4c19020a7d4cc998517c6ba1"
GENERATED_AT = "2026-08-25T11:20:00+00:00"


def identity(obj: str = "project retrospective sweep", *, polarity: str = "positive") -> dict:
    return {
        "kind": "requirement",
        "subject": "signal tower",
        "predicate": "preserve",
        "object": obj,
        "scope": "chatgpt project",
        "polarity": polarity,
    }


def candidate(summary: str = "Preserve durable Project decisions without duplicate Signals", *,
              signal_kind: str = "REQUIREMENT", domain: str = "SECOND_BRAIN_SYSTEM") -> dict:
    return {
        "public_safe_summary": summary,
        "signal_kind": signal_kind,
        "epistemic_state": "USER_EXPLICIT",
        "desired_effect": "Preserve durable Project-level learning through the existing Signal Tower.",
        "problem_to_solve": "Important Project history is fragmented across conversation windows.",
        "success_condition": "Only current genuine new Signals are admitted after canonical reconciliation.",
        "expected_problems": ["cross-window duplication"],
        "risks": ["false complete-coverage claims"],
        "assumptions": ["the caller reports source coverage truthfully"],
        "unknowns": ["full product-level Project enumeration may be unavailable"],
        "dependencies": [],
        "counterevidence_refs": [],
        "proposed_primary_domain": domain,
        "related_domains": [],
        "privacy_scope": "PUBLIC_SAFE_METADATA_ONLY",
        "historical_status": "HISTORICAL_CANDIDATE",
        "model_tool_version_work_item_refs": {"model_ref": "GPT-5.6-Sol"},
    }


def item(message_ref: str, *, semantic_identity: dict | None = None, summary: str | None = None,
         directive: str = "CAPTURE_ALLOWED", payload: dict | None = None,
         relations: list | None = None, semantic_identity_ref: str | None = None) -> dict:
    value = {
        "source_message_ref": message_ref,
        "source_time_range": {
            "start": "2026-08-25T10:00:00+00:00",
            "end": "2026-08-25T10:01:00+00:00",
        },
        "source_evidence_refs": [f"opaque://evidence/{message_ref.rsplit('/', 1)[-1]}"],
        "original_intent_ref": f"intent://{message_ref.rsplit('/', 1)[-1]}",
        "capture_directive": directive,
        "semantic_identity": semantic_identity or identity(),
        "candidate": payload or candidate(summary or f"summary for {message_ref}"),
    }
    if relations is not None:
        value["relations"] = relations
    if semantic_identity_ref is not None:
        value["semantic_identity_ref"] = semantic_identity_ref
    return value


def source_snapshot(windows: list, *, status: str = "PARTIAL_ENUMERATION",
                    omitted: list | None = None, evidence: list | None = None) -> dict:
    refs = [window["window_ref"] for window in windows]
    return {
        "schema_version": SOURCE_SCHEMA,
        "project_ref": "chatgpt-project://second-brain-knowledge-base",
        "source_project": "SECOND_BRAIN_PROJECT",
        "snapshot_ref": "project-snapshot://2026-08-25T19:20+08",
        "enumeration_mode": "CHATGPT_PROJECT_CONTEXT",
        "enumeration_started_at": "2026-08-25T11:18:00+00:00",
        "enumeration_completed_at": "2026-08-25T11:19:00+00:00",
        "window_refs": refs,
        "window_count_observed": len(refs),
        "coverage_status": status,
        "coverage_evidence_refs": ["provider://project-context/partial"] if evidence is None else evidence,
        "omitted_or_unavailable_refs": ["window://not-enumerable"] if omitted is None else omitted,
        "source_provider_version": "chatgpt-project-context/v1",
        "windows": windows,
    }


def one_window(*items: dict, ref: str = "window://one") -> list:
    return [{"window_ref": ref, "items": list(items)}]


class CoverageContractTests(unittest.TestCase):
    def test_partial_enumeration_can_never_claim_complete(self) -> None:
        snapshot = source_snapshot(one_window(item("message://1")))
        normalized = validate_source_snapshot(snapshot)
        self.assertFalse(normalized["project_scan_complete"])
        plan = prepare_project_sweep(snapshot, generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertFalse(plan["project_scan_complete"])
        self.assertEqual(plan["coverage_status"], "PARTIAL_ENUMERATION")

    def test_complete_enumeration_requires_mechanical_coverage_evidence(self) -> None:
        snapshot = source_snapshot(
            one_window(item("message://1")),
            status="COMPLETE_ENUMERATION_PROVEN",
            omitted=[],
            evidence=[],
        )
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_COMPLETE_COVERAGE_EVIDENCE_REQUIRED"):
            validate_source_snapshot(snapshot)

    def test_complete_enumeration_forbids_omitted_refs(self) -> None:
        snapshot = source_snapshot(
            one_window(item("message://1")),
            status="CALLER_SUPPLIED_EXPORT_COMPLETE",
            omitted=["window://missing"],
            evidence=["manifest://complete-export"],
        )
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_COMPLETE_WITH_OMISSIONS_FORBIDDEN"):
            validate_source_snapshot(snapshot)

    def test_enumeration_unavailable_cannot_contain_windows(self) -> None:
        snapshot = source_snapshot(one_window(item("message://1")), status="ENUMERATION_UNAVAILABLE")
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_ENUMERATION_UNAVAILABLE_WITH_WINDOWS"):
            validate_source_snapshot(snapshot)


class CrossWindowNormalizationTests(unittest.TestCase):
    def test_same_semantic_candidate_across_five_windows_dedupes_to_one(self) -> None:
        windows = [
            {"window_ref": f"window://{index}", "items": [item(f"message://{index}", summary=f"different wording {index}")]}
            for index in range(5)
        ]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertEqual(plan["candidate_count"], 1)
        self.assertEqual(len(plan["candidate_ids"]), 1)
        built = plan["package"]["candidates"][0]
        self.assertEqual(len([ref for ref in built["evidence_refs"] if ref.startswith("source-message://")]), 5)
        self.assertEqual(validate_import_package(plan["package"])["candidate_errors"], [])

    def test_repeat_run_is_deterministic(self) -> None:
        snapshot = source_snapshot(one_window(item("message://1")))
        first = prepare_project_sweep(snapshot, generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        second = prepare_project_sweep(copy.deepcopy(snapshot), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertEqual(first["sweep_id"], second["sweep_id"])
        self.assertEqual(first["candidate_ids"], second["candidate_ids"])
        self.assertEqual(first["package"], second["package"])

    def test_explicit_no_capture_wins(self) -> None:
        windows = one_window(
            item("message://keep", semantic_identity=identity("keep")),
            item("message://skip", semantic_identity=identity("skip"), directive="DO_NOT_CAPTURE"),
        )
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertEqual(plan["candidate_count"], 1)
        self.assertEqual(len(plan["excluded_items"]), 1)
        self.assertEqual(plan["excluded_items"][0]["reason"], "DO_NOT_CAPTURE")

    def test_semantic_identity_ref_cannot_be_reused_for_changed_semantics(self) -> None:
        first_snapshot = source_snapshot(one_window(item("message://1")))
        first_plan = prepare_project_sweep(first_snapshot, generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        semantic_ref = "semantic://r148/" + first_plan["candidate_ids"][0].removeprefix("r148-")
        changed = item(
            "message://2",
            semantic_identity=identity("different meaning", polarity="negative"),
            semantic_identity_ref=semantic_ref,
        )
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_SEMANTIC_IDENTITY_REF_MISMATCH"):
            prepare_project_sweep(source_snapshot(one_window(changed)), generated_at=GENERATED_AT, expected_canonical_main=MAIN)

    def test_same_semantic_group_cannot_drift_domain_or_signal_kind(self) -> None:
        same = identity("one mechanism")
        windows = [
            {"window_ref": "window://a", "items": [item("message://a", semantic_identity=same)]},
            {"window_ref": "window://b", "items": [item(
                "message://b", semantic_identity=same,
                payload=candidate("same mechanism", signal_kind="DECISION"),
            )]},
        ]
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_SEMANTIC_GROUP_CORE_DRIFT"):
            prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)

    def test_correction_relation_is_preserved_without_overwrite(self) -> None:
        old_identity = identity("old project sweep policy")
        new_identity = identity("corrected project sweep policy")
        relation = [{
            "relation": "SUPERSEDES",
            "target_semantic_identity": old_identity,
            "evidence_refs": ["opaque://evidence/correction"],
        }]
        windows = [
            {"window_ref": "window://old", "items": [item("message://old", semantic_identity=old_identity)]},
            {"window_ref": "window://new", "items": [item("message://new", semantic_identity=new_identity, relations=relation)]},
        ]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertEqual(plan["candidate_count"], 2)
        relations = [rel for candidate_row in plan["package"]["candidates"] for rel in candidate_row["candidate_relations"]]
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]["relation"], "SUPERSEDES")
        self.assertIn(relations[0]["target_ref"], plan["candidate_ids"])

    def test_private_raw_or_credential_material_fails_closed(self) -> None:
        unsafe = item("message://unsafe")
        unsafe["candidate"]["raw_source_body"] = "do not persist this"
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_PRIVATE_OR_UNSAFE"):
            prepare_project_sweep(source_snapshot(one_window(unsafe)), generated_at=GENERATED_AT, expected_canonical_main=MAIN)


class AuthorityBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = prepare_project_sweep(
            source_snapshot(one_window(item("message://1"))), generated_at=GENERATED_AT, expected_canonical_main=MAIN
        )
        self.candidate_id = self.plan["candidate_ids"][0]
        parsed = validate_import_package(self.plan["package"])
        self.candidate_digest = parsed["candidates"][0]["candidate_digest"]

    def test_r148_delegates_disposition_to_r142_reconcile_function(self) -> None:
        observed = {}

        def fake_reconcile(package, snapshot, **kwargs):
            observed["package"] = package
            observed["snapshot"] = snapshot
            observed["kwargs"] = kwargs
            return {
                "package_digest": "pkg",
                "canonical_snapshot_or_main": MAIN,
                "snapshot_digest": "snap",
                "results": [{
                    "candidate_id": self.candidate_id,
                    "candidate_digest": self.candidate_digest,
                    "disposition": "ALREADY_SATISFIED",
                }],
            }

        result = reconcile_project_sweep(
            self.plan, {"opaque": "snapshot"}, expected_canonical_main=MAIN, reconcile_fn=fake_reconcile
        )
        self.assertIs(observed["package"], self.plan["package"])
        self.assertEqual(observed["kwargs"]["expected_canonical_main"], MAIN)
        self.assertEqual(result["disposition_counts"], {"ALREADY_SATISFIED": 1})
        self.assertEqual(build_r147_requests(self.plan, result), [])

    def test_only_r142_new_durable_signal_becomes_r147_request(self) -> None:
        reconciliation = {
            "sweep_id": self.plan["sweep_id"],
            "disposition_counts": {"NEW_DURABLE_SIGNAL": 1},
            "results": [{
                "candidate_id": self.candidate_id,
                "candidate_digest": self.candidate_digest,
                "disposition": "NEW_DURABLE_SIGNAL",
            }],
        }
        requests = build_r147_requests(self.plan, reconciliation)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["capture_identity"], f"r148:{self.candidate_id}")
        self.assertEqual(requests[0]["capture_command"], "把这个录入信号塔")
        self.assertEqual(requests[0]["proposed_primary_domain"], "SECOND_BRAIN_SYSTEM")

    def test_r142_candidate_digest_mismatch_fails_closed(self) -> None:
        reconciliation = {
            "sweep_id": self.plan["sweep_id"],
            "disposition_counts": {"NEW_DURABLE_SIGNAL": 1},
            "results": [{
                "candidate_id": self.candidate_id,
                "candidate_digest": "0" * 64,
                "disposition": "NEW_DURABLE_SIGNAL",
            }],
        }
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_R142_CANDIDATE_DIGEST_MISMATCH"):
            build_r147_requests(self.plan, reconciliation)

    def test_verified_r147_receipt_is_accepted_without_side_effects(self) -> None:
        reconciliation = {
            "sweep_id": self.plan["sweep_id"],
            "disposition_counts": {"NEW_DURABLE_SIGNAL": 1},
            "results": [{
                "candidate_id": self.candidate_id,
                "candidate_digest": self.candidate_digest,
                "disposition": "NEW_DURABLE_SIGNAL",
            }],
        }

        def admit(_request):
            return {
                "status": "ADMITTED",
                "durable_success": True,
                "readback_verification_status": "VERIFIED_SAME_LEDGER",
                "fresh_replay_verification_status": "VERIFIED_FRESH_S0C_REPLAY",
                "signal_id": "signal:test",
                "event_id": "event:test",
                "receipt_id": "receipt:test",
                "receipt_offset": 1,
                "task_created": False,
                "route_created": False,
                "work_claim_created": False,
                "write_permission_created": False,
                "transport_replay_after": {"projection_checksum": "abc123"},
            }

        receipt = execute_r147_admissions(self.plan, reconciliation, admit_fn=admit)
        self.assertTrue(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(receipt["new_durable_signal_count"], 1)
        self.assertEqual(len(receipt["admitted_signal_refs"]), 1)
        self.assertFalse(receipt["project_scan_complete"])
        self.assertNotEqual(receipt["coverage_caveat"], "NONE")
        self.assertFalse(receipt["automatic_task_created"])
        self.assertFalse(receipt["second_signal_truth_created"])

    def test_missing_same_ledger_readback_never_becomes_success(self) -> None:
        reconciliation = {
            "sweep_id": self.plan["sweep_id"],
            "disposition_counts": {"NEW_DURABLE_SIGNAL": 1},
            "results": [{
                "candidate_id": self.candidate_id,
                "candidate_digest": self.candidate_digest,
                "disposition": "NEW_DURABLE_SIGNAL",
            }],
        }
        request = build_r147_requests(self.plan, reconciliation)[0]
        bad = {
            "r148_capture_identity": request["capture_identity"],
            "status": "ADMITTED",
            "durable_success": True,
            "readback_verification_status": "NOT_VERIFIED",
            "fresh_replay_verification_status": "VERIFIED_FRESH_S0C_REPLAY",
            "task_created": False,
            "route_created": False,
            "work_claim_created": False,
            "write_permission_created": False,
        }
        receipt = finalize_sweep_receipt(self.plan, reconciliation, [bad])
        self.assertFalse(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(receipt["admitted_signal_refs"], [])
        self.assertEqual(receipt["admission_failures"][0]["reason"], "R147_DURABLE_VERIFICATION_FAILED")


if __name__ == "__main__":
    unittest.main()
