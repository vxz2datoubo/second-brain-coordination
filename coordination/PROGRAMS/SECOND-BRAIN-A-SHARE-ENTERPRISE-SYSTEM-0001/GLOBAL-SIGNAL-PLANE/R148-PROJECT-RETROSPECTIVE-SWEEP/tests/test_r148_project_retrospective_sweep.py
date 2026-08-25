from __future__ import annotations

import copy
import hashlib
import json
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
R147_RECEIPT_SCHEMA = "R147AutomaticIngressReceipt/v1"
R147_TRANSPORT_SCHEMA = "R147GitReplayTransport/v1"
HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def identity(obj: str = "project retrospective sweep", *, polarity: str = "positive") -> dict:
    return {
        "kind": "requirement",
        "subject": "signal tower",
        "predicate": "preserve",
        "object": obj,
        "scope": "chatgpt project",
        "polarity": polarity,
    }


def candidate(
    summary: str = "Preserve durable Project decisions without duplicate Signals",
    *,
    signal_kind: str = "REQUIREMENT",
    domain: str = "SECOND_BRAIN_SYSTEM",
    privacy_scope: str = "PUBLIC_SAFE_METADATA_ONLY",
) -> dict:
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
        "privacy_scope": privacy_scope,
        "historical_status": "HISTORICAL_CANDIDATE",
        "model_tool_version_work_item_refs": {"model_ref": "GPT-5.6-Sol"},
    }


def item(
    message_ref: str,
    *,
    semantic_identity: dict | None = None,
    summary: str | None = None,
    directive: str = "CAPTURE_ALLOWED",
    payload: dict | None = None,
    relations: list | None = None,
    semantic_identity_ref: str | None = None,
) -> dict:
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


def source_snapshot(
    windows: list,
    *,
    status: str = "PARTIAL_ENUMERATION",
    omitted: list | None = None,
    evidence: list | None = None,
) -> dict:
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


def one_window(*items_: dict, ref: str = "window://one") -> list:
    return [{"window_ref": ref, "items": list(items_)}]


def trusted_complete_verifier(request: dict) -> dict:
    body = {
        "schema_version": "ProjectCoverageVerificationAttestation/v1",
        "verification_status": "VERIFIED_COMPLETE_ENUMERATION",
        "project_ref": request["project_ref"],
        "snapshot_ref": request["snapshot_ref"],
        "coverage_status": request["coverage_status"],
        "window_manifest_digest": request["window_manifest_digest"],
        "coverage_evidence_refs": request["coverage_evidence_refs"],
        "verifier_ref": "trusted-provider://project-export-manifest/v1",
    }
    return {**body, "attestation_digest": sha(body)}


def replay(count: int, *, revision: str) -> dict:
    return {
        "schema_version": R147_TRANSPORT_SCHEMA,
        "event_count": count,
        "input_revision": revision,
        "history_digest": HEX_A,
        "projection_checksum": HEX_B,
        "journal_digest": HEX_C,
    }


def valid_r147_receipt(request: dict, *, status: str = "ADMITTED", before_count: int = 0) -> dict:
    after_count = before_count + (1 if status == "ADMITTED" else 0)
    offset = after_count if status == "ADMITTED" else max(1, after_count)
    return {
        "schema_version": R147_RECEIPT_SCHEMA,
        "attempt_id": request["attempt_id"],
        "status": status,
        "durable_success": True,
        "signal_id": "signal:r148-test",
        "event_id": "r136:r148-test",
        "receipt_id": "durable-admission:r148-test",
        "receipt_offset": offset,
        "input_revision": "revision-after",
        "primary_domain": request["proposed_primary_domain"],
        "authority_binding_digest": HEX_A,
        "authority_refs": ["authority://verified/r145"],
        "content_digest": HEX_B,
        "event_digest": HEX_C,
        "readback_verification_status": "VERIFIED_SAME_LEDGER",
        "fresh_replay_verification_status": "VERIFIED_FRESH_S0C_REPLAY",
        "transport_replay_before": replay(before_count, revision="revision-before"),
        "transport_replay_after": replay(after_count, revision="revision-after"),
        "task_created": False,
        "route_created": False,
        "work_claim_created": False,
        "write_permission_created": False,
    }


