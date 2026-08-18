"""Bounded R135 source binding and durable S0C-backed shadow admission.

This module never exposes a source write operation.  A source observation is
admitted only after the checked-out worktree payload, exact Git tree entry, and
activated per-path blob binding all agree.  The S0D reducer is deliberately a
non-authoritative staging summary; durable event history and replay are owned
by the accepted S0C ``DurableSignalLedger``.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping

import yaml


AI_FILM_REPOSITORY = "vxz2datoubo/eustia-ai-film"
AI_FILM_COMMIT = "44c383afd2207a97caf45b1b0da6ee1dece43a76"
PROJECT_INDEX_BLOB = "a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19"

# Unicode escapes are intentional: the exact Git paths must not depend on the
# Windows console code page used by a caller.
ALLOWED_PATHS = (
    "PROJECT_INDEX.yaml",
    "07_\u8fde\u7eed\u6027\u4e0e\u751f\u4ea7\u72b6\u6001/\u8fde\u7eed\u6027\u4e0e\u5f53\u524d\u751f\u4ea7\u72b6\u6001.md",
    "10_\u8fd0\u884c\u65f6/pending_canonical_writes.yaml",
    "10_\u8fd0\u884c\u65f6/director_route_index.yaml",
    "10_\u8fd0\u884c\u65f6/maturity_model.yaml",
    "11_\u9a8c\u6536/director_regression_cases.yaml",
    "11_\u9a8c\u6536/golden_prompt_regression_cases.yaml",
    "11_\u9a8c\u6536/golden_case_director_pull_regression_cases.yaml",
    "12_\u672a\u77e5\u9879/UNKNOWN_REGISTRY.yaml",
    "12_\u672a\u77e5\u9879/SOUND_UNKNOWN_REGISTRY.yaml",
)

_ACTIVATED_BLOBS = (
    ("PROJECT_INDEX.yaml", "a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19"),
    ("07_\u8fde\u7eed\u6027\u4e0e\u751f\u4ea7\u72b6\u6001/\u8fde\u7eed\u6027\u4e0e\u5f53\u524d\u751f\u4ea7\u72b6\u6001.md", "6d8d3880d389e36f83367606f2f37420d3a373df"),
    ("10_\u8fd0\u884c\u65f6/pending_canonical_writes.yaml", "83abe6c3b7dc8450a4462e5f13903146188c688d"),
    ("10_\u8fd0\u884c\u65f6/director_route_index.yaml", "af06aed1751bd516f9d968e8c7decc8c5259a148"),
    ("10_\u8fd0\u884c\u65f6/maturity_model.yaml", "5226ffffaab5e720efabe760b28322cdf19c5519"),
    ("11_\u9a8c\u6536/director_regression_cases.yaml", "f11c5fbfed3fce2ce18b7de7962410139995524e"),
    ("11_\u9a8c\u6536/golden_prompt_regression_cases.yaml", "a2aefa6c15878648f7c69e08a4940707b1b3a2f4"),
    ("11_\u9a8c\u6536/golden_case_director_pull_regression_cases.yaml", "4c461a4f41f8adff4cc513416f8c6c8de90d8dc2"),
    ("12_\u672a\u77e5\u9879/UNKNOWN_REGISTRY.yaml", "87790fa327b1195463fdb32ddfebef9ce9a274c8"),
    ("12_\u672a\u77e5\u9879/SOUND_UNKNOWN_REGISTRY.yaml", "cc62d2a9540e1078a3086b74d36fa077294e97b2"),
)

STATE_MAP = {
    "completed": "COMPLETED", "resolved": "COMPLETED", "closed": "COMPLETED",
    "active": "ACTIVE", "pending": "PENDING", "blocked": "BLOCKED",
    "unknown": "UNKNOWN", "open": "UNKNOWN", "candidate": "UNKNOWN",
    "research": "RESEARCH", "learning": "LEARNING", "user_requested": "USER_REQUESTED",
    "regression": "REGRESSION",
}


class ShadowError(ValueError):
    """Stable public-safe R135 error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _content_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_blob(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def _git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False,
    )
    if completed.returncode != 0:
        raise ShadowError("SOURCE_GIT_VERIFICATION_FAILED", "read-only Git verification failed")
    return completed.stdout if binary else completed.stdout.decode("utf-8", errors="strict").strip()


