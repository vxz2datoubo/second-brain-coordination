from dataclasses import replace
from pathlib import Path
import json
import sys
import unittest

try:
    import jsonschema
except ModuleNotFoundError:
    jsonschema = None
try:
    import yaml
except ModuleNotFoundError:
    yaml = None

SLICE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SLICE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from offline_research.research_integrity import (
    Disposition,
    ExperimentFamilySnapshot,
    IntegrityValidationError,
    LockboxAccessReceipt,
    LockboxPurpose,
    LockboxStatus,
    MethodResult,
    MethodStatus,
    PITEvidence,
    PITStatus,
    R183_AUTH_WITNESS_REF,
    R183_WORK_CLAIM_REF,
    TrialRecord,
    TrialStatus,
    W2_DATASET_REF,
    W2_ENGINE_REF,
    W2_PARAMETER_REF,
    W2_RULE_RUNTIME_REF,
    audit_research_integrity,
    canonical_audit_digest,
    lockbox_configuration_digest,
)

W2_RULE_BLOB = "18311ff30beab7ea97d54c09e44fd6e6ebe921ed"
W2_DATASET_BLOB = "934b95414a41c003392f4dd870f401474affa839"
W2_PARAMETER_BLOB = "7b19b75714701643006ac8d846ee934d764ca224"
W2_ENGINE_BLOB = "7c2ecacd1bebd62fd453d25d6374da5df193446e"
R183_CLAIM_BLOB = "0c210c6daff8352516f1f80d7b5de6aabb5597c3"
R183_AUTH_BLOB = "d75bce3a40835e63b7ef98196a3dbb7c747cfddc"
ACCESSOR_ID = "GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1"
TASK_ID = "GPT-DS10-RESEARCH-INTEGRITY-P0A-R183"
RULE_ID = "SSE_MAIN_NORMAL_PRE_20260706"
FREEZE_AT = "2026-01-07T08:00:00+08:00"
SELECTED_AT = "2026-01-07T09:00:00+08:00"
OPENED_AT = "2026-01-08T09:00:00+08:00"
OBSERVED_AT = "2026-01-09T09:00:00+08:00"


def sha(ch: str) -> str:
    return ch * 64


def lock_config(**overrides):
    base = dict(
        dataset_artifact_ref=W2_DATASET_REF,
        dataset_artifact_blob_sha=W2_DATASET_BLOB,
        code_artifact_ref=W2_ENGINE_REF,
        code_artifact_blob_sha=W2_ENGINE_BLOB,
        parameter_artifact_ref=W2_PARAMETER_REF,
        parameter_artifact_blob_sha=W2_PARAMETER_BLOB,
        cost_artifact_ref=W2_ENGINE_REF,
        cost_artifact_blob_sha=W2_ENGINE_BLOB,
        rule_artifact_ref=W2_RULE_RUNTIME_REF,
        rule_artifact_blob_sha=W2_RULE_BLOB,
        rule_snapshot_id=RULE_ID,
        accessor_claim_ref=R183_WORK_CLAIM_REF,
        accessor_claim_blob_sha=R183_CLAIM_BLOB,
        authorization_witness_ref=R183_AUTH_WITNESS_REF,
        authorization_witness_blob_sha=R183_AUTH_BLOB,
        accessor_id=ACCESSOR_ID,
        task_id=TASK_ID,
        configuration_frozen_at=FREEZE_AT,
    )
    base.update(overrides)
    return base


def default_configuration_digest() -> str:
    return lockbox_configuration_digest(**lock_config())


def trial(trial_id: str, digest: str, status=TrialStatus.SUCCESS, **kwargs):
    return TrialRecord(trial_id, digest, status, **kwargs)