def plan_one() -> dict:
    return prepare_project_sweep(
        source_snapshot(one_window(item("message://1"))),
        generated_at=GENERATED_AT,
        expected_canonical_main=MAIN,
    )


def exact_reconciliation(plan: dict, *, dispositions: dict[str, str] | None = None) -> dict:
    parsed = validate_import_package(plan["package"])
    dispositions = dispositions or {row["candidate_id"]: "NEW_DURABLE_SIGNAL" for row in parsed["candidates"]}
    rows = []
    counts = {}
    for row in parsed["candidates"]:
        disposition = dispositions[row["candidate_id"]]
        counts[disposition] = counts.get(disposition, 0) + 1
        rows.append({
            "candidate_id": row["candidate_id"],
            "candidate_digest": row["candidate_digest"],
            "disposition": disposition,
        })
    return {
        "schema_version": "ProjectRetrospectiveReconciliation/v1",
        "sweep_id": plan["sweep_id"],
        "disposition_counts": counts,
        "results": rows,
    }


class CoverageContractTests(unittest.TestCase):
    def test_partial_enumeration_never_claims_complete(self):
        snapshot = source_snapshot(one_window(item("message://1")))
        self.assertFalse(validate_source_snapshot(snapshot)["project_scan_complete"])
        self.assertFalse(plan_one()["project_scan_complete"])

    def test_raw_complete_mapping_cannot_mint_complete(self):
        snapshot = source_snapshot(
            one_window(item("message://1")),
            status="COMPLETE_ENUMERATION_PROVEN",
            omitted=[],
            evidence=["manifest://caller-claims-complete"],
        )
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_TRUSTED_COMPLETE_COVERAGE_VERIFIER_REQUIRED"):
            validate_source_snapshot(snapshot)

    def test_trusted_complete_attestation_binds_manifest(self):
        snapshot = source_snapshot(
            one_window(item("message://1")),
            status="CALLER_SUPPLIED_EXPORT_COMPLETE",
            omitted=[],
            evidence=["manifest://complete-export"],
        )
        normalized = validate_source_snapshot(snapshot, complete_coverage_verifier=trusted_complete_verifier)
        self.assertTrue(normalized["project_scan_complete"])
        self.assertEqual(normalized["coverage_attestation"]["verification_status"], "VERIFIED_COMPLETE_ENUMERATION")
        plan = prepare_project_sweep(
            snapshot,
            generated_at=GENERATED_AT,
            expected_canonical_main=MAIN,
            complete_coverage_verifier=trusted_complete_verifier,
        )
        self.assertTrue(plan["project_scan_complete"])

    def test_complete_attestation_wrong_manifest_fails_closed(self):
        snapshot = source_snapshot(
            one_window(item("message://1")),
            status="COMPLETE_ENUMERATION_PROVEN",
            omitted=[],
            evidence=["manifest://complete"],
        )
        def forged(request):
            result = trusted_complete_verifier(request)
            result["window_manifest_digest"] = "0" * 64
            return result
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_COMPLETE_COVERAGE_ATTESTATION_MISMATCH"):
            validate_source_snapshot(snapshot, complete_coverage_verifier=forged)

    def test_complete_with_omissions_is_forbidden(self):
        snapshot = source_snapshot(
            one_window(item("message://1")),
            status="CALLER_SUPPLIED_EXPORT_COMPLETE",
            omitted=["window://missing"],
            evidence=["manifest://complete-export"],
        )
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_COMPLETE_WITH_OMISSIONS_FORBIDDEN"):
            validate_source_snapshot(snapshot, complete_coverage_verifier=trusted_complete_verifier)