@dataclass(frozen=True)
class ExactSourceBinding:
    """Immutable expected Git tree for one admitted source snapshot."""

    repository: str
    commit: str
    authority_path: str
    authority_blob_sha: str
    path_blobs: tuple[tuple[str, str], ...]

    @property
    def allowed_paths(self) -> tuple[str, ...]:
        return tuple(path for path, _ in self.path_blobs)

    def blob_for(self, path: str) -> str:
        for candidate, blob in self.path_blobs:
            if candidate == path:
                return blob
        raise ShadowError("FORBIDDEN_SOURCE_PATH", "path is outside the exact source allowlist")

    @classmethod
    def fixture_from_git_snapshot(
        cls, root: str | Path, *, repository: str, commit: str, allowed_paths: Iterable[str],
        authority_path: str = "PROJECT_INDEX.yaml",
    ) -> "ExactSourceBinding":
        """Test-only trusted binding maker: derive all blobs from one real Git tree."""
        source_root = Path(root).resolve()
        entries = tuple((path, str(_git(source_root, "rev-parse", f"{commit}:{path}"))) for path in allowed_paths)
        authority_blob = dict(entries).get(authority_path)
        if authority_blob is None:
            raise ShadowError("SOURCE_AUTHORITY_PATH_MISSING", "authority must be in the exact allowlist")
        return cls(repository, commit, authority_path, authority_blob, entries)


ACTIVATED_SOURCE_BINDING = ExactSourceBinding(
    AI_FILM_REPOSITORY, AI_FILM_COMMIT, "PROJECT_INDEX.yaml", PROJECT_INDEX_BLOB, _ACTIVATED_BLOBS,
)


@dataclass(frozen=True)
class DerivedItem:
    stable_ref: str
    state: str

    def public_dict(self) -> dict[str, str]:
        return {"stable_ref": self.stable_ref, "state": self.state}


@dataclass(frozen=True)
class SourceObservation:
    repository: str
    commit: str
    path: str
    blob_sha: str
    content_sha256: str
    authority: str
    schema_ref: str
    metadata: Mapping[str, str]
    derived_state: str
    derived_items: tuple[DerivedItem, ...]

    def opaque_ref(self) -> str:
        return f"git://{self.repository}@{self.commit}/{self.path}#blob={self.blob_sha}"

    def public_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "commit": self.commit,
            "path": self.path,
            "blob_sha": self.blob_sha,
            "content_sha256": self.content_sha256,
            "authority": self.authority,
            "schema_ref": self.schema_ref,
            "metadata": dict(sorted(self.metadata.items())),
            "derived_state": self.derived_state,
            "derived_items": [item.public_dict() for item in self.derived_items],
            "opaque_ref": self.opaque_ref(),
        }


def _state(value: Any) -> str:
    return STATE_MAP.get(str(value).casefold(), "UNKNOWN") if isinstance(value, str) else "UNKNOWN"


