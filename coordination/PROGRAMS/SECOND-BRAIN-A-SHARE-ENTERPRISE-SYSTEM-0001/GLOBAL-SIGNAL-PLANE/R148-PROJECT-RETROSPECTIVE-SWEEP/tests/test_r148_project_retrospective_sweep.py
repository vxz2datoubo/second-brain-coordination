from __future__ import annotations

import copy
import hashlib
import json
import unittest

from global_signal_gateway.retrospective_intake import validate_import_package
from global_signal_plane.ledger import DurableSignalLedger
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
from test_r142_retrospective_intake import (
    MAIN as CURRENT_TEST_HEAD,
    bound_snapshot,
    evidence as r142_evidence,
    exact_current_reads,
    synthetic_governed_provider,
)

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
        "kind": "requirement", "subject": "signal tower", "predicate": "preserve",
        "object": obj, "scope": "chatgpt project", "polarity": polarity,
    }


def candidate(
    summary: str = "Preserve durable Project decisions without duplicate Signals",
    *, signal_kind: str = "REQUIREMENT", domain: str = "SHARED_COGNITIVE_OS",
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
        "assumptions": ["source coverage must be mechanically accounted"],
        "unknowns": ["full product-level Project enumeration may be unavailable"],
        "dependencies": [], "counterevidence_refs": [],
        "proposed_primary_domain": domain, "related_domains": [],
        "privacy_scope": privacy_scope, "historical_status": "HISTORICAL_CANDIDATE",
        "model_tool_version_work_item_refs": {"model_ref": "GPT-5.6-Sol", "work_item_ref": "R148"},
    }


def item(
    message_ref: str, *, semantic_identity: dict | None = None, summary: str | None = None,
    directive: str = "CAPTURE_ALLOWED", payload: dict | None = None,
    relations: list | None = None, semantic_identity_ref: str | None = None,
) -> dict:
    value = {
        "source_message_ref": message_ref,
        "source_time_range": {"start": "2026-08-25T10:00:00+00:00", "end": "2026-08-25T10:01:00+00:00"},
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
    windows: list, *, status: str = "PARTIAL_ENUMERATION",
    omitted: list | None = None, evidence: list | None = None,
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
        "window_refs": refs, "window_count_observed": len(refs),
        "coverage_status": status,
        "coverage_evidence_refs": ["provider://project-context/partial"] if evidence is None else evidence,
        "omitted_or_unavailable_refs": ["window://not-enumerable"] if omitted is None else omitted,
        "source_provider_version": "chatgpt-project-context/v1", "windows": windows,
    }


def one_window(*items_: dict, ref: str = "window://one") -> list:
    return [{"window_ref": ref, "items": list(items_)}]


def trusted_complete_verifier(request: dict) -> dict:
    body = {
        "schema_version": "ProjectCoverageVerificationAttestation/v1",
        "verification_status": "VERIFIED_COMPLETE_ENUMERATION",
        "project_ref": request["project_ref"], "snapshot_ref": request["snapshot_ref"],
        "coverage_status": request["coverage_status"],
        "window_manifest_digest": request["window_manifest_digest"],
        "coverage_evidence_refs": request["coverage_evidence_refs"],
        "verifier_ref": "trusted-provider://project-export-manifest/v1",
    }
    return {**body, "attestation_digest": sha(body)}


def replay(count: int, *, revision: str) -> dict:
    return {
        "schema_version": R147_TRANSPORT_SCHEMA, "event_count": count,
        "input_revision": revision, "history_digest": HEX_A,
        "projection_checksum": HEX_B, "journal_digest": HEX_C,
    }


def valid_r147_receipt(request: dict, *, status: str = "ADMITTED", before_count: int = 0) -> dict:
    after_count = before_count + (1 if status == "ADMITTED" else 0)
    offset = after_count if status == "ADMITTED" else max(1, after_count)
    return {
        "schema_version": R147_RECEIPT_SCHEMA, "attempt_id": request["attempt_id"],
        "status": status, "durable_success": True,
        "signal_id": "signal:r148-test", "event_id": "r136:r148-test",
        "receipt_id": "durable-admission:r148-test", "receipt_offset": offset,
        "input_revision": "revision-after", "primary_domain": request["proposed_primary_domain"],
        "authority_binding_digest": HEX_A, "authority_refs": ["authority://verified/r145"],
        "content_digest": HEX_B, "event_digest": HEX_C,
        "readback_verification_status": "VERIFIED_SAME_LEDGER",
        "fresh_replay_verification_status": "VERIFIED_FRESH_S0C_REPLAY",
        "transport_replay_before": replay(before_count, revision="revision-before"),
        "transport_replay_after": replay(after_count, revision="revision-after"),
        "task_created": False, "route_created": False,
        "work_claim_created": False, "write_permission_created": False,
    }


