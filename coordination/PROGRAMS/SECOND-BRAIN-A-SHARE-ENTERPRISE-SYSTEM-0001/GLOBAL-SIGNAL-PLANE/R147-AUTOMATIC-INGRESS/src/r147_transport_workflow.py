"""GitHub push-range and remote-race host for R147 durable ingress.

This module is transport machinery only. It never interprets Signal truth. Each
request is still processed by :func:`r147_ingress.process_github_request`, which
replays the Git journal into the canonical S0C DurableSignalLedger and invokes
the canonical R145/R146 authority/admission chain.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Mapping, Sequence


ZERO_SHA = "0" * 40
R147_ROOT = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "GLOBAL-SIGNAL-PLANE/R147-AUTOMATIC-INGRESS"
)
REQUEST_PREFIX = f"{R147_ROOT}/transport/requests/"
STATE_PREFIX = f"{R147_ROOT}/transport/"
_REQUEST_RE = re.compile(rf"^{re.escape(REQUEST_PREFIX)}[^/]+\.json$")
_RECEIPT_RE = re.compile(rf"^{re.escape(STATE_PREFIX)}receipts/[^/]+\.json$")
JOURNAL_PATH = f"{STATE_PREFIX}admitted_events.jsonl"


class TransportWorkflowError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class RequestChange:
    commit: str
    path: str

    def public_dict(self) -> dict[str, str]:
        return {"commit": self.commit, "path": self.path}


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _git(root: Path, *args: str) -> str:
    result = _run_git(root, *args)
    if result.returncode:
        raise TransportWorkflowError(
            "R147_GIT_OPERATION_FAILED",
            f"{' '.join(args)}::{result.stderr.strip()}",
        )
    return result.stdout.strip()


def _require_commit(root: Path, ref: str, *, code: str) -> None:
    result = _run_git(root, "cat-file", "-e", f"{ref}^{{commit}}")
    if result.returncode:
        raise TransportWorkflowError(code, ref)


def resolve_push_base(
    root: Path,
    *,
    before: str,
    after: str,
    created: bool,
    main_ref: str = "origin/main",
) -> str:
    """Resolve the exact lower bound for one GitHub push event.

    Existing branches are strictly bound to ``before..after``. For a new branch,
    GitHub supplies an all-zero ``before``; the allowed first transport range is
    therefore bounded from the branch's merge-base with canonical main rather
    than accidentally replaying the repository's whole history.
    """
    if not after or after == ZERO_SHA:
        raise TransportWorkflowError("R147_PUSH_AFTER_INVALID", after)
    _require_commit(root, after, code="R147_PUSH_AFTER_MISSING")

    if created or before == ZERO_SHA:
        _require_commit(root, main_ref, code="R147_NEW_BRANCH_MAIN_REF_MISSING")
        base = _git(root, "merge-base", after, main_ref)
        if not base:
            raise TransportWorkflowError("R147_NEW_BRANCH_BASE_UNRESOLVED")
        return base

    _require_commit(root, before, code="R147_PUSH_BEFORE_MISSING")
    ancestry = _run_git(root, "merge-base", "--is-ancestor", before, after)
    if ancestry.returncode:
        raise TransportWorkflowError(
            "R147_PUSH_RANGE_NOT_FAST_FORWARD",
            f"{before}..{after}",
        )
    return before


def enumerate_push_request_changes(
    root: Path,
    *,
    before: str,
    after: str,
    created: bool,
    main_ref: str = "origin/main",
) -> list[RequestChange]:
    """Return every request mutation in commit order and audit the whole range."""
    base = resolve_push_base(
        root,
        before=before,
        after=after,
        created=created,
        main_ref=main_ref,
    )
    commits = [
        line.strip()
        for line in _git(root, "rev-list", "--reverse", f"{base}..{after}").splitlines()
        if line.strip()
    ]
    if not commits:
        raise TransportWorkflowError("R147_PUSH_RANGE_EMPTY", f"{base}..{after}")

    changes: list[RequestChange] = []
    for commit in commits:
        rows = _git(
            root,
            "diff-tree",
            "--root",
            "--no-commit-id",
            "--name-status",
            "--no-renames",
            "-r",
            commit,
        ).splitlines()
        if not rows:
            raise TransportWorkflowError("R147_REQUEST_COMMIT_EMPTY", commit)
        for row in rows:
            parts = row.split("\t", 1)
            if len(parts) != 2:
                raise TransportWorkflowError("R147_CHANGE_ROW_INVALID", row)
            status, path = parts
            if status not in {"A", "M"}:
                raise TransportWorkflowError(
                    "R147_TRIGGER_MUTATION_FORBIDDEN",
                    f"{status}:{path}",
                )
            if not _REQUEST_RE.fullmatch(path):
                raise TransportWorkflowError("R147_TRIGGER_SCOPE_FORBIDDEN", path)
            changes.append(RequestChange(commit=commit, path=path))

    if not changes:
        raise TransportWorkflowError("R147_NO_REQUEST_CHANGES")
    return changes


def _fetch_and_reset_to_remote(
    root: Path,
    *,
    remote_branch: str,
    trigger_after: str,
) -> str:
    remote_ref = f"refs/remotes/origin/{remote_branch}"
    fetch = _run_git(
        root,
        "fetch",
        "--no-tags",
        "origin",
        f"+refs/heads/{remote_branch}:{remote_ref}",
    )
    if fetch.returncode:
        raise TransportWorkflowError("R147_REMOTE_FETCH_FAILED", fetch.stderr.strip())
    ancestry = _run_git(root, "merge-base", "--is-ancestor", trigger_after, remote_ref)
    if ancestry.returncode:
        raise TransportWorkflowError(
            "R147_TRIGGER_HISTORY_REWRITTEN",
            f"{trigger_after}!<={remote_ref}",
        )
    _git(root, "reset", "--hard", remote_ref)
    _git(root, "clean", "-fd")
    return remote_ref


def _materialize_request(root: Path, change: RequestChange) -> Path:
    if not _REQUEST_RE.fullmatch(change.path):
        raise TransportWorkflowError("R147_REQUEST_PATH_INVALID", change.path)
    show = _run_git(root, "show", f"{change.commit}:{change.path}")
    if show.returncode:
        raise TransportWorkflowError(
            "R147_REQUEST_BLOB_UNAVAILABLE",
            f"{change.commit}:{change.path}",
        )
    target = root / change.path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(show.stdout, encoding="utf-8")
    return target


def _restore_request_tree(root: Path, remote_ref: str) -> None:
    request_root = REQUEST_PREFIX.rstrip("/")
    result = _run_git(root, "checkout", remote_ref, "--", request_root)
    if result.returncode:
        raise TransportWorkflowError("R147_REQUEST_TREE_RESTORE_FAILED", result.stderr.strip())


def _staged_output_paths(root: Path) -> list[str]:
    output = _git(root, "diff", "--cached", "--name-only")
    return [line.strip() for line in output.splitlines() if line.strip()]


def _validate_output_scope(paths: Sequence[str]) -> None:
    for path in paths:
        if path == JOURNAL_PATH or _RECEIPT_RE.fullmatch(path):
            continue
        raise TransportWorkflowError("R147_OUTPUT_SCOPE_FORBIDDEN", path)


def _receipt_attempts(root: Path, attempts: Sequence[str]) -> None:
    for attempt in attempts:
        receipt = root / STATE_PREFIX / "receipts" / f"{attempt}.json"
        if not receipt.is_file():
            raise TransportWorkflowError("R147_EXPECTED_RECEIPT_MISSING", attempt)
        try:
            payload = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TransportWorkflowError("R147_EXPECTED_RECEIPT_INVALID", attempt) from exc
        if payload.get("attempt_id") != attempt:
            raise TransportWorkflowError("R147_EXPECTED_RECEIPT_ID_MISMATCH", attempt)


def persist_push_batch(
    *,
    runtime_root: Path,
    transport_root: Path,
    before: str,
    after: str,
    created: bool,
    observation_pr: int,
    remote_branch: str = "signal-tower/ingress",
    main_ref: str = "origin/main",
    max_push_attempts: int = 5,
    processor: Callable[..., Mapping[str, Any]] | None = None,
    before_push_hook: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Process the exact push range and persist outputs without losing races.

    The manifest is immutable evidence from the triggering ``before/after`` range.
    Before every persistence attempt we fetch and hard-reset to the newest remote
    transport state, replay the manifest against that state, and use an ordinary
    fast-forward push. A non-fast-forward push never discards the receipt: the
    whole operation is recomputed on the newer journal and retried, without force.
    """
    if max_push_attempts < 1:
        raise TransportWorkflowError("R147_PUSH_ATTEMPTS_INVALID")
    manifest = enumerate_push_request_changes(
        transport_root,
        before=before,
        after=after,
        created=created,
        main_ref=main_ref,
    )
    if processor is None:
        from r147_ingress import process_github_request as processor  # local import: canonical runtime seam

    last_push_error = ""
    for push_attempt in range(1, max_push_attempts + 1):
        remote_ref = _fetch_and_reset_to_remote(
            transport_root,
            remote_branch=remote_branch,
            trigger_after=after,
        )
        receipt_attempts: list[str] = []
        for change in manifest:
            request_path = _materialize_request(transport_root, change)
            receipt = processor(
                runtime_root=runtime_root,
                transport_root=transport_root,
                request_path=request_path,
                observation_pr=observation_pr,
            )
            attempt_id = receipt.get("attempt_id")
            if not isinstance(attempt_id, str) or not attempt_id:
                raise TransportWorkflowError(
                    "R147_PROCESSOR_RECEIPT_ID_INVALID",
                    change.path,
                )
            receipt_attempts.append(attempt_id)

        _restore_request_tree(transport_root, remote_ref)
        _git(transport_root, "config", "user.name", "github-actions[bot]")
        _git(
            transport_root,
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        )
        _git(transport_root, "add", "-A", STATE_PREFIX)
        staged = _staged_output_paths(transport_root)
        _validate_output_scope(staged)
        _receipt_attempts(transport_root, receipt_attempts)
        if not staged:
            return {
                "status": "ALREADY_PERSISTED",
                "push_attempt": push_attempt,
                "request_change_count": len(manifest),
                "receipt_attempts": receipt_attempts,
                "remote_ref": _git(transport_root, "rev-parse", remote_ref),
            }

        _git(
            transport_root,
            "commit",
            "-m",
            f"R147 transport: process {after[:12]} ({len(manifest)} request changes)",
        )
        if before_push_hook is not None:
            before_push_hook(push_attempt)
        push = _run_git(
            transport_root,
            "push",
            "origin",
            f"HEAD:refs/heads/{remote_branch}",
        )
        if push.returncode == 0:
            return {
                "status": "PERSISTED",
                "push_attempt": push_attempt,
                "request_change_count": len(manifest),
                "receipt_attempts": receipt_attempts,
                "persisted_head": _git(transport_root, "rev-parse", "HEAD"),
            }
        last_push_error = push.stderr.strip()

    raise TransportWorkflowError(
        "R147_REMOTE_PUSH_RETRY_EXHAUSTED",
        last_push_error,
    )


def _parse_bool(value: str) -> bool:
    folded = value.strip().casefold()
    if folded in {"true", "1", "yes"}:
        return True
    if folded in {"false", "0", "no"}:
        return False
    raise argparse.ArgumentTypeError("expected boolean")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    persist = sub.add_parser("persist-batch")
    persist.add_argument("--runtime-root", required=True)
    persist.add_argument("--transport-root", required=True)
    persist.add_argument("--before", required=True)
    persist.add_argument("--after", required=True)
    persist.add_argument("--created", required=True, type=_parse_bool)
    persist.add_argument("--observation-pr", required=True, type=int)
    persist.add_argument("--remote-branch", default="signal-tower/ingress")
    args = parser.parse_args(argv)

    if args.command == "persist-batch":
        try:
            result = persist_push_batch(
                runtime_root=Path(args.runtime_root),
                transport_root=Path(args.transport_root),
                before=args.before,
                after=args.after,
                created=args.created,
                observation_pr=args.observation_pr,
                remote_branch=args.remote_branch,
            )
        except TransportWorkflowError as exc:
            print(json.dumps({"status": "INFRASTRUCTURE_FAILURE", "code": exc.code, "detail": exc.detail}))
            return 2
        print(json.dumps(result, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
