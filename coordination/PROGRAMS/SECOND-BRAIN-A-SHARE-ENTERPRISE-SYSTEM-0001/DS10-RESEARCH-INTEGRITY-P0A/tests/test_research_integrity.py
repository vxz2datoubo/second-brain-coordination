from dataclasses import replace
from pathlib import Path
import hashlib
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
    Disposition, ExperimentFamilySnapshot, IntegrityValidationError, LockboxAccessReceipt,
    LockboxPurpose, LockboxStatus, MethodResult, MethodStatus, PITEvidence, PITStatus,
    TrialRecord, TrialStatus, audit_research_integrity, canonical_audit_digest,
)


def sha(ch: str) -> str:
    return ch * 64


def trial(trial_id: str, digest: str, status=TrialStatus.SUCCESS, **kwargs):
    return TrialRecord(trial_id, digest, status, **kwargs)


def make_snapshot(**overrides):
    expected = {"t1": sha("1"), "t2": sha("2"), "t3": sha("3")}
    base = dict(
        experiment_family_ref="w4:family:alpha", expected_trial_digests=expected,
        trials=(trial("t1", sha("1"), TrialStatus.SUCCESS),
                trial("t2", sha("2"), TrialStatus.FAILURE),
                trial("t3", sha("3"), TrialStatus.ABORTED)),
        benchmark_ref="benchmark:v1", metric_id="NET_RETURN", horizon_id="5D",
        search_space_ref="search:v1", selection_rule_ref="selection:v1",
        registered_family_digest=sha("0"), selection_rule_registered_at="2026-01-01T09:00:00+08:00",
        selected_trial_id="t1", selected_at="2026-01-02T09:00:00+08:00",
        candidate_frozen_at="2026-01-02T08:00:00+08:00", family_frozen_at="2026-01-02T08:00:00+08:00",
        lockbox_id="lockbox:alpha", lockbox_access_history_complete=True,
        code_digest=sha("c"), parameter_digest=sha("d"), cost_model_digest=sha("e"),
        rule_snapshot_digest=sha("f"), dataset_snapshot_digest=sha("a"),
        lockbox_accessor_id="worker:ds10-final-eval", lockbox_task_id="task:family-alpha-final-eval",
        declared_trial_count=3, required_method_ids=(),
    )
    base.update(overrides)
    temp = ExperimentFamilySnapshot(**base)
    if "registered_family_digest" not in overrides:
        base["registered_family_digest"] = temp.computed_family_digest()
    return ExperimentFamilySnapshot(**base)


def declared_pass_pit():
    return PITEvidence(PITStatus.PASS, PITStatus.PASS, PITStatus.PASS, PITStatus.PASS, PITStatus.PASS)


def unknown_pit():
    return PITEvidence(PITStatus.UNKNOWN, PITStatus.UNKNOWN, PITStatus.UNKNOWN, PITStatus.UNKNOWN, PITStatus.UNKNOWN)


def receipt(snapshot=None, **overrides):
    s = snapshot or make_snapshot()
    base = dict(
        access_id="a1", lockbox_id=s.lockbox_id, opened_at="2026-01-03T09:00:00+08:00",
        candidate_id=s.selected_trial_id, candidate_digest=s.expected_trial_digests[s.selected_trial_id],
        purpose=LockboxPurpose.FINAL_EVAL, result_digest=sha("b"), selection_consumed_after=False,
        task_id=s.lockbox_task_id, accessor_id=s.lockbox_accessor_id, code_digest=s.code_digest,
        parameter_digest=s.parameter_digest, cost_model_digest=s.cost_model_digest,
        rule_snapshot_digest=s.rule_snapshot_digest, dataset_snapshot_digest=s.dataset_snapshot_digest,
        frozen_configuration_digest=s.lockbox_configuration_digest(), subsequent_action=None,
    )
    base.update(overrides)
    return LockboxAccessReceipt(**base)


def audit(snapshot=None, *, expected_digest=True, receipts=(), pit=None, methods=(),
          observed="2026-01-04T09:00:00+08:00"):
    snapshot = snapshot or make_snapshot()
    comparison_digest = snapshot.snapshot_digest() if expected_digest else None
    return audit_research_integrity(snapshot, expected_w4_snapshot_digest=comparison_digest,
                                    lockbox_receipts=receipts, pit_evidence=pit or declared_pass_pit(),
                                    method_results=methods, observed_at=observed)


