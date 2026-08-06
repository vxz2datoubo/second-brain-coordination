"""Verify Provider evidence through an exact, disposable Git archive."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from typing import Mapping

from .core import AuthorityError, canonical_bytes


TASK_RELATIVE = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E57"
REQUIRED_RELATIVE_FILES = (
    f"{TASK_RELATIVE}/src/e57_authority/provider.py",
    f"{TASK_RELATIVE}/src/e57_authority/provider_verify.py",
    f"{TASK_RELATIVE}/tools/verify_provider_evidence.py",
)


def _git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise AuthorityError(completed.stderr.decode("utf-8", "replace").strip() or "clean archive Git operation failed")
    return completed.stdout


def _extract_archive(archive_bytes: bytes, destination: Path) -> None:
    try:
        with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:") as archive:
            members = archive.getmembers()
            for member in members:
                candidate = (destination / member.name).resolve()
                if not candidate.is_relative_to(destination.resolve()) or not (member.isdir() or member.isfile()):
                    raise AuthorityError("Git archive contains an unsafe member")
            for member in members:
                extract_options: dict[str, object] = {"path": destination, "set_attrs": False}
                if sys.version_info >= (3, 12):
                    extract_options["filter"] = "data"
                archive.extract(member, **extract_options)
    except AuthorityError:
        raise
    except (tarfile.TarError, OSError) as exc:
        raise AuthorityError("exact Git archive could not be safely extracted") from exc


def verify_from_clean_archive(
    *,
    repo: Path,
    head: str,
    tested_path: Path,
    receipt_path: Path,
    tested_head: str,
    receipt_head: str,
    expected_tested_evidence_digest: str,
    expected_receipt_evidence_digest: str,
) -> Mapping[str, object]:
    """Rebuild verifier code from ``head`` and run it outside the worktree."""

    tree_sha = _git(repo, "rev-parse", f"{head}^{{tree}}").decode("ascii").strip()
    archive_bytes = _git(repo, "archive", "--format=tar", head)
    expected_sources = {
        path: sha256(_git(repo, "show", f"{head}:{path}")).hexdigest() for path in REQUIRED_RELATIVE_FILES
    }
    with tempfile.TemporaryDirectory(prefix="e57-clean-archive-") as temporary:
        root = Path(temporary)
        _extract_archive(archive_bytes, root)
        actual_sources = {
            path: sha256((root / path).read_bytes()).hexdigest() for path in REQUIRED_RELATIVE_FILES
        }
        if actual_sources != expected_sources:
            raise AuthorityError("extracted verifier source differs from the exact Git head")
        output_path = root / "provider-verification.json"
        command = [
            sys.executable,
            str(root / TASK_RELATIVE / "tools" / "verify_provider_evidence.py"),
            "--tested",
            str(tested_path),
            "--receipt",
            str(receipt_path),
            "--tested-head",
            tested_head,
            "--receipt-head",
            receipt_head,
            "--expected-tested-evidence-digest",
            expected_tested_evidence_digest,
            "--expected-receipt-evidence-digest",
            expected_receipt_evidence_digest,
            "--out",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, check=False)
        if completed.returncode:
            raise AuthorityError("clean-archive Provider verifier rejected the evidence")
        try:
            result = json.loads(output_path.read_bytes())
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthorityError("clean-archive Provider verifier emitted malformed output") from exc
    return {
        "schema": "e57-clean-archive-verification-v1",
        "verified_head": head,
        "verified_tree": tree_sha,
        "archive_sha256": sha256(archive_bytes).hexdigest(),
        "source_sha256": actual_sources,
        "verification": result,
        "verification_sha256": sha256(canonical_bytes(result)).hexdigest(),
    }
