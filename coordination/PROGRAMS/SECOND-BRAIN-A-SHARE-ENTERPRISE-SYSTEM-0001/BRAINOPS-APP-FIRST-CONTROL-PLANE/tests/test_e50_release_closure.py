"""E50 test-first closure for real git graph and provider authority."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.e50_release_verifier import (  # noqa: E402
    E50GitGraphCode,
    E50ProviderAuthorityCode,
    evaluate_git_ancestry,
    reject_caller_provider_document,
)


class E50ReleaseClosureTests(unittest.TestCase):
    def _git(self, repository: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return completed.stdout.strip()

    def _commit(self, repository: Path, name: str, content: str) -> str:
        (repository / name).write_text(content, encoding="utf-8")
        self._git(repository, "add", name)
        self._git(repository, "commit", "-m", name)
        return self._git(repository, "rev-parse", "HEAD")

    def test_exit_status_drives_real_positive_and_negative_git_graphs(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            self._git(repository, "init", "-q")
            self._git(repository, "config", "user.email", "e50@example.invalid")
            self._git(repository, "config", "user.name", "E50 Test")
            base = self._commit(repository, "base.txt", "base\n")
            plan = self._commit(repository, "plan.txt", "plan\n")
            tested = self._commit(repository, "tested.txt", "tested\n")
            self._git(repository, "checkout", "-q", "-b", "unrelated", base)
            unrelated = self._commit(repository, "unrelated.txt", "unrelated\n")

            positive = evaluate_git_ancestry(repository, plan, tested)
            negative = evaluate_git_ancestry(repository, unrelated, tested)

        self.assertEqual(positive.code, E50GitGraphCode.ANCESTOR)
        self.assertEqual(negative.code, E50GitGraphCode.NOT_ANCESTOR)

    def test_fully_forged_provider_document_is_not_provider_authority(self):
        forged = {
            "provider_source": "EXTERNAL_READ_ONLY_API",
            "declared_success": False,
            "tested_head": "a" * 40,
            "receipt_head": "b" * 40,
            "remote_branch_head": "b" * 40,
            "runs": [{"run_id": 1, "conclusion": "success"}],
        }

        result = reject_caller_provider_document(forged)

        self.assertEqual(result.code, E50ProviderAuthorityCode.UNTRUSTED_CALLER_DOCUMENT)

