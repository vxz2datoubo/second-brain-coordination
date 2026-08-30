from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from integration_state_isolation import (
    AUTHORITY_FLAGS,
    COMMAND_SNAPSHOT_SCHEMA,
    FINAL_PASS,
    RecordingResult,
    SNAPSHOT_SCHEMA,
    compare_snapshots,
    environment_invalid_receipt,
    failure_fingerprint,
    normalize_failure_text,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "integration_state_isolation.schema.json").read_text(encoding="utf-8")
)


def _stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value) -> str:
    return hashlib.sha256(_stable(value).encode()).hexdigest()


def snapshot(
    rows: list[tuple[str, str, str | None]],
    *,
    python_version: str = "3.13.0",
) -> dict:
    results = [
        {
            "test_id": test_id,
            "status": status,
            "failure_fingerprint": fingerprint,
        }
        for test_id, status, fingerprint in sorted(rows)
    ]
    ids = [row["test_id"] for row in results]
    return {
        "schema": SNAPSHOT_SCHEMA,
        "python_version": python_version,
        "test_count": len(results),
        "test_id_digest": _digest(ids),
        "state_digest": _digest(results),
        "environment_errors": [],
        "results": results,
    }


def command_snapshot(rows: list[tuple[str, int, str | None]]) -> dict:
    results = [
        {
            "command_id": command_id,
            "exit_code": exit_code,
            "failure_fingerprint": fingerprint,
        }
        for command_id, exit_code, fingerprint in sorted(rows)
    ]
    ids = [row["command_id"] for row in results]
    return {
        "schema": COMMAND_SNAPSHOT_SCHEMA,
        "command_count": len(results),
        "command_id_digest": _digest(ids),
        "state_digest": _digest(results),
        "results": results,
    }


class _SubtestProbe(unittest.TestCase):
    def __init__(self, should_fail: bool):
        super().__init__("probe")
        self.should_fail = should_fail

    def probe(self):
        for value in (1, 2):
            with self.subTest(value=value):
                if self.should_fail and value == 2:
                    self.assertEqual(value, 999, "subtest semantic failure")
                else:
                    self.assertIn(value, (1, 2))


def record_subtest_probe(should_fail: bool) -> dict[str, dict]:
    result = RecordingResult(roots=())
    _SubtestProbe(should_fail).run(result)
    return result.records


