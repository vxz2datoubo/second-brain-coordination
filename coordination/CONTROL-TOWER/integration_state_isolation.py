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
COMMAND_SNAPSHOT_SCHEMA = "ControlCommandSnapshot/v1"
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
_CONTROL_COMMAND_IDS = (
    "CONTROL_TOWER_RECONCILE",
    "LANE_CLAIMS_VALIDATE",
    "CLAIM_PROJECTION_CHECK",
    "AUTH_WITNESS_LANE_C_ROUND_TRIP",
    "AUTH_WITNESS_LANE_B_ROUND_TRIP",
    "CODEX_ROUTE_WITNESS",
)


class IsolationError(RuntimeError):
    """Fail-closed integration proof error."""


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def normalize_failure_text(text: str, *, roots: Iterable[str | Path] = ()) -> str:
    """Remove only demonstrably volatile execution noise without erasing semantics."""

    normalized = str(text or "").replace("\\", "/")
    candidates = {str(Path(root).resolve()).replace("\\", "/") for root in roots if str(root)}
    candidates.add(str(Path(tempfile.gettempdir()).resolve()).replace("\\", "/"))
    for root in sorted(candidates, key=len, reverse=True):
        if root:
            normalized = normalized.replace(root, "<ROOT>")

    # Normalize only Python's default object repr identity address, e.g.
    # ``<Probe object at 0xABCDEF>``. Generic angle-bracket prose such as
    # ``<mask at 0x20>`` is semantic payload and must remain fingerprint-visible.
    normalized = re.sub(
        r"(<[^>\n]*\bobject\s+at\s+)0x[0-9A-Fa-f]+(?=>)",
        r"\g<1>0x<ADDR>",
        normalized,
    )

    # Normalize a line number only in a Python traceback frame. Prose such as
    # ``policy violation at line 12`` is semantic payload and must be preserved.
    normalized = re.sub(
        r'(File\s+"[^"\n]+",\s+line\s+)\d+(\s*,\s+in\s+[^\n]+)',
        r"\g<1><LINE>\g<2>",
        normalized,
    )
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

    def addFailure(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, Any],
    ) -> None:  # noqa: N802
        super().addFailure(test, err)
        self._record_event(test, "FAIL", self._exc_info_to_string(err, self._parent_test(test)))

    def addError(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, Any],
    ) -> None:  # noqa: N802
        super().addError(test, err)
        self._record_event(test, "ERROR", self._exc_info_to_string(err, self._parent_test(test)))

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:  # noqa: N802
        super().addSkip(test, reason)
        parent = self._parent_test(test)
        prefix = f"SUBTEST:{test.id()}\n" if parent is not test else ""
        self._record_event(parent, "SKIP", f"{prefix}{reason}")

    def addExpectedFailure(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, Any],
    ) -> None:  # noqa: N802
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
                "failure_fingerprint": None
                if status == PASS
                else failure_fingerprint(status, details, roots=self.roots),
            }
        if "unittest.loader._FailedTest" in test_id or test.__class__.__name__ == "_FailedTest":
            self.environment_errors.append(f"COLLECTION_OR_IMPORT_FAILURE:{test_id}")
        super().stopTest(test)


def _snapshot_payload(
    records: Mapping[str, Mapping[str, Any]],
    *,
    python_version: str,
    environment_errors: list[str],
) -> dict[str, Any]:
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


def collect_snapshot(
    repo_root: str | Path,
    *,
    test_dir: str = "coordination/CONTROL-TOWER/tests",
    pattern: str = "test_*.py",
) -> dict[str, Any]:
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
            result.environment_errors.extend(
                f"UNFINALIZED_TEST_ID:{test_id}" for test_id in sorted(result._pending)
            )
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


