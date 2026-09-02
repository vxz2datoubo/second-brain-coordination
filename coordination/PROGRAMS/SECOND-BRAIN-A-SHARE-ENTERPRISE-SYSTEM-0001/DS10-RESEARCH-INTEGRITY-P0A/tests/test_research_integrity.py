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
    TrialRecord,
    TrialStatus,
    audit_research_integrity,
    canonical_audit_digest,
)


def sha(ch: str) -> str:
    return ch * 64


def trial(trial_id: str, digest: str, status=TrialStatus.SUCCESS, **kwargs):
    return TrialRecord(trial_id, digest, status, **kwargs)


def make_snapshot(**overrides):
    expected = {"t1": sha("1"), "t2": sha("2"), "t3": sha("3")}
    base = dict(
        experiment_family_ref="w4:family:alpha",
        expected_trial_digests=expected,
        trials=(
            trial("t1", sha("1"), TrialStatus.SUCCESS),
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
        selected_at="2026-01-02T09:00:00+08:00",
        candidate_frozen_at="2026-01-02T08:00:00+08:00",
        family_frozen_at="2026-01-02T08:00:00+08:00",
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


def clean_pit():
    return PITEvidence(PITStatus.PASS, PITStatus.PASS, PITStatus.PASS, PITStatus.PASS, PITStatus.PASS)


def receipt(**overrides):
    base = dict(
        access_id="a1",
        lockbox_id="lockbox:alpha",
        opened_at="2026-01-03T09:00:00+08:00",
        candidate_id="t1",
        candidate_digest=sha("1"),
        purpose=LockboxPurpose.FINAL_EVAL,
        result_digest=sha("a"),
        selection_consumed_after=False,
        subsequent_action=None,
    )
    base.update(overrides)
    return LockboxAccessReceipt(**base)


def audit(snapshot=None, *, expected_digest=True, receipts=(), pit=None, methods=(), observed="2026-01-04T09:00:00+08:00"):
    snapshot = snapshot or make_snapshot()
    comparison_digest = snapshot.snapshot_digest() if expected_digest else None
    return audit_research_integrity(
        snapshot,
        expected_w4_snapshot_digest=comparison_digest,
        lockbox_receipts=receipts,
        pit_evidence=pit or clean_pit(),
        method_results=methods,
        observed_at=observed,
    )


class TrialIntegrityTests(unittest.TestCase):
    def test_clean_manifest_uses_observed_count(self):
        result = audit()
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 3)
        self.assertEqual(result["trial_reconciliation"]["failed_trial_count"], 1)
        self.assertEqual(result["trial_reconciliation"]["aborted_trial_count"], 1)

    def test_declared_ten_observed_hundred_never_shrinks_denominator(self):
        expected = {f"t{i}": f"{i % 10}" * 64 for i in range(100)}
        trials = tuple(trial(key, digest) for key, digest in expected.items())
        snapshot = make_snapshot(expected_trial_digests=expected, trials=trials, declared_trial_count=10, selected_trial_id="t0")
        result = audit(snapshot)
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 100)
        codes = {x["code"] for x in result["nonblocking_findings"]}
        self.assertIn("DECLARED_TRIAL_COUNT_MISMATCH", codes)

    def test_missing_losing_trial_blocks(self):
        snapshot = make_snapshot(trials=(trial("t1", sha("1")), trial("t3", sha("3"), TrialStatus.ABORTED)))
        result = audit(snapshot)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY.value)
        self.assertIn("t2", result["trial_reconciliation"]["missing_trial_ids"])

    def test_failed_trial_is_preserved_not_treated_as_bad_history(self):
        result = audit()
        self.assertNotIn("MISSING_EXPECTED_TRIAL", {x["code"] for x in result["blocking_findings"]})

    def test_same_id_changed_digest_blocks(self):
        snapshot = make_snapshot(trials=(trial("t1", sha("9")), trial("t2", sha("2")), trial("t3", sha("3"))))
        result = audit(snapshot)
        self.assertIn("t1", result["trial_reconciliation"]["mutated_trial_ids"])

    def test_unregistered_selection_trial_blocks(self):
        snapshot = make_snapshot(trials=make_snapshot().trials + (trial("t4", sha("4")),))
        result = audit(snapshot)
        self.assertIn("t4", result["trial_reconciliation"]["unexpected_selection_trial_ids"])

    def test_duplicate_trial_id_blocks(self):
        snapshot = make_snapshot(trials=make_snapshot().trials + (trial("t1", sha("1")),))
        result = audit(snapshot)
        self.assertIn("DUPLICATE_TRIAL_ID", {x["code"] for x in result["blocking_findings"]})

    def test_exact_reproducibility_rerun_does_not_increase_economic_trial_count(self):
        rerun = trial("rerun-t2", sha("2"), TrialStatus.FAILURE, selection_affecting=False, rerun_of="t2")
        snapshot = make_snapshot(trials=make_snapshot().trials + (rerun,))
        result = audit(snapshot)
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 3)
        self.assertEqual(result["trial_reconciliation"]["reproducibility_rerun_count"], 1)

    def test_rerun_changed_digest_blocks(self):
        rerun = trial("rerun-t2", sha("8"), TrialStatus.FAILURE, selection_affecting=False, rerun_of="t2")
        result = audit(make_snapshot(trials=make_snapshot().trials + (rerun,)))
        self.assertIn("INVALID_REPRODUCIBILITY_RERUN", {x["code"] for x in result["blocking_findings"]})

    def test_nonselection_without_rerun_link_rejected_at_contract(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            trial("x", sha("1"), selection_affecting=False)
        self.assertEqual(ctx.exception.code, "NON_SELECTION_TRIAL_WITHOUT_RERUN_LINK")


class AuthorityAndSelectionTests(unittest.TestCase):
    def test_missing_external_content_digest_abstains(self):
        result = audit(expected_digest=False)
        self.assertFalse(result["w4_snapshot_digest_matches_expected"])
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_even_matching_digest_does_not_mint_w4_authority(self):
        result = audit()
        self.assertTrue(result["w4_snapshot_digest_matches_expected"])
        self.assertEqual(result["w4_authority_state"], "EXTERNAL_CANONICAL_BINDING_REQUIRED")
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)
        self.assertIn("W4_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", {x["code"] for x in result["nonblocking_findings"]})

    def test_wrong_external_w4_digest_blocks(self):
        snapshot = make_snapshot()
        result = audit_research_integrity(
            snapshot,
            expected_w4_snapshot_digest=sha("f"),
            lockbox_receipts=(),
            pit_evidence=clean_pit(),
            observed_at="2026-01-04T09:00:00+08:00",
        )
        self.assertIn("W4_SNAPSHOT_DIGEST_MISMATCH", {x["code"] for x in result["blocking_findings"]})
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_family_narrowed_after_registration_requires_retest(self):
        snapshot = make_snapshot(metric_id="SHARPE", registered_family_digest=make_snapshot().registered_family_digest)
        result = audit(snapshot)
        self.assertEqual(result["research_integrity_disposition"], Disposition.RETEST_WITH_PREREGISTERED_FAMILY.value)

    def test_benchmark_changed_after_registration_requires_retest(self):
        snapshot = make_snapshot(benchmark_ref="benchmark:v2", registered_family_digest=make_snapshot().registered_family_digest)
        self.assertEqual(audit(snapshot)["research_integrity_disposition"], Disposition.RETEST_WITH_PREREGISTERED_FAMILY.value)

    def test_horizon_changed_after_registration_requires_retest(self):
        snapshot = make_snapshot(horizon_id="20D", registered_family_digest=make_snapshot().registered_family_digest)
        self.assertEqual(audit(snapshot)["research_integrity_disposition"], Disposition.RETEST_WITH_PREREGISTERED_FAMILY.value)

    def test_selection_rule_registered_after_winner_blocks(self):
        snapshot = make_snapshot(selection_rule_registered_at="2026-01-03T09:00:00+08:00")
        self.assertIn("SELECTION_RULE_REGISTERED_AFTER_SELECTION", {x["code"] for x in audit(snapshot)["blocking_findings"]})

    def test_selected_trial_must_be_in_manifest(self):
        snapshot = make_snapshot(selected_trial_id="ghost")
        self.assertIn("SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY", {x["code"] for x in audit(snapshot)["blocking_findings"]})

    def test_timezone_naive_selection_time_rejected(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            make_snapshot(selected_at="2026-01-02T09:00:00")
        self.assertEqual(ctx.exception.code, "NAIVE_TIMESTAMP")


class LockboxTests(unittest.TestCase):
    def test_complete_empty_access_history_is_sealed_unused(self):
        result = audit()
        self.assertEqual(result["lockbox_status"], LockboxStatus.SEALED_UNUSED.value)

    def test_missing_access_history_is_unknown_not_sealed(self):
        result = audit(make_snapshot(lockbox_access_history_complete=False))
        self.assertEqual(result["lockbox_status"], LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_one_final_eval_after_freeze_is_eligible_state(self):
        result = audit(receipts=(receipt(),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.OPENED_ONCE_FINAL_EVAL.value)
        self.assertEqual(result["adjusted_evidence_grade"], "UNKNOWN")
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_lockbox_opened_twice_is_contaminated(self):
        result = audit(receipts=(receipt(), receipt(access_id="a2", opened_at="2026-01-03T10:00:00+08:00")))
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_LOCKBOX_CONTAMINATION.value)

    def test_lockbox_tuning_use_is_contaminated(self):
        result = audit(receipts=(receipt(purpose=LockboxPurpose.TUNING),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION.value)

    def test_llm_prompt_optimization_after_lockbox_is_contamination(self):
        result = audit(receipts=(receipt(purpose=LockboxPurpose.PROMPT_OPTIMIZATION, subsequent_action="LLM invented replacement factor"),))
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_LOCKBOX_CONTAMINATION.value)

    def test_final_result_consumed_by_reselection_is_contamination(self):
        result = audit(receipts=(receipt(selection_consumed_after=True, subsequent_action="replacement winner selected"),))
        self.assertIn("LOCKBOX_RESULT_CONSUMED_BY_LATER_SELECTION", {x["code"] for x in result["blocking_findings"]})

    def test_wrong_candidate_digest_contaminates(self):
        result = audit(receipts=(receipt(candidate_digest=sha("9")),))
        self.assertIn("LOCKBOX_CANDIDATE_IDENTITY_MISMATCH", {x["code"] for x in result["blocking_findings"]})

    def test_open_before_candidate_freeze_contaminates(self):
        snapshot = make_snapshot(candidate_frozen_at="2026-01-05T09:00:00+08:00")
        result = audit(snapshot, receipts=(receipt(),))
        self.assertIn("LOCKBOX_OPENED_BEFORE_FREEZE", {x["code"] for x in result["blocking_findings"]})

    def test_candidate_can_be_frozen_after_selection_but_before_lockbox(self):
        snapshot = make_snapshot(candidate_frozen_at="2026-01-02T12:00:00+08:00")
        result = audit(snapshot, receipts=(receipt(),))
        self.assertNotIn("LOCKBOX_OPENED_BEFORE_FREEZE", {x["code"] for x in result["blocking_findings"]})


class PITTests(unittest.TestCase):
    def test_revised_financial_report_visible_early_blocks(self):
        pit = PITEvidence(PITStatus.PASS, PITStatus.FAIL, PITStatus.PASS, PITStatus.FAIL, PITStatus.PASS,
                          ("revised financial report visible before revised available_at",))
        result = audit(pit=pit)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_current_rule_applied_backward_blocks(self):
        pit = replace(clean_pit(), rule_version=PITStatus.FAIL)
        self.assertEqual(audit(pit=pit)["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_future_universe_membership_blocks(self):
        pit = replace(clean_pit(), universe_membership=PITStatus.FAIL)
        self.assertEqual(audit(pit=pit)["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_unknown_available_at_abstains(self):
        pit = replace(clean_pit(), available_at_lineage=PITStatus.UNKNOWN)
        self.assertEqual(audit(pit=pit)["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_future_information_finding_blocks_even_when_flags_pass(self):
        pit = replace(clean_pit(), future_information_findings=("future-known delisting removed from universe",))
        self.assertEqual(audit(pit=pit)["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)


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

    def test_reasoned_not_applicable_can_clear_method_gate(self):
        snapshot = make_snapshot(required_method_ids=("ROMANO_WOLF",))
        result = audit(snapshot, methods=(MethodResult("ROMANO_WOLF", MethodStatus.NOT_APPLICABLE, applicability_reason="single pre-registered hypothesis"),))
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_not_applicable_without_reason_rejected(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            MethodResult("SPA", MethodStatus.NOT_APPLICABLE)
        self.assertEqual(ctx.exception.code, "NOT_APPLICABLE_REQUIRES_REASON")


class AuthorityAndDeterminismTests(unittest.TestCase):
    def test_all_authority_flags_false(self):
        result = audit()
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertFalse(result["w7_handoff_is_acceptance"])

    def test_p0a_clear_state_cannot_self_promote_to_w7_eligible(self):
        result = audit()
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)
        self.assertFalse(result["w7_handoff_is_acceptance"])

    def test_audit_digest_is_deterministic(self):
        first = audit()
        second = audit()
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

    def test_invalid_sha_rejected(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            trial("x", "not-a-digest")
        self.assertEqual(ctx.exception.code, "INVALID_SHA256")


@unittest.skipUnless(jsonschema is not None and yaml is not None, "jsonschema/PyYAML not installed")
class SchemaAndFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_schema = json.loads((SLICE_ROOT / "RESEARCH-INTEGRITY-AUDIT.schema.json").read_text())
        cls.lockbox_schema = json.loads((SLICE_ROOT / "LOCKBOX-ACCESS-RECEIPT.schema.json").read_text())
        cls.fixture = yaml.safe_load((SLICE_ROOT / "fixtures" / "research-integrity.synthetic.yaml").read_text())

    def test_positive_audit_validates_closed_schema(self):
        jsonschema.Draft202012Validator(self.audit_schema, format_checker=jsonschema.FormatChecker()).validate(audit())

    def test_lockbox_receipt_validates_closed_schema(self):
        jsonschema.Draft202012Validator(self.lockbox_schema, format_checker=jsonschema.FormatChecker()).validate(receipt().as_dict())

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
        self.assertIn("complete_family", cases)
        statuses = [row["status"] for row in cases["complete_family"]["trials"]]
        self.assertIn("FAILURE", statuses)
        self.assertIn("ABORTED", statuses)
        self.assertTrue(any(row.get("rerun_of") for row in cases["complete_family"]["trials"]))

    def test_fixture_declared_count_is_non_authoritative(self):
        self.assertEqual(self.fixture["cases"]["trial_count_laundering_attempt"]["declared_trial_count"], 1)
        self.assertEqual(len(self.fixture["cases"]["trial_count_laundering_attempt"]["expected_trial_digests"]), 3)


if __name__ == "__main__":
    unittest.main()