def plan_one(*, main: str = CURRENT_TEST_HEAD) -> dict:
    return prepare_project_sweep(
        source_snapshot(one_window(item("message://1"))),
        generated_at=GENERATED_AT, expected_canonical_main=main,
    )


def current_reconciliation(plan: dict):
    ledger = DurableSignalLedger()
    parsed = validate_import_package(plan["package"])
    candidate_evidence = {row["candidate_id"]: r142_evidence() for row in parsed["candidates"]}
    try:
        with synthetic_governed_provider() as proof:
            exact = exact_current_reads("r148-current-binding")
            snapshot = bound_snapshot(ledger, proof, exact, candidate_evidence)
            reconciliation = reconcile_project_sweep(
                plan, snapshot, expected_canonical_main=CURRENT_TEST_HEAD,
                live_observation_proof=proof, exact_read_proofs=exact, ledger=ledger,
            )
        return reconciliation
    finally:
        ledger.close()


class CoverageContractTests(unittest.TestCase):
    def test_partial_enumeration_never_claims_complete(self):
        snapshot = source_snapshot(one_window(item("message://1")))
        self.assertFalse(validate_source_snapshot(snapshot)["project_scan_complete"])

    def test_raw_complete_mapping_cannot_mint_complete(self):
        snapshot = source_snapshot(one_window(item("message://1")), status="COMPLETE_ENUMERATION_PROVEN", omitted=[], evidence=["opaque://self-asserted"])
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_TRUSTED_COMPLETE_COVERAGE_VERIFIER_REQUIRED"):
            validate_source_snapshot(snapshot)

    def test_trusted_attestation_binds_complete_manifest(self):
        snapshot = source_snapshot(one_window(item("message://1")), status="CALLER_SUPPLIED_EXPORT_COMPLETE", omitted=[], evidence=["manifest://complete-export"])
        normalized = validate_source_snapshot(snapshot, complete_coverage_verifier=trusted_complete_verifier)
        self.assertTrue(normalized["project_scan_complete"])
        self.assertEqual(normalized["coverage_attestation"]["verification_status"], "VERIFIED_COMPLETE_ENUMERATION")

    def test_wrong_complete_manifest_attestation_fails_closed(self):
        snapshot = source_snapshot(one_window(item("message://1")), status="COMPLETE_ENUMERATION_PROVEN", omitted=[], evidence=["manifest://complete"])
        def forged(request):
            value = trusted_complete_verifier(request); value["window_manifest_digest"] = "0" * 64; return value
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_COMPLETE_COVERAGE_ATTESTATION_MISMATCH"):
            validate_source_snapshot(snapshot, complete_coverage_verifier=forged)

    def test_enumeration_unavailable_produces_zero_candidate_audit_plan(self):
        snapshot = source_snapshot([], status="ENUMERATION_UNAVAILABLE", omitted=["project://enumeration-unavailable"], evidence=[])
        plan = prepare_project_sweep(snapshot, generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)
        self.assertEqual(plan["candidate_count"], 0)
        self.assertTrue(plan["no_capture_work"])
        self.assertIsNone(plan["package"])
        rec = reconcile_project_sweep(plan, {}, expected_canonical_main=CURRENT_TEST_HEAD)
        receipt = finalize_sweep_receipt(plan, rec, [])
        self.assertEqual(receipt["new_durable_signal_count"], 0)
        self.assertFalse(receipt["project_scan_complete"])


