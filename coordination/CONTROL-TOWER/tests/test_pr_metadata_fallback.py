import base64
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py"
spec = importlib.util.spec_from_file_location("pr_metadata_fallback", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

HEAD = "a" * 40
REPO = "o/r"
PR = 96


def incident_registry(*, include=True):
    incidents = []
    if include:
        incidents.append({
            "incident_id": "TEST-INCIDENT",
            "status": "ACTIVE",
            "scope": "SINGLE_TARGET_EXACT_HEAD",
            "repository": REPO,
            "pr_number": PR,
            "expected_head": HEAD,
            "operation": "mark_ready_for_review",
            "primary_transport": "CHATGPT_GITHUB_CONNECTOR",
            "failure_fingerprint": "Repository.fullDatabaseId",
            "evidence_refs": ["github://trusted/evidence"],
        })
    return {
        "schema": "PR_METADATA_FALLBACK_INCIDENT_REGISTRY/v1",
        "incidents": incidents,
    }


class FakeRunner:
    def __init__(self, before=None, after=None, *, mutation_errors=None, registry=None):
        self.before = before or {"head": HEAD, "draft": True, "state": "open", "merged": False, "base": "main"}
        self.after = after or {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
        self.mutation_errors = mutation_errors
        self.registry = registry if registry is not None else incident_registry()
        self.reads = 0
        self.calls = []

    def __call__(self, args, input_text=None):
        self.calls.append(args)
        if args[0] == "api" and "/contents/" in args[1]:
            payload = json.dumps(self.registry).encode("utf-8")
            return base64.b64encode(payload).decode("ascii") + "\n"
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


def invoke(fake, repository=REPO, pr_number=PR, head=HEAD):
    with patch.object(mod, "_run_gh", fake):
        return mod.mark_ready_for_review(repository, pr_number, head)


class PRMetadataFallbackTests(unittest.TestCase):
    def test_success_requires_canonical_incident_and_before_after_exact_head(self):
        fake = FakeRunner()
        receipt = invoke(fake)
        self.assertEqual(receipt.status, "SUCCESS")
        self.assertEqual(receipt.incident_id, "TEST-INCIDENT")
        self.assertTrue(receipt.before_draft)
        self.assertFalse(receipt.after_draft)
        self.assertEqual(receipt.before_head, HEAD)
        self.assertEqual(receipt.after_head, HEAD)
        self.assertTrue(all(value is False for value in receipt.authority.values()))
        self.assertEqual(fake.reads, 2)

    def test_direct_fallback_without_canonical_primary_failure_incident_fails_closed(self):
        fake = FakeRunner(registry=incident_registry(include=False))
        with self.assertRaisesRegex(mod.FallbackError, "fallback not eligible"):
            invoke(fake)
        self.assertEqual(fake.reads, 0)
        self.assertFalse(any(args[:2] == ["api", "graphql"] for args in fake.calls))

    def test_caller_cannot_substitute_target_for_registered_incident(self):
        fake = FakeRunner()
        with self.assertRaisesRegex(mod.FallbackError, "fallback not eligible"):
            invoke(fake, repository="attacker/repo", pr_number=7)
        self.assertEqual(fake.reads, 0)

    def test_wrong_head_fails_before_mutation(self):
        registry = incident_registry()
        registry["incidents"][0]["expected_head"] = "b" * 40
        fake = FakeRunner(registry=registry)
        with self.assertRaisesRegex(mod.FallbackError, "fallback not eligible"):
            invoke(fake)
        self.assertEqual(fake.reads, 0)

    def test_live_head_move_after_mutation_fails_closed(self):
        fake = FakeRunner(after={"head": "b" * 40, "draft": False, "state": "open", "merged": False, "base": "main"})
        with self.assertRaisesRegex(mod.FallbackError, "exact-head fence failed after mutation"):
            invoke(fake)

    def test_mutation_that_leaves_draft_true_fails_closed(self):
        fake = FakeRunner(after={"head": HEAD, "draft": True, "state": "open", "merged": False, "base": "main"})
        with self.assertRaisesRegex(mod.FallbackError, "postcondition failed after mutation"):
            invoke(fake)

    def test_graphql_errors_fail_closed(self):
        fake = FakeRunner(mutation_errors=[{"message": "schema failure"}])
        with self.assertRaisesRegex(mod.FallbackError, "GraphQL mutation failed"):
            invoke(fake)

    def test_closed_or_merged_pr_rejected_before_mutation(self):
        cases = (
            {"head": HEAD, "draft": True, "state": "closed", "merged": False, "base": "main"},
            {"head": HEAD, "draft": True, "state": "open", "merged": True, "base": "main"},
        )
        for before in cases:
            with self.subTest(before=before):
                fake = FakeRunner(before=before)
                with self.assertRaisesRegex(mod.FallbackError, "open and unmerged before mutation"):
                    invoke(fake)

    def test_already_ready_is_idempotent_only_after_second_fenced_readback(self):
        ready = {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
        fake = FakeRunner(before=ready, after=ready)
        receipt = invoke(fake)
        self.assertEqual(receipt.status, "ALREADY_READY")
        self.assertEqual(fake.reads, 2)
        self.assertFalse(any(args[:2] == ["api", "graphql"] for args in fake.calls))

    def test_already_ready_head_move_fails_closed(self):
        before = {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
        after = {"head": "b" * 40, "draft": False, "state": "open", "merged": False, "base": "main"}
        with self.assertRaisesRegex(mod.FallbackError, "exact-head fence failed after idempotent readback"):
            invoke(FakeRunner(before=before, after=after))

    def test_already_ready_redraft_fails_closed(self):
        before = {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
        after = {"head": HEAD, "draft": True, "state": "open", "merged": False, "base": "main"}
        with self.assertRaisesRegex(mod.FallbackError, "postcondition failed after idempotent readback"):
            invoke(FakeRunner(before=before, after=after))

    def test_already_ready_close_or_merge_drift_fails_closed(self):
        before = {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
        cases = (
            {"head": HEAD, "draft": False, "state": "closed", "merged": False, "base": "main"},
            {"head": HEAD, "draft": False, "state": "open", "merged": True, "base": "main"},
        )
        for after in cases:
            with self.subTest(after=after):
                with self.assertRaisesRegex(mod.FallbackError, "open and unmerged after idempotent readback"):
                    invoke(FakeRunner(before=before, after=after))

    def test_invalid_sha_rejected_before_transport(self):
        fake = FakeRunner()
        with patch.object(mod, "_run_gh", fake):
            with self.assertRaisesRegex(mod.FallbackError, "40-hex"):
                mod.mark_ready_for_review(REPO, PR, "not-a-sha")
        self.assertEqual(fake.calls, [])

    def test_receipt_digest_is_deterministic(self):
        r1 = invoke(FakeRunner())
        r2 = invoke(FakeRunner())
        self.assertEqual(r1.digest(), r2.digest())

    def test_public_function_has_no_caller_supplied_runner_or_incident_receipt(self):
        import inspect
        params = inspect.signature(mod.mark_ready_for_review).parameters
        self.assertEqual(list(params), ["repository", "pr_number", "expected_head"])

    def test_v1_exposes_no_merge_code_or_branch_write_authority(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        for expected in (
            'choices=["mark_ready_for_review"]',
            '"grants_merge": False',
            '"grants_code_write": False',
            '"grants_branch_write": False',
            '"grants_review_accept": False',
            '"grants_release": False',
        ):
            self.assertIn(expected, source)
        for forbidden in ("merge_pull_request", "git push", "git commit", "curl "):
            self.assertNotIn(forbidden, source)

    def test_no_embedded_secret_material(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        for token in ("GITHUB_TOKEN=", "ghp_", "github_pat_", "Authorization: Bearer", "Authorization: token"):
            self.assertNotIn(token, source)

    def test_registry_is_fixed_to_canonical_main(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("PR-METADATA-FALLBACK-INCIDENTS.json", source)
        self.assertIn("?ref=main", source)
        self.assertNotIn("incident_receipt", source)


if __name__ == "__main__":
    unittest.main()
