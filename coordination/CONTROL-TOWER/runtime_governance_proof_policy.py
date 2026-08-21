from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

EXPECTED_REPOSITORY = "vxz2datoubo/second-brain-coordination"
EXPECTED_WORKFLOW_NAME = "Runtime governance root"
EXPECTED_WORKFLOW_PATH = ".github/workflows/runtime-governance-root.yml"
EXPECTED_PR_NUMBER = 418
STATUS_CONTEXT = "r145/runtime-governance-live-proof"
SUCCESS_CONCLUSION = "success"
FAILURE_CONCLUSIONS = frozenset(
    {
        "failure",
        "timed_out",
        "cancelled",
        "action_required",
        "skipped",
        "neutral",
        "startup_failure",
        "stale",
    }
)
SHA40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class ProofDecision:
    publish: bool
    state: str | None
    head_sha: str | None
    target_url: str | None
    context: str
    reason: str
    root_run_id: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fail(reason: str, run_id: int | None = None) -> ProofDecision:
    return ProofDecision(False, None, None, None, STATUS_CONTEXT, reason, run_id)


def _sha(value: Any) -> str | None:
    return value if isinstance(value, str) and SHA40.fullmatch(value) else None


def evaluate_live_proof(
    event: dict[str, Any],
    original_run: dict[str, Any],
    expected_workflow: dict[str, Any],
    current_pr: dict[str, Any],
) -> ProofDecision:
    workflow_run = event.get("workflow_run") if isinstance(event.get("workflow_run"), dict) else {}
    workflow = event.get("workflow") if isinstance(event.get("workflow"), dict) else {}
    repository = event.get("repository") if isinstance(event.get("repository"), dict) else {}
    run_id = original_run.get("id") if isinstance(original_run.get("id"), int) else None

    if event.get("action") != "completed":
        return _fail("WORKFLOW_RUN_NOT_COMPLETED_ACTION", run_id)
    if repository.get("full_name") != EXPECTED_REPOSITORY:
        return _fail("REPOSITORY_MISMATCH", run_id)
    if workflow_run.get("id") != run_id:
        return _fail("WORKFLOW_RUN_ID_MISMATCH", run_id)
    if workflow_run.get("name") != EXPECTED_WORKFLOW_NAME or original_run.get("name") != EXPECTED_WORKFLOW_NAME:
        return _fail("WORKFLOW_NAME_MISMATCH", run_id)
    if workflow_run.get("event") != "pull_request_target" or original_run.get("event") != "pull_request_target":
        return _fail("WORKFLOW_EVENT_MISMATCH", run_id)
    if workflow_run.get("status") != "completed" or original_run.get("status") != "completed":
        return _fail("WORKFLOW_RUN_NOT_COMPLETED", run_id)

    expected_id = expected_workflow.get("id")
    if not isinstance(expected_id, int):
        return _fail("EXPECTED_WORKFLOW_ID_MISSING", run_id)
    if expected_workflow.get("name") != EXPECTED_WORKFLOW_NAME or expected_workflow.get("path") != EXPECTED_WORKFLOW_PATH:
        return _fail("EXPECTED_WORKFLOW_IDENTITY_MISMATCH", run_id)
    if workflow.get("id") != expected_id or workflow_run.get("workflow_id") != expected_id or original_run.get("workflow_id") != expected_id:
        return _fail("WORKFLOW_ID_MISMATCH", run_id)
    if workflow.get("path") != EXPECTED_WORKFLOW_PATH:
        return _fail("WORKFLOW_PATH_MISMATCH", run_id)
    original_path = original_run.get("path")
    if not isinstance(original_path, str) or original_path.split("@", 1)[0] != EXPECTED_WORKFLOW_PATH:
        return _fail("WORKFLOW_RUN_PATH_MISMATCH", run_id)

    original_repository = original_run.get("repository") if isinstance(original_run.get("repository"), dict) else {}
    if original_repository.get("full_name") != EXPECTED_REPOSITORY:
        return _fail("ORIGINAL_RUN_REPOSITORY_MISMATCH", run_id)

    prs = original_run.get("pull_requests")
    if not isinstance(prs, list) or len(prs) != 1:
        return _fail("PR_BINDING_AMBIGUOUS_OR_MISSING", run_id)
    binding = prs[0] if isinstance(prs[0], dict) else {}
    if binding.get("number") != EXPECTED_PR_NUMBER:
        return _fail("PR_NUMBER_MISMATCH", run_id)

    bound_head = binding.get("head") if isinstance(binding.get("head"), dict) else {}
    bound_base = binding.get("base") if isinstance(binding.get("base"), dict) else {}
    head_sha = _sha(bound_head.get("sha"))
    base_sha = _sha(bound_base.get("sha"))
    if head_sha is None:
        return _fail("BOUND_HEAD_SHA_MISSING", run_id)
    if base_sha is None:
        return _fail("BOUND_BASE_SHA_MISSING", run_id)

    target_url = original_run.get("html_url")
    expected_url = f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/{run_id}"
    if target_url != expected_url:
        return _fail("ROOT_RUN_TARGET_URL_MISMATCH", run_id)

    if current_pr.get("number") != EXPECTED_PR_NUMBER:
        return ProofDecision(True, "error", head_sha, target_url, STATUS_CONTEXT, "CURRENT_PR_IDENTITY_MISMATCH", run_id)
    current_head = current_pr.get("head") if isinstance(current_pr.get("head"), dict) else {}
    current_base = current_pr.get("base") if isinstance(current_pr.get("base"), dict) else {}
    if current_head.get("sha") != head_sha or current_base.get("sha") != base_sha:
        return ProofDecision(True, "error", head_sha, target_url, STATUS_CONTEXT, "STALE_ROOT_RUN_FOR_OLDER_PR_HEAD", run_id)

    conclusion = original_run.get("conclusion")
    if workflow_run.get("conclusion") != conclusion:
        return ProofDecision(True, "error", head_sha, target_url, STATUS_CONTEXT, "WORKFLOW_CONCLUSION_MISMATCH", run_id)
    if conclusion == SUCCESS_CONCLUSION:
        return ProofDecision(True, "success", head_sha, target_url, STATUS_CONTEXT, "ROOT_RUN_SUCCESS", run_id)
    if conclusion in FAILURE_CONCLUSIONS:
        return ProofDecision(True, "failure", head_sha, target_url, STATUS_CONTEXT, f"ROOT_RUN_{str(conclusion).upper()}", run_id)
    return ProofDecision(True, "error", head_sha, target_url, STATUS_CONTEXT, "ROOT_RUN_CONCLUSION_UNKNOWN", run_id)
