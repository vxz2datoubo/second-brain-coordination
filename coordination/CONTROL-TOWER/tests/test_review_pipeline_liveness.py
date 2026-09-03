from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys
import unittest
from unittest import mock

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
MAIN_SHA = "a" * 40
HEAD_A = "b" * 40
HEAD_B = "c" * 40


def caller_minted_provenance(repository: str, queue_issue: int) -> EvidenceEnvelope:
    queue_ref = f"github://{repository}/issues/{queue_issue}/comments/fresh"
    return EvidenceEnvelope(
        schema=PROVENANCE_SCHEMA,
        repository=repository,
        queue_issue=queue_issue,
        canonical_main_sha=MAIN_SHA,
        queue_snapshot_ref=queue_ref,
        surface_reads=tuple(
            SurfaceRead(
                surface=surface,
                source_ref=queue_ref,
                observed_revision=f"caller-rev:{surface}",
                observed_main_sha=MAIN_SHA,
                complete=True,
            )
            for surface in sorted(REQUIRED_LIVENESS_SURFACES)
        ),
    )


def request(comment_id: int, pr_number: int, head: str) -> dict:
    return {
        "id": comment_id,
        "body": f"""```yaml
schema: REVIEW_REQUEST/v1
project: SECOND_BRAIN
pr: {pr_number}
exact_head: {head}
```""",
    }


def result(comment_id: int, pr_number: int, head: str, verdict: str) -> dict:
    return {
        "id": comment_id,
        "body": f"""```yaml
schema: REVIEW_RESULT/v1
project: SECOND_BRAIN
pr: {pr_number}
reviewed_head: {head}
verdict: {verdict}
```""",
    }


def pull(
    number: int,
    head: str,
    *,
    body: str = "",
    state: str = "open",
    merged: bool = False,
) -> dict:
    return {
        "number": number,
        "state": state,
        "merged": merged,
        "merged_at": "2026-08-29T00:00:00Z" if merged else None,
        "head": {"sha": head},
        "body": body,
    }


def ci_run(head: str, *, status: str = "completed", conclusion: str | None = "success", name: str = "tests") -> dict:
    return {
        "id": abs(hash((head, status, conclusion, name))) % 100000 + 1,
        "name": name,
        "head_sha": head,
        "status": status,
        "conclusion": conclusion,
    }


class FakeGatewayError(Exception):
    pass


class FakeObserver:
    def __init__(
        self,
        *,
        comments=None,
        open_prs=None,
        open_issues=None,
        pr_details=None,
        ci_runs=None,
        main_sha=MAIN_SHA,
        fail_path=None,
        mutate_after_first_snapshot=False,
    ):
        self.comments = list(comments or [])
        self.open_prs = list(open_prs or [])
        self.open_issues = list(open_issues or [])
        self.pr_details = dict(pr_details or {})
        self.ci_runs = {key: list(value) for key, value in (ci_runs or {}).items()}
        self.main_sha = main_sha
        self.fail_path = fail_path
        self.mutate_after_first_snapshot = mutate_after_first_snapshot
        self.main_reads = 0

    def _get_json(self, path):
        if path == self.fail_path:
            raise FakeGatewayError("transport")
        if path.endswith("/git/ref/heads/main"):
            self.main_reads += 1
            sha = self.main_sha
            if self.mutate_after_first_snapshot and self.main_reads >= 2:
                sha = HEAD_B
            payload = {"object": {"sha": sha}}
        elif "/actions/runs?" in path:
            head = path.split("head_sha=", 1)[1].split("&", 1)[0]
            page = int(path.rsplit("page=", 1)[1])
            payload = {
                "total_count": len(self.ci_runs.get(head, [])),
                "workflow_runs": self.ci_runs.get(head, []) if page == 1 else [],
            }
        elif "/issues/" in path and "/comments?" not in path and "?state=" not in path:
            number = int(path.rsplit("/", 1)[1])
            payload = {"number": number, "state": "open"}
        elif "/comments?per_page=100&page=" in path:
            page = int(path.rsplit("=", 1)[1])
            payload = self.comments if page == 1 else []
        elif "/pulls?state=open&per_page=100&page=" in path:
            page = int(path.rsplit("=", 1)[1])
            payload = self.open_prs if page == 1 else []
        elif "/issues?state=open&per_page=100&page=" in path:
            page = int(path.rsplit("=", 1)[1])
            payload = self.open_issues if page == 1 else []
        elif "/pulls/" in path:
            number = int(path.rsplit("/", 1)[1])
            payload = self.pr_details[number]
        else:
            raise AssertionError(path)
        return {}, payload, {}


