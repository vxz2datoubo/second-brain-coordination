import importlib.util
import json
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py"
spec = importlib.util.spec_from_file_location("pr_metadata_fallback", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
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


class PRMetadataFallbackTests(unittest.TestCase):
    def test_success_requires_before_and_after_exact_head_readback(self):
        fake = FakeRunner()
        receipt = mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)
        self.assertEqual(receipt.status, "SUCCESS")
        self.assertTrue(receipt.before_draft)
        self.assertFalse(receipt.after_draft)
        self.assertEqual(receipt.before_head, HEAD)
        self.assertEqual(receipt.after_head, HEAD)
        self.assertTrue(all(value is False for value in receipt.authority.values()))
        self.assertEqual(fake.reads, 2)

    def test_wrong_head_fails_before_mutation(self):
        fake = FakeRunner(before={"head": "b" * 40, "draft": True, "state": "open", "merged": False, "base": "main"})
        with self.assertRaisesRegex(mod.FallbackError, "exact-head fence failed before mutation"):
            mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)
        self.assertFalse(any(args[:2] == ["api", "graphql"] for args in fake.calls))

    def test_head_move_after_mutation_fails_closed(self):
        fake = FakeRunner(after={"head": "b" * 40, "draft": False, "state": "open", "merged": False, "base": "main"})
        with self.assertRaisesRegex(mod.FallbackError, "exact-head fence failed after mutation"):
            mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)

    def test_mutation_that_leaves_draft_true_fails_closed(self):
        fake = FakeRunner(after={"head": HEAD, "draft": True, "state": "open", "merged": False, "base": "main"})
        with self.assertRaisesRegex(mod.FallbackError, "postcondition failed"):
            mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)

    def test_graphql_errors_fail_closed(self):
        fake = FakeRunner(mutation_errors=[{"message": "schema failure"}])
        with self.assertRaisesRegex(mod.FallbackError, "GraphQL mutation failed"):
            mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)

    def test_closed_or_merged_pr_rejected(self):
        cases = (
            {"head": HEAD, "draft": True, "state": "closed", "merged": False, "base": "main"},
            {"head": HEAD, "draft": True, "state": "open", "merged": True, "base": "main"},
        )
        for before in cases:
            with self.subTest(before=before):
                with self.assertRaisesRegex(mod.FallbackError, "open and unmerged"):
                    mod.mark_ready_for_review("o/r", 96, HEAD, runner=FakeRunner(before=before))

    def test_already_ready_is_idempotent_and_does_not_mutate(self):
        ready = {"head": HEAD, "draft": False, "state": "open", "merged": False, "base": "main"}
        fake = FakeRunner(before=ready, after=ready)
        receipt = mod.mark_ready_for_review("o/r", 96, HEAD, runner=fake)
        self.assertEqual(receipt.status, "ALREADY_READY")
        self.assertFalse(any(args[:2] == ["api", "graphql"] for args in fake.calls))

    def test_invalid_sha_rejected_before_transport(self):
        fake = FakeRunner()
        with self.assertRaisesRegex(mod.FallbackError, "40-hex"):
            mod.mark_ready_for_review("o/r", 96, "not-a-sha", runner=fake)
        self.assertEqual(fake.calls, [])

    def test_receipt_digest_is_deterministic(self):
        r1 = mod.mark_ready_for_review("o/r", 96, HEAD, runner=FakeRunner())
        r2 = mod.mark_ready_for_review("o/r", 96, HEAD, runner=FakeRunner())
        self.assertEqual(r1.digest(), r2.digest())

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

    def test_policy_keeps_native_connector_primary_and_fallback_bounded(self):
        doc = (MODULE_PATH.parent / "PR-METADATA-FALLBACK-V1.md").read_text(encoding="utf-8")
        for expected in (
            "Primary lane",
            "Fallback lane",
            "only after the primary lane returns a concrete transport/schema failure",
            "not a second governance system",
            "cannot authorize merge or review acceptance",
            "fresh PR readback is mandatory",
        ):
            self.assertIn(expected, doc)

    def test_receipt_fixture_pins_exact_head_and_all_false_authority(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "pr_metadata_fallback_receipt_example.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "PR_METADATA_FALLBACK_RECEIPT/v1")
        self.assertEqual(data["before_head"], data["expected_head"])
        self.assertEqual(data["expected_head"], data["after_head"])
        self.assertTrue(data["before_draft"])
        self.assertFalse(data["after_draft"])
        self.assertTrue(all(value is False for value in data["authority"].values()))


if __name__ == "__main__":
    unittest.main()
