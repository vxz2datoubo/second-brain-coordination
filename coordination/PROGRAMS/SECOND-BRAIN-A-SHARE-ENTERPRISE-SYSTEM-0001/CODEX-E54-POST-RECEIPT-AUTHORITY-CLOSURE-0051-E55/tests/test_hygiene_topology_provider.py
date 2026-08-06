from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
_TEMPORARIES: list[tempfile.TemporaryDirectory[str]] = []

from e55_authority.authority import AuthorityError  # noqa: E402
from e55_authority.hygiene import is_forbidden_path, scan_commit_range  # noqa: E402
from e55_authority.provider import DownloadedArtifact, validate_provider_evidence  # noqa: E402
from e55_authority.topology import RouteExpectation, verify_final_receipt  # noqa: E402


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def make_repo() -> Path:
    temporary = tempfile.TemporaryDirectory(prefix="e55-git-")
    repo = Path(temporary.name)
    _TEMPORARIES.append(temporary)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "e55@example.invalid")
    git(repo, "config", "user.name", "E55 Test")
    return repo


def commit_file(repo: Path, path: str, content: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    git(repo, "add", "--", path)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


class HygieneTests(unittest.TestCase):
    def test_forbidden_classes_cover_suffixes_and_directories(self) -> None:
        blocked = (
            "x.generated", "x.generated.json", "x.tmp", ".coverage", "x.sqlite", "x.jsonl",
            "artifacts/x.txt", "generated/x.txt", "tmp/x.txt", ".pytest_cache/x", "__pycache__/x.pyc",
        )
        for path in blocked:
            with self.subTest(path=path):
                self.assertTrue(is_forbidden_path(path))
        self.assertFalse(is_forbidden_path("coordination/report.md"))

    def test_add_then_delete_generated_file_remains_in_history(self) -> None:
        repo = make_repo()
        base = commit_file(repo, "keep.txt", "base", "base")
        commit_file(repo, "notes/output.generated", "transient", "add generated")
        (repo / "notes/output.generated").unlink()
        git(repo, "add", "-u")
        git(repo, "commit", "-q", "-m", "remove generated")
        report = scan_commit_range(repo, base)
        self.assertFalse(report.clean)
        self.assertTrue(any(item.path == "notes/output.generated" for item in report.forbidden_history_paths))

    def test_rename_and_copy_destination_are_checked(self) -> None:
        repo = make_repo()
        base = commit_file(repo, "safe.txt", "base", "base")
        commit_file(repo, "artifacts/copied.txt", "base", "copy artifact")
        report = scan_commit_range(repo, base)
        self.assertTrue(any(item.path == "artifacts/copied.txt" for item in report.forbidden_history_paths))

    def test_merge_parent_history_is_not_silently_hidden(self) -> None:
        repo = make_repo()
        base = commit_file(repo, "base.txt", "base", "base")
        git(repo, "checkout", "-q", "-b", "topic")
        commit_file(repo, "tmp/feature.tmp", "temporary", "feature transient")
        git(repo, "checkout", "-q", "master")
        commit_file(repo, "master.txt", "master", "master change")
        git(repo, "merge", "--no-ff", "-m", "merge topic", "topic")
        report = scan_commit_range(repo, base)
        self.assertTrue(any(item.path == "tmp/feature.tmp" for item in report.forbidden_history_paths))


class ProviderEvidenceTests(unittest.TestCase):
    def _fixture(self):
        versions, seeds = ("3.11", "3.13"), ("0", "1", "777")
        head = "a" * 40
        run = {"run_id": 99, "head_sha": head, "workflow": "e55.yml", "branch": "codex/e55", "conclusion": "success"}
        jobs, artifacts, digests = [], [], []
        artifact_id = 100
        job_id = 1
        mutations = ["M1", "M2"]
        for version in versions:
            for seed in seeds:
                jobs.append({
                    "job_id": job_id, "name": f"authority / py{version} / seed={seed}", "python_version": version,
                    "hash_seed": seed, "conclusion": "success", "head_sha": head, "test_count": 42, "mutation_ids": mutations,
                })
                for kind in ("canonical", "environment"):
                    payload = json.dumps({"kind": kind, "version": version, "seed": seed}, sort_keys=True).encode("utf-8")
                    digest = sha256(payload).hexdigest()
                    digests.append(digest)
                    artifacts.append(DownloadedArtifact(artifact_id, f"{kind}-py{version}-seed{seed}", job_id, payload, digest))
                    artifact_id += 1
                job_id += 1
        combined = sha256("".join(sorted(digests)).encode("ascii")).hexdigest()
        compare = json.dumps({"artifact_digests": sorted(digests), "combined_sha256": combined}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifacts.append(DownloadedArtifact(artifact_id, "provider-compare", None, compare, sha256(compare).hexdigest()))
        return run, jobs, artifacts, head, mutations, combined

    def test_metadata_and_downloaded_bytes_are_bound(self) -> None:
        run, jobs, artifacts, head, mutations, combined = self._fixture()
        self.assertEqual(validate_provider_evidence(run, jobs, artifacts, expected_head=head, expected_workflow="e55.yml", expected_branch="codex/e55", expected_test_count=42, expected_mutation_ids=mutations), combined)

    def test_changed_head_or_job_name_is_rejected(self) -> None:
        run, jobs, artifacts, head, mutations, _ = self._fixture()
        run = {**run, "head_sha": "b" * 40}
        with self.assertRaises(AuthorityError):
            validate_provider_evidence(run, jobs, artifacts, expected_head=head, expected_workflow="e55.yml", expected_branch="codex/e55", expected_test_count=42, expected_mutation_ids=mutations)
        run, jobs, artifacts, head, mutations, _ = self._fixture()
        jobs[0] = {**jobs[0], "name": "wrong"}
        with self.assertRaises(AuthorityError):
            validate_provider_evidence(run, jobs, artifacts, expected_head=head, expected_workflow="e55.yml", expected_branch="codex/e55", expected_test_count=42, expected_mutation_ids=mutations)

    def test_missing_mutation_or_tampered_artifact_bytes_are_rejected(self) -> None:
        run, jobs, artifacts, head, mutations, _ = self._fixture()
        jobs[0] = {**jobs[0], "mutation_ids": ["M1"]}
        with self.assertRaises(AuthorityError):
            validate_provider_evidence(run, jobs, artifacts, expected_head=head, expected_workflow="e55.yml", expected_branch="codex/e55", expected_test_count=42, expected_mutation_ids=mutations)
        run, jobs, artifacts, head, mutations, _ = self._fixture()
        first = artifacts[0]
        artifacts[0] = DownloadedArtifact(first.artifact_id, first.name, first.job_id, b"tampered", first.recorded_sha256)
        with self.assertRaises(AuthorityError):
            validate_provider_evidence(run, jobs, artifacts, expected_head=head, expected_workflow="e55.yml", expected_branch="codex/e55", expected_test_count=42, expected_mutation_ids=mutations)


class TopologyTests(unittest.TestCase):
    def _fixture(self):
        repo = make_repo()
        base = commit_file(repo, "base.txt", "base", "base")
        plan = commit_file(repo, "plan.md", "plan", "plan")
        tested = commit_file(repo, "source.py", "assert True\n", "tested")
        receipt_path = "receipt/AMED.yaml"
        receipt = {
            "task_id": "E55", "route_epoch": 57, "issue": 179, "pull_request": 182, "branch": "codex/e55",
            "base_sha": base, "plan_sha": plan, "tested_sha": tested, "workflow": "e55.yml", "completion_signal": "READY", "receipt_paths": [receipt_path],
        }
        receipt_sha = commit_file(repo, receipt_path, json.dumps(receipt, sort_keys=True), "receipt")
        expected = RouteExpectation("E55", 57, 179, 182, "codex/e55", base, plan, "e55.yml", "READY", (receipt_path,))
        tree = git(repo, "rev-parse", f"{receipt_sha}^{{tree}}")
        anchor = {
            "task_id": "E55", "route_epoch": 57, "issue": 179, "pull_request": 182, "branch": "codex/e55", "workflow": "e55.yml",
            "completion_signal": "READY", "receipt_head_sha": receipt_sha, "receipt_parent_sha": tested, "receipt_tree_sha": tree,
            "provider_compare_sha256": "c" * 64,
        }
        return repo, receipt_sha, expected, receipt, anchor

    def test_exact_base_plan_tested_receipt_topology_passes(self) -> None:
        repo, receipt_sha, expected, receipt, anchor = self._fixture()
        report = verify_final_receipt(repo, receipt_sha, expected, receipt, anchor)
        self.assertEqual(report.parent_sha, receipt["tested_sha"])
        self.assertTrue(report.externally_bound)

    def test_actual_receipt_parent_cannot_be_faked_in_body_or_anchor(self) -> None:
        repo, receipt_sha, expected, receipt, anchor = self._fixture()
        receipt = {**receipt, "tested_sha": expected.plan_sha}
        with self.assertRaises(AuthorityError):
            verify_final_receipt(repo, receipt_sha, expected, receipt, anchor)

    def test_route_epoch_and_exact_receipt_path_set_fail_closed(self) -> None:
        repo, receipt_sha, expected, receipt, anchor = self._fixture()
        with self.assertRaises(AuthorityError):
            verify_final_receipt(repo, receipt_sha, expected, {**receipt, "route_epoch": 58}, anchor)
        with self.assertRaises(AuthorityError):
            verify_final_receipt(repo, receipt_sha, expected, {**receipt, "receipt_paths": []}, anchor)


if __name__ == "__main__":
    unittest.main()