def _metadata(document: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key in ("schema_version", "project_id", "registry_id"):
        value = document.get(key)
        if isinstance(value, (str, int, float)):
            result[key] = str(value)
    return result


def _known_items(path: str, document: Mapping[str, Any]) -> tuple[str, tuple[DerivedItem, ...]]:
    """Extract only documented registry item states; every other path is UNKNOWN."""
    list_key = None
    schema_ref = "UNRECOGNIZED_SCHEMA/UNKNOWN"
    if path.endswith("pending_canonical_writes.yaml"):
        list_key, schema_ref = "items", "AI_FILM_PENDING_CANONICAL_WRITES/v1"
    elif path.endswith("UNKNOWN_REGISTRY.yaml") or path.endswith("SOUND_UNKNOWN_REGISTRY.yaml"):
        list_key, schema_ref = "unknowns", "AI_FILM_UNKNOWN_REGISTRY/v1"
    elif path == "PROJECT_INDEX.yaml":
        schema_ref = "AI_FILM_PROJECT_INDEX/v1"
    elif path.endswith(".md"):
        schema_ref = "MARKDOWN_UNSTRUCTURED/UNKNOWN"
    if list_key is None:
        return schema_ref, ()
    raw_items = document.get(list_key)
    if not isinstance(raw_items, list):
        return schema_ref, ()
    items: list[DerivedItem] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            continue
        item_id = item.get("id")
        stable_id = str(item_id) if isinstance(item_id, (str, int)) and str(item_id) else f"ordinal-{index}"
        items.append(DerivedItem(f"{path}#{list_key}/{stable_id}", _state(item.get("status"))))
    return schema_ref, tuple(items)


def _derived_state(items: tuple[DerivedItem, ...]) -> str:
    states = {item.state for item in items}
    return next(iter(states)) if len(states) == 1 else "UNKNOWN"


class ReadOnlyExactCommitAdapter:
    """Read-only adapter with Git-root, HEAD, tree, blob, and payload verification."""

    def __init__(self, root: str | Path, *, binding: ExactSourceBinding = ACTIVATED_SOURCE_BINDING) -> None:
        self.root = Path(root).resolve()
        self.binding = binding
        self._authority_metadata: dict[str, str] | None = None
        self._verify_root()

    def _verify_root(self) -> None:
        top_level = Path(str(_git(self.root, "rev-parse", "--show-toplevel"))).resolve()
        if top_level != self.root:
            raise ShadowError("SOURCE_ROOT_NOT_REPOSITORY_ROOT", "source root must be the verified repository root")
        head = str(_git(self.root, "rev-parse", "HEAD"))
        if head != self.binding.commit:
            raise ShadowError("SOURCE_COMMIT_DRIFT", "source HEAD is not the activated exact commit")
        for path in self.binding.allowed_paths:
            self._verify_path(path)

    def _verify_path(self, path: str) -> bytes:
        expected_blob = self.binding.blob_for(path)
        tree_blob = str(_git(self.root, "rev-parse", f"{self.binding.commit}:{path}"))
        if tree_blob != expected_blob:
            raise ShadowError("SOURCE_TREE_BLOB_MISMATCH", "exact source tree does not match the activated binding")
        committed_payload = _git(self.root, "show", f"{self.binding.commit}:{path}", binary=True)
        assert isinstance(committed_payload, bytes)
        if _git_blob(committed_payload) != expected_blob:
            raise ShadowError("SOURCE_GIT_OBJECT_MISMATCH", "Git object content does not match its bound blob")
        worktree_path = self.root / path
        try:
            worktree_payload = worktree_path.read_bytes()
        except OSError as exc:
            raise ShadowError("SOURCE_PATH_UNREADABLE", "allowlisted source path cannot be read") from exc
        if worktree_payload != committed_payload:
            raise ShadowError("SOURCE_WORKTREE_PAYLOAD_MISMATCH", "worktree payload differs from the exact Git snapshot")
        return worktree_payload

    def _authority(self) -> dict[str, str]:
        if self._authority_metadata is not None:
            return self._authority_metadata
        payload = self._verify_path(self.binding.authority_path)
        if self.binding.authority_blob_sha != self.binding.blob_for(self.binding.authority_path):
            raise ShadowError("SOURCE_AUTHORITY_BLOB_MISMATCH", "authority blob is not the activated authority blob")
        try:
            document = yaml.safe_load(payload.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ShadowError("SOURCE_AUTHORITY_PARSE_FAILED", "authority declaration is not parseable") from exc
        if not isinstance(document, Mapping) or document.get("source_authority") != "this_file":
            raise ShadowError("SOURCE_AUTHORITY_DECLARATION_INVALID", "PROJECT_INDEX does not resolve itself as source authority")
        project_id = document.get("project_id")
        if project_id != "EUSTIA_AI_FILM":
            raise ShadowError("SOURCE_AUTHORITY_PROJECT_INVALID", "authority project identity is invalid")
        self._authority_metadata = {"project_id": str(project_id), "authority_declaration": "this_file"}
        return self._authority_metadata

    def read(self, path: str) -> SourceObservation:
        if path not in self.binding.allowed_paths:
            raise ShadowError("FORBIDDEN_SOURCE_PATH", "path is outside the exact source allowlist")
        payload = self._verify_path(path)
        authority = self._authority()
        document: Mapping[str, Any] = {}
        if path.endswith(".yaml"):
            try:
                parsed = yaml.safe_load(payload.decode("utf-8"))
            except (UnicodeDecodeError, yaml.YAMLError) as exc:
                raise ShadowError("SOURCE_SCHEMA_PARSE_FAILED", "allowlisted YAML source is not parseable") from exc
            if not isinstance(parsed, Mapping):
                raise ShadowError("SOURCE_SCHEMA_NOT_OBJECT", "allowlisted YAML source must be a mapping")
            document = parsed
        schema_ref, items = _known_items(path, document)
        metadata = _metadata(document) | authority
        return SourceObservation(
            self.binding.repository, self.binding.commit, path, self.binding.blob_for(path),
            _content_hash(payload), self.binding.authority_path, schema_ref, metadata,
            _derived_state(items), items,
        )

    def write(self, *_: Any, **__: Any) -> None:
        raise ShadowError("CROSS_REPO_WRITE_FORBIDDEN", "R135 exposes no cross-repository write capability")

    def authorize_domain_write_or_successor(self) -> None:
        raise ShadowError("SIGNAL_NOT_DOMAIN_OR_SUCCESSOR_AUTHORITY", "shadow observation cannot authorize a domain write or successor")


def _s0c_imports() -> tuple[Any, Any, Any]:
    s0c_src = Path(__file__).resolve().parents[3] / "S0-SYNTHETIC" / "src"
    if str(s0c_src) not in sys.path:
        sys.path.insert(0, str(s0c_src))
    from global_signal_plane.ledger import DurableSignalLedger
    from global_signal_plane.models import SignalEvent, SignalLink
    return DurableSignalLedger, SignalEvent, SignalLink


class DurableShadowAdmission:
    """Non-authoritative source staging followed by real S0C durable admission."""

    def __init__(self, db_path: str | Path) -> None:
        DurableSignalLedger, _, _ = _s0c_imports()
        self.db_path = str(db_path)
        self.ledger = DurableSignalLedger(self.db_path)

    def close(self) -> None:
        self.ledger.close()

    @staticmethod
    def _ids(observation: SourceObservation) -> tuple[str, str]:
        signal_id = "s0d-source:" + _digest({"repository": observation.repository, "path": observation.path})[:24]
        event_id = "s0d-observation:" + _digest(observation.public_dict())[:24]
        return signal_id, event_id

    def admit(self, observation: SourceObservation, *, source_sequence: int) -> dict[str, Any]:
        _, SignalEvent, SignalLink = _s0c_imports()
        signal_id, event_id = self._ids(observation)
        execution_state = "DONE" if observation.derived_state == "COMPLETED" else "BLOCKED" if observation.derived_state == "BLOCKED" else "NOT_STARTED"
        epistemic_state = "UNKNOWN" if observation.derived_state == "UNKNOWN" else "CONFIRMED_FACT"
        payload = {
            "schema_version": "SignalEvent/v1", "signal_id": signal_id, "event_id": event_id,
            "event_source": "S0D_READ_ONLY_ADAPTER", "event_type": "SOURCE_OBSERVATION",
            "occurred_at": "2026-08-16T00:00:00+00:00", "observed_at": "2026-08-16T00:00:00+00:00",
            "source_type": "GIT_EXACT_SNAPSHOT", "source_ref": observation.opaque_ref(),
            "source_project": observation.repository, "source_actor": "CODEX",
            "primary_domain": "W8_GLOBAL_SIGNAL_PLANE", "related_domains": ["AI_FILM_READ_ONLY"],
            "signal_kind": "STATUS", "planning_state": "CAPTURED", "execution_state": execution_state,
            "epistemic_state": epistemic_state, "privacy_scope_ref": "PUBLIC_SAFE_METADATA_ONLY",
            "authority_targets": [], "touch_set": ["S0D_READ_ONLY_SHADOW"], "related_signal_refs": [],
            "supersedes_refs": [], "revokes_refs": [], "cross_domain_candidate": False,
            "summary_ref": observation.opaque_ref(), "source_sequence": source_sequence,
            "idempotency_key": event_id, "payload_schema_ref": observation.schema_ref,
            "public_safe_metadata": observation.public_dict(),
        }
        event = SignalEvent.from_dict(payload)
        event_receipt = self.ledger.ingest(event)
        link = SignalLink.from_dict({
            "link_id": "s0d-evidence:" + _digest({"event": event_id, "ref": observation.opaque_ref()})[:24],
            "from_signal_ref": signal_id, "to_signal_ref": observation.opaque_ref(), "relation_type": "SHARED_EVIDENCE",
            "evidence_refs": [observation.opaque_ref()], "created_at": "2026-08-16T00:00:00+00:00", "created_by": "CODEX",
        })
        link_receipt = self.ledger.append_link(link)
        return {"event": event_receipt, "link": link_receipt, "signal_id": signal_id, "event_id": event_id}

    def admit_snapshot(self, observations: Iterable[SourceObservation], *, source_sequence_start: int = 1) -> list[dict[str, Any]]:
        """Admit only present observations; omission deliberately emits no revoke or supersede."""
        return [
            self.admit(observation, source_sequence=source_sequence_start + index)
            for index, observation in enumerate(observations)
        ]

    def durable_replay_receipt(self) -> dict[str, Any]:
        if self.db_path == ":memory:":
            raise ShadowError("DURABLE_REPLAY_REQUIRES_FILE", "fresh-ledger replay requires a SQLite file")
        first = self.ledger.current_projection() or self.ledger.rebuild_projection(expected_version=self.ledger.current_projection_version())
        self.ledger.close()
        DurableSignalLedger, _, _ = _s0c_imports()
        rebuilt = DurableSignalLedger(self.db_path)
        try:
            fresh = rebuilt.rebuild_projection(expected_version=rebuilt.current_projection_version())
            return {
                "replayed_from_persisted_history": True,
                "before_checksum": first["checksum"], "fresh_checksum": fresh["checksum"],
                "match": first["checksum"] == fresh["checksum"], "history_count": len(rebuilt.history()),
            }
        finally:
            rebuilt.close()
            self.ledger = DurableSignalLedger(self.db_path)

    def staging_summary(self, observations: Iterable[SourceObservation]) -> dict[str, Any]:
        records = [observation.public_dict() for observation in observations]
        unresolved = sorted(record["path"] for record in records if record["derived_state"] == "UNKNOWN")
        missing = sorted(set(ALLOWED_PATHS) - {record["path"] for record in records})
        summary = {
            "reducer_version": "S0D_NON_AUTHORITATIVE_STAGING/v2",
            "missing_paths": missing, "unresolved_paths": unresolved,
            "backlog_state": "AI_FILM_DOMAIN_BACKLOG_BOOTSTRAP_REQUIRED" if missing or unresolved else "BOOTSTRAP_COVERAGE_COMPLETE",
        }
        summary["checksum"] = _digest(summary)
        return summary


def _control_file_binding(root: Path, commit: str, path: str) -> dict[str, str]:
    payload = _git(root, "show", f"{commit}:{path}", binary=True)
    assert isinstance(payload, bytes)
    return {"path": path, "blob_sha": str(_git(root, "rev-parse", f"{commit}:{path}")), "content_sha256": _content_hash(payload)}


def build_second_brain_snapshot(root: str | Path, *, commit: str) -> dict[str, Any]:
    """Read an exact public-safe Second Brain control-plane snapshot through Git."""
    repository_root = Path(root).resolve()
    exact_commit = str(_git(repository_root, "rev-parse", commit))
    active_path = "coordination/ACTIVE-CODEX-TASK.yaml"
    active_payload = _git(repository_root, "show", f"{exact_commit}:{active_path}", binary=True)
    assert isinstance(active_payload, bytes)
    try:
        active = yaml.safe_load(active_payload.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ShadowError("SECOND_BRAIN_CONTROL_PARSE_FAILED", "active route cannot be parsed") from exc
    if not isinstance(active, Mapping) or not isinstance(active.get("canonical_route"), str):
        raise ShadowError("SECOND_BRAIN_CONTROL_INVALID", "active route does not declare its canonical route")
    route_path = str(active["canonical_route"])
    work_claim_path = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
    program_lane_path = "coordination/ACTIVE-PROGRAM-LANES.yaml"
    paths = (active_path, route_path, work_claim_path, program_lane_path)
    return {
        "repository": "vxz2datoubo/second-brain-coordination", "main": exact_commit,
        "task_id": str(active.get("task_id", "UNKNOWN")), "route_epoch": str(active.get("route_epoch", "UNKNOWN")),
        "route": route_path, "work_claim": work_claim_path, "program_lane": program_lane_path,
        "file_bindings": [_control_file_binding(repository_root, exact_commit, path) for path in paths],
    }


def self_shadow(snapshot: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    fields = ("repository", "main", "task_id", "route_epoch", "route", "work_claim", "program_lane", "file_bindings")
    changed = sorted(field for field in fields if snapshot.get(field) != current.get(field))
    return {"valid": not changed, "result": "PASS" if not changed else "BLOCKED", "codes": [] if not changed else ["CROSS_WINDOW_STATE_DRIFT"], "changed_fields": changed}


def one_shot_receipt(
    adapter: ReadOnlyExactCommitAdapter, *, db_path: str | Path, second_brain_root: str | Path,
    second_brain_commit: str,
) -> dict[str, Any]:
    """Produce a public-safe, reproducible manifest and durable replay witness."""
    observations = [adapter.read(path) for path in adapter.binding.allowed_paths]
    admission = DurableShadowAdmission(db_path)
    try:
        admissions = admission.admit_snapshot(observations)
        durable_replay = admission.durable_replay_receipt()
        durable_projection = admission.ledger.current_projection()
        control_snapshot = build_second_brain_snapshot(second_brain_root, commit=second_brain_commit)
        return {
            "receipt_type": "REAL_SOURCE_ONE_SHOT_SHADOW_RECEIPT/v2",
            "source_binding": {
                "repository": adapter.binding.repository, "exact_commit": adapter.binding.commit,
                "authority_path": adapter.binding.authority_path, "authority_blob_sha": adapter.binding.authority_blob_sha,
            },
            "observations": [observation.public_dict() for observation in observations],
            "staging_summary": admission.staging_summary(observations),
            "durable_s0c_admission": {"event_and_link_receipts": admissions, "projection": durable_projection, "replay": durable_replay},
            "second_brain_self_shadow": {"snapshot": control_snapshot, "drift_result": self_shadow(control_snapshot, control_snapshot)},
            "raw_domain_body_persisted": False, "cross_repo_write_authorized": False,
        }
    finally:
        admission.close()