class TrialIntegrityTests(unittest.TestCase):
    def test_clean_manifest_uses_observed_count(self):
        result = audit()
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 3)
        self.assertEqual(result["trial_reconciliation"]["failed_trial_count"], 1)
        self.assertEqual(result["trial_reconciliation"]["aborted_trial_count"], 1)

    def test_declared_ten_observed_hundred_never_shrinks_denominator(self):
        expected = {f"t{i}": f"{i % 10}" * 64 for i in range(100)}
        trials = tuple(trial(key, digest) for key, digest in expected.items())
        result = audit(make_snapshot(expected_trial_digests=expected, trials=trials,
                                     declared_trial_count=10, selected_trial_id="t0"))
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 100)
        self.assertIn("DECLARED_TRIAL_COUNT_MISMATCH", {x["code"] for x in result["nonblocking_findings"]})

    def test_missing_losing_trial_blocks(self):
        snapshot = make_snapshot(trials=(trial("t1", sha("1")), trial("t3", sha("3"), TrialStatus.ABORTED)))
        result = audit(snapshot)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY.value)
        self.assertIn("t2", result["trial_reconciliation"]["missing_trial_ids"])

    def test_failed_trial_is_preserved_not_treated_as_bad_history(self):
        self.assertNotIn("MISSING_EXPECTED_TRIAL", {x["code"] for x in audit()["blocking_findings"]})

    def test_same_id_changed_digest_blocks(self):
        snapshot = make_snapshot(trials=(trial("t1", sha("9")), trial("t2", sha("2")), trial("t3", sha("3"))))
        self.assertIn("t1", audit(snapshot)["trial_reconciliation"]["mutated_trial_ids"])

    def test_unregistered_selection_trial_blocks(self):
        snapshot = make_snapshot(trials=make_snapshot().trials + (trial("t4", sha("4")),))
        self.assertIn("t4", audit(snapshot)["trial_reconciliation"]["unexpected_selection_trial_ids"])

    def test_duplicate_trial_id_blocks(self):
        snapshot = make_snapshot(trials=make_snapshot().trials + (trial("t1", sha("1")),))
        self.assertIn("DUPLICATE_TRIAL_ID", {x["code"] for x in audit(snapshot)["blocking_findings"]})

    def test_exact_reproducibility_rerun_does_not_increase_economic_trial_count(self):
        rerun = trial("rerun-t2", sha("2"), TrialStatus.FAILURE, selection_affecting=False, rerun_of="t2")
        result = audit(make_snapshot(trials=make_snapshot().trials + (rerun,)))
        self.assertEqual(result["trial_reconciliation"]["observed_trial_count"], 3)
        self.assertEqual(result["trial_reconciliation"]["reproducibility_rerun_count"], 1)

    def test_rerun_changed_digest_blocks(self):
        rerun = trial("rerun-t2", sha("8"), TrialStatus.FAILURE, selection_affecting=False, rerun_of="t2")
        result = audit(make_snapshot(trials=make_snapshot().trials + (rerun,)))
        self.assertIn("INVALID_REPRODUCIBILITY_RERUN", {x["code"] for x in result["blocking_findings"]})

    def test_nonselection_without_rerun_link_rejected(self):
        with self.assertRaises(IntegrityValidationError):
            trial("x", sha("1"), selection_affecting=False)


class AuthorityAndSelectionTests(unittest.TestCase):
    def test_missing_external_content_digest_abstains(self):
        result = audit(expected_digest=False)
        self.assertFalse(result["w4_snapshot_digest_matches_expected"])
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_matching_digest_never_mints_w4_authority(self):
        result = audit()
        self.assertEqual(result["w4_authority_state"], "EXTERNAL_CANONICAL_BINDING_REQUIRED")
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)
        self.assertIn("W4_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", {x["code"] for x in result["nonblocking_findings"]})

    def test_wrong_external_w4_digest_blocks(self):
        s = make_snapshot()
        result = audit_research_integrity(s, expected_w4_snapshot_digest=sha("9"), lockbox_receipts=(),
                                          pit_evidence=declared_pass_pit(), observed_at="2026-01-04T09:00:00+08:00")
        self.assertIn("W4_SNAPSHOT_DIGEST_MISMATCH", {x["code"] for x in result["blocking_findings"]})

    def _assert_registration_mutation(self, **overrides):
        original = make_snapshot()
        mutated = make_snapshot(registered_family_digest=original.registered_family_digest, **overrides)
        self.assertEqual(audit(mutated)["research_integrity_disposition"], Disposition.RETEST_WITH_PREREGISTERED_FAMILY.value)

    def test_metric_changed_after_registration_requires_retest(self): self._assert_registration_mutation(metric_id="SHARPE")
    def test_benchmark_changed_after_registration_requires_retest(self): self._assert_registration_mutation(benchmark_ref="benchmark:v2")
    def test_horizon_changed_after_registration_requires_retest(self): self._assert_registration_mutation(horizon_id="20D")
    def test_code_changed_after_registration_requires_retest(self): self._assert_registration_mutation(code_digest=sha("8"))
    def test_parameter_changed_after_registration_requires_retest(self): self._assert_registration_mutation(parameter_digest=sha("8"))

    def test_selection_rule_registered_after_winner_blocks(self):
        result = audit(make_snapshot(selection_rule_registered_at="2026-01-03T09:00:00+08:00"))
        self.assertIn("SELECTION_RULE_REGISTERED_AFTER_SELECTION", {x["code"] for x in result["blocking_findings"]})

    def test_selected_trial_must_be_in_manifest(self):
        self.assertIn("SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY",
                      {x["code"] for x in audit(make_snapshot(selected_trial_id="ghost"))["blocking_findings"]})

    def test_timezone_naive_selection_time_rejected(self):
        with self.assertRaises(IntegrityValidationError) as ctx:
            make_snapshot(selected_at="2026-01-02T09:00:00")
        self.assertEqual(ctx.exception.code, "NAIVE_TIMESTAMP")


