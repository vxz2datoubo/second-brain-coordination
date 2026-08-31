from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.verify_creative_executor_checkpoint import run_clean_reproduction


class ExecutorCheckpointTests(unittest.TestCase):
    def _repo(self, root: Path) -> str:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "executor@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Executor Test"], cwd=root, check=True)
        (root / "tracked.txt").write_text("offline\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            stdout=subprocess.PIPE, text=True,
        ).stdout.strip()

    def test_clean_exact_head_records_hashed_command_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            head = self._repo(repo)
            receipt = run_clean_reproduction(
                repo,
                expected_head=head,
                baseline=head,
                policy_floor_ref=head,
                agent_id="WORKBUDDY",
                command_plan=[("offline_probe", [sys.executable, "-c", "print('ok')"])],
            )
            self.assertEqual(receipt["status"], "PASS")
            self.assertFalse(receipt["independent_acceptance"])
            self.assertEqual(receipt["verification_class"], "EXECUTOR_CLEAN_REPRODUCTION")
            command = receipt["commands"][0]
            self.assertEqual(command["exit_code"], 0)
            self.assertEqual(len(command["stdout_sha256"]), 64)
            self.assertNotIn("stdout", command)

    def test_wrong_head_dirty_tree_and_failed_command_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            head = self._repo(repo)
            wrong = "0" * 40
            mismatch = run_clean_reproduction(
                repo, expected_head=wrong, baseline=head, policy_floor_ref=head,
                agent_id="CODEX", command_plan=[],
            )
            self.assertEqual(mismatch["failure_stage"], "PRE_HEAD_IDENTITY")

            (repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            dirty = run_clean_reproduction(
                repo, expected_head=head, baseline=head, policy_floor_ref=head,
                agent_id="CODEX", command_plan=[],
            )
            self.assertEqual(dirty["failure_stage"], "PRE_WORKTREE_CLEANLINESS")
            (repo / "untracked.txt").unlink()

            failed = run_clean_reproduction(
                repo,
                expected_head=head,
                baseline=head,
                policy_floor_ref=head,
                agent_id="WORKBUDDY",
                command_plan=[
                    ("fails", [sys.executable, "-c", "raise SystemExit(7)"]),
                    ("must_not_run", [sys.executable, "-c", "raise SystemExit(0)"]),
                ],
            )
            self.assertEqual(failed["status"], "FAIL")
            self.assertEqual(failed["failure_stage"], "fails")
            self.assertEqual(len(failed["commands"]), 1)

    def test_remote_ref_must_bind_the_same_exact_head(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            head = self._repo(repo)
            subprocess.run(
                ["git", "update-ref", "refs/remotes/origin/candidate", head],
                cwd=repo, check=True,
            )
            passed = run_clean_reproduction(
                repo, expected_head=head, baseline=head, policy_floor_ref=head,
                agent_id="WORKBUDDY", remote_ref="refs/remotes/origin/candidate",
                command_plan=[],
            )
            self.assertEqual(passed["status"], "PASS")
            subprocess.run(
                ["git", "commit", "--allow-empty", "-q", "-m", "later"], cwd=repo, check=True,
            )
            later = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                stdout=subprocess.PIPE, text=True,
            ).stdout.strip()
            mismatch = run_clean_reproduction(
                repo, expected_head=later, baseline=head, policy_floor_ref=head,
                agent_id="CODEX", remote_ref="refs/remotes/origin/candidate",
                command_plan=[],
            )
            self.assertEqual(mismatch["failure_stage"], "PRE_REMOTE_IDENTITY")


if __name__ == "__main__":
    unittest.main()
