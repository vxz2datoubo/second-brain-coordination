from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE = Path(__file__).resolve().parents[1] / "review_pipeline_liveness.py"
spec = importlib.util.spec_from_file_location("review_pipeline_liveness", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

LivenessEvidence = mod.LivenessEvidence
ReviewPipelineLivenessError = mod.ReviewPipelineLivenessError
classify_review_cycle = mod.classify_review_cycle
validate_review_cycle_status = mod.validate_review_cycle_status


class ReviewPipelineLivenessTests(unittest.TestCase):
    def test_pending_ticket_keeps_reviewer_as_next_authority(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=2)
        )
        self.assertEqual(out["pipeline_status"], "ACTIVE")
        self.assertEqual(out["blocker_class"], "NONE")
        self.assertEqual(out["next_authority_role"], "INDEPENDENT_REVIEWER")
        self.assertEqual(out["next_required_action"], "REVIEW_PENDING_EXACT_HEAD_TICKETS")
        self.assertEqual(out["reviewer_mutations"], "NONE")

    def test_empty_queue_detects_accept_not_canonicalized(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(
                project="AI_WORLD_SIMULATION_ENGINE",
                queue_issue=50,
                pending_exact_head_tickets=0,
                accepted_not_canonicalized_ref="PR#96@8651edec",
            )
        )
        self.assertEqual(out["pipeline_status"], "BLOCKED")
        self.assertEqual(out["blocker_class"], "ACCEPTED_NOT_CANONICALIZED")
        self.assertEqual(out["next_authority_role"], "CANONICALIZER")
        self.assertEqual(out["next_required_action"], "CANONICALIZE_ACCEPTED_EXACT_HEAD")

    def test_empty_queue_does_not_claim_idle_when_evidence_incomplete(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(
                project="EUSTIA_AI_FILM",
                queue_issue=15,
                pending_exact_head_tickets=0,
                evidence_complete=False,
            )
        )
        self.assertEqual(out["pipeline_status"], "UNKNOWN")
        self.assertEqual(out["blocker_class"], "UNKNOWN_BLOCKED")
        self.assertEqual(out["next_required_action"], "OBTAIN_MISSING_FRESH_GITHUB_EVIDENCE")

    def test_normal_idle_requires_complete_evidence_and_no_stall(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(
                project="SECOND_BRAIN",
                queue_issue=453,
                pending_exact_head_tickets=0,
                evidence_complete=True,
            )
        )
        self.assertEqual(out["pipeline_status"], "IDLE")
        self.assertEqual(out["blocker_class"], "NORMAL_IDLE")
        self.assertEqual(out["stall_fingerprint"], "NONE")

    def test_stale_request_precedes_downstream_stalls(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(
                project="SECOND_BRAIN",
                queue_issue=453,
                pending_exact_head_tickets=0,
                stale_review_request_ref="PR#1@oldhead",
                accepted_not_canonicalized_ref="PR#2@accepted",
            )
        )
        self.assertEqual(out["blocker_class"], "STALE_REVIEW_REQUEST")

    def test_repeat_stall_suppresses_fake_new_evidence(self) -> None:
        first = classify_review_cycle(
            LivenessEvidence(
                project="AI_WORLD_SIMULATION_ENGINE",
                queue_issue=50,
                pending_exact_head_tickets=0,
                accepted_not_canonicalized_ref="PR#96@8651edec",
            )
        )
        second = classify_review_cycle(
            LivenessEvidence(
                project="AI_WORLD_SIMULATION_ENGINE",
                queue_issue=50,
                pending_exact_head_tickets=0,
                accepted_not_canonicalized_ref="PR#96@8651edec",
                prior_stall_fingerprint=first["stall_fingerprint"],
                prior_stall_repeat_count=first["stall_repeat_count"],
            )
        )
        self.assertIs(first["new_evidence"], True)
        self.assertIs(second["new_evidence"], False)
        self.assertEqual(second["stall_repeat_count"], 2)

    def test_no_privileged_mutation_is_valid_status_invariant(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=0)
        )
        validate_review_cycle_status(out)
        bad = dict(out)
        bad["reviewer_mutations"] = "MERGE"
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "REVIEWER_MUTATION_FORBIDDEN"):
            validate_review_cycle_status(bad)

    def test_invalid_counts_fail_closed(self) -> None:
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "PENDING_TICKETS_INVALID"):
            classify_review_cycle(
                LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=-1)
            )

    def test_implemented_not_queued_routes_to_engineering_without_inventing_review(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(
                project="EUSTIA_AI_FILM",
                queue_issue=15,
                pending_exact_head_tickets=0,
                implemented_not_queued_ref="PR#30@abcdef",
            )
        )
        self.assertEqual(out["blocker_class"], "IMPLEMENTED_NOT_QUEUED")
        self.assertEqual(out["next_authority_role"], "ENGINEERING")
        self.assertEqual(out["next_required_action"], "POST_CANONICAL_REVIEW_REQUEST_FOR_EXACT_HEAD")


if __name__ == "__main__":
    unittest.main()