class CrossWindowNormalizationTests(unittest.TestCase):
    def test_same_semantic_candidate_across_five_windows_dedupes_to_one(self):
        windows = [
            {"window_ref": f"window://{index}", "items": [item(f"message://{index}", summary=f"wording {index}")]}
            for index in range(5)
        ]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertEqual(plan["candidate_count"], 1)
        built = plan["package"]["candidates"][0]
        self.assertEqual(len([ref for ref in built["evidence_refs"] if ref.startswith("source-message://")]), 5)

    def test_repeat_run_is_deterministic(self):
        snapshot = source_snapshot(one_window(item("message://1")))
        first = prepare_project_sweep(snapshot, generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        second = prepare_project_sweep(copy.deepcopy(snapshot), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertEqual(first["sweep_id"], second["sweep_id"])
        self.assertEqual(first["package"], second["package"])

    def test_negative_directive_wins_across_same_semantic_group(self):
        shared = identity("shared idea")
        windows = [
            {"window_ref": "window://allow", "items": [item("message://allow", semantic_identity=shared)]},
            {"window_ref": "window://deny", "items": [item("message://deny", semantic_identity=shared, directive="DO_NOT_CAPTURE")]},
            {"window_ref": "window://other", "items": [item("message://other", semantic_identity=identity("other idea"))]},
        ]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        self.assertEqual(plan["candidate_count"], 1)
        self.assertEqual(len(plan["excluded_items"]), 1)
        self.assertEqual(plan["excluded_items"][0]["reason"], "DO_NOT_CAPTURE")
        self.assertNotIn("shared idea", plan["package"]["candidates"][0]["public_safe_summary"])

    def test_non_public_scope_fails_before_r147(self):
        unsafe = item("message://private", payload=candidate(privacy_scope="PRIVATE"))
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_PUBLIC_SAFE_PRIVACY_SCOPE_REQUIRED"):
            prepare_project_sweep(source_snapshot(one_window(unsafe)), generated_at=GENERATED_AT, expected_canonical_main=MAIN)

    def test_private_raw_or_credential_material_fails_closed(self):
        unsafe = item("message://unsafe")
        unsafe["candidate"]["raw_source_body"] = "never persist"
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_PRIVATE_OR_UNSAFE"):
            prepare_project_sweep(source_snapshot(one_window(unsafe)), generated_at=GENERATED_AT, expected_canonical_main=MAIN)

    def test_same_semantic_group_cannot_drift_domain_or_kind(self):
        same = identity("one mechanism")
        windows = [
            {"window_ref": "window://a", "items": [item("message://a", semantic_identity=same)]},
            {"window_ref": "window://b", "items": [item("message://b", semantic_identity=same, payload=candidate(signal_kind="DECISION"))]},
        ]
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_SEMANTIC_GROUP_CORE_DRIFT"):
            prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)

    def test_correction_relation_is_preserved_in_r142_package(self):
        old_identity = identity("old policy")
        new_identity = identity("corrected policy")
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
        relations = [rel for row in plan["package"]["candidates"] for rel in row["candidate_relations"]]
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]["relation"], "SUPERSEDES")


class AuthorityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.plan = plan_one()
        parsed = validate_import_package(self.plan["package"])
        self.row = parsed["candidates"][0]

    def test_r148_delegates_current_disposition_to_r142(self):
        observed = {}
        def fake_reconcile(package, snapshot, **kwargs):
            observed["package"] = package
            observed["kwargs"] = kwargs
            return {
                "package_digest": "pkg",
                "canonical_snapshot_or_main": MAIN,
                "snapshot_digest": "snap",
                "results": [{
                    "candidate_id": self.row["candidate_id"],
                    "candidate_digest": self.row["candidate_digest"],
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

    def test_new_requires_exact_r142_candidate_digest(self):
        bad = {
            "sweep_id": self.plan["sweep_id"],
            "disposition_counts": {"NEW_DURABLE_SIGNAL": 1},
            "results": [{"candidate_id": self.row["candidate_id"], "disposition": "NEW_DURABLE_SIGNAL"}],
        }
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_R142_CANDIDATE_DIGEST_MISMATCH"):
            build_r147_requests(self.plan, bad)
        bad["results"][0]["candidate_digest"] = "UNKNOWN"
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_R142_CANDIDATE_DIGEST_MISMATCH"):
            build_r147_requests(self.plan, bad)

    def test_relation_bearing_new_fails_closed_until_canonical_relation_admission_exists(self):
        old_identity = identity("old relation target")
        new_identity = identity("new correction")
        windows = [
            {"window_ref": "window://old", "items": [item("message://old", semantic_identity=old_identity)]},
            {"window_ref": "window://new", "items": [item(
                "message://new", semantic_identity=new_identity, relations=[{
                    "relation": "SUPERSEDES",
                    "target_semantic_identity": old_identity,
                    "evidence_refs": ["opaque://evidence/supersedes"],
                }]
            )]},
        ]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=MAIN)
        parsed = validate_import_package(plan["package"])
        relation_row = next(row for row in parsed["candidates"] if row["candidate_relations"])
        dispositions = {
            row["candidate_id"]: ("NEW_DURABLE_SIGNAL" if row["candidate_id"] == relation_row["candidate_id"] else "ALREADY_CANONICAL")
            for row in parsed["candidates"]
        }
        reconciliation = exact_reconciliation(plan, dispositions=dispositions)
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_RELATION_CAPABLE_CANONICAL_ADMISSION_REQUIRED"):
            build_r147_requests(plan, reconciliation)

    def test_verified_request_bound_r147_receipt_is_accepted(self):
        reconciliation = exact_reconciliation(self.plan)
        def admit(request):
            return valid_r147_receipt(request)
        receipt = execute_r147_admissions(self.plan, reconciliation, admit_fn=admit)
        self.assertTrue(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(len(receipt["admitted_signal_refs"]), 1)
        self.assertFalse(receipt["automatic_task_created"])
        self.assertFalse(receipt["second_signal_truth_created"])

    def test_label_only_fabricated_r147_receipt_never_becomes_success(self):
        reconciliation = exact_reconciliation(self.plan)
        request = build_r147_requests(self.plan, reconciliation)[0]
        fake = {
            "schema_version": R147_RECEIPT_SCHEMA,
            "attempt_id": request["attempt_id"],
            "status": "ADMITTED",
            "durable_success": True,
            "readback_verification_status": "VERIFIED_SAME_LEDGER",
            "fresh_replay_verification_status": "VERIFIED_FRESH_S0C_REPLAY",
            "task_created": False,
            "route_created": False,
            "work_claim_created": False,
            "write_permission_created": False,
        }
        receipt = finalize_sweep_receipt(self.plan, reconciliation, [fake])
        self.assertFalse(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(receipt["admitted_signal_refs"], [])
        self.assertTrue(receipt["admission_failures"])

    def test_r147_receipt_wrong_attempt_or_domain_fails_closed(self):
        reconciliation = exact_reconciliation(self.plan)
        request = build_r147_requests(self.plan, reconciliation)[0]
        wrong_attempt = valid_r147_receipt(request)
        wrong_attempt["attempt_id"] = "wrong-attempt"
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_R147_RECEIPT_BINDING_INVALID"):
            finalize_sweep_receipt(self.plan, reconciliation, [wrong_attempt])
        wrong_domain = valid_r147_receipt(request)
        wrong_domain["primary_domain"] = "WRONG_DOMAIN"
        receipt = finalize_sweep_receipt(self.plan, reconciliation, [wrong_domain])
        self.assertFalse(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(receipt["admission_failures"][0]["reason"], "R148_R147_RECEIPT_DOMAIN_MISMATCH")

    def test_r147_replay_shape_must_bind_offset_and_event_count(self):
        reconciliation = exact_reconciliation(self.plan)
        request = build_r147_requests(self.plan, reconciliation)[0]
        forged = valid_r147_receipt(request)
        forged["transport_replay_after"]["event_count"] = 99
        receipt = finalize_sweep_receipt(self.plan, reconciliation, [forged])
        self.assertFalse(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(receipt["admission_failures"][0]["reason"], "R148_R147_REPLAY_BINDING_MISMATCH")


if __name__ == "__main__":
    unittest.main()