def _command_snapshot(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted((dict(record) for record in records), key=lambda row: row["command_id"])
    ids = [row["command_id"] for row in ordered]
    return {
        "schema": COMMAND_SNAPSHOT_SCHEMA,
        "command_count": len(ordered),
        "command_id_digest": _sha256(ids),
        "state_digest": _sha256(ordered),
        "results": ordered,
    }


def _empty_command_snapshot() -> dict[str, Any]:
    return _command_snapshot([])


def _index_command_snapshot(
    snapshot: Mapping[str, Any],
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    if snapshot.get("schema") != COMMAND_SNAPSHOT_SCHEMA:
        raise IsolationError(f"{label}:INVALID_COMMAND_SNAPSHOT_SCHEMA")
    raw_results = snapshot.get("results")
    if not isinstance(raw_results, list):
        raise IsolationError(f"{label}:COMMAND_RESULTS_NOT_LIST")
    index: dict[str, dict[str, Any]] = {}
    for raw in raw_results:
        if not isinstance(raw, Mapping):
            raise IsolationError(f"{label}:INVALID_COMMAND_RESULT_SHAPE")
        command_id = str(raw.get("command_id") or "")
        exit_code = raw.get("exit_code")
        fingerprint = raw.get("failure_fingerprint")
        if not command_id or not isinstance(exit_code, int):
            raise IsolationError(f"{label}:INVALID_COMMAND_RESULT:{command_id}")
        if exit_code == 0 and fingerprint is not None:
            raise IsolationError(f"{label}:PASS_COMMAND_HAS_FAILURE_FINGERPRINT:{command_id}")
        if exit_code != 0 and not (
            isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint)
        ):
            raise IsolationError(f"{label}:FAIL_COMMAND_MISSING_FINGERPRINT:{command_id}")
        if command_id in index:
            raise IsolationError(f"{label}:DUPLICATE_COMMAND_ID:{command_id}")
        index[command_id] = dict(raw)
    if snapshot.get("command_count") != len(index):
        raise IsolationError(f"{label}:COMMAND_COUNT_MISMATCH")
    if snapshot.get("command_id_digest") != _sha256(sorted(index)):
        raise IsolationError(f"{label}:COMMAND_ID_DIGEST_MISMATCH")
    ordered = [index[key] for key in sorted(index)]
    if snapshot.get("state_digest") != _sha256(ordered):
        raise IsolationError(f"{label}:COMMAND_STATE_DIGEST_MISMATCH")
    return index


def _same_nonpass(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        left.get("status") == right.get("status")
        and left.get("status") != PASS
        and left.get("failure_fingerprint") == right.get("failure_fingerprint")
    )


def _compare_command_snapshots(
    baseline: Mapping[str, Any],
    integrated: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    before_index = _index_command_snapshot(baseline, label="BASELINE_COMMANDS")
    after_index = _index_command_snapshot(integrated, label="INTEGRATED_COMMANDS")
    before_ids = set(before_index)
    after_ids = set(after_index)
    if before_ids != after_ids:
        missing = sorted(before_ids - after_ids)
        added = sorted(after_ids - before_ids)
        raise IsolationError(
            "COMMAND_SET_MISMATCH:"
            f"missing={','.join(missing) or '-'}:"
            f"added={','.join(added) or '-'}"
        )

    preserved: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    introduced: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    for command_id in sorted(before_ids):
        before = before_index[command_id]
        after = after_index[command_id]
        before_code = before["exit_code"]
        after_code = after["exit_code"]
        if before_code == 0 and after_code == 0:
            classification = "UNCHANGED_PASS"
        elif before_code == 0 and after_code != 0:
            classification = "CANDIDATE_INTRODUCED_COMMAND_FAILURE"
            introduced.append(
                {
                    "command_id": command_id,
                    "integrated_exit_code": after_code,
                    "failure_fingerprint": after["failure_fingerprint"],
                }
            )
        elif before_code != 0 and after_code == 0:
            classification = "CANDIDATE_BASELINE_COMMAND_IMPROVEMENT"
            improvements.append(
                {
                    "command_id": command_id,
                    "baseline_exit_code": before_code,
                    "baseline_failure_fingerprint": before["failure_fingerprint"],
                }
            )
        elif (
            before_code == after_code
            and before["failure_fingerprint"] == after["failure_fingerprint"]
        ):
            classification = "BASELINE_CURRENT_MAIN_COMMAND_FAILURE"
            preserved.append(
                {
                    "command_id": command_id,
                    "exit_code": before_code,
                    "failure_fingerprint": before["failure_fingerprint"],
                }
            )
        else:
            classification = "CANDIDATE_MODIFIED_BASELINE_COMMAND_FAILURE"
            modified.append(
                {
                    "command_id": command_id,
                    "baseline_exit_code": before_code,
                    "integrated_exit_code": after_code,
                    "baseline_failure_fingerprint": before["failure_fingerprint"],
                    "integrated_failure_fingerprint": after["failure_fingerprint"],
                }
            )
        observations.append(
            {
                "command_id": command_id,
                "baseline_exit_code": before_code,
                "integrated_exit_code": after_code,
                "classification": classification,
            }
        )
    return {
        "preserved": preserved,
        "improvements": improvements,
        "introduced": introduced,
        "modified": modified,
        "observations": observations,
    }


def compare_snapshots(
    baseline: Mapping[str, Any],
    integrated: Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
    environment_errors: Iterable[str] = (),
    baseline_commands: Mapping[str, Any] | None = None,
    integrated_commands: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline_index = _index_snapshot(baseline, label="BASELINE")
    integrated_index = _index_snapshot(integrated, label="INTEGRATED")
    baseline_command_snapshot = baseline_commands or _empty_command_snapshot()
    integrated_command_snapshot = integrated_commands or _empty_command_snapshot()
    command_delta = _compare_command_snapshots(
        baseline_command_snapshot,
        integrated_command_snapshot,
    )

    env = set(str(item) for item in environment_errors if str(item))
    env.update(str(item) for item in baseline.get("environment_errors", []) if str(item))
    env.update(str(item) for item in integrated.get("environment_errors", []) if str(item))
    if baseline.get("python_version") != integrated.get("python_version"):
        env.add("PYTHON_RUNTIME_MISMATCH")

    missing = sorted(set(baseline_index) - set(integrated_index))
    if missing:
        env.update(f"MISSING_BASELINE_TEST_ID:{test_id}" for test_id in missing)

    candidate_only = sorted(set(integrated_index) - set(baseline_index))
    candidate_only_failures = [
        test_id
        for test_id in candidate_only
        if integrated_index[test_id]["status"] != PASS
    ]

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
            introduced.append(
                {
                    "test_id": test_id,
                    "integrated_status": after_status,
                    "failure_fingerprint": after.get("failure_fingerprint"),
                }
            )
        elif before_status != PASS and after_status == PASS:
            classification = "CANDIDATE_BASELINE_IMPROVEMENT"
            improvements.append(
                {
                    "test_id": test_id,
                    "baseline_status": before_status,
                    "baseline_failure_fingerprint": before.get("failure_fingerprint"),
                }
            )
        elif _same_nonpass(before, after):
            classification = "BASELINE_CURRENT_MAIN_FAILURE"
            preserved.append(
                {
                    "test_id": test_id,
                    "status": before_status,
                    "failure_fingerprint": before.get("failure_fingerprint"),
                }
            )
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
    elif introduced or command_delta["introduced"]:
        final = "CANDIDATE_INTRODUCED_FAILURE"
    elif modified or command_delta["modified"]:
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
        "baseline_command_count": baseline_command_snapshot.get("command_count"),
        "integrated_command_count": integrated_command_snapshot.get("command_count"),
        "baseline_command_id_digest": baseline_command_snapshot.get("command_id_digest"),
        "integrated_command_id_digest": integrated_command_snapshot.get("command_id_digest"),
        "baseline_command_state_digest": baseline_command_snapshot.get("state_digest"),
        "integrated_command_state_digest": integrated_command_snapshot.get("state_digest"),
        "baseline_command_failures_preserved": command_delta["preserved"],
        "command_improvements": command_delta["improvements"],
        "candidate_introduced_command_failures": command_delta["introduced"],
        "candidate_modified_baseline_command_failures": command_delta["modified"],
        "per_command_observations": command_delta["observations"],
        "environment_errors": sorted(env),
        "per_test_observations": observations,
        "classification": final,
        "baseline_declared_healthy": False,
        "authority": dict(AUTHORITY_FLAGS),
    }
    receipt["receipt_digest"] = _sha256(
        {key: value for key, value in receipt.items() if key != "receipt_digest"}
    )
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
        raise IsolationError(
            f"GIT_COMMAND_FAILED:{' '.join(args)}:{proc.stderr.strip()}"
        )
    return proc


def _git(repo: Path, *args: str) -> str:
    return _run(repo, *args).stdout.strip()


def _remote_sha(repo: Path, branch: str) -> str:
    output = _git(repo, "ls-remote", "origin", f"refs/heads/{branch}")
    fields = output.split()
    if len(fields) < 1 or not re.fullmatch(r"[0-9a-f]{40}", fields[0]):
        raise IsolationError(f"REMOTE_REF_UNRESOLVED:{branch}")
    return fields[0]


def _collect_via_subprocess(
    helper: Path,
    repo_root: Path,
    output: Path,
    test_dir: str,
    pattern: str,
) -> dict[str, Any]:
    proc = subprocess.run(
        [
            sys.executable,
            str(helper),
            "collect",
            "--repo-root",
            str(repo_root),
            "--test-dir",
            test_dir,
            "--pattern",
            pattern,
            "--output",
            str(output),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise IsolationError(
            f"SNAPSHOT_COLLECTION_FAILED:{repo_root}:"
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return json.loads(output.read_text(encoding="utf-8"))


def _command_record(
    command_id: str,
    proc: subprocess.CompletedProcess[str],
    *,
    roots: Iterable[str | Path],
    extra_text: str = "",
) -> dict[str, Any]:
    combined = "\n".join(
        part for part in (extra_text, proc.stdout, proc.stderr) if part
    ).strip()
    return {
        "command_id": command_id,
        "exit_code": int(proc.returncode),
        "failure_fingerprint": None
        if proc.returncode == 0
        else failure_fingerprint("COMMAND_FAILURE", combined, roots=roots),
    }


def _run_python_command(
    control_tower: Path,
    args: list[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=control_tower,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _witness_round_trip(
    repo: Path,
    *,
    command_id: str,
    lane: str,
    temp_dir: Path,
) -> dict[str, Any]:
    control_tower = repo / "coordination/CONTROL-TOWER"
    witness_path = temp_dir / f"{command_id.lower()}.json"
    create = _run_python_command(
        control_tower,
        [
            "run_authorization_witness.py",
            "create",
            "--repo-root",
            str(repo),
            "--lane",
            lane,
        ],
    )
    roots = (repo, temp_dir, control_tower)
    if create.returncode != 0:
        return _command_record(command_id, create, roots=roots)
    witness_path.write_text(create.stdout, encoding="utf-8")
    verify = _run_python_command(
        control_tower,
        [
            "run_authorization_witness.py",
            "verify",
            "--repo-root",
            str(repo),
            "--lane",
            lane,
            "--witness-file",
            str(witness_path),
        ],
    )
    return _command_record(command_id, verify, roots=roots, extra_text=create.stderr)


def collect_control_commands(
    repo_root: str | Path,
    *,
    temp_dir: str | Path,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    scratch = Path(temp_dir).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    control_tower = repo / "coordination/CONTROL-TOWER"
    if not control_tower.is_dir():
        raise IsolationError(f"CONTROL_TOWER_DIRECTORY_MISSING:{control_tower}")
    roots = (repo, scratch, control_tower)
    records: list[dict[str, Any]] = []

    simple_specs = (
        (
            "CONTROL_TOWER_RECONCILE",
            ["run_control_tower.py", "check", "--repo-root", str(repo)],
        ),
        (
            "LANE_CLAIMS_VALIDATE",
            ["run_lane_claims.py", "--repo-root", str(repo)],
        ),
        (
            "CLAIM_PROJECTION_CHECK",
            ["run_claim_projection.py", "check", "--repo-root", str(repo)],
        ),
        (
            "CODEX_ROUTE_WITNESS",
            [
                "run_control_tower.py",
                "witness",
                "--repo-root",
                str(repo),
                "--agent",
                "CODEX",
            ],
        ),
    )
    for command_id, argv in simple_specs:
        records.append(
            _command_record(
                command_id,
                _run_python_command(control_tower, argv),
                roots=roots,
            )
        )

    records.append(
        _witness_round_trip(
            repo,
            command_id="AUTH_WITNESS_LANE_C_ROUND_TRIP",
            lane="LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP",
            temp_dir=scratch,
        )
    )
    records.append(
        _witness_round_trip(
            repo,
            command_id="AUTH_WITNESS_LANE_B_ROUND_TRIP",
            lane="LANE-B-A-SHARE-REMEDIATION",
            temp_dir=scratch,
        )
    )
    snapshot = _command_snapshot(records)
    if tuple(sorted(row["command_id"] for row in records)) != tuple(
        sorted(_CONTROL_COMMAND_IDS)
    ):
        raise IsolationError("CANONICAL_CONTROL_COMMAND_SET_DRIFT")
    return snapshot


def environment_invalid_receipt(
    error: str,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    empty = _snapshot_payload(
        {},
        python_version=".".join(str(part) for part in sys.version_info[:3]),
        environment_errors=[],
    )
    return compare_snapshots(
        empty,
        empty,
        metadata=metadata,
        environment_errors=[str(error)],
        baseline_commands=_empty_command_snapshot(),
        integrated_commands=_empty_command_snapshot(),
    )


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
    metadata: dict[str, Any] = {
        "repository": _git(repo, "config", "--get", "remote.origin.url")
    }

    if _git(repo, "status", "--porcelain"):
        raise IsolationError("TRUSTED_REPOSITORY_WORKTREE_DIRTY")

    initial_main = _remote_sha(repo, "main")
    initial_candidate = _remote_sha(repo, candidate_branch)
    local_head = _git(repo, "rev-parse", "HEAD")
    if local_head != initial_candidate:
        raise IsolationError(
            f"LOCAL_HEAD_NOT_EXACT_REMOTE_CANDIDATE:{local_head}:{initial_candidate}"
        )

    _run(
        repo,
        "fetch",
        "--no-tags",
        "origin",
        f"main:refs/remotes/origin/main",
        f"{candidate_branch}:refs/remotes/origin/{candidate_branch}",
    )
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
            baseline = _collect_via_subprocess(
                helper, base_root, base_json, test_dir, pattern
            )
            baseline_commands = collect_control_commands(
                base_root,
                temp_dir=temp / "baseline-command-scratch",
            )
            if merge_proc.returncode != 0:
                environment_errors.append("INTEGRATION_MERGE_FAILED")
                _run(integrated_root, "merge", "--abort", check=False)
                integrated = baseline
                integrated_commands = baseline_commands
                integration_commit = None
                parents: list[str] = []
                integrated_tree = None
            else:
                integration_commit = _git(integrated_root, "rev-parse", "HEAD")
                parents = _git(
                    integrated_root, "show", "-s", "--format=%P", "HEAD"
                ).split()
                integrated_tree = _git(integrated_root, "rev-parse", "HEAD^{tree}")
                if _git(integrated_root, "status", "--porcelain"):
                    environment_errors.append("INTEGRATED_WORKTREE_DIRTY")
                if parents != [initial_main, initial_candidate]:
                    environment_errors.append("INTEGRATION_PARENT_MISMATCH")
                integrated = _collect_via_subprocess(
                    helper, integrated_root, integrated_json, test_dir, pattern
                )
                integrated_commands = collect_control_commands(
                    integrated_root,
                    temp_dir=temp / "integrated-command-scratch",
                )
            if _git(base_root, "status", "--porcelain"):
                environment_errors.append("BASELINE_WORKTREE_DIRTY_AFTER_COMMANDS")
            if _git(integrated_root, "status", "--porcelain"):
                environment_errors.append("INTEGRATED_WORKTREE_DIRTY_AFTER_COMMANDS")
            metadata.update(
                {
                    "integration_commit_sha": integration_commit,
                    "integration_parent_shas": parents,
                    "integrated_tree_sha": integrated_tree,
                }
            )
        finally:
            _run(repo, "worktree", "remove", "--force", str(base_root), check=False)
            _run(
                repo,
                "worktree",
                "remove",
                "--force",
                str(integrated_root),
                check=False,
            )
            _run(repo, "worktree", "prune", check=False)

    final_main = _remote_sha(repo, "main")
    final_candidate = _remote_sha(repo, candidate_branch)
    metadata["final_main_sha"] = final_main
    metadata["final_candidate_sha"] = final_candidate
    if final_main != initial_main:
        environment_errors.append("CURRENT_MAIN_DRIFT_DURING_PROOF")
    if final_candidate != initial_candidate:
        environment_errors.append("CANDIDATE_HEAD_DRIFT_DURING_PROOF")

    return compare_snapshots(
        baseline,
        integrated,
        metadata=metadata,
        environment_errors=environment_errors,
        baseline_commands=baseline_commands,
        integrated_commands=integrated_commands,
    )


def _write_json(path: str | Path, value: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IsolationError("JSON_ROOT_NOT_OBJECT")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Canonical Control Tower CI state isolation helper"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--repo-root", required=True)
    collect_parser.add_argument(
        "--test-dir", default="coordination/CONTROL-TOWER/tests"
    )
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
    proof_parser.add_argument(
        "--test-dir", default="coordination/CONTROL-TOWER/tests"
    )
    proof_parser.add_argument("--pattern", default="test_*.py")
    proof_parser.add_argument("--output", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            snapshot = collect_snapshot(
                args.repo_root,
                test_dir=args.test_dir,
                pattern=args.pattern,
            )
            _write_json(args.output, snapshot)
            return 0
        if args.command == "compare":
            metadata = _load_json(args.metadata) if args.metadata else {}
            receipt = compare_snapshots(
                _load_json(args.baseline),
                _load_json(args.integrated),
                metadata=metadata,
            )
            _write_json(args.output, receipt)
            return 0 if receipt["classification"] == FINAL_PASS else 2
        if args.command == "proof":
            receipt = run_proof(
                args.repo_root,
                candidate_branch=args.candidate_branch,
                test_dir=args.test_dir,
                pattern=args.pattern,
            )
            _write_json(args.output, receipt)
            print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
            return 0 if receipt["classification"] == FINAL_PASS else 2
    except IsolationError as exc:
        if args.command == "proof" and getattr(args, "output", None):
            receipt = environment_invalid_receipt(str(exc))
            _write_json(args.output, receipt)
            print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
        print(f"TEST_ENVIRONMENT_INVALID: {exc}", file=sys.stderr)
        return 3
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