class CrossWindowNormalizationTests(unittest.TestCase):
    def test_same_semantic_candidate_across_five_windows_dedupes_to_one(self):
        windows = [{"window_ref": f"window://{i}", "items": [item(f"message://{i}", summary=f"wording {i}")]} for i in range(5)]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)
        self.assertEqual(plan["candidate_count"], 1)
        refs = plan["package"]["candidates"][0]["evidence_refs"]
        self.assertEqual(len([ref for ref in refs if ref.startswith("source-message://")]), 5)

    def test_repeat_run_is_deterministic(self):
        snapshot = source_snapshot(one_window(item("message://1")))
        first = prepare_project_sweep(snapshot, generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)
        second = prepare_project_sweep(copy.deepcopy(snapshot), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)
        self.assertEqual(first["sweep_id"], second["sweep_id"])
        self.assertEqual(first["package"], second["package"])

    def test_negative_directive_wins_across_semantic_group(self):
        shared = identity("shared idea")
        windows = [
            {"window_ref": "window://allow", "items": [item("message://allow", semantic_identity=shared)]},
            {"window_ref": "window://deny", "items": [item("message://deny", semantic_identity=shared, directive="DO_NOT_CAPTURE")]},
            {"window_ref": "window://other", "items": [item("message://other", semantic_identity=identity("other idea"))]},
        ]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)
        self.assertEqual(plan["candidate_count"], 1)
        self.assertEqual(plan["excluded_items"][0]["reason"], "DO_NOT_CAPTURE")

    def test_all_negative_items_produce_auditable_zero_candidate_plan(self):
        windows = one_window(item("message://skip", directive="DISCUSSION_ONLY"))
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)
        self.assertEqual(plan["candidate_count"], 0)
        self.assertEqual(plan["excluded_items"][0]["reason"], "DISCUSSION_ONLY")
        rec = reconcile_project_sweep(plan, {}, expected_canonical_main=CURRENT_TEST_HEAD)
        self.assertEqual(build_r147_requests(plan, rec), [])

    def test_non_public_scope_fails_before_transport(self):
        unsafe = item("message://private", payload=candidate(privacy_scope="PRIVATE"))
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_PUBLIC_SAFE_PRIVACY_SCOPE_REQUIRED"):
            prepare_project_sweep(source_snapshot(one_window(unsafe)), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)

    def test_private_raw_or_credential_material_fails_closed(self):
        unsafe = item("message://unsafe"); unsafe["candidate"]["raw_source_body"] = "never persist"
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_PRIVATE_OR_UNSAFE"):
            prepare_project_sweep(source_snapshot(one_window(unsafe)), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)

    def test_same_semantic_group_cannot_drift_domain_or_kind(self):
        same = identity("one mechanism")
        windows = [
            {"window_ref": "window://a", "items": [item("message://a", semantic_identity=same)]},
            {"window_ref": "window://b", "items": [item("message://b", semantic_identity=same, payload=candidate(signal_kind="DECISION"))]},
        ]
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_SEMANTIC_GROUP_CORE_DRIFT"):
            prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)


