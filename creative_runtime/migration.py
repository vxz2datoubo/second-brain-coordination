"""Lossless legacy-session migration with publication-time source binding.

The source descriptor remains open (and is locked where the platform exposes a
lock primitive) from the first read through publication.  The source and path
identity are checked before and after create-only publication.  If the
post-publication check detects a race, only the inode/file-id created by this
attempt is removed; pre-existing or attacker-replaced targets are never deleted.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, BinaryIO, Mapping

from .contracts import canonical_json
from .ledger import CreativeLedger, LedgerViolation


LEGACY_SCHEMA = "CreativeSession/v1"
CURRENT_SCHEMA = "CreativeSession/v2"
_SLOT = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
# msvcrt.locking uses a signed C long byte count. Locking the entire positive
# range also covers appends beyond the current EOF; sessions at or above this
# bound fail closed instead of leaving an unprotected tail.
_WINDOWS_LOCK_SPAN = 0x7FFFFFFF


class MigrationViolation(ValueError):
    """The migration could not prove confinement, identity, or losslessness."""


def _unique_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MigrationViolation(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _is_reparse(details: os.stat_result) -> bool:
    return bool(_REPARSE_ATTRIBUTE and getattr(details, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE)


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _identity(details: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(details.st_dev), int(details.st_ino), int(details.st_size),
        int(details.st_mtime_ns), int(details.st_ctime_ns),
    )


def _file_id(details: os.stat_result) -> tuple[int, int]:
    return int(details.st_dev), int(details.st_ino)


def _assert_component_not_indirect(path: Path, *, directory: bool) -> os.stat_result:
    try:
        details = path.lstat()
    except OSError as error:
        raise MigrationViolation(f"Cannot inspect confined path component: {path}") from error
    if stat.S_ISLNK(details.st_mode) or _is_reparse(details):
        raise MigrationViolation(f"Linked, junction, or reparse path is forbidden: {path}")
    if directory and not stat.S_ISDIR(details.st_mode):
        raise MigrationViolation(f"Expected a confined directory: {path}")
    return details


def _assert_ancestor_chain(path: Path) -> None:
    absolute = _lexical_absolute(path)
    chain: list[Path] = []
    current = absolute
    while True:
        chain.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    for component in reversed(chain):
        if not component.exists() and not component.is_symlink():
            continue
        details = _assert_component_not_indirect(component, directory=component != absolute or absolute.is_dir())
        if component != Path(component.anchor) and stat.S_ISDIR(details.st_mode) and os.path.ismount(component):
            raise MigrationViolation(f"Nested mount point is outside the confinement model: {component}")


def _assert_within(workspace: Path, candidate: Path) -> None:
    workspace_absolute = _lexical_absolute(workspace)
    candidate_absolute = _lexical_absolute(candidate)
    try:
        shared = os.path.commonpath((os.fspath(workspace_absolute), os.fspath(candidate_absolute)))
    except ValueError as error:
        raise MigrationViolation("Candidate path is on a different filesystem root") from error
    if os.path.normcase(shared) != os.path.normcase(os.fspath(workspace_absolute)):
        raise MigrationViolation("Candidate path escapes the workspace")


def _acquire_lock(stream: BinaryIO, size: int) -> str:
    if os.name == "nt":
        if size >= _WINDOWS_LOCK_SPAN:
            raise MigrationViolation("Legacy source exceeds the Windows lockable confinement bound")
        try:
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, _WINDOWS_LOCK_SPAN)
            return "windows_byte_range"
        except (ImportError, OSError) as error:
            raise MigrationViolation("Could not acquire the Windows source lock") from error
    try:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return "posix_flock"
    except (ImportError, OSError) as error:
        raise MigrationViolation("Could not acquire the POSIX source lock") from error


def _release_lock(stream: BinaryIO, lock_kind: str, size: int) -> None:
    try:
        if lock_kind == "windows_byte_range":
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, _WINDOWS_LOCK_SPAN)
        elif lock_kind == "posix_flock":
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    except OSError:
        # Closing the descriptor releases the platform lock even if explicit
        # unlock fails. There is no safe recovery action during context exit.
        pass


class _BoundSource(AbstractContextManager["_BoundSource"]):
    def __init__(self, path: Path) -> None:
        self.path = _lexical_absolute(path)
        self.stream: BinaryIO | None = None
        self.initial_identity: tuple[int, int, int, int, int] | None = None
        self.initial_bytes = b""
        self.lock_kind = ""

    def __enter__(self) -> "_BoundSource":
        _assert_ancestor_chain(self.path.parent)
        path_details = _assert_component_not_indirect(self.path, directory=False)
        if not stat.S_ISREG(path_details.st_mode):
            raise MigrationViolation("Legacy source must be a regular file")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags)
            # Unbuffered reads are required: post-publication verification must
            # observe the descriptor's current bytes, not a BufferedReader cache.
            self.stream = os.fdopen(descriptor, "rb", buffering=0, closefd=True)
        except OSError as error:
            raise MigrationViolation("Could not open the legacy source without following links") from error
        descriptor_details = os.fstat(self.stream.fileno())
        if not stat.S_ISREG(descriptor_details.st_mode) or _file_id(descriptor_details) != _file_id(path_details):
            self.stream.close()
            raise MigrationViolation("Legacy path and opened descriptor identities differ")
        self.initial_identity = _identity(descriptor_details)
        self.lock_kind = _acquire_lock(self.stream, descriptor_details.st_size)
        self.initial_bytes = self._read_descriptor()
        self.verify_unchanged("initial_read")
        return self

    def _read_descriptor(self) -> bytes:
        if self.stream is None:
            raise MigrationViolation("Source descriptor is not open")
        self.stream.seek(0)
        data = self.stream.read()
        self.stream.seek(0)
        return data

    def verify_unchanged(self, phase: str) -> None:
        if self.stream is None or self.initial_identity is None:
            raise MigrationViolation("Source descriptor binding is unavailable")
        descriptor_details = os.fstat(self.stream.fileno())
        path_details = _assert_component_not_indirect(self.path, directory=False)
        if (
            _identity(descriptor_details) != self.initial_identity
            or _file_id(path_details) != _file_id(descriptor_details)
            or self._read_descriptor() != self.initial_bytes
        ):
            raise MigrationViolation(f"Legacy source identity changed during {phase}")

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.stream is not None:
            _release_lock(self.stream, self.lock_kind, len(self.initial_bytes))
            self.stream.close()
        self.stream = None


def _parse_legacy(source: bytes) -> CreativeLedger:
    try:
        document = json.loads(
            source.decode("utf-8", errors="strict"), object_pairs_hook=_unique_mapping
        )
    except (UnicodeDecodeError, json.JSONDecodeError, MigrationViolation) as error:
        raise MigrationViolation("Legacy session must be strict, duplicate-free UTF-8 JSON") from error
    if not isinstance(document, dict) or document.get("schema") != LEGACY_SCHEMA:
        raise MigrationViolation("Unsupported legacy schema")
    records = document.get("events")
    if not isinstance(records, list) or not records:
        raise MigrationViolation("Legacy session has no event ledger")
    try:
        ledger = CreativeLedger.from_records(records)
        ledger.replay()
    except (KeyError, TypeError, ValueError, LedgerViolation) as error:
        raise MigrationViolation("Legacy event ledger is invalid") from error
    return ledger


def _v2_document(source: bytes, ledger: CreativeLedger) -> dict[str, Any]:
    return {
        "schema": CURRENT_SCHEMA,
        "migration": {
            "kind": "lossless_bound_legacy_envelope",
            "source_schema": LEGACY_SCHEMA,
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "legacy_event_count": len(ledger.events),
        },
        "events": ledger.to_records(),
        "replayed_state": ledger.replay().to_dict(),
    }


def _read_existing_target(target: Path, expected: Mapping[str, Any]) -> bool:
    if target.is_symlink():
        raise MigrationViolation("Existing target must not be linked")
    if not target.exists():
        return False
    details = _assert_component_not_indirect(target, directory=False)
    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        raise MigrationViolation("Existing target must be an unlinked regular file")
    try:
        document = json.loads(
            target.read_text(encoding="utf-8", errors="strict"), object_pairs_hook=_unique_mapping
        )
    except (UnicodeDecodeError, json.JSONDecodeError, MigrationViolation) as error:
        raise MigrationViolation("Existing target is invalid") from error
    if document != dict(expected):
        raise MigrationViolation("Existing target does not exactly match this source")
    try:
        CreativeLedger.from_records(document["events"]).replay()
    except (KeyError, TypeError, ValueError, LedgerViolation) as error:
        raise MigrationViolation("Existing target ledger is invalid") from error
    return True


def _stage(save_directory: Path, payload: bytes) -> Path:
    descriptor, raw_path = tempfile.mkstemp(prefix=".bound-v2-", suffix=".tmp", dir=save_directory)
    staged = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        details = _assert_component_not_indirect(staged, directory=False)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise MigrationViolation("Staged output is not a private regular file")
        return staged
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


def _publish_create_only(staged: Path, target: Path) -> tuple[int, int]:
    try:
        os.link(staged, target, follow_symlinks=False)
    except FileExistsError as error:
        raise MigrationViolation("Target appeared before create-only publication") from error
    except OSError as error:
        raise MigrationViolation("Create-only publication failed") from error
    try:
        target_details = target.lstat()
        if not stat.S_ISREG(target_details.st_mode) or _is_reparse(target_details):
            raise MigrationViolation("Published target identity is unsafe")
        published_id = _file_id(target_details)
    except BaseException:
        try:
            target.unlink(missing_ok=True)
        finally:
            staged.unlink(missing_ok=True)
        raise
    staged.unlink(missing_ok=True)
    return published_id


def _remove_only_created_target(target: Path, published_id: tuple[int, int]) -> None:
    try:
        details = target.lstat()
        if _file_id(details) == published_id and stat.S_ISREG(details.st_mode):
            target.unlink()
    except FileNotFoundError:
        return
    except OSError as error:
        raise MigrationViolation("Race detected and the created target could not be safely removed") from error


def migrate_legacy_session(workspace: Path, slot: str = "default") -> Path:
    """Create a confined v2 save while preserving and binding the v1 source."""

    if not _SLOT.fullmatch(slot):
        raise MigrationViolation("Unsafe save slot")
    workspace = _lexical_absolute(Path(workspace))
    _assert_ancestor_chain(workspace)
    _assert_component_not_indirect(workspace, directory=True)
    source = workspace / "session.json"
    save_directory = workspace / "saves"
    target = save_directory / f"{slot}.json"
    _assert_within(workspace, source)
    _assert_within(workspace, target)

    with _BoundSource(source) as binding:
        ledger = _parse_legacy(binding.initial_bytes)
        expected = _v2_document(binding.initial_bytes, ledger)
        if save_directory.exists() or save_directory.is_symlink():
            _assert_ancestor_chain(save_directory)
            _assert_component_not_indirect(save_directory, directory=True)
        else:
            save_directory.mkdir(parents=False, exist_ok=False)
            _assert_ancestor_chain(save_directory)
        if _read_existing_target(target, expected):
            binding.verify_unchanged("idempotent_target_validation")
            return target

        payload = (canonical_json(expected) + "\n").encode("utf-8")
        staged = _stage(save_directory, payload)
        published_id: tuple[int, int] | None = None
        try:
            _assert_ancestor_chain(staged)
            binding.verify_unchanged("pre_publication")
            published_id = _publish_create_only(staged, target)
            _assert_ancestor_chain(target)
            binding.verify_unchanged("post_publication")
            target_details = _assert_component_not_indirect(target, directory=False)
            if _file_id(target_details) != published_id or target_details.st_nlink != 1:
                raise MigrationViolation("Published target identity changed before commit completion")
        except BaseException as error:
            staged.unlink(missing_ok=True)
            if published_id is not None:
                _remove_only_created_target(target, published_id)
            if isinstance(error, MigrationViolation):
                raise
            raise MigrationViolation("Migration publication failed safely") from error
        return target