def make_snapshot(**overrides):
    expected = {"t1": sha("1"), "t2": sha("2"), "t3": sha("3")}
    cfg = default_configuration_digest()
    base = dict(
        experiment_family_ref="w4:family:alpha",
        expected_trial_digests=expected,
        trials=(
            trial("t1", sha("1"), TrialStatus.SUCCESS, configuration_digest=cfg),
            trial("t2", sha("2"), TrialStatus.FAILURE),
            trial("t3", sha("3"), TrialStatus.ABORTED),
        ),
        benchmark_ref="benchmark:v1",
        metric_id="NET_RETURN",
        horizon_id="5D",
        search_space_ref="search:v1",
        selection_rule_ref="selection:v1",
        registered_family_digest=sha("0"),
        selection_rule_registered_at="2026-01-01T09:00:00+08:00",
        selected_trial_id="t1",
        selected_at=SELECTED_AT,
        candidate_frozen_at=FREEZE_AT,
        family_frozen_at=FREEZE_AT,
        lockbox_id="lockbox:alpha",
        lockbox_access_history_complete=True,
        declared_trial_count=3,
        required_method_ids=(),
    )
    base.update(overrides)
    temp = ExperimentFamilySnapshot(**base)
    if "registered_family_digest" not in overrides:
        base["registered_family_digest"] = temp.computed_family_digest()
    return ExperimentFamilySnapshot(**base)


def untrusted_pit(**overrides):
    base = dict(
        dataset_lineage=PITStatus.PASS,
        available_at_lineage=PITStatus.PASS,
        rule_version=PITStatus.PASS,
        revision_timing=PITStatus.PASS,
        universe_membership=PITStatus.PASS,
    )
    base.update(overrides)
    return PITEvidence(**base)


def governed_pit(**overrides):
    base = dict(
        dataset_lineage=PITStatus.PASS,
        available_at_lineage=PITStatus.PASS,
        rule_version=PITStatus.PASS,
        revision_timing=PITStatus.PASS,
        universe_membership=PITStatus.PASS,
        authority_source_ref=W2_RULE_RUNTIME_REF,
        authority_source_blob_sha=W2_RULE_BLOB,
        dataset_artifact_ref=W2_DATASET_REF,
        dataset_artifact_blob_sha=W2_DATASET_BLOB,
        dataset_event_id="json-demo-01",
        symbol="600000.SH",
        exchange="SSE",
        board="MAIN",
        security_status="NORMAL",
        trading_day="2026-01-05",
        rule_snapshot_id=RULE_ID,
    )
    base.update(overrides)
    return PITEvidence(**base)


def receipt(**overrides):
    cfg = lock_config()
    base = dict(
        access_id="a1",
        lockbox_id="lockbox:alpha",
        opened_at=OPENED_AT,
        candidate_id="t1",
        candidate_digest=sha("1"),
        purpose=LockboxPurpose.FINAL_EVAL,
        result_digest=sha("a"),
        selection_consumed_after=False,
        configuration_digest=lockbox_configuration_digest(**cfg),
        subsequent_action=None,
        **cfg,
    )
    base.update(overrides)
    return LockboxAccessReceipt(**base)


def bare_receipt(**overrides):
    base = dict(
        access_id="a1",
        lockbox_id="lockbox:alpha",
        opened_at=OPENED_AT,
        candidate_id="t1",
        candidate_digest=sha("1"),
        purpose=LockboxPurpose.FINAL_EVAL,
        result_digest=sha("a"),
        selection_consumed_after=False,
        subsequent_action=None,
    )
    base.update(overrides)
    return LockboxAccessReceipt(**base)


def audit(snapshot=None, *, expected_digest=True, receipts=(), pit=None, methods=(), observed=OBSERVED_AT):
    snapshot = snapshot or make_snapshot()
    comparison_digest = snapshot.snapshot_digest() if expected_digest else None
    return audit_research_integrity(
        snapshot,
        expected_w4_snapshot_digest=comparison_digest,
        lockbox_receipts=receipts,
        pit_evidence=pit or untrusted_pit(),
        method_results=methods,
        observed_at=observed,
    )


