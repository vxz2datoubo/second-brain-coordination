import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "coordination" / "GOVERNANCE" / "unified_execution_canonicalization_extension.py"
spec = importlib.util.spec_from_file_location("unified_execution_canonicalization_extension", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

HEAD = "61ff56f1f1ad9c84e40bb68b3860a10bd1d6befb"
BASE = "e6c5c1e019e652650e9e55c9b4fad2431ffcd8ac"
TREE = "26256afce26dbedcccd4cca7b8214347f3ee21fc"
MERGE = "5967215d1efb2831bcb60e13f483fed88ecbb226"


def evidence(**overrides):
    payload = {
        "repository": "vxz2datoubo/second-brain-coordination",
        "pull_request": 615,
        "exact_head_sha": HEAD,
        "canonicalizer_identity": "CANONICALIZER-B",
        "session_or_workload_identity": "session-b",
        "carrier": "GPT_DIRECT",
        "runtime_mode": "WRITE_CAPABLE",
        "independence_evidence_source": "GOVERNED_SESSION_ATTESTATION",
        "capability_evidence_source": "PROTECTED_CAPABILITY_PROBE",
        "merge_write_capable": True,
        "github_principal": "canonicalizer-bot",
        "allowed_github_actors": ["canonicalizer-bot", "web-flow"],
        "permission_policy_digest": "policy-1",
        "fencing_identity": "fence-1",
        "observed_at": "2026-09-08T21:00:00Z",
    }
    payload.update(overrides)
    return mod._issue_verified_canonicalizer_evidence(payload)


def contributor_set():
    return mod.build_contributor_conflict_set(
        ["AUTHOR-A", "session-a", "author-github"],
        ["EXECUTOR-A"],
        ["ORCHESTRATOR-A"],
    )


def admission(**overrides):
    return mod.admit_canonicalizer(evidence(**overrides), contributor_set())


def request(**overrides):
    payload = {
        "repository": "vxz2datoubo/second-brain-coordination",
        "pull_request": 615,
        "exact_head_sha": HEAD,
        "fresh_main_sha": BASE,
        "observed_base_sha": BASE,
        "candidate_tree_sha": TREE,
        "operation_id": "op-1",
        "attempt_id": "attempt-1",
        "fencing_identity": "fence-1",
        "head_lock_semantics": "HEAD_ONLY_NOT_BASE_CAS",
        "review_required": True,
        "ci_required": True,
    }
    payload.update(overrides)
    return payload


def review(**overrides):
    payload = {
        "reviewed_head": HEAD,
        "verdict": "ACCEPT_WITH_BOUNDED_NONBLOCKING_FINDINGS",
        "review_evidence_ref": "review-1",
    }
    payload.update(overrides)
    return payload


def ci(**overrides):
    payload = {
        "actual_checkout_sha": HEAD,
        "result": "PASS",
        "audit_status": "AUTHORITATIVE",
    }
    payload.update(overrides)
    return payload


def merged_receipt(**overrides):
    payload = {
        "effect_status": "MERGED",
        "operation_id": "op-1",
        "attempt_id": "attempt-1",
        "fencing_identity": "fence-1",
        "merge_request_actor_identity": "CANONICALIZER-B",
        "github_actor": "web-flow",
        "observed_pr_head": HEAD,
        "merge_commit_sha": MERGE,
        "parent_shas": [BASE, HEAD],
        "result_tree_sha": TREE,
    }
    payload.update(overrides)
    return payload


class CanonicalizationEffectIsolationTests(unittest.TestCase):
    def test_core_has_no_github_side_effect_or_merge_authority(self):
        self.assertFalse(mod.CANONICALIZATION_EFFECT_CORE_HAS_GITHUB_SIDE_EFFECTS)
        self.assertFalse(mod.CANONICALIZATION_EFFECT_CORE_CAN_MINT_MERGE_AUTHORITY)

    def test_valid_independent_capable_canonicalizer_admits(self):
        adm = admission()
        self.assertEqual(adm.as_mapping()["admission_status"], "ROLE_AND_CAPABILITY_ADMISSION")

    def test_plain_mapping_is_not_trusted_canonicalizer_evidence(self):
        with self.assertRaisesRegex(Exception, "caller-supplied"):
            mod.admit_canonicalizer({"merge_write_capable": True}, {"AUTHOR-A"})

    def test_caller_claimed_independence_source_is_rejected(self):
        with self.assertRaisesRegex(Exception, "independence evidence source"):
            admission(independence_evidence_source="CALLER_ASSERTED_INDEPENDENT_TRUE")

    def test_caller_claimed_write_capability_source_is_rejected(self):
        with self.assertRaisesRegex(Exception, "capability evidence source"):
            admission(capability_evidence_source="CALLER_ASSERTED_WRITE_CAPABLE_TRUE")

    def test_author_identity_conflict_rejected(self):
        with self.assertRaisesRegex(Exception, "INDEPENDENCE_CONFLICT"):
            admission(canonicalizer_identity="AUTHOR-A")

    def test_new_session_does_not_clear_github_principal_conflict(self):
        with self.assertRaisesRegex(Exception, "INDEPENDENCE_CONFLICT"):
            admission(
                session_or_workload_identity="new-session",
                github_principal="author-github",
                allowed_github_actors=["author-github"],
            )

    def test_read_only_canonicalizer_cannot_be_counted_as_merge_capable(self):
        with self.assertRaisesRegex(Exception, "RUNTIME_MODE_DISALLOWS_MERGE"):
            admission(runtime_mode="PLAN_ONLY")

    def test_write_unavailable_has_no_author_fallback(self):
        with self.assertRaisesRegex(Exception, "CANONICALIZER_WRITE_UNAVAILABLE"):
            admission(merge_write_capable=False)
        recovery = mod.canonicalizer_failure_recovery("CANONICALIZER_WRITE_UNAVAILABLE")
        self.assertIn("SELECT_ANOTHER", recovery)
        self.assertNotIn("AUTHOR_FALLBACK", recovery)

    def test_no_eligible_canonicalizer_persists_without_author_fallback(self):
        recovery = mod.canonicalizer_failure_recovery("NO_ELIGIBLE_CANONICALIZER")
        self.assertEqual(recovery, "PERSIST_WAIT_NO_AUTHOR_OR_ORCHESTRATOR_FALLBACK")

    def test_state_machine_requires_every_gate(self):
        state = "REVIEW_ACCEPTED"
        for event, expected in (
            ("SELECT", "SELECT_ELIGIBLE_CANONICALIZER"),
            ("ADMIT", "ROLE_AND_CAPABILITY_ADMISSION"),
            ("GATES_PASS", "FRESH_CANONICALIZATION_GATES"),
            ("REQUEST_MERGE", "MERGE_REQUESTED"),
            ("EFFECT_READBACK", "REMOTE_EFFECT_RECONCILED"),
            ("RECORD", "CANONICALIZATION_RECORDED"),
        ):
            state = mod.canonicalization_state_transition(state, event)
            self.assertEqual(state, expected)

    def test_state_machine_rejects_skip(self):
        with self.assertRaisesRegex(Exception, "illegal transition"):
            mod.canonicalization_state_transition("REVIEW_ACCEPTED", "REQUEST_MERGE")

    def test_pre_merge_gate_accepts_exact_bound_evidence(self):
        gate = mod.validate_pre_merge_effect_gate(request(), admission(), review(), ci())
        self.assertEqual(gate["state"], "FRESH_CANONICALIZATION_GATES")

    def test_head_drift_rejected(self):
        with self.assertRaisesRegex(Exception, "HEAD_DRIFT"):
            mod.validate_pre_merge_effect_gate(
                request(exact_head_sha="a" * 40), admission(), review(), ci()
            )

    def test_base_drift_rejected(self):
        with self.assertRaisesRegex(Exception, "BASE_OR_POLICY_DRIFT"):
            mod.validate_pre_merge_effect_gate(
                request(fresh_main_sha="a" * 40), admission(), review(), ci()
            )

    def test_review_mismatch_rejected(self):
        with self.assertRaisesRegex(Exception, "CI_OR_REVIEW_IDENTITY_MISMATCH"):
            mod.validate_pre_merge_effect_gate(
                request(), admission(), review(reviewed_head="a" * 40), ci()
            )

    def test_ci_checkout_mismatch_rejected(self):
        with self.assertRaisesRegex(Exception, "CI_OR_REVIEW_IDENTITY_MISMATCH"):
            mod.validate_pre_merge_effect_gate(
                request(), admission(), review(), ci(actual_checkout_sha="a" * 40)
            )

    def test_merge_api_head_lock_cannot_be_claimed_as_atomic_base_cas(self):
        with self.assertRaisesRegex(Exception, r"base\+head atomic CAS"):
            mod.validate_pre_merge_effect_gate(
                request(head_lock_semantics="ATOMIC_BASE_AND_HEAD_CAS"),
                admission(),
                review(),
                ci(),
            )

    def test_unknown_effect_requires_readback_before_retry(self):
        gate = mod.validate_pre_merge_effect_gate(request(), admission(), review(), ci())
        receipt = merged_receipt(effect_status="UNKNOWN")
        outcome = mod.reconcile_merge_effect(gate, admission(), receipt)
        self.assertEqual(outcome["state"], "MERGE_EFFECT_UNKNOWN")
        self.assertFalse(outcome["retry_allowed"])

    def test_stale_attempt_or_fence_is_rejected(self):
        adm = admission()
        gate = mod.validate_pre_merge_effect_gate(request(), adm, review(), ci())
        with self.assertRaisesRegex(Exception, "LEASE_OR_FENCING_INVALID"):
            mod.reconcile_merge_effect(
                gate, adm, merged_receipt(attempt_id="late-old-attempt")
            )

    def test_merge_request_actor_mismatch_rejected(self):
        adm = admission()
        gate = mod.validate_pre_merge_effect_gate(request(), adm, review(), ci())
        with self.assertRaisesRegex(Exception, "MERGE_ACTOR_MISMATCH"):
            mod.reconcile_merge_effect(
                gate, adm, merged_receipt(merge_request_actor_identity="AUTHOR-A")
            )

    def test_github_actor_mismatch_rejected(self):
        adm = admission()
        gate = mod.validate_pre_merge_effect_gate(request(), adm, review(), ci())
        with self.assertRaisesRegex(Exception, "MERGE_ACTOR_MISMATCH"):
            mod.reconcile_merge_effect(
                gate, adm, merged_receipt(github_actor="author-github")
            )

    def test_unexpected_base_or_tree_rejected(self):
        adm = admission()
        gate = mod.validate_pre_merge_effect_gate(request(), adm, review(), ci())
        with self.assertRaisesRegex(Exception, "MERGED_WITH_UNEXPECTED_BASE_OR_TREE"):
            mod.reconcile_merge_effect(
                gate, adm, merged_receipt(parent_shas=["a" * 40, HEAD])
            )
        with self.assertRaisesRegex(Exception, "MERGED_WITH_UNEXPECTED_BASE_OR_TREE"):
            mod.reconcile_merge_effect(
                gate, adm, merged_receipt(result_tree_sha="b" * 40)
            )

    def test_valid_effect_receipt_records_distinct_actors(self):
        adm = admission()
        gate = mod.validate_pre_merge_effect_gate(request(), adm, review(), ci())
        result = mod.reconcile_merge_effect(gate, adm, merged_receipt())
        self.assertEqual(result["state"], "CANONICALIZATION_RECORDED")
        self.assertEqual(result["merge_request_actor_identity"], "CANONICALIZER-B")
        self.assertEqual(result["github_actor"], "web-flow")

    def test_pr615_adjudication_is_prospective_and_non_retroactive(self):
        record = {
            "schema": "PR615_POST_MERGE_ADJUDICATION/v1",
            "incident_ref": 618,
            "original_pr": 615,
            "accepted_exact_head": HEAD,
            "pre_merge_main": BASE,
            "original_merge_commit": MERGE,
            "accepted_candidate_tree": TREE,
            "merged_tree": TREE,
            "historical_merge_procedure": "GOVERNANCE_DEFECT_SELF_MERGE",
            "original_merge_authorization_retroactively_granted": False,
            "content_disposition": "RETAIN_BY_NEW_GOVERNED_DECISION",
            "effective_from": "ON_LAWFUL_CANONICAL_PUBLICATION_OF_THIS_ADJUDICATION",
            "r187_reactivation_authorized": False,
            "rollback_default": False,
            "original_canonicalization_receipt_clean_authority": False,
        }
        mod.validate_pr615_prospective_adjudication(record)
        bad = dict(record)
        bad["original_merge_authorization_retroactively_granted"] = True
        with self.assertRaisesRegex(Exception, "retroactively"):
            mod.validate_pr615_prospective_adjudication(bad)


if __name__ == "__main__":
    unittest.main()
