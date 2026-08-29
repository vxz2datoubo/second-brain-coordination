import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py"
spec = importlib.util.spec_from_file_location("pr_metadata_fallback", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

HEAD = "a" * 40


class FakeRunner:
    def __init__(self, before=None, after=None, *, mutation_errors=None):
        self.before = before or {"head": HEAD, "draft": True, "state": "open", "merged": False, "base": "main"}
        self.after = after or {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
        self.mutation_errors = mutation_errors
        self.reads = 0
        self.calls = []

    def __call__(self, args, input_text=None):
        self.calls.append(args)
        if args[:2] == ["api", "graphql"]:
            if any("pullRequest(number" in a for a in args):
                return "PR_NODE_123\n"
            if self.mutation_errors:
                return json.dumps({"errors": self.mutation_errors})
            return json.dumps({"data": {"markPullRequestReadyForReview": {"pullRequest": {"id": "PR_NODE_123", "isDraft": False, "headRefOid": HEAD}}}})
        if args[0] == "api" and "/pulls/" in args[1]:
            self.reads += 1
            return json.dumps(self.before if self.reads == 1 else self.after)
        raise AssertionError(args)


def test_success_requires_before_and_after_exact_head_readback():
    fake = FakeRunner()
    receipt = mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)
    assert receipt.status == "SUCCESS"
    assert receipt.before_draft is True
    assert receipt.after_draft is False
    assert receipt.before_head == HEAD == receipt.after_head
    assert all(value is False for value in receipt.authority.values())
    assert fake.reads == 2


def test_wrong_head_fails_before_mutation():
    fake = FakeRunner(before={"head": "b" * 40, "draft": True, "state": "open", "merged": False, "base": "main"})
    with pytest.raises(mod.FallbackError, match="exact-head fence failed before mutation"):
        mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)
    assert not any(args[:2] == ["api", "graphql"] for args in fake.calls)


def test_head_move_after_mutation_fails_closed():
    fake = FakeRunner(after={"head": "b" * 40, "draft": False, "state": "open", "merged": False, "base": "main"})
    with pytest.raises(mod.FallbackError, match="exact-head fence failed after mutation"):
        mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)


def test_mutation_that_leaves_draft_true_fails_closed():
    fake = FakeRunner(after={"head": HEAD, "draft": True, "state": "open", "merged": False, "base": "main"})
    with pytest.raises(mod.FallbackError, match="postcondition failed"):
        mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)


def test_graphql_errors_fail_closed():
    fake = FakeRunner(mutation_errors=[{"message": "schema failure"}])
    with pytest.raises(mod.FallbackError, match="GraphQL mutation failed"):
        mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)


def test_closed_or_merged_pr_rejected():
    for before in (
        {"head": HEAD, "draft": True, "state": "closed", "merged": False, "base": "main"},
        {"head": HEAD, "draft": True, "state": "open", "merged": True, "base": "main"},
    ):
        with pytest.raises(mod.FallbackError, match="open and unmerged"):
            mod.mark_ready_for_review("o/r", 96, HEAD, runner=FakeRunner(before=before))


def test_already_ready_is_idempotent_and_does_not_mutate():
    ready = {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
    fake = FakeRunner(before=ready, after=ready)
    receipt = mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)
    assert receipt.status == "ALREADY_READY"
    # GraphQL node lookup/mutation is never needed for an already-ready PR.
    assert not any(args[:2] == ["api", "graphql"] for args in fake.calls)


def test_invalid_sha_rejected():
    with pytest.raises(mod.FallbackError, match="40-hex"):
        mod.mark_ready_for_review("o/r", 96, "not-a-sha", runner=FakeRunner())


def test_receipt_digest_is_deterministic():
    fake1 = FakeRunner()
    fake2 = FakeRunner()
    r1 = mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake1)
    r2 = mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake2)
    assert r1.digest() == r2.digest()


def test_v1_exposes_no_merge_or_code_write_operation():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert 'choices=["mark_ready_for_review"]' in source
    assert '"grants_merge": False' in source
    assert '"grants_code_write": False' in source
    assert '"grants_branch_write": False' in source
