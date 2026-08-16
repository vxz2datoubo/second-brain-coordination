"""Read-only exact-commit source adapter and deterministic metadata shadow reducer."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

AI_FILM_REPOSITORY = "vxz2datoubo/eustia-ai-film"
AI_FILM_COMMIT = "44c383afd2207a97caf45b1b0da6ee1dece43a76"
PROJECT_INDEX_BLOB = "a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19"
ALLOWED_PATHS = (
    "PROJECT_INDEX.yaml", "07_连续性与生产状态/连续性与当前生产状态.md",
    "10_运行时/pending_canonical_writes.yaml", "10_运行时/director_route_index.yaml",
    "10_运行时/maturity_model.yaml", "11_验收/director_regression_cases.yaml",
    "11_验收/golden_prompt_regression_cases.yaml", "11_验收/golden_case_director_pull_regression_cases.yaml",
    "12_未知项/UNKNOWN_REGISTRY.yaml", "12_未知项/SOUND_UNKNOWN_REGISTRY.yaml",
)
STATE_MAP = {"completed": "COMPLETED", "active": "ACTIVE", "pending": "PENDING", "blocked": "BLOCKED", "unknown": "UNKNOWN", "open": "UNKNOWN", "candidate": "UNKNOWN", "research": "RESEARCH", "learning": "LEARNING", "user_requested": "USER_REQUESTED", "regression": "REGRESSION", "closed": "COMPLETED"}


class ShadowError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message); self.code = code


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _git_blob(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


@dataclass(frozen=True)
class SourceObservation:
    repository: str
    commit: str
    path: str
    blob_sha: str
    content_sha256: str
    authority: str
    metadata: Mapping[str, str]
    observed_states: tuple[str, ...]

    def opaque_ref(self) -> str:
        return f"git://{self.repository}@{self.commit}/{self.path}#blob={self.blob_sha}"

    def public_dict(self) -> dict[str, Any]:
        return {"repository": self.repository, "commit": self.commit, "path": self.path, "blob_sha": self.blob_sha, "content_sha256": self.content_sha256, "authority": self.authority, "metadata": dict(self.metadata), "observed_states": list(self.observed_states), "opaque_ref": self.opaque_ref()}


class ReadOnlyExactCommitAdapter:
    """Filesystem source is accepted only as an exact bound snapshot; no write API exists."""
    def __init__(self, root: str | Path, *, repository: str = AI_FILM_REPOSITORY, commit: str = AI_FILM_COMMIT) -> None:
        self.root, self.repository, self.commit = Path(root), repository, commit
        if repository != AI_FILM_REPOSITORY or commit != AI_FILM_COMMIT:
            raise ShadowError("SOURCE_COMMIT_DRIFT", "source repository or commit is not the activated snapshot")

    def read(self, path: str) -> SourceObservation:
        if path not in ALLOWED_PATHS:
            raise ShadowError("FORBIDDEN_SOURCE_PATH", "path is outside the read allowlist")
        payload = (self.root / path).read_bytes()
        text = payload.decode("utf-8", errors="replace")
        fields = {key: value.strip().strip('"') for key, value in re.findall(r"(?m)^([A-Za-z_][A-Za-z0-9_]*):\s*([^#\r\n]+)", text) if key in {"schema_version", "project_id", "status", "source_authority", "registry_id"}}
        states = tuple(sorted({STATE_MAP.get(value.casefold(), "UNKNOWN") for value in re.findall(r"(?im)^\s*status:\s*([A-Za-z_]+)", text)} or {"UNKNOWN"}))
        observation = SourceObservation(self.repository, self.commit, path, _git_blob(payload), hashlib.sha256(payload).hexdigest(), "PROJECT_INDEX.yaml", fields, states)
        if path == "PROJECT_INDEX.yaml" and observation.blob_sha != PROJECT_INDEX_BLOB:
            raise ShadowError("SOURCE_AUTHORITY_BLOB_MISMATCH", "PROJECT_INDEX blob does not match activated authority")
        return observation

    def write(self, *_: Any, **__: Any) -> None:
        raise ShadowError("CROSS_REPO_WRITE_FORBIDDEN", "R135 adapter exposes no cross-repository write capability")


class ShadowLedger:
    """Append-only metadata history; projections never retain source bodies."""
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    def append(self, observation: SourceObservation) -> dict[str, Any]:
        public = observation.public_dict(); identity = _digest(public)
        if identity in self._seen:
            return {"status": "IDEMPOTENT_DUPLICATE", "identity": identity}
        self._seen.add(identity); self._history.append({"identity": identity, "observation": public})
        return {"status": "ADMITTED", "identity": identity}

    def history(self) -> list[dict[str, Any]]:
        return json.loads(_canonical(self._history))

    def projection(self, *, required_paths: tuple[str, ...] = ALLOWED_PATHS) -> dict[str, Any]:
        current: dict[str, dict[str, Any]] = {}
        for item in self._history:
            obs = item["observation"]; current[obs["path"]] = obs
        missing = sorted(set(required_paths) - set(current)); unresolved = sorted(path for path, obs in current.items() if obs["observed_states"] == ["UNKNOWN"])
        states = sorted({state for obs in current.values() for state in obs["observed_states"]})
        backlog = "AI_FILM_DOMAIN_BACKLOG_BOOTSTRAP_REQUIRED" if missing or unresolved else "BOOTSTRAP_COVERAGE_COMPLETE"
        body_free = {"reducer_version": "S0D-1", "source_commit": AI_FILM_COMMIT, "observations": [current[path] for path in sorted(current)], "missing_paths": missing, "unresolved_paths": unresolved, "observed_states": states, "backlog_state": backlog, "history_count": len(self._history)}
        body_free["checksum"] = _digest(body_free)
        return body_free


def self_shadow(snapshot: Mapping[str, str], current: Mapping[str, str]) -> dict[str, Any]:
    fields = ("repository", "main", "task_id", "route", "work_claim", "program_lane")
    changed = sorted(field for field in fields if snapshot.get(field) != current.get(field))
    return {"valid": not changed, "result": "PASS" if not changed else "BLOCKED", "codes": [] if not changed else ["CROSS_WINDOW_STATE_DRIFT"], "changed_fields": changed}


def one_shot_receipt(adapter: ReadOnlyExactCommitAdapter) -> dict[str, Any]:
    ledger = ShadowLedger()
    for path in ALLOWED_PATHS:
        ledger.append(adapter.read(path))
    projection = ledger.projection()
    return {"receipt_type": "REAL_SOURCE_ONE_SHOT_SHADOW_RECEIPT", "source_repository": AI_FILM_REPOSITORY, "source_commit": AI_FILM_COMMIT, "source_authority": "PROJECT_INDEX.yaml", "source_authority_blob_sha": PROJECT_INDEX_BLOB, "approved_read_paths": list(ALLOWED_PATHS), "projection": projection, "raw_domain_body_persisted": False, "cross_repo_write_authorized": False}