class ReviewPipelineLivenessTests(unittest.TestCase):
    def test_pending_ticket_keeps_reviewer_as_next_authority(self):
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
        validate_review_cycle_status(out, evidence)

    def test_explicit_accept_not_canonicalized_routes_to_canonicalizer(self):
        evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            repository=AI_WORLD_REPO,
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@8651",
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["blocker_class"], "ACCEPTED_NOT_CANONICALIZED")
        self.assertEqual(out["next_authority_role"], "CANONICALIZER")
        validate_review_cycle_status(out, evidence)

    def test_no_caller_provenance_is_unknown(self):
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
        )
        self.assertEqual(classify_review_cycle(evidence)["blocker_class"], "UNKNOWN_BLOCKED")

    def test_caller_minted_full_github_prefix_provenance_cannot_mint_idle(self):
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
            provenance=caller_minted_provenance(SECOND_BRAIN_REPO, 453),
        )
        out = classify_review_cycle(evidence)
        self.assertEqual(out["blocker_class"], "UNKNOWN_BLOCKED")
        self.assertNotEqual(out["pipeline_status"], "IDLE")

    def test_project_queue_binding_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "PROJECT_QUEUE_BINDING_MISMATCH"):
            classify_review_cycle(
                LivenessEvidence(
                    project="SECOND_BRAIN",
                    repository=AI_WORLD_REPO,
                    queue_issue=50,
                    pending_exact_head_tickets=0,
                )
            )

    def test_status_semantics_still_rederived(self):
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

    def test_reviewer_mutation_lock_preserved(self):
        evidence = LivenessEvidence(
            project="SECOND_BRAIN",
            repository=SECOND_BRAIN_REPO,
            queue_issue=453,
            pending_exact_head_tickets=0,
        )
        bad = classify_review_cycle(evidence)
        bad["reviewer_mutations"] = "MERGE"
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "REVIEWER_MUTATION_FORBIDDEN"):
            validate_review_cycle_status(bad, evidence)

    def test_repeat_stall_semantics_preserved(self):
        first_evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            repository=AI_WORLD_REPO,
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@head",
        )
        first = classify_review_cycle(first_evidence)
        second_evidence = LivenessEvidence(
            project="AI_WORLD_SIMULATION_ENGINE",
            repository=AI_WORLD_REPO,
            queue_issue=50,
            pending_exact_head_tickets=0,
            accepted_not_canonicalized_ref="PR#96@head",
            prior_stall_fingerprint=first["stall_fingerprint"],
            prior_stall_repeat_count=first["stall_repeat_count"],
        )
        second = classify_review_cycle(second_evidence)
        self.assertFalse(second["new_evidence"])
        self.assertEqual(second["stall_repeat_count"], 2)

    def _observe(self, observer, project="SECOND_BRAIN"):
        with mock.patch.object(
            mod, "_make_live_observer", return_value=(observer, FakeGatewayError)
        ):
            return mod.observe_review_cycle("/repo", project)

    def test_live_observer_clean_scan_can_mint_normal_idle(self):
        out = self._observe(FakeObserver())
        self.assertEqual(out["blocker_class"], "NORMAL_IDLE")
        self.assertEqual(out["pipeline_status"], "IDLE")

    def test_live_observer_pending_ticket_derives_queue_first_with_green_ci(self):
        observer = FakeObserver(
            comments=[request(10, 485, HEAD_A)],
            open_prs=[pull(485, HEAD_A)],
            pr_details={485: pull(485, HEAD_A)},
            ci_runs={HEAD_A: [ci_run(HEAD_A)]},
        )
        out = self._observe(observer)
        self.assertEqual(out["pending_exact_head_tickets"], 1)
        self.assertEqual(out["next_authority_role"], "INDEPENDENT_REVIEWER")

    def test_pending_ticket_failed_ci_is_explicit_but_queue_remains_primary(self):
        observer = FakeObserver(
            comments=[request(10, 485, HEAD_A)],
            open_prs=[pull(485, HEAD_A)],
            pr_details={485: pull(485, HEAD_A)},
            ci_runs={HEAD_A: [ci_run(HEAD_A, conclusion="failure")]},
        )
        out = self._observe(observer)
        self.assertEqual(out["pending_exact_head_tickets"], 1)
        self.assertEqual(out["next_authority_role"], "INDEPENDENT_REVIEWER")

    def test_live_observer_stale_request_detected_from_real_pr_head(self):
        observer = FakeObserver(
            comments=[request(10, 485, HEAD_A)],
            open_prs=[pull(485, HEAD_B)],
            pr_details={485: pull(485, HEAD_B)},
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "STALE_REVIEW_REQUEST")
        self.assertIn(HEAD_A, out["blocking_ref"])
        self.assertIn(HEAD_B, out["blocking_ref"])

    def test_live_observer_accept_not_canonicalized_is_derived(self):
        observer = FakeObserver(
            comments=[request(10, 485, HEAD_A), result(20, 485, HEAD_A, "ACCEPT")],
            open_prs=[pull(485, HEAD_A)],
            pr_details={485: pull(485, HEAD_A)},
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "ACCEPTED_NOT_CANONICALIZED")

    def test_live_observer_changes_required_without_requeue_routes_engineering_with_green_ci(self):
        observer = FakeObserver(
            comments=[
                request(10, 485, HEAD_A),
                result(20, 485, HEAD_A, "CHANGES_REQUIRED"),
            ],
            open_prs=[pull(485, HEAD_A)],
            pr_details={485: pull(485, HEAD_A)},
            ci_runs={HEAD_A: [ci_run(HEAD_A)]},
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "REMEDIATION_NOT_REQUEUED")
        self.assertEqual(out["next_authority_role"], "ENGINEERING")

    def test_remediation_failed_ci_routes_ci_before_requeue(self):
        observer = FakeObserver(
            comments=[
                request(10, 485, HEAD_A),
                result(20, 485, HEAD_A, "CHANGES_REQUIRED"),
            ],
            open_prs=[pull(485, HEAD_B)],
            pr_details={485: pull(485, HEAD_B)},
            ci_runs={HEAD_B: [ci_run(HEAD_B, conclusion="failure")]},
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "CI_OR_PROVENANCE_BLOCKED")
        self.assertIn("CI_FAILURE", out["blocking_ref"])

    def test_remediation_without_observable_exact_head_ci_fails_closed(self):
        observer = FakeObserver(
            comments=[
                request(10, 485, HEAD_A),
                result(20, 485, HEAD_A, "CHANGES_REQUIRED"),
            ],
            open_prs=[pull(485, HEAD_B)],
            pr_details={485: pull(485, HEAD_B)},
            ci_runs={HEAD_B: []},
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "CI_OR_PROVENANCE_BLOCKED")
        self.assertIn("NO_OBSERVABLE_EXACT_HEAD_CI", out["blocking_ref"])

    def test_skipped_only_ci_does_not_mint_ci_complete(self):
        observer = FakeObserver(
            comments=[
                request(10, 485, HEAD_A),
                result(20, 485, HEAD_A, "CHANGES_REQUIRED"),
            ],
            open_prs=[pull(485, HEAD_B)],
            pr_details={485: pull(485, HEAD_B)},
            ci_runs={HEAD_B: [ci_run(HEAD_B, conclusion="skipped")]},
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "CI_OR_PROVENANCE_BLOCKED")

    def test_unqueued_completion_marker_with_green_ci_is_detected(self):
        observer = FakeObserver(
            open_prs=[
                pull(492, HEAD_A, body="completion_signal: READY_FOR_INDEPENDENT_REVIEW")
            ],
            ci_runs={HEAD_A: [ci_run(HEAD_A)]},
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "IMPLEMENTED_NOT_QUEUED")

    def test_released_issue_without_implementation_is_detected(self):
        observer = FakeObserver(
            open_issues=[
                {
                    "number": 777,
                    "body": "State: CONTROL_TOWER_RELEASED / BOUNDED_ENGINEERING_AUTHORIZED",
                }
            ]
        )
        out = self._observe(observer)
        self.assertEqual(out["blocker_class"], "RELEASED_NOT_IMPLEMENTED")

    def test_final_readback_main_drift_fails_closed(self):
        observer = FakeObserver(mutate_after_first_snapshot=True)
        with self.assertRaisesRegex(
            ReviewPipelineLivenessError, "LIVE_OBSERVATION_CHANGED_DURING_SCAN"
        ):
            self._observe(observer)

    def test_final_readback_queue_drift_fails_closed(self):
        observer = FakeObserver()
        original = observer._get_json
        seen = {"comments": 0}
        def changing(path):
            if "/comments?per_page=100&page=1" in path:
                seen["comments"] += 1
                if seen["comments"] >= 2:
                    observer.comments.append({"id": 999, "body": "late engineering update"})
            return original(path)
        observer._get_json = changing
        with self.assertRaisesRegex(
            ReviewPipelineLivenessError, "LIVE_OBSERVATION_CHANGED_DURING_SCAN"
        ):
            self._observe(observer)

    def test_live_provider_failure_does_not_fall_back_to_caller_idle(self):
        observer = FakeObserver(
            fail_path=f"/repos/{SECOND_BRAIN_REPO}/git/ref/heads/main"
        )
        with mock.patch.object(
            mod, "_make_live_observer", return_value=(observer, FakeGatewayError)
        ):
            with self.assertRaisesRegex(ReviewPipelineLivenessError, "LIVE_GITHUB_READ_FAILED"):
                mod.observe_review_cycle("/repo", "SECOND_BRAIN")

    def test_ci_provider_failure_fails_closed(self):
        path = (
            f"/repos/{SECOND_BRAIN_REPO}/actions/runs?head_sha={HEAD_A}"
            "&event=pull_request&per_page=100&page=1"
        )
        observer = FakeObserver(
            comments=[request(10, 485, HEAD_A)],
            open_prs=[pull(485, HEAD_A)],
            pr_details={485: pull(485, HEAD_A)},
            fail_path=path,
        )
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "LIVE_CI_READ_FAILED"):
            self._observe(observer)

    def test_observe_api_has_no_provider_receipt_runner_or_repository_override(self):
        params = set(inspect.signature(mod.observe_review_cycle).parameters)
        self.assertEqual(
            params,
            {
                "repo_root",
                "project",
                "prior_stall_fingerprint",
                "prior_stall_repeat_count",
            },
        )

    def test_live_observer_unregistered_project_fails_before_transport(self):
        with self.assertRaisesRegex(ReviewPipelineLivenessError, "PROJECT_NOT_REGISTERED"):
            mod.observe_review_cycle("/repo", "CALLER_FORGED_PROJECT")


if __name__ == "__main__":
    unittest.main()
