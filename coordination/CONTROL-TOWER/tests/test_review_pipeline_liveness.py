from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


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


def test_pending_ticket_keeps_reviewer_as_next_authority() -> None:
    out = classify_review_cycle(
        LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=2)
    )
    assert out["pipeline_status"] == "ACTIVE"
    assert out["blocker_class"] == "NONE"
    assert out["next_authority_role"] == "INDEPENDENT_REVIEWER"
    assert out["next_required_action"] == "REVIEW_PENDING_EXACT_HEAD_TICKETS"
    assert out["reviewer_mutations"] == "NONE"


def test_empty_queue_detects_accept_not_canonicalized() -> None:
    out = classify_review_cycle(
        LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651edec",
        )
    )
    assert out["pipeline_status"] == "BLOCKED"
    assert out["blocker_class"] == "ACCEPTED_NOT_CANONICALIZED"
    assert out["next_authority_role"] == "CANONICALIZER"
    assert out["next_required_action"] == "CANONICALIZE_ACCEPTED_EXACT_HEAD"


def test_empty_queue_does_not_claim_idle_when_evidence_incomplete() -> None:
    out = classify_review_cycle(
        LivenessEvidence(
            project="EUSTIA_AI_FILM",
            queue_issue=15,
            pending_exact_head_tickets=0,
            evidence_complete=False,
        )
    )
    assert out["pipeline_status"] == "UNKNOWN"
    assert out["blocker_class"] == "UNKNOWN_BLOCKED"
    assert out["next_required_action"] == "OBTAIN_MISSING_FRESH_GITHUB_EVIDENCE"


def test_normal_idle_requires_complete_evidence_and_no_stall() -> None:
    out = classify_review_cycle(
        LivenessEvidence(
            project="SECOND_BRAIN",
            queue_issue=453,
            pending_exact_head_tickets=0,
            evidence_complete=True,
        )
    )
    assert out["pipeline_status"] == "IDLE"
    assert out["blocker_class"] == "NORMAL_IDLE"
    assert out["stall_fingerprint"] == "NONE"


def test_stale_request_precedes_downstream_stalls() -> None:
    out = classify_review_cycle(
        LivenessEvidence(
            project="SECOND_BRAIN",
            queue_issue=453,
            pending_exact_head_tickets=0,
            stale_review_request_ref="PR#1@oldhead",
            accepted_not_canonicalized_ref="PR#2@accepted",
        )
    )
    assert out["blocker_class"] == "STALE_REVIEW_REQUEST"


def test_repeat_stall_suppresses_fake_new_evidence() -> None:
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
    assert first["new_evidence"] is True
    assert second["new_evidence"] is False
    assert second["stall_repeat_count"] == 2


def test_no_privileged_mutation_is_valid_status_invariant() -> None:
    out = classify_review_cycle(
        LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=0)
    )
    validate_review_cycle_status(out)
    bad = dict(out)
    bad["reviewer_mutations"] = "MERGE"
    with pytest.raises(ReviewPipelineLivenessError, match="REVIEWER_MUTATION_FORBIDDEN"):
        validate_review_cycle_status(bad)


def test_invalid_counts_fail_closed() -> None:
    with pytest.raises(ReviewPipelineLivenessError, match="PENDING_TICKETS_INVALID"):
        classify_review_cycle(
            LivenessEvidence(project="SECOND_BRAIN", queue_issue=453, pending_exact_head_tickets=-1)
        )


def test_implemented_not_queued_routes_to_engineering_without_inventing_review() -> None:
    out = classify_review_cycle(
        LivenessEvidence(
            project="EUSTIA_AI_FILM",
            queue_issue=15,
            pending_exact_head_tickets=0,
            implemented_not_queued_ref="PR#30@abcdef",
        )
    )
    assert out["blocker_class"] == "IMPLEMENTED_NOT_QUEUED"
    assert out["next_authority_role"] == "ENGINEERING"
    assert out["next_required_action"] == "POST_CANONICAL_REVIEW_REQUEST_FOR_EXACT_HEAD"
