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
        evidence = LivenessEvidence(
            project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=2
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["pipeline_status"], "ACTIVE")
        self.assertEqual(out["blocker_class"], "NONE")
        self.assertEqual(out["next_authority_role"], "INDEPENDENT_REVIEWER")
        self.assertEqual(out["next_required_action"], "REVIEW_PENDING_EXACT_HEAD_TICKETS")
        self.assertEqual(out["reviewer_mutations"], "NONE")
        validate_review_cycle_status(out, evidence)

    def test_empty_queue_detects_accept_not_canonicalized(self) -> None:
        evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["pipeline_status"], "BLOCKED")
        self.assertEqual(out["blocker_class"], "ACCEPTED_NOT_CANONICALIZED")
        self.assertEqual(out["next_authority_role"], "CANONICALIZER")
        self.assertEqual(out["next_required_action"], "CANONICALIZE_ACCEPTED_EXACT_HEAD")
        validate_review_cycle_status(out, evidence)

    def test_empty_queue_does_not_claim_idle_when_evidence_incomplete(self) -> None:
        evidence = LivenessEvidence(
            project="EUSTIA_AI_FILM",
            queue_issue=15,
            pending_exact_head_tickets=0,
            evidence_complete=False,
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["pipeline_status"], "UNKNOWN")
        self.assertEqual(out["blocker_class"], "UNKNOWN_BLOCKED")
        self.assertEqual(out["next_required_action"], "OBTAIN_MISSING_FRESH_GITHUB_EVIDENCE")
        validate_review_cycle_status(out, evidence)

    def test_normal_idle_requires_complete_evidence_and_no_stall(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            queue_issue=453,
            pending_exact_head_tickets=0,
            evidence_complete=True,
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["pipeline_status"], "IDLE")
        self.assertEqual(out["blocker_class"], "NORMAL_IDLE")
        self.assertEqual(out["stall_fingerprint"], "NONE")
        validate_review_cycle_status(out, evidence)

    def test_stale_request_precedes_downstream_stalls(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            queue_issue=453,
            pending_exact_head_tickets=0,
            stale_review_request_ref="PR#1@oldhead",
            accepted_not_canonicalized_ref="PR#2@accepted",
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["blocker_class"], "STALE_REVIEW_REQUEST")
        validate_review_cycle_status(out, evidence)

    def test_repeat_stall_suppresses_fake_new_evidence(self) -> None:
        first_evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
        first = classify_review_cycle(first_evidence)
        second_evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
            prior_stall_fingerprint=first["stall_fingerprint"],
            prior_stall_repeat_count=first["stall_repeat_count"],
        )
        second = classify_review_cycle(second_evidence)
        self.assertIs(first["new_evidence"], True)
        self.assertIs(second["new_evidence"], False)
        self.assertEqual(second["stall_repeat_count"], 2)
        validate_review_cycle_status(second, second_evidence)

    def test_no_privileged_mutation_is_valid_status_invariant(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=0
        )
        out = classify_review_cycle(evidence)
        validate_review_cycle_status(out, evidence)
        bad = dict(out)
        bad["reviewer_mutations"] = "MERGE"
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "REVIEWER_MUTATION_FORBIDDEN"):
            validate_review_cycle_status(bad, evidence)

    def test_invalid_counts_fail_closed(self) -> None:
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "PENDING_TICKETS_INVALID"):
            classify_review_cycle(
                LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=-1)
            )

    def test_implemented_not_queued_routes_to_engineering_without_inventing_review(self) -> None:
        evidence = LivenessEvidence(
            project="EUSTIA_AI_FILM",
            queue_issue=15,
            pending_exact_head_tickets=0,
            implemented_not_queued_ref="PR#30@abcdef",
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["blocker_class"], "IMPLEMENTED_NOT_QUEUED")
        self.assertEqual(out["next_authority_role"], "ENGINEERING")
        self.assertEqual(out["next_required_action"], "POST_CANONICAL_REVIEW_REQUEST_FOR_EXACT_HEAD")
        validate_review_cycle_status(out, evidence)

    def test_validation_requires_authoritative_liveness_evidence(self) -> None:
        out = classify_review_cycle(
            LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=0)
        )
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "LIVENESS_EVIDENCE_REQUIRED"):
            validate_review_cycle_status(out)

    def test_adversarial_pending_ticket_cannot_be_laundered_to_idle(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=1
        )
        bad = classify_review_cycle(evidence)
        bad.update(
            pipeline_status="IDLE",
            blocker_class="NORMAL_IDLE",
            next_authority_role="NONE",
            next_required_action="NONE",
        )
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "STATUS_SEMANTICS_MISMATCH"):
            validate_review_cycle_status(bad, evidence)

    def test_adversarial_blocker_cannot_route_to_wrong_role_or_action(self) -> None:
        evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
        bad = classify_review_cycle(evidence)
        bad["next_authority_role"] = "ENGINEERING"
        bad["next_required_action"] = "START_BOUNDED_ENGINEERING_SLICE"
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "STATUS_SEMANTICS_MISMATCH"):
            validate_review_cycle_status(bad, evidence)

    def test_adversarial_blocking_ref_and_fingerprint_cannot_drift(self) -> None:
        evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
        bad = classify_review_cycle(evidence)
        bad["blocking_ref"] = "PR#999@forged"
        bad["stall_fingerprint"] = "AI_WORLD_SIMULATION_ENGINE|ACCEPTED_NOT_CANONICALIZED|PR#999@forged"
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "STATUS_SEMANTICS_MISMATCH"):
            validate_review_cycle_status(bad, evidence)

    def test_adversarial_repeat_count_and_new_evidence_cannot_contradict_history(self) -> None:
        first_evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
        first = classify_review_cycle(first_evidence)
        evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
            prior_stall_fingerprint=first["stall_fingerprint"],
            prior_stall_repeat_count=1,
        )
        bad = classify_review_cycle(evidence)
        bad["stall_repeat_count"] = 1
        bad["new_evidence"] = True
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "STATUS_SEMANTICS_MISMATCH"):
            validate_review_cycle_status(bad, evidence)


if __name__ == "__main__":
    unittest.main()
