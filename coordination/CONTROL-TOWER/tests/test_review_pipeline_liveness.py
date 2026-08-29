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

EvidenceEnvelope = mod.LivenessProvenanceEnvelope
LivenessEvidence = mod.LivenessEvidence
PROVENANCE_SCHEMA = mod.PROVENANCE_SCHEMA
REQUIRED_LIVENESS_SURFACES = mod.REQUIRED_LIVENESS_SURFACES
ReviewPipelineLivenessError = mod.ReviewPipelineLivenessError
SurfaceRead = mod.SurfaceReadAttestation
classify_review_cycle = mod.classify_review_cycle
validate_review_cycle_status = mod.validate_review_cycle_status

SECOND_BRAIN_REPO = "vxz2datoubo/second-brain-coordination"
AI_WORLD_REPO = "vxz2datoubo/ai-world-simulation-engine"
AI_FILM_REPO = "vxz2datoubo/eustia-ai-film"
MAIN_SHA = "a" * 40


def complete_provenance(
    repository: str,
    queue_issue: int,
    *,
    stale_surface: str | None = None,
    incomplete_surface: str | None = None,
    omit_surface: str | None = None,
    duplicate_surface: str | None = None,
    queue_override: int | None = None,
    repository_override: str | None = None,
    main_sha: str = MAIN_SHA,
    invalid_ref_surface: str | None = None,
    queue_ref_mismatch: bool = False,
) -> EvidenceEnvelope:
    queue_ref = f"github://{repository}/issues/{queue_issue}/comments/fresh"
    reads = []
    for surface in sorted(REQUIRED_LIVENESS_SURFACES):
        if surface == omit_surface:
            continue
        observed_main = "b" * 40 if surface == stale_surface else main_sha
        source_ref = queue_ref if surface == "REVIEW_QUEUE" else f"github://{repository}/{surface.lower()}"
        if surface == invalid_ref_surface:
            source_ref = "caller://forged"
        reads.append(
            SurfaceRead(
                surface=surface,
                source_ref=source_ref,
                observed_revision=f"rev:{surface}",
                observed_main_sha=observed_main,
                complete=surface != incomplete_surface,
            )
        )
    if duplicate_surface:
        reads.append(
            SurfaceRead(
                surface=duplicate_surface,
                source_ref=f"github://{repository}/duplicate",
                observed_revision="rev:duplicate",
                observed_main_sha=main_sha,
                complete=True,
            )
        )
    return EvidenceEnvelope(
        schema=PROVENANCE_SCHEMA,
        repository=repository if repository_override is None else repository_override,
        queue_issue=queue_issue if queue_override is None else queue_override,
        canonical_main_sha=main_sha,
        queue_snapshot_ref=(
            f"github://{repository}/wrong-queue-snapshot" if queue_ref_mismatch else queue_ref
        ),
        surface_reads=tuple(reads),
    )


class ReviewPipelineLivenessTests(unittest.TestCase):
    def test_pending_ticket_keeps_reviewer_as_next_authority(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=2,
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
            repository=AI_WORLD_REPO,
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

    def test_empty_refs_without_provenance_fail_closed_unknown(self) -> None:
        evidence = LivenessEvidence(
            project="EUSTIA_AI_FILM",
            repository=AI_FILM_REPO,
            queue_issue=15,
            pending_exact_head_tickets=0,
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["pipeline_status"], "UNKNOWN")
        self.assertEqual(out["blocker_class"], "UNKNOWN_BLOCKED")
        self.assertEqual(out["next_required_action"], "OBTAIN_MISSING_FRESH_GITHUB_EVIDENCE")
        validate_review_cycle_status(out, evidence)

    def test_normal_idle_requires_complete_fresh_provenance(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(SECOND_BRAIN_REPO, 453),
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["pipeline_status"], "IDLE")
        self.assertEqual(out["blocker_class"], "NORMAL_IDLE")
        self.assertEqual(out["stall_fingerprint"], "NONE")
        validate_review_cycle_status(out, evidence)

    def test_stale_request_precedes_provenance_completeness(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
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
            repository=AI_WORLD_REPO,
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
        first = classify_review_cycle(first_evidence)
        second_evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            repository=AI_WORLD_REPO,
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
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
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
                LivenessEvidence(
                    project="SECOND_BRAIN",
                    repository=SECOND_BRAIN_REPO,
                    queue_issue=453,
                    pending_exact_head_tickets=-1,
                )
            )

    def test_zero_queue_issue_fails_closed(self) -> None:
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "QUEUE_ISSUE_INVALID"):
            classify_review_cycle(
                LivenessEvidence(
                    project="SECOND_BRAIN",
                    repository=SECOND_BRAIN_REPO,
                    queue_issue=0,
                    pending_exact_head_tickets=0,
                )
            )

    def test_implemented_not_queued_routes_to_engineering_without_inventing_review(self) -> None:
        evidence = LivenessEvidence(
            project="EUSTIA_AI_FILM",
            repository=AI_FILM_REPO,
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
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
        )
        out = classify_review_cycle(evidence)
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "LIVENESS_EVIDENCE_REQUIRED"):
            validate_review_cycle_status(out)

    def test_adversarial_pending_ticket_cannot_be_laundered_to_idle(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=1,
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
            repository=AI_WORLD_REPO,
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
            repository=AI_WORLD_REPO,
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
            repository=AI_WORLD_REPO,
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
        first = classify_review_cycle(first_evidence)
        evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            repository=AI_WORLD_REPO,
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

    def test_partial_provenance_cannot_mint_normal_idle(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(
                SECOND_BRAIN_REPO, 453, omit_surface="CI_PROVENANCE"
            ),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_stale_surface_main_binding_yields_unknown_blocked(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(
                SECOND_BRAIN_REPO, 453, stale_surface="PR_STATE"
            ),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_incomplete_surface_provenance_yields_unknown_blocked(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(
                SECOND_BRAIN_REPO, 453, incomplete_surface="CANONICALIZATION"
            ),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_duplicate_surface_attestation_fails_closed(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(
                SECOND_BRAIN_REPO, 453, duplicate_surface="REVIEW_QUEUE"
            ),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_queue_identity_mismatch_fails_closed(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(SECOND_BRAIN_REPO, 453, queue_override=999),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_repository_identity_mismatch_fails_closed(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(
                SECOND_BRAIN_REPO,
                453,
                repository_override="vxz2datoubo/other",
            ),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_non_full_main_sha_fails_closed(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(SECOND_BRAIN_REPO, 453, main_sha="abc123"),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_non_github_surface_ref_fails_closed(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(
                SECOND_BRAIN_REPO, 453, invalid_ref_surface="CI_PROVENANCE"
            ),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_queue_snapshot_must_bind_review_queue_read(self) -> None:
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=complete_provenance(
                SECOND_BRAIN_REPO, 453, queue_ref_mismatch=True
            ),
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")


if __name__ == "__main__":
    unittest.main()