class AuthorityBoundaryTests(unittest.TestCase):
    def test_non_new_fake_reconcile_is_sealed_but_not_admission_capable(self):
        plan = plan_one(); parsed = validate_import_package(plan["package"]); row = parsed["candidates"][0]
        def fake(package, snapshot, **kwargs):
            return {
                "package_digest": parsed["package_digest"], "canonical_snapshot_or_main": CURRENT_TEST_HEAD,
                "snapshot_digest": "test-snapshot", "results": [{
                    "candidate_id": row["candidate_id"], "candidate_digest": row["candidate_digest"],
                    "disposition": "ALREADY_SATISFIED",
                }],
            }
        rec = reconcile_project_sweep(plan, {}, expected_canonical_main=CURRENT_TEST_HEAD, reconcile_fn=fake)
        self.assertEqual(build_r147_requests(plan, rec), [])

    def test_plain_or_stale_r142_mapping_cannot_build_transport(self):
        plan = plan_one(); real = current_reconciliation(plan); plain = dict(real)
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_VERIFIED_R142_RECONCILIATION_REQUIRED"):
            build_r147_requests(plan, plain)

    def test_duplicate_r142_decisions_rejected_before_any_admission(self):
        plan = plan_one(); parsed = validate_import_package(plan["package"]); row = parsed["candidates"][0]
        calls = []
        def duplicate(package, snapshot, **kwargs):
            decision = {"candidate_id": row["candidate_id"], "candidate_digest": row["candidate_digest"], "disposition": "NEW_DURABLE_SIGNAL"}
            return {"package_digest": parsed["package_digest"], "canonical_snapshot_or_main": CURRENT_TEST_HEAD, "snapshot_digest": "x", "results": [decision, dict(decision)]}
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_R142_RESULT_BINDING_INVALID"):
            rec = reconcile_project_sweep(plan, {}, expected_canonical_main=CURRENT_TEST_HEAD, reconcile_fn=duplicate)
            execute_r147_admissions(plan, rec, admit_fn=lambda request: calls.append(request))
        self.assertEqual(calls, [])

    def test_current_canonical_r142_reconciliation_builds_one_new_request(self):
        plan = plan_one(); rec = current_reconciliation(plan)
        self.assertEqual(rec["disposition_counts"], {"NEW_DURABLE_SIGNAL": 1})
        requests = build_r147_requests(plan, rec)
        self.assertEqual(len(requests), 1)
        self.assertTrue(any(ref.startswith("r142-reconciliation://sha256/") for ref in requests[0]["evidence_refs"]))

    def test_relation_bearing_new_fails_closed_until_canonical_relation_seam_exists(self):
        old_identity = identity("old relation target"); new_identity = identity("new correction")
        windows = [
            {"window_ref": "window://old", "items": [item("message://old", semantic_identity=old_identity)]},
            {"window_ref": "window://new", "items": [item("message://new", semantic_identity=new_identity, relations=[{
                "relation": "SUPERSEDES", "target_semantic_identity": old_identity,
                "evidence_refs": ["opaque://evidence/supersedes"],
            }])]},
        ]
        plan = prepare_project_sweep(source_snapshot(windows), generated_at=GENERATED_AT, expected_canonical_main=CURRENT_TEST_HEAD)
        rec = current_reconciliation(plan)
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_RELATION_CAPABLE_CANONICAL_ADMISSION_REQUIRED"):
            build_r147_requests(plan, rec)

    def test_verified_request_bound_r147_receipt_is_accepted(self):
        plan = plan_one(); rec = current_reconciliation(plan)
        receipt = execute_r147_admissions(plan, rec, admit_fn=lambda request: valid_r147_receipt(request))
        self.assertTrue(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(len(receipt["admitted_signal_refs"]), 1)
        self.assertFalse(receipt["automatic_task_created"])

    def test_same_reconciliation_capability_cannot_execute_twice(self):
        plan = plan_one(); rec = current_reconciliation(plan)
        execute_r147_admissions(plan, rec, admit_fn=lambda request: valid_r147_receipt(request))
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_RECONCILIATION_ALREADY_USED"):
            execute_r147_admissions(plan, rec, admit_fn=lambda request: valid_r147_receipt(request))

    def test_label_only_fabricated_r147_receipt_never_becomes_success(self):
        plan = plan_one(); rec = current_reconciliation(plan); request = build_r147_requests(plan, rec)[0]
        fake = {
            "schema_version": R147_RECEIPT_SCHEMA, "attempt_id": request["attempt_id"],
            "status": "ADMITTED", "durable_success": True,
            "readback_verification_status": "VERIFIED_SAME_LEDGER",
            "fresh_replay_verification_status": "VERIFIED_FRESH_S0C_REPLAY",
            "task_created": False, "route_created": False, "work_claim_created": False, "write_permission_created": False,
        }
        receipt = finalize_sweep_receipt(plan, rec, [fake])
        self.assertFalse(receipt["durable_admission_complete_for_observed_new"])
        self.assertEqual(receipt["admitted_signal_refs"], [])
        self.assertTrue(receipt["admission_failures"])

    def test_wrong_attempt_domain_or_replay_binding_fails_closed(self):
        plan = plan_one(); rec = current_reconciliation(plan); request = build_r147_requests(plan, rec)[0]
        wrong_attempt = valid_r147_receipt(request); wrong_attempt["attempt_id"] = "wrong"
        with self.assertRaisesRegex(ProjectRetrospectiveSweepError, "R148_R147_RECEIPT_BINDING_INVALID"):
            finalize_sweep_receipt(plan, rec, [wrong_attempt])
        wrong_domain = valid_r147_receipt(request); wrong_domain["primary_domain"] = "WRONG"
        result = finalize_sweep_receipt(plan, rec, [wrong_domain])
        self.assertEqual(result["admission_failures"][0]["reason"], "R148_R147_RECEIPT_DOMAIN_MISMATCH")
        forged = valid_r147_receipt(request); forged["transport_replay_after"]["event_count"] = 99
        result = finalize_sweep_receipt(plan, rec, [forged])
        self.assertEqual(result["admission_failures"][0]["reason"], "R148_R147_REPLAY_BINDING_MISMATCH")


if __name__ == "__main__":
    unittest.main()
