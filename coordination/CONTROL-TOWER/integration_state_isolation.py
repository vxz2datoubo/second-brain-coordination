from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Iterable, Mapping

SNAPSHOT_SCHEMA = "TestStateSnapshot/v1"
RECEIPT_SCHEMA = "IntegrationStateIsolationReceipt/v1"
PASS = "PASS"
NONPASS_STATUSES = {"FAIL", "ERROR", "SKIP", "XFAIL", "XPASS"}
FINAL_PASS = "PASS_NO_CANDIDATE_REGRESSION"
AUTHORITY_FLAGS = {
    "review_authorized": False,
    "ready_transition_authorized": False,
    "merge_authorized": False,
    "release_authorized": False,
    "domain_write_authorized": False,
    "trading_authorized": False,
}
_STATUS_PRECEDENCE = {
    PASS: 0,
    "XFAIL": 1,
    "SKIP": 2,
    "XPASS": 3,
    "FAIL": 4,
    "ERROR": 5,
}


class IsolationError(RuntimeError):
    """Fail-closed integration proof error."""


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def normalize_failure_text(text: str, *, roots: Iterable[str | Path] = ()) -> str:
    """Remove volatile path/address/line-number noise without erasing failure semantics."""

    normalized = str(text or "").replace("\\", "/")
    candidates = {str(Path(root).resolve()).replace("\\", "/") for root in roots if str(root)}
    candidates.add(str(Path(tempfile.gettempdir()).resolve()).replace("\\", "/"))
    for root in sorted(candidates, key=len, reverse=True):
        if root:
            normalized = normalized.replace(root, "<ROOT>")
    normalized = re.sub(r"0x[0-9A-Fa-f]+", "0x<ADDR>", normalized)
    normalized = re.sub(r"\bline\s+\d+\b", "line <LINE>", normalized)
    normalized = re.sub(r"\\?\\?\\Temp\\[^\s\"']+", "<ROOT>", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    return normalized.strip()


def failure_fingerprint(kind: str, text: str, *, roots: Iterable[str | Path] = ()) -> str:
    return _sha256({"kind": kind, "normalized": normalize_failure_text(text, roots=roots)})


class RecordingResult(unittest.TestResult):
    """Aggregate unittest and subTest outcomes under stable parent test IDs."""

    def __init__(self, *, roots: Iterable[str | Path]) -> None:
        super().__init__()
        self.roots = tuple(roots)
        self.records: dict[str, dict[str, Any]] = {}
        self.environment_errors: list[str] = []
        self._pending: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _parent_test(test: unittest.case.TestCase) -> unittest.case.TestCase:
        parent = getattr(test, "test_case", None)
        return parent if parent is not None else test

    def startTest(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        super().startTest(test)
        test_id = test.id()
        if test_id in self._pending:
            self.environment_errors.append(f"DUPLICATE_PENDING_TEST_ID:{test_id}")
        self._pending[test_id] = {"status": PASS, "details": []}

    def _record_event(self, test: unittest.case.TestCase, status: str, detail: str | None = None) -> None:
        parent = self._parent_test(test)
        test_id = parent.id()
        pending = self._pending.setdefault(test_id, {"status": PASS, "details": []})
        if _STATUS_PRECEDENCE[status] > _STATUS_PRECEDENCE[pending["status"]]:
            pending["status"] = status
        if detail:
            pending["details"].append(detail)

    def addSuccess(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        super().addSuccess(test)
        self._record_event(test, PASS)

    def addFailure(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:  # noqa: N802
        super().addFailure(test, err)
        self._record_event(test, "FAIL", self._exc_info_to_string(err, self._parent_test(test)))

    def addError(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:  # noqa: N802
        super().addError(test, err)
        self._record_event(test, "ERROR", self._exc_info_to_string(err, self._parent_test(test)))

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:  # noqa: N802
        super().addSkip(test, reason)
        parent = self._parent_test(test)
        prefix = f"SUBTEST:{test.id()}\n" if parent is not test else ""
        self._record_event(parent, "SKIP", f"{prefix}{reason}")

    def addExpectedFailure(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:  # noqa: N802
        super().addExpectedFailure(test, err)
        self._record_event(test, "XFAIL", self._exc_info_to_string(err, self._parent_test(test)))

    def addUnexpectedSuccess(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        super().addUnexpectedSuccess(test)
        self._record_event(test, "XPASS", "unexpected success")

    def addSubTest(
        self,
        test: unittest.case.TestCase,
        subtest: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, Any] | None,
    ) -> None:  # noqa: N802
        super().addSubTest(test, subtest, err)
        if err is None:
            return
        status = "FAIL" if issubclass(err[0], test.failureException) else "ERROR"
        detail = f"SUBTEST:{subtest.id()}\n{self._exc_info_to_string(err, test)}"
        self._record_event(test, status, detail)

    def stopTest(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        test_id = test.id()
        pending = self._pending.pop(test_id, {"status": PASS, "details": []})
        if test_id in self.records:
            self.environment_errors.append(f"DUPLICATE_TEST_ID:{test_id}")
        else:
            status = pending["status"]
            details = "\n---\n".join(pending["details"])
            self.records[test_id] = {
                "test_id": test_id,
                "status": status,
                "failure_fingerprint": None if status == PASS else failure_fingerprint(status, details, roots=self.roots),
            }
        if "unittest.loader._FailedTest" in test_id or test.__class__.__name__ == "_FailedTest":
            self.environment_errors.append(f"COLLECTION_OR_IMPORT_FAILURE:{test_id}")
        super().stopTest(test)


def _snapshot_payload(records: Mapping[str, Mapping[str, Any]], *, python_version: str, environment_errors: list[str]) -> dict[str, Any]:
    ordered = [dict(records[key]) for key in sorted(records)]
    ids = [item["test_id"] for item in ordered]
    return {
        "schema": SNAPSHOT_SCHEMA,
        "python_version": python_version,
        "test_count": len(ordered),
        "test_id_digest": _sha256(ids),
        "state_digest": _sha256(ordered),
        "environment_errors": sorted(set(environment_errors)),
        "results": ordered,
    }


def collect_snapshot(repo_root: str | Path, *, test_dir: str = "coordination/CONTROL-TOWER/tests", pattern: str = "test_*.py") -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    tests = (repo / test_dir).resolve()
    if not tests.is_dir():
        raise IsolationError(f"TEST_DIRECTORY_MISSING:{tests}")
    control_tower = (repo / "coordination/CONTROL-TOWER").resolve()
    old_cwd = Path.cwd()
    old_path = list(sys.path)
    try:
        os.chdir(repo)
        sys.path.insert(0, str(control_tower))
        suite = unittest.defaultTestLoader.discover(str(tests), pattern=pattern)
        result = RecordingResult(roots=(repo, tests, control_tower))
        suite.run(result)
        if result._pending:
            result.environment_errors.extend(f"UNFINALIZED_TEST_ID:{test_id}" for test_id in sorted(result._pending))
        return _snapshot_payload(
            result.records,
            python_version=".".join(str(part) for part in sys.version_info[:3]),
            environment_errors=result.environment_errors,
        )
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path


def _index_snapshot(snapshot: Mapping[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise IsolationError(f"{label}:INVALID_SNAPSHOT_SCHEMA")
    raw_results = snapshot.get("results")
    if not isinstance(raw_results, list):
        raise IsolationError(f"{label}:RESULTS_NOT_LIST")
    index: dict[str, dict[str, Any]] = {}
    for raw in raw_results:
        if not isinstance(raw, Mapping):
            raise IsolationError(f"{label}:INVALID_RESULT_SHAPE")
        test_id = str(raw.get("test_id") or "")
        status = str(raw.get("status") or "")
        if not test_id or status not in {PASS, *NONPASS_STATUSES}:
            raise IsolationError(f"{label}:INVALID_RESULT:{test_id}:{status}")
        if test_id in index:
            raise IsolationError(f"{label}:DUPLICATE_TEST_ID:{test_id}")
        index[test_id] = dict(raw)
    if snapshot.get("test_count") != len(index):
        raise IsolationError(f"{label}:TEST_COUNT_MISMATCH")
    if snapshot.get("test_id_digest") != _sha256(sorted(index)):
        raise IsolationError(f"{label}:TEST_ID_DIGEST_MISMATCH")
    ordered = [index[key] for key in sorted(index)]
    if snapshot.get("state_digest") != _sha256(ordered):
        raise IsolationError(f"{label}:STATE_DIGEST_MISMATCH")
    return index


def _same_nonpass(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        left.get("status") == right.get("status")
        and left.get("status") != PASS
        and left.get("failure_fingerprint") == right.get("failure_fingerprint")
    )


def compare_snapshots(
    baseline: Mapping[str, Any],
    integrated: Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
    environment_errors: Iterable[str] = (),
) -> dict[str, Any]:
    baseline_index = _index_snapshot(baseline, label="BASELINE")
    integrated_index = _index_snapshot(integrated, label="INTEGRATED")

    env = set(str(item) for item in environment_errors if str(item))
    env.update(str(item) for item in baseline.get("environment_errors", []) if str(item))
    env.update(str(item) for item in integrated.get("environment_errors", []) if str(item))
    if baseline.get("python_version") != integrated.get("python_version"):
        env.add("PYTHON_RUNTIME_MISMATCH")

    missing = sorted(set(baseline_index) - set(integrated_index))
    if missing:
        env.update(f"MISSING_BASELINE_TEST_ID:{test_id}" for test_id in missing)

    candidate_only = sorted(set(integrated_index) - set(baseline_index))
    candidate_only_failures = [test_id for test_id in candidate_only if integrated_index[test_id]["status"] != PASS]

    preserved: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    introduced: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    for test_id in sorted(set(baseline_index) & set(integrated_index)):
        before = baseline_index[test_id]
        after = integrated_index[test_id]
        before_status = before["status"]
        after_status = after["status"]
        if before_status == PASS and after_status == PASS:
            classification = "UNCHANGED_PASS"
        elif before_status == PASS and after_status != PASS:
            classification = "CANDIDATE_INTRODUCED_FAILURE"
            introduced.append({"test_id": test_id, "integrated_status": after_status, "failure_fingerprint": after.get("failure_fingerprint")})
        elif before_status != PASS and after_status == PASS:
            classification = "CANDIDATE_BASELINE_IMPROVEMENT"
            improvements.append({"test_id": test_id, "baseline_status": before_status, "baseline_failure_fingerprint": before.get("failure_fingerprint")})
        elif _same_nonpass(before, after):
            classification = "BASELINE_CURRENT_MAIN_FAILURE"
            preserved.append({"test_id": test_id, "status": before_status, "failure_fingerprint": before.get("failure_fingerprint")})
        else:
            classification = "CANDIDATE_MODIFIED_BASELINE_FAILURE"
            modified.append(
                {
                    "test_id": test_id,
                    "baseline_status": before_status,
                    "integrated_status": after_status,
                    "baseline_failure_fingerprint": before.get("failure_fingerprint"),
                    "integrated_failure_fingerprint": after.get("failure_fingerprint"),
                }
            )
        observations.append(
            {
                "test_id": test_id,
                "baseline_status": before_status,
                "integrated_status": after_status,
                "classification": classification,
            }
        )

    if env:
        final = "TEST_ENVIRONMENT_INVALID"
    elif candidate_only_failures:
        final = "CANDIDATE_EXACT_HEAD_FAILURE"
    elif introduced:
        final = "CANDIDATE_INTRODUCED_FAILURE"
    elif modified:
        final = "CANDIDATE_MODIFIED_BASELINE_FAILURE"
    else:
        final = FINAL_PASS

    meta = dict(metadata or {})
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "repository": meta.get("repository"),
        "initial_main_sha": meta.get("initial_main_sha"),
        "final_main_sha": meta.get("final_main_sha"),
        "initial_candidate_sha": meta.get("initial_candidate_sha"),
        "final_candidate_sha": meta.get("final_candidate_sha"),
        "merge_base_sha": meta.get("merge_base_sha"),
        "integration_commit_sha": meta.get("integration_commit_sha"),
        "integration_parent_shas": list(meta.get("integration_parent_shas") or []),
        "main_tree_sha": meta.get("main_tree_sha"),
        "integrated_tree_sha": meta.get("integrated_tree_sha"),
        "python_version": baseline.get("python_version"),
        "baseline_test_count": baseline.get("test_count"),
        "integrated_test_count": integrated.get("test_count"),
        "baseline_test_id_digest": baseline.get("test_id_digest"),
        "integrated_test_id_digest": integrated.get("test_id_digest"),
        "baseline_state_digest": baseline.get("state_digest"),
        "integrated_state_digest": integrated.get("state_digest"),
        "candidate_only_test_ids": candidate_only,
        "missing_baseline_test_ids": missing,
        "baseline_failures_preserved": preserved,
        "baseline_improvements": improvements,
        "candidate_introduced_failures": introduced,
        "candidate_modified_baseline_failures": modified,
        "candidate_exact_head_failures": candidate_only_failures,
        "environment_errors": sorted(env),
        "per_test_observations": observations,
        "classification": final,
        "baseline_declared_healthy": False,
        "authority": dict(AUTHORITY_FLAGS),
    }
    receipt["receipt_digest"] = _sha256({key: value for key, value in receipt.items() if key != "receipt_digest"})
    return receipt


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        raise IsolationError(f"GIT_COMMAND_FAILED:{' '.join(args)}:{proc.stderr.strip()}")
    return proc


def _git(repo: Path, *args: str) -> str:
    return _run(repo, *args).stdout.strip()


def _remote_sha(repo: Path, branch: str) -> str:
    output = _git(repo, "ls-remote", "origin", f"refs/heads/{branch}")
    fields = output.split()
    if len(fields) < 1 or not re.fullmatch(r"[0-9a-f]{40}", fields[0]):
        raise IsolationError(f"REMOTE_REF_UNRESOLVED:{branch}")
    return fields[0]


def _collect_via_subprocess(helper: Path, repo_root: Path, output: Path, test_dir: str, pattern: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(helper), "collect", "--repo-root", str(repo_root), "--test-dir", test_dir, "--pattern", pattern, "--output", str(output)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise IsolationError(f"SNAPSHOT_COLLECTION_FAILED:{repo_root}:{proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(output.read_text(encoding="utf-8"))


def run_proof(
    repo_root: str | Path,
    *,
    candidate_branch: str,
    test_dir: str = "coordination/CONTROL-TOWER/tests",
    pattern: str = "test_*.py",
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    helper = Path(__file__).resolve()
    environment_errors: list[str] = []
    metadata: dict[str, Any] = {"repository": _git(repo, "config", "--get", "remote.origin.url")}

    if _git(repo, "status", "--porcelain"):
        raise IsolationError("TRUSTED_REPOSITORY_WORKTREE_DIRTY")

    initial_main = _remote_sha(repo, "main")
    initial_candidate = _remote_sha(repo, candidate_branch)
    local_head = _git(repo, "rev-parse", "HEAD")
    if local_head != initial_candidate:
        raise IsolationError(f"LOCAL_HEAD_NOT_EXACT_REMOTE_CANDIDATE:{local_head}:{initial_candidate}")

    _run(repo, "fetch", "--no-tags", "origin", f"main:refs/remotes/origin/main", f"{candidate_branch}:refs/remotes/origin/{candidate_branch}")
    merge_base = _git(repo, "merge-base", initial_main, initial_candidate)
    main_tree = _git(repo, "rev-parse", f"{initial_main}^{{tree}}")

    metadata.update(
        {
            "initial_main_sha": initial_main,
            "initial_candidate_sha": initial_candidate,
            "merge_base_sha": merge_base,
            "main_tree_sha": main_tree,
        }
    )

    with tempfile.TemporaryDirectory(prefix="ci-state-isolation-") as temp_dir:
        temp = Path(temp_dir)
        base_root = temp / "baseline"
        integrated_root = temp / "integrated"
        base_json = temp / "baseline.json"
        integrated_json = temp / "integrated.json"
        try:
            _run(repo, "worktree", "add", "--detach", str(base_root), initial_main)
            _run(repo, "worktree", "add", "--detach", str(integrated_root), initial_main)
            if _git(base_root, "status", "--porcelain"):
                environment_errors.append("BASELINE_WORKTREE_DIRTY")
            merge_env = os.environ.copy()
            merge_env.update(
                {
                    "GIT_AUTHOR_NAME": "ci-state-isolation",
                    "GIT_AUTHOR_EMAIL": "ci-state-isolation@example.invalid",
                    "GIT_COMMITTER_NAME": "ci-state-isolation",
                    "GIT_COMMITTER_EMAIL": "ci-state-isolation@example.invalid",
                }
            )
            merge_proc = subprocess.run(
                ["git", "merge", "--no-ff", "--no-edit", initial_candidate],
                cwd=integrated_root,
                env=merge_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if merge_proc.returncode != 0:
                environment_errors.append("INTEGRATION_MERGE_FAILED")
                _run(integrated_root, "merge", "--abort", check=False)
                baseline = _collect_via_subprocess(helper, base_root, base_json, test_dir, pattern)
                integrated = baseline
                integration_commit = None
                parents: list[str] = []
                integrated_tree = None
            else:
                integration_commit = _git(integrated_root, "rev-parse", "HEAD")
                parents = _git(integrated_root, "show", "-s", "--format=%P", "HEAD").split()
                integrated_tree = _git(integrated_root, "rev-parse", "HEAD^{tree}")
                if _git(integrated_root, "status", "--porcelain"):
                    environment_errors.append("INTEGRATED_WORKTREE_DIRTY")
                if parents != [initial_main, initial_candidate]:
                    environment_errors.append("INTEGRATION_PARENT_MISMATCH")
                baseline = _collect_via_subprocess(helper, base_root, base_json, test_dir, pattern)
                integrated = _collect_via_subprocess(helper, integrated_root, integrated_json, test_dir, pattern)

            metadata.update(
                {
                    "integration_commit_sha": integration_commit,
                    "integration_parent_shas": parents,
                    "integrated_tree_sha": integrated_tree,
                }
            )
        finally:
            _run(repo, "worktree", "remove", "--force", str(base_root), check=False)
            _run(repo, "worktree", "remove", "--force", str(integrated_root), check=False)
            _run(repo, "worktree", "prune", check=False)

    final_main = _remote_sha(repo, "main")
    final_candidate = _remote_sha(repo, candidate_branch)
    metadata["final_main_sha"] = final_main
    metadata["final_candidate_sha"] = final_candidate
    if final_main != initial_main:
        environment_errors.append("CURRENT_MAIN_DRIFT_DURING_PROOF")
    if final_candidate != initial_candidate:
        environment_errors.append("CANDIDATE_HEAD_DRIFT_DURING_PROOF")

    return compare_snapshots(baseline, integrated, metadata=metadata, environment_errors=environment_errors)


def _write_json(path: str | Path, value: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IsolationError("JSON_ROOT_NOT_OBJECT")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canonical Control Tower CI state isolation helper")
    sub = parser.add_subparsers(dest="command", required=True)

    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--repo-root", required=True)
    collect_parser.add_argument("--test-dir", default="coordination/CONTROL-TOWER/tests")
    collect_parser.add_argument("--pattern", default="test_*.py")
    collect_parser.add_argument("--output", required=True)

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--integrated", required=True)
    compare_parser.add_argument("--metadata")
    compare_parser.add_argument("--output", required=True)

    proof_parser = sub.add_parser("proof")
    proof_parser.add_argument("--repo-root", required=True)
    proof_parser.add_argument("--candidate-branch", required=True)
    proof_parser.add_argument("--test-dir", default="coordination/CONTROL-TOWER/tests")
    proof_parser.add_argument("--pattern", default="test_*.py")
    proof_parser.add_argument("--output", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            snapshot = collect_snapshot(args.repo_root, test_dir=args.test_dir, pattern=args.pattern)
            _write_json(args.output, snapshot)
            return 0
        if args.command == "compare":
            metadata = _load_json(args.metadata) if args.metadata else {}
            receipt = compare_snapshots(_load_json(args.baseline), _load_json(args.integrated), metadata=metadata)
            _write_json(args.output, receipt)
            return 0 if receipt["classification"] == FINAL_PASS else 2
        if args.command == "proof":
            receipt = run_proof(args.repo_root, candidate_branch=args.candidate_branch, test_dir=args.test_dir, pattern=args.pattern)
            _write_json(args.output, receipt)
            print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
            return 0 if receipt["classification"] == FINAL_PASS else 2
    except IsolationError as exc:
        print(f"TEST_ENVIRONMENT_INVALID: {exc}", file=sys.stderr)
        return 3
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