class LockboxTests(unittest.TestCase):
    def assert_contaminated_with(self, code, **overrides):
        s = make_snapshot()
        result = audit(s, receipts=(receipt(s, **overrides),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION.value)
        self.assertIn(code, {x["code"] for x in result["blocking_findings"]})
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_LOCKBOX_CONTAMINATION.value)

    def test_self_declared_empty_complete_history_is_unknown_not_sealed(self):
        result = audit()
        self.assertEqual(result["lockbox_status"], LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN.value)
        self.assertIn("LOCKBOX_POSITIVE_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A",
                      {x["code"] for x in result["nonblocking_findings"]})

    def test_missing_access_history_is_unknown(self):
        self.assertEqual(audit(make_snapshot(lockbox_access_history_complete=False))["lockbox_status"],
                         LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN.value)

    def test_internally_consistent_final_eval_still_cannot_mint_clean_positive_state(self):
        s = make_snapshot(); result = audit(s, receipts=(receipt(s),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN.value)
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)
        self.assertIn("LOCKBOX_POSITIVE_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A",
                      {x["code"] for x in result["nonblocking_findings"]})

    def test_lockbox_opened_twice_is_contaminated(self):
        s = make_snapshot()
        result = audit(s, receipts=(receipt(s), receipt(s, access_id="a2", opened_at="2026-01-03T10:00:00+08:00")))
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_LOCKBOX_CONTAMINATION.value)

    def test_lockbox_tuning_use_is_contaminated(self):
        s = make_snapshot(); result = audit(s, receipts=(receipt(s, purpose=LockboxPurpose.TUNING),))
        self.assertEqual(result["lockbox_status"], LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION.value)

    def test_prompt_optimization_is_contamination(self):
        s = make_snapshot()
        result = audit(s, receipts=(receipt(s, purpose=LockboxPurpose.PROMPT_OPTIMIZATION,
                                            subsequent_action="LLM replacement factor"),))
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_LOCKBOX_CONTAMINATION.value)

    def test_reselection_consumption_is_contamination(self):
        s = make_snapshot()
        result = audit(s, receipts=(receipt(s, selection_consumed_after=True, subsequent_action="replacement winner"),))
        self.assertIn("LOCKBOX_RESULT_CONSUMED_BY_LATER_SELECTION", {x["code"] for x in result["blocking_findings"]})

    def test_wrong_candidate_digest_contaminates(self): self.assert_contaminated_with("LOCKBOX_CANDIDATE_IDENTITY_MISMATCH", candidate_digest=sha("9"))
    def test_code_identity_mutation_contaminates(self): self.assert_contaminated_with("LOCKBOX_CODE_IDENTITY_MISMATCH", code_digest=sha("9"))
    def test_parameter_identity_mutation_contaminates(self): self.assert_contaminated_with("LOCKBOX_PARAMETER_IDENTITY_MISMATCH", parameter_digest=sha("9"))
    def test_cost_identity_mutation_contaminates(self): self.assert_contaminated_with("LOCKBOX_COST_MODEL_IDENTITY_MISMATCH", cost_model_digest=sha("9"))
    def test_rule_identity_mutation_contaminates(self): self.assert_contaminated_with("LOCKBOX_RULE_SNAPSHOT_IDENTITY_MISMATCH", rule_snapshot_digest=sha("9"))
    def test_dataset_identity_mutation_contaminates(self): self.assert_contaminated_with("LOCKBOX_DATASET_IDENTITY_MISMATCH", dataset_snapshot_digest=sha("9"))
    def test_accessor_identity_mutation_contaminates(self): self.assert_contaminated_with("LOCKBOX_ACCESSOR_IDENTITY_MISMATCH", accessor_id="worker:forged")
    def test_task_identity_mutation_contaminates(self): self.assert_contaminated_with("LOCKBOX_TASK_IDENTITY_MISMATCH", task_id="task:forged")

    def test_recomputed_self_digest_cannot_hide_wrong_code(self):
        s = make_snapshot(); forged = receipt(s, code_digest=sha("9"))
        recomputed = hashlib.sha256(json.dumps(forged.configuration_material(), sort_keys=True,
                                                separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        result = audit(s, receipts=(replace(forged, frozen_configuration_digest=recomputed),))
        codes = {x["code"] for x in result["blocking_findings"]}
        self.assertIn("LOCKBOX_CODE_IDENTITY_MISMATCH", codes)
        self.assertIn("LOCKBOX_FROZEN_CONFIGURATION_MISMATCH", codes)

    def test_open_before_candidate_freeze_contaminates(self):
        s = make_snapshot(candidate_frozen_at="2026-01-05T09:00:00+08:00")
        self.assertIn("LOCKBOX_OPENED_BEFORE_FREEZE", {x["code"] for x in audit(s, receipts=(receipt(s),))["blocking_findings"]})

    def test_candidate_can_freeze_after_selection_but_before_lockbox(self):
        s = make_snapshot(candidate_frozen_at="2026-01-02T12:00:00+08:00")
        self.assertNotIn("LOCKBOX_OPENED_BEFORE_FREEZE", {x["code"] for x in audit(s, receipts=(receipt(s),))["blocking_findings"]})


class PITTests(unittest.TestCase):
    def test_self_authored_all_pass_degrades_to_unknown(self):
        result = audit(pit=declared_pass_pit())
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)
        for key in ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership"):
            self.assertEqual(result["pit_evidence"][key], "UNKNOWN")
        self.assertIn("PIT_POSITIVE_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A",
                      {x["code"] for x in result["nonblocking_findings"]})

    def test_each_declared_pass_gets_dimension_unverified_finding(self):
        codes = {x["code"] for x in audit(pit=declared_pass_pit())["nonblocking_findings"]}
        for dim in ("DATASET_LINEAGE", "AVAILABLE_AT_LINEAGE", "RULE_VERSION", "REVISION_TIMING", "UNIVERSE_MEMBERSHIP"):
            self.assertIn(f"PIT_{dim}_POSITIVE_AUTHORITY_UNVERIFIED", codes)

    def test_revised_financial_report_visible_early_blocks(self):
        pit = PITEvidence(PITStatus.PASS, PITStatus.FAIL, PITStatus.PASS, PITStatus.FAIL, PITStatus.PASS,
                          ("revised report visible early",))
        self.assertEqual(audit(pit=pit)["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_current_rule_applied_backward_blocks(self):
        self.assertEqual(audit(pit=replace(declared_pass_pit(), rule_version=PITStatus.FAIL))["research_integrity_disposition"],
                         Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_future_universe_membership_blocks(self):
        self.assertEqual(audit(pit=replace(declared_pass_pit(), universe_membership=PITStatus.FAIL))["research_integrity_disposition"],
                         Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)

    def test_unknown_available_at_abstains(self):
        self.assertEqual(audit(pit=replace(declared_pass_pit(), available_at_lineage=PITStatus.UNKNOWN))["research_integrity_disposition"],
                         Disposition.ABSTAIN.value)

    def test_future_information_blocks_even_if_declared_pass(self):
        pit = replace(declared_pass_pit(), future_information_findings=("future-known delisting removed",))
        result = audit(pit=pit)
        self.assertEqual(result["research_integrity_disposition"], Disposition.REJECT_POINT_IN_TIME_LEAKAGE.value)
        self.assertIn("FUTURE_INFORMATION_LEAKAGE", {x["code"] for x in result["blocking_findings"]})

    def test_all_unknown_remains_unknown_without_positive_claim(self):
        result = audit(pit=unknown_pit())
        self.assertNotIn("PIT_POSITIVE_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A",
                         {x["code"] for x in result["nonblocking_findings"]})
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)


class MethodStateTests(unittest.TestCase):
    def test_not_run_never_equals_pass(self):
        s = make_snapshot(required_method_ids=("DSR",))
        self.assertEqual(audit(s, methods=(MethodResult("DSR", MethodStatus.NOT_RUN),))["research_integrity_disposition"],
                         Disposition.INSUFFICIENT_EVIDENCE.value)

    def test_numerical_failure_never_equals_pass(self):
        s = make_snapshot(required_method_ids=("PBO",))
        self.assertEqual(audit(s, methods=(MethodResult("PBO", MethodStatus.NUMERICAL_FAILURE),))["research_integrity_disposition"],
                         Disposition.INSUFFICIENT_EVIDENCE.value)

    def test_missing_required_method_blocks(self):
        self.assertEqual(audit(make_snapshot(required_method_ids=("SPA",)))["research_integrity_disposition"],
                         Disposition.INSUFFICIENT_EVIDENCE.value)

    def test_reasoned_not_applicable_clears_method_gate_but_global_abstain_remains(self):
        s = make_snapshot(required_method_ids=("ROMANO_WOLF",))
        result = audit(s, methods=(MethodResult("ROMANO_WOLF", MethodStatus.NOT_APPLICABLE,
                                                applicability_reason="single preregistered hypothesis"),))
        self.assertEqual(result["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_not_applicable_without_reason_rejected(self):
        with self.assertRaises(IntegrityValidationError):
            MethodResult("SPA", MethodStatus.NOT_APPLICABLE)


class AuthorityAndDeterminismTests(unittest.TestCase):
    def test_all_authority_flags_false(self):
        result = audit()
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertFalse(result["w7_handoff_is_acceptance"])

    def test_p0a_cannot_self_promote_to_w7(self):
        self.assertEqual(audit()["research_integrity_disposition"], Disposition.ABSTAIN.value)

    def test_audit_digest_is_deterministic(self):
        first, second = audit(), audit()
        self.assertEqual(first["audit_digest"], second["audit_digest"])
        self.assertEqual(canonical_audit_digest(first), first["audit_digest"])

    def test_audit_mutation_breaks_digest(self):
        result = audit(); result["selection_bias_risk"] = "HIGH"
        with self.assertRaises(IntegrityValidationError):
            canonical_audit_digest(result)

    def test_declared_count_boolean_rejected(self):
        with self.assertRaises(IntegrityValidationError):
            make_snapshot(declared_trial_count=True)

    def test_invalid_sha_rejected(self):
        with self.assertRaises(IntegrityValidationError):
            trial("x", "not-a-digest")


@unittest.skipUnless(jsonschema is not None, "jsonschema not installed")
class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_schema = json.loads((SLICE_ROOT / "RESEARCH-INTEGRITY-AUDIT.schema.json").read_text())
        cls.lockbox_schema = json.loads((SLICE_ROOT / "LOCKBOX-ACCESS-RECEIPT.schema.json").read_text())

    def test_positive_audit_validates_closed_schema(self):
        jsonschema.Draft202012Validator(self.audit_schema, format_checker=jsonschema.FormatChecker()).validate(audit())

    def test_lockbox_receipt_validates_closed_schema(self):
        jsonschema.Draft202012Validator(self.lockbox_schema, format_checker=jsonschema.FormatChecker()).validate(receipt().as_dict())

    def test_audit_schema_rejects_trade_authority_true(self):
        payload = audit(); payload["authority"]["trade_authority"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.audit_schema).validate(payload)

    def test_audit_schema_rejects_unknown_top_level_field(self):
        payload = audit(); payload["parallel_trial_ledger"] = {}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.audit_schema).validate(payload)

    def test_lockbox_schema_rejects_authority_injection(self):
        payload = receipt().as_dict(); payload["selection_authority"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.lockbox_schema).validate(payload)

    def test_lockbox_schema_requires_accessor_task_and_configuration(self):
        payload = receipt().as_dict(); del payload["accessor_id"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.lockbox_schema).validate(payload)


@unittest.skipUnless(yaml is not None, "PyYAML not installed")
class FixtureRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = yaml.safe_load((SLICE_ROOT / "fixtures" / "research-integrity.synthetic.yaml").read_text())

    def test_fixture_preserves_failed_aborted_and_rerun_examples(self):
        cases = self.fixture["cases"]
        statuses = [row["status"] for row in cases["complete_family"]["trials"]]
        self.assertIn("FAILURE", statuses); self.assertIn("ABORTED", statuses)
        self.assertTrue(any(row.get("rerun_of") for row in cases["complete_family"]["trials"]))

    def test_fixture_declared_count_is_non_authoritative(self):
        case = self.fixture["cases"]["trial_count_laundering_attempt"]
        self.assertEqual(case["declared_trial_count"], 1)
        self.assertEqual(len(case["expected_trial_digests"]), 3)


if __name__ == "__main__":
    unittest.main()