class IntegrationStateIsolationTests(unittest.TestCase):
    def test_preserved_baseline_failure_is_visible_but_not_candidate_regression(self):
        fp = "a" * 64
        before = snapshot([("t.pass", "PASS", None), ("t.base", "FAIL", fp)])
        after = snapshot(
            [
                ("t.pass", "PASS", None),
                ("t.base", "FAIL", fp),
                ("t.new", "PASS", None),
            ]
        )
        receipt = compare_snapshots(before, after)
        self.assertEqual(receipt["classification"], FINAL_PASS)
        self.assertEqual(
            [x["test_id"] for x in receipt["baseline_failures_preserved"]],
            ["t.base"],
        )
        self.assertEqual(receipt["candidate_only_test_ids"], ["t.new"])
        self.assertFalse(receipt["baseline_declared_healthy"])

    def test_new_retained_failure_blocks(self):
        before = snapshot([("t", "PASS", None)])
        after = snapshot([("t", "FAIL", "b" * 64)])
        receipt = compare_snapshots(before, after)
        self.assertEqual(receipt["classification"], "CANDIDATE_INTRODUCED_FAILURE")
        self.assertEqual(receipt["candidate_introduced_failures"][0]["test_id"], "t")

    def test_modified_baseline_failure_fingerprint_blocks(self):
        before = snapshot([("t", "ERROR", "a" * 64)])
        after = snapshot([("t", "ERROR", "b" * 64)])
        receipt = compare_snapshots(before, after)
        self.assertEqual(
            receipt["classification"],
            "CANDIDATE_MODIFIED_BASELINE_FAILURE",
        )

    def test_baseline_improvement_is_recorded_not_penalized(self):
        before = snapshot([("t", "FAIL", "a" * 64)])
        after = snapshot([("t", "PASS", None)])
        receipt = compare_snapshots(before, after)
        self.assertEqual(receipt["classification"], FINAL_PASS)
        self.assertEqual(receipt["baseline_improvements"][0]["test_id"], "t")

    def test_candidate_only_test_must_pass(self):
        before = snapshot([("old", "PASS", None)])
        after = snapshot(
            [("old", "PASS", None), ("new", "ERROR", "c" * 64)]
        )
        receipt = compare_snapshots(before, after)
        self.assertEqual(receipt["classification"], "CANDIDATE_EXACT_HEAD_FAILURE")
        self.assertEqual(receipt["candidate_exact_head_failures"], ["new"])

    def test_missing_baseline_id_is_environment_invalid(self):
        before = snapshot([("a", "PASS", None), ("b", "PASS", None)])
        after = snapshot([("a", "PASS", None)])
        receipt = compare_snapshots(before, after)
        self.assertEqual(receipt["classification"], "TEST_ENVIRONMENT_INVALID")
        self.assertEqual(receipt["missing_baseline_test_ids"], ["b"])

    def test_explicit_environment_error_is_fail_closed(self):
        before = snapshot([("a", "PASS", None)])
        after = snapshot([("a", "PASS", None)])
        receipt = compare_snapshots(
            before,
            after,
            environment_errors=["TRUSTED_REPOSITORY_WORKTREE_DIRTY"],
        )
        self.assertEqual(receipt["classification"], "TEST_ENVIRONMENT_INVALID")

    def test_runtime_mismatch_is_environment_invalid(self):
        before = snapshot([("a", "PASS", None)], python_version="3.11.0")
        after = snapshot([("a", "PASS", None)], python_version="3.13.0")
        receipt = compare_snapshots(before, after)
        self.assertEqual(receipt["classification"], "TEST_ENVIRONMENT_INVALID")
        self.assertIn("PYTHON_RUNTIME_MISMATCH", receipt["environment_errors"])

    def test_volatile_paths_addresses_and_line_numbers_normalize(self):
        one = (
            'File "/tmp/a/work/repo/test.py", line 12, in test_x\n'
            "AssertionError: object 0xABCDEF"
        )
        two = (
            'File "/tmp/b/work/repo/test.py", line 998, in test_x\n'
            "AssertionError: object 0x123456"
        )
        normalized_one = normalize_failure_text(one, roots=["/tmp/a/work/repo"])
        normalized_two = normalize_failure_text(two, roots=["/tmp/b/work/repo"])
        self.assertEqual(normalized_one, normalized_two)
        self.assertEqual(
            failure_fingerprint("FAIL", one, roots=["/tmp/a/work/repo"]),
            failure_fingerprint("FAIL", two, roots=["/tmp/b/work/repo"]),
        )

    def test_semantically_different_failure_messages_change_fingerprint(self):
        left = failure_fingerprint("FAIL", "AssertionError: expected A")
        right = failure_fingerprint("FAIL", "AssertionError: expected B")
        self.assertNotEqual(left, right)

    def test_tampered_snapshot_digest_fails_closed(self):
        before = snapshot([("a", "PASS", None)])
        after = snapshot([("a", "PASS", None)])
        before["state_digest"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "STATE_DIGEST_MISMATCH"):
            compare_snapshots(before, after)

    def test_receipt_is_deterministic_for_same_inputs(self):
        before = snapshot(
            [("a", "PASS", None), ("b", "FAIL", "a" * 64)]
        )
        after = snapshot(
            [("a", "PASS", None), ("b", "FAIL", "a" * 64)]
        )
        meta = {
            "repository": "example/repo",
            "initial_main_sha": "1" * 40,
            "final_main_sha": "1" * 40,
            "initial_candidate_sha": "2" * 40,
            "final_candidate_sha": "2" * 40,
            "merge_base_sha": "3" * 40,
            "integration_commit_sha": "4" * 40,
            "integration_parent_shas": ["1" * 40, "2" * 40],
            "main_tree_sha": "5" * 40,
            "integrated_tree_sha": "6" * 40,
        }
        commands = command_snapshot([("CONTROL", 1, "d" * 64)])
        self.assertEqual(
            compare_snapshots(
                before,
                after,
                metadata=meta,
                baseline_commands=commands,
                integrated_commands=commands,
            ),
            compare_snapshots(
                before,
                after,
                metadata=meta,
                baseline_commands=commands,
                integrated_commands=commands,
            ),
        )

    def test_authority_flags_are_all_false(self):
        receipt = compare_snapshots(
            snapshot([("a", "PASS", None)]),
            snapshot([("a", "PASS", None)]),
        )
        self.assertEqual(receipt["authority"], AUTHORITY_FLAGS)
        self.assertTrue(
            all(value is False for value in receipt["authority"].values())
        )

    def test_schema_is_closed_and_authority_is_const_false(self):
        self.assertFalse(SCHEMA["additionalProperties"])
        authority = SCHEMA["properties"]["authority"]
        self.assertFalse(authority["additionalProperties"])
        for field in authority["required"]:
            self.assertIs(authority["properties"][field]["const"], False)
        for required in (
            "baseline_command_state_digest",
            "integrated_command_state_digest",
            "candidate_introduced_command_failures",
            "candidate_modified_baseline_command_failures",
        ):
            self.assertIn(required, SCHEMA["required"])

    def test_main_or_candidate_drift_can_be_injected_as_environment_invalid(self):
        before = snapshot([("a", "PASS", None)])
        after = deepcopy(before)
        receipt = compare_snapshots(
            before,
            after,
            environment_errors=[
                "CURRENT_MAIN_DRIFT_DURING_PROOF",
                "CANDIDATE_HEAD_DRIFT_DURING_PROOF",
            ],
        )
        self.assertEqual(receipt["classification"], "TEST_ENVIRONMENT_INVALID")
        self.assertEqual(len(receipt["environment_errors"]), 2)

    def test_baseline_failure_status_change_is_modified_not_preserved(self):
        before = snapshot([("a", "FAIL", "a" * 64)])
        after = snapshot([("a", "ERROR", "a" * 64)])
        receipt = compare_snapshots(before, after)
        self.assertEqual(
            receipt["classification"],
            "CANDIDATE_MODIFIED_BASELINE_FAILURE",
        )

    def test_subtest_outcome_uses_stable_parent_id(self):
        passing = record_subtest_probe(False)
        failing = record_subtest_probe(True)
        self.assertEqual(set(passing), set(failing))
        self.assertEqual(len(passing), 1)
        test_id = next(iter(passing))
        self.assertEqual(passing[test_id]["status"], "PASS")
        self.assertEqual(failing[test_id]["status"], "FAIL")
        self.assertIsNone(passing[test_id]["failure_fingerprint"])
        self.assertRegex(
            failing[test_id]["failure_fingerprint"],
            r"^[0-9a-f]{64}$",
        )

    def test_subtest_pass_to_fail_is_candidate_introduced_failure(self):
        passing = record_subtest_probe(False)
        failing = record_subtest_probe(True)
        before = snapshot(
            [
                (test_id, row["status"], row["failure_fingerprint"])
                for test_id, row in passing.items()
            ]
        )
        after = snapshot(
            [
                (test_id, row["status"], row["failure_fingerprint"])
                for test_id, row in failing.items()
            ]
        )
        receipt = compare_snapshots(before, after)
        self.assertEqual(receipt["classification"], "CANDIDATE_INTRODUCED_FAILURE")
        self.assertEqual(
            receipt["candidate_introduced_failures"][0]["test_id"],
            next(iter(passing)),
        )

    def test_preserved_baseline_command_failure_is_visible_but_not_regression(self):
        tests = snapshot([("a", "PASS", None)])
        commands = command_snapshot([("CONTROL", 1, "a" * 64)])
        receipt = compare_snapshots(
            tests,
            tests,
            baseline_commands=commands,
            integrated_commands=commands,
        )
        self.assertEqual(receipt["classification"], FINAL_PASS)
        self.assertEqual(
            receipt["baseline_command_failures_preserved"][0]["command_id"],
            "CONTROL",
        )
        self.assertFalse(receipt["baseline_declared_healthy"])

    def test_passing_baseline_command_to_failure_blocks(self):
        tests = snapshot([("a", "PASS", None)])
        before = command_snapshot([("CONTROL", 0, None)])
        after = command_snapshot([("CONTROL", 2, "b" * 64)])
        receipt = compare_snapshots(
            tests,
            tests,
            baseline_commands=before,
            integrated_commands=after,
        )
        self.assertEqual(receipt["classification"], "CANDIDATE_INTRODUCED_FAILURE")
        self.assertEqual(
            receipt["candidate_introduced_command_failures"][0]["command_id"],
            "CONTROL",
        )

    def test_modified_baseline_command_failure_blocks(self):
        tests = snapshot([("a", "PASS", None)])
        before = command_snapshot([("CONTROL", 2, "a" * 64)])
        after = command_snapshot([("CONTROL", 2, "b" * 64)])
        receipt = compare_snapshots(
            tests,
            tests,
            baseline_commands=before,
            integrated_commands=after,
        )
        self.assertEqual(
            receipt["classification"],
            "CANDIDATE_MODIFIED_BASELINE_FAILURE",
        )

    def test_baseline_command_improvement_is_recorded(self):
        tests = snapshot([("a", "PASS", None)])
        before = command_snapshot([("CONTROL", 2, "a" * 64)])
        after = command_snapshot([("CONTROL", 0, None)])
        receipt = compare_snapshots(
            tests,
            tests,
            baseline_commands=before,
            integrated_commands=after,
        )
        self.assertEqual(receipt["classification"], FINAL_PASS)
        self.assertEqual(
            receipt["command_improvements"][0]["command_id"],
            "CONTROL",
        )

    def test_command_set_mismatch_fails_closed(self):
        tests = snapshot([("a", "PASS", None)])
        before = command_snapshot([("CONTROL", 0, None)])
        after = command_snapshot([("OTHER", 0, None)])
        with self.assertRaisesRegex(RuntimeError, "COMMAND_SET_MISMATCH"):
            compare_snapshots(
                tests,
                tests,
                baseline_commands=before,
                integrated_commands=after,
            )

    def test_tampered_command_digest_fails_closed(self):
        tests = snapshot([("a", "PASS", None)])
        commands = command_snapshot([("CONTROL", 1, "a" * 64)])
        commands["state_digest"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "COMMAND_STATE_DIGEST_MISMATCH"):
            compare_snapshots(
                tests,
                tests,
                baseline_commands=commands,
                integrated_commands=commands,
            )

    def test_environment_invalid_receipt_is_machine_readable_and_non_authorizing(self):
        receipt = environment_invalid_receipt("REMOTE_REF_UNRESOLVED:branch")
        self.assertEqual(receipt["classification"], "TEST_ENVIRONMENT_INVALID")
        self.assertEqual(
            receipt["environment_errors"],
            ["REMOTE_REF_UNRESOLVED:branch"],
        )
        self.assertEqual(receipt["baseline_command_count"], 0)
        self.assertEqual(receipt["integrated_command_count"], 0)
        self.assertTrue(
            all(value is False for value in receipt["authority"].values())
        )
        self.assertRegex(receipt["receipt_digest"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