class TrialIntegrityTests(unittest.TestCase):
    def test_clean_manifest_uses_observed_count(self):
        result = audit()
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 3)
        self.assertEqual(result["trial_reconciliation"]["failed_trial_count"], 1)
        self.assertEqual(result["trial_reconciliation"]["aborted_trial_count"], 1)

    def test_declared_count_never_shrinks_denominator(self):
        result = audit(make_snapshot(declared_trial_count=1))
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 3)
        self.assertIn("DECLARED_TRIAL_COUNT_MISMATCH", {x["code"] for x in result["nonblocking_findings"]})

    def test_missing_losing_trial_blocks(self):
        snapshot = make_snapshot(trials=(
            trial("t1", sha("1"), configuration_digest=default_configuration_digest()),
            trial("t3", sha("3"), TrialStatus.ABORTED),
        ))
        result = audit(snapshot)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY.value)
        self.assertIn("t2", result["trial_reconciliation"]["missing_trial_ids"])

    def test_same_id_changed_digest_blocks(self):
        snapshot = make_snapshot(trials=(
            trial("t1", sha("9"), configuration_digest=default_configuration_digest()),
            trial("t2", sha("2")), trial("t3", sha("3")),
        ))
        self.assertIn("t1", audit(snapshot)["trial_reconciliation"]["mutated_trial_ids"])

    def test_unregistered_selection_trial_blocks(self):
        snapshot = make_snapshot(trials=make_snapshot().trials + (trial("t4", sha("4")),))
        self.assertIn("t4", audit(snapshot)["trial_reconciliation"]["unexpected_selection_trial_ids"])

    def test_duplicate_trial_id_blocks(self):
        snapshot = make_snapshot(trials=make_snapshot().trials + (trial("t1", sha("1")),))
        self.assertIn("DUPLICATE_TRIAL_ID", {x["code"] for x in audit(snapshot)["blocking_findings"]})

    def test_exact_rerun_does_not_increase_denominator(self):
        rerun = trial("rerun-t2", sha("2"), TrialStatus.FAILURE, selection_affecting=False, rerun_of="t2")
        result = audit(make_snapshot(trials=make_snapshot().trials + (rerun,)))
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 3)
        self.assertEqual(result["trial_reconciliation"]["reproducibility_rerun_count"], 1)

    def test_rerun_changed_digest_blocks(self):
        rerun = trial("rerun-t2", sha("8"), TrialStatus.FAILURE, selection_affecting=False, rerun_of="t2")
        result = audit(make_snapshot(trials=make_snapshot().trials + (rerun,)))
        self.assertIn("INVALID_REPRODUCIBILITY_RERUN", {x["code"] for x in result["blocking_findings"]})

    def test_nonselection_without_rerun_rejected(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            trial("x", sha("1"), selection_affecting=False)
        self.assertEqual(ctx.exception.code, "NON_SELECTION_TRIAL_WITHOUT_RERUN_LINK")


class SelectionAndW4BoundaryTests(unittest.TestCase):
    def test_matching_digest_never_mints_w4_authority(self):
        result = audit(pit=governed_pit())
        self.assertTrue(result["w4_snapshot_digest_matches_expected"])
        self.assertEqual(result["w4_authority_state"], "EXTERNAL_CANONICAL_BINDING_REQUIRED")
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_missing_external_content_digest_abstains(self):
        result = audit(expected_digest=False)
        self.assertFalse(result["w4_snapshot_digest_matches_expected"])
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_family_metric_mutation_requires_retest(self):
        baseline = make_snapshot()
        snapshot = make_snapshot(metric_id="SHARPE", registered_family_digest=baseline.registered_family_digest)
        self.assertEqual(audit(snapshot)["research_integrity_disposition"], Disposition.RETEST_WITH_PREREGISTERED_FAMILY.value)

    def test_benchmark_mutation_requires_retest(self):
        baseline = make_snapshot()
        snapshot = make_snapshot(benchmark_ref="benchmark:v2", registered_family_digest=baseline.registered_family_digest)
        self.assertEqual(audit(snapshot)["research_integrity_disposition"], Disposition.RETEST_WITH_PREREGISTERED_FAMILY.value)

    def test_horizon_mutation_requires_retest(self):
        baseline = make_snapshot()
        snapshot = make_snapshot(horizon_id="20D", registered_family_digest=baseline.registered_family_digest)
        self.assertEqual(audit(snapshot)["research_integrity_disposition"], Disposition.RETEST_WITH_PREREGISTERED_FAMILY.value)

    def test_selection_rule_registered_after_winner_blocks(self):
        snapshot = make_snapshot(selection_rule_registered_at="2026-01-08T09:00:00+08:00")
        self.assertIn("SELECTION_RULE_REGISTERED_AFTER_SELECTION", {x["code"] for x in audit(snapshot)["blocking_findings"]})

    def test_selected_trial_must_be_manifested(self):
        result = audit(make_snapshot(selected_trial_id="ghost"))
        self.assertIn("SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY", {x["code"] for x in result["blocking_findings"]})

    def test_timezone_naive_selection_time_rejected(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            make_snapshot(selected_at="2026-01-07T09:00:00")
        self.assertEqual(ctx.exception.code, "NAIVE_TIMESTAMP")


class PITAuthorityTests(unittest.TestCase):
    def test_caller_all_pass_is_demoted_to_unknown(self):
        result = audit(pit=untrusted_pit())
        for key in ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership"):
            self.assertEqual(result["pit_evidence"][key], PITStatus.UNKNOWN.value)
        self.assertIn("PIT_CALLER_DECLARED_PASS_UNTRUSTED", {x["code"] for x in result["nonblocking_findings"]})
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_governed_w2_binding_derives_all_pass(self):
        result = audit(pit=governed_pit())
        for key in ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership"):
            self.assertEqual(result["pit_evidence"][key], PITStatus.PASS.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_wrong_governed_rule_snapshot_fails(self):
        result = audit(pit=governed_pit(rule_snapshot_id="SSE_MAIN_NORMAL_POST_20260706"))
        self.assertEqual(result["pit_evidence"]["rule_version"], PITStatus.FAIL.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_future_available_at_fails(self):
        snapshot = make_snapshot(
            selected_at="2026-01-05T15:00:00Z",
            candidate_frozen_at="2026-01-05T14:00:00Z",
            family_frozen_at="2026-01-05T14:00:00Z",
        )
        result = audit(snapshot, pit=governed_pit())
        self.assertEqual(result["pit_evidence"]["available_at_lineage"], PITStatus.FAIL.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_minted_rule_blob_cannot_pass(self):
        result = audit(pit=governed_pit(authority_source_blob_sha="0" * 40))
        self.assertNotEqual(result["pit_evidence"]["rule_version"], PITStatus.PASS.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_minted_dataset_blob_cannot_pass(self):
        result = audit(pit=governed_pit(dataset_artifact_blob_sha="0" * 40))
        self.assertNotEqual(result["pit_evidence"]["dataset_lineage"], PITStatus.PASS.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_missing_event_fails_closed(self):
        result = audit(pit=governed_pit(dataset_event_id="missing-event"))
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)
        self.assertIn("PIT_EVENT_NOT_UNIQUE", {x["code"] for x in result["nonblocking_findings"]})

    def test_symbol_identity_mismatch_is_pit_failure(self):
        result = audit(pit=governed_pit(symbol="000001.SZ"))
        self.assertEqual(result["pit_evidence"]["dataset_lineage"], PITStatus.FAIL.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_future_information_finding_blocks(self):
        pit = governed_pit(future_information_findings=("future-known delisting removed from universe",))
        self.assertEqual(audit(pit=pit)["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_caller_negative_finding_remains_conservative(self):
        pit = untrusted_pit(rule_version=PITStatus.FAIL)
        self.assertEqual(audit(pit=pit)["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)


class LockboxProvenanceTests(unittest.TestCase):
    def test_complete_empty_access_history_is_sealed_unused(self):
        self.assertEqual(audit()["lockbox_status"], LockboxStatus.SEALED_UNUSED.value)

    def test_missing_access_history_is_unknown_not_sealed(self):
        result = audit(make_snapshot(lockbox_access_history_complete=False))
        self.assertEqual(result["lockbox_status"], LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN.value)

    def test_bare_caller_receipt_cannot_mint_clean_final_eval(self):
        result = audit(receipts=(bare_receipt(),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN.value)
        self.assertIn("LOCKBOX_CONFIGURATION_PROVENANCE_INCOMPLETE", {x["code"] for x in result["nonblocking_findings"]})

    def test_governed_configuration_and_accessor_can_open_once(self):
        result = audit(receipts=(receipt(),), pit=governed_pit())
        self.assertEqual(result["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_lockbox_opened_twice_is_contaminated(self):
        result = audit(receipts=(receipt(), receipt(access_id="a2", opened_at="2026-01-08T10:00:00+08:00")))
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_LOCKBOX_CONTAMINATION.value)

    def test_tuning_use_is_contaminated(self):
        result = audit(receipts=(receipt(purpose=LockboxPurpose.TUNING),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION.value)

    def test_prompt_optimization_is_contamination(self):
        result = audit(receipts=(receipt(purpose=LockboxPurpose.PROMPT_OPTIMIZATION, subsequent_action="LLM invented replacement factor"),))
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_LOCKBOX_CONTAMINATION.value)

    def test_final_result_reselection_is_contamination(self):
        result = audit(receipts=(receipt(selection_consumed_after=True, subsequent_action="replacement winner selected"),))
        self.assertIn("LOCKBOX_RESULT_CONSUMED_BY_LATER_SELECTION", {x["code"] for x in result["blocking_findings"]})

    def test_wrong_candidate_digest_contaminates(self):
        result = audit(receipts=(receipt(candidate_digest=sha("9")),))
        self.assertIn("LOCKBOX_CANDIDATE_IDENTITY_MISMATCH", {x["code"] for x in result["blocking_findings"]})

    def test_open_before_candidate_freeze_contaminates(self):
        snapshot = make_snapshot(candidate_frozen_at="2026-01-09T09:00:00+08:00")
        result = audit(snapshot, receipts=(receipt(),))
        self.assertIn("LOCKBOX_OPENED_BEFORE_FREEZE", {x["code"] for x in result["blocking_findings"]})

    def test_mutated_code_blob_cannot_remain_clean(self):
        result = audit(receipts=(receipt(code_artifact_blob_sha="0" * 40),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION.value)

    def test_mutated_parameter_blob_cannot_remain_clean(self):
        self.assertNotEqual(audit(receipts=(receipt(parameter_artifact_blob_sha="0" * 40),))["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)

    def test_mutated_cost_blob_cannot_remain_clean(self):
        self.assertNotEqual(audit(receipts=(receipt(cost_artifact_blob_sha="0" * 40),))["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)

    def test_mutated_rule_blob_cannot_remain_clean(self):
        self.assertNotEqual(audit(receipts=(receipt(rule_artifact_blob_sha="0" * 40),))["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)

    def test_mutated_dataset_blob_cannot_remain_clean(self):
        self.assertNotEqual(audit(receipts=(receipt(dataset_artifact_blob_sha="0" * 40),))["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)

    def test_wrong_accessor_identity_cannot_remain_clean(self):
        result = audit(receipts=(receipt(accessor_id="GPT-WORKER-FAKE"),))
        self.assertNotEqual(result["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)
        self.assertIn("LOCKBOX_ACCESSOR_TASK_PROVENANCE_MISMATCH", {x["code"] for x in result["blocking_findings"]})

    def test_wrong_task_identity_cannot_remain_clean(self):
        result = audit(receipts=(receipt(task_id="FAKE-TASK"),))
        self.assertNotEqual(result["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)

    def test_freeze_time_mutation_cannot_remain_clean(self):
        cfg = lock_config(configuration_frozen_at="2026-01-06T08:00:00+08:00")
        result = audit(receipts=(receipt(
            configuration_frozen_at=cfg["configuration_frozen_at"],
            configuration_digest=lockbox_configuration_digest(**cfg),
        ),))
        self.assertIn("LOCKBOX_CONFIGURATION_FREEZE_MISMATCH", {x["code"] for x in result["blocking_findings"]})

    def test_configuration_digest_mutation_cannot_remain_clean(self):
        result = audit(receipts=(receipt(configuration_digest=sha("f")),))
        self.assertNotEqual(result["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)


class MethodStateTests(unittest.TestCase):
    def test_not_run_never_equals_pass(self):
        snapshot = make_snapshot(required_method_ids=("DSR",))
        result = audit(snapshot, methods=(MethodResult("DSR", MethodStatus.NOT_RUN),))
        self.assertEqual(result["research_integrity_disposition"], Disposition.INSUFFICIENT_EVIDENCE.value)

    def test_numerical_failure_never_equals_pass(self):
        snapshot = make_snapshot(required_method_ids=("PBO",))
        result = audit(snapshot, methods=(MethodResult("PBO", MethodStatus.NUMERICAL_FAILURE),))
        self.assertEqual(result["research_integrity_disposition"], Disposition.INSUFFICIENT_EVIDENCE.value)

    def test_missing_required_method_blocks(self):
        snapshot = make_snapshot(required_method_ids=("SPA",))
        self.assertEqual(audit(snapshot)["research_integrity_disposition"], Disposition.INSUFFICIENT_EVIDENCE.value)

    def test_not_applicable_requires_reason(self):
        with self.assertRaises(IntegrityValidationError):
            MethodResult("PBO", MethodStatus.NOT_APPLICABLE)

    def test_not_applicable_with_reason_is_explicit(self):
        snapshot = make_snapshot(required_method_ids=("PBO",))
        result = audit(snapshot, methods=(MethodResult("PBO", MethodStatus.NOT_APPLICABLE, applicability_reason="single strategy"),))
        self.assertEqual(result["method_results"][0]["status"], MethodStatus.NOT_APPLICABLE.value)

    def test_duplicate_method_result_blocks(self):
        snapshot = make_snapshot(required_method_ids=("DSR",))
        result = audit(snapshot, methods=(MethodResult("DSR", MethodStatus.PASS), MethodResult("DSR", MethodStatus.PASS)))
        self.assertIn("DUPLICATE_METHOD_RESULT", {x["code"] for x in result["blocking_findings"]})


class AuthorityAndDeterminismTests(unittest.TestCase):
    def test_all_authority_flags_false(self):
        result = audit()
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertFalse(result["w7_handoff_is_acceptance"])

    def test_p0a_cannot_self_promote_to_w7(self):
        self.assertEqual(audit(pit=governed_pit())["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_audit_digest_is_deterministic(self):
        first, second = audit(), audit()
        self.assertEqual(first["audit_digest"], second["audit_digest"])
        self.assertEqual(canonical_audit_digest(first), first["audit_digest"])

    def test_audit_mutation_breaks_digest(self):
        result = audit()
        result["selection_bias_risk"] = "HIGH"
        with self.assertRaises(IntegrityValidationError) as ctx:
            canonical_audit_digest(result)
        self.assertEqual(ctx.exception.code, "AUDIT_DIGEST_MISMATCH")

    def test_declared_count_boolean_is_rejected(self):
        with self.assertRaises(IntegrityValidationError):
            make_snapshot(declared_trial_count=True)

    def test_invalid_trial_sha_rejected(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            trial("x", "not-a-digest")
        self.assertEqual(ctx.exception.code, "INVALID_SHA256")

    def test_configuration_digest_changes_with_accessor(self):
        a = lockbox_configuration_digest(**lock_config())
        b = lockbox_configuration_digest(**lock_config(accessor_id="DIFFERENT"))
        self.assertNotEqual(a, b)

    def test_configuration_digest_changes_with_cost_identity(self):
        a = lockbox_configuration_digest(**lock_config())
        b = lockbox_configuration_digest(**lock_config(cost_artifact_blob_sha="0" * 40))
        self.assertNotEqual(a, b)


@unittest.skipUnless(jsonschema is not None and yaml is not None, "jsonschema/PyYAML not installed")
class SchemaAndFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_schema = json.loads((SLICE_ROOT / "RESEARCH-INTEGRITY-AUDIT.schema.json").read_text())
        cls.lockbox_schema = json.loads((SLICE_ROOT / "LOCKBOX-ACCESS-RECEIPT.schema.json").read_text())
        cls.fixture = yaml.safe_load((SLICE_ROOT / "fixtures" / "research-integrity.synthetic.yaml").read_text())

    def test_audit_validates_closed_schema(self):
        jsonschema.Draft202012Validator(self.audit_schema, format_checker=jsonschema.FormatChecker()).validate(audit())

    def test_governed_audit_validates_closed_schema(self):
        payload = audit(receipts=(receipt(),), pit=governed_pit())
        jsonschema.Draft202012Validator(self.audit_schema, format_checker=jsonschema.FormatChecker()).validate(payload)

    def test_lockbox_receipt_validates_closed_schema(self):
        jsonschema.Draft202012Validator(self.lockbox_schema, format_checker=jsonschema.FormatChecker()).validate(receipt().as_dict())

    def test_bare_lockbox_receipt_schema_valid_but_not_authoritative(self):
        jsonschema.Draft202012Validator(self.lockbox_schema, format_checker=jsonschema.FormatChecker()).validate(bare_receipt().as_dict())
        self.assertNotEqual(audit(receipts=(bare_receipt(),))["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)

    def test_audit_schema_rejects_trade_authority_true(self):
        payload = audit()
        payload["authority"]["trade_authority"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.audit_schema).validate(payload)

    def test_audit_schema_rejects_unknown_top_level_field(self):
        payload = audit()
        payload["parallel_trial_ledger"] = {}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.audit_schema).validate(payload)

    def test_lockbox_schema_rejects_selection_authority_injection(self):
        payload = receipt().as_dict()
        payload["selection_authority"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.lockbox_schema).validate(payload)

    def test_fixture_preserves_failed_aborted_and_rerun_examples(self):
        cases = self.fixture["cases"]
        statuses = [row["status"] for row in cases["complete_family"]["trials"]]
        self.assertIn("FAILURE", statuses)
        self.assertIn("ABORTED", statuses)
        self.assertTrue(any(row.get("rerun_of") for row in cases["complete_family"]["trials"]))

    def test_fixture_declared_count_is_non_authoritative(self):
        self.assertEqual(self.fixture["cases"]["trial_count_laundering_attempt"]["declared_trial_count"], 1)
        self.assertEqual(len(self.fixture["cases"]["trial_count_laundering_attempt"]["expected_trial_digests"]), 3)

    def test_fixture_documents_new_provenance_attacks(self):
        self.assertIn("caller_minted_all_pass_pit", self.fixture["cases"])
        self.assertIn("governed_w2_pit_revalidation", self.fixture["cases"])
        self.assertIn("lockbox_configuration_mutation", self.fixture["cases"])


if __name__ == "__main__":
    unittest.main()
