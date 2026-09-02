from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

AUDIT_SCHEMA = "ResearchIntegrityAudit/v1"
LOCKBOX_SCHEMA = "LockboxAccessReceipt/v1"
SKILL_ID = "RESEARCH-MULTIPLE-TESTING-OVERFITTING-AUDIT-SKILL-0012J"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")

W2_RULE_RUNTIME_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-2-OFFLINE-VERTICAL-SLICE/src/offline_research/r143_rules.py"
W2_DATASET_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-2-OFFLINE-VERTICAL-SLICE/fixtures/synthetic_bars.jsonl"
W2_PARAMETER_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-2-OFFLINE-VERTICAL-SLICE/fixtures/r143_cases.json"
W2_ENGINE_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-2-OFFLINE-VERTICAL-SLICE/src/offline_research/engine.py"
R183_WORK_CLAIM_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/DS10-RESEARCH-INTEGRITY-P0A-R183/WORK-CLAIM.yaml"
R183_AUTH_WITNESS_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/DS10-RESEARCH-INTEGRITY-P0A-R183/AUTHORIZATION-WITNESS.yaml"

# P0A trust roots are exact canonical Git artifacts. Callers may name them, but
# runtime re-reads the bytes and verifies the Git blob identity before emitting
# any positive PIT/lockbox provenance subclaim.
_GOVERNED_ARTIFACTS = {
    W2_RULE_RUNTIME_REF: "18311ff30beab7ea97d54c09e44fd6e6ebe921ed",
    W2_DATASET_REF: "934b95414a41c003392f4dd870f401474affa839",
    W2_PARAMETER_REF: "7b19b75714701643006ac8d846ee934d764ca224",
    W2_ENGINE_REF: "7c2ecacd1bebd62fd453d25d6374da5df193446e",
    R183_WORK_CLAIM_REF: "0c210c6daff8352516f1f80d7b5de6aabb5597c3",
    R183_AUTH_WITNESS_REF: "d75bce3a40835e63b7ef98196a3dbb7c747cfddc",
}


class TrialStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ABORTED = "ABORTED"
    ERROR = "ERROR"


class PITStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class MethodStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"


class LockboxStatus(str, Enum):
    SEALED_UNUSED = "SEALED_UNUSED"
    OPENED_ONCE_FINAL_EVAL = "OPENED_ONCE_FINAL_EVAL"
    CONTAMINATED_REUSED_FOR_SELECTION = "CONTAMINATED_REUSED_FOR_SELECTION"
    IDENTITY_OR_ACCESS_HISTORY_UNKNOWN = "IDENTITY_OR_ACCESS_HISTORY_UNKNOWN"


class LockboxPurpose(str, Enum):
    FINAL_EVAL = "FINAL_EVAL"
    TUNING = "TUNING"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    PROMPT_OPTIMIZATION = "PROMPT_OPTIMIZATION"
    MODEL_SELECTION = "MODEL_SELECTION"
    PARAMETER_SELECTION = "PARAMETER_SELECTION"
    RESELECTION = "RESELECTION"
    DIAGNOSTIC = "DIAGNOSTIC"


class Disposition(str, Enum):
    ELIGIBLE_FOR_W7_VALIDATION = "ELIGIBLE_FOR_W7_VALIDATION"
    RETEST_WITH_PREREGISTERED_FAMILY = "RETEST_WITH_PREREGISTERED_FAMILY"
    REJECT_INCOMPLETE_TRIAL_HISTORY = "REJECT_INCOMPLETE_TRIAL_HISTORY"
    REJECT_LOCKBOX_CONTAMINATION = "REJECT_LOCKBOX_CONTAMINATION"
    REJECT_POINT_IN_TIME_LEAKAGE = "REJECT_POINT_IN_TIME_LEAKAGE"
    REJECT_SELECTION_BIAS = "REJECT_SELECTION_BIAS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ABSTAIN = "ABSTAIN"


class IntegrityValidationError(ValueError):
    def __init__(self, code: str, path: str, message: str):
        super().__init__(f"{code} at {path}: {message}")
        self.code, self.path, self.message = code, path, message


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode()).hexdigest()


def _text(value: str, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntegrityValidationError("EMPTY_IDENTITY", path, "non-empty string required")
    return value.strip()


def _sha(value: str, path: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise IntegrityValidationError("INVALID_SHA256", path, "lowercase 64-hex SHA-256 required")
    return value


def _git_sha(value: str, path: str) -> str:
    if not isinstance(value, str) or not _GIT_SHA.fullmatch(value):
        raise IntegrityValidationError("INVALID_GIT_BLOB_SHA", path, "lowercase 40-hex Git blob SHA required")
    return value


def _time(value: str, path: str) -> datetime:
    _text(value, path)
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntegrityValidationError("INVALID_TIMESTAMP", path, "ISO-8601 timestamp required") from exc
    if out.tzinfo is None or out.utcoffset() is None:
        raise IntegrityValidationError("NAIVE_TIMESTAMP", path, "timezone required")
    return out


def _as_enum(value: Any, kind: type[Enum], path: str):
    try:
        return kind(value)
    except (TypeError, ValueError) as exc:
        raise IntegrityValidationError("INVALID_ENUM", path, f"invalid {kind.__name__}") from exc


def _finding(code: str, severity: str, path: str, detail: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "path": path, "detail": detail}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "coordination").is_dir():
            return parent
    raise IntegrityValidationError("REPO_ROOT_UNRESOLVED", "repository", "coordination root not found")


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _verify_governed_artifact(ref: str, claimed_blob_sha: str, path: str) -> tuple[Path, bytes]:
    _text(ref, f"{path}.ref")
    _git_sha(claimed_blob_sha, f"{path}.blob_sha")
    expected = _GOVERNED_ARTIFACTS.get(ref)
    if expected is None:
        raise IntegrityValidationError("UNGOVERNED_ARTIFACT_REF", f"{path}.ref", "ref is not a P0A governed trust root")
    if claimed_blob_sha != expected:
        raise IntegrityValidationError("GOVERNED_ARTIFACT_CLAIM_MISMATCH", f"{path}.blob_sha", "claimed blob differs from governed identity")
    root = _repo_root().resolve()
    target = (root / ref).resolve()
    if root not in target.parents:
        raise IntegrityValidationError("ARTIFACT_PATH_ESCAPE", f"{path}.ref", "artifact escaped repository root")
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise IntegrityValidationError("GOVERNED_ARTIFACT_UNAVAILABLE", f"{path}.ref", "governed artifact cannot be read") from exc
    actual = _git_blob_sha(raw)
    if actual != expected:
        raise IntegrityValidationError("GOVERNED_ARTIFACT_BYTES_DRIFTED", f"{path}.blob_sha", f"actual={actual}")
    return target, raw


def _load_verified_w2_rule_module(ref: str, blob_sha: str):
    path, _ = _verify_governed_artifact(ref, blob_sha, "pit.authority_source")
    spec = importlib.util.spec_from_file_location("_ds10_verified_w2_rules", path)
    if spec is None or spec.loader is None:
        raise IntegrityValidationError("W2_RULE_MODULE_LOAD_FAILED", "pit.authority_source_ref", "module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_jsonl_event(ref: str, blob_sha: str, event_id: str) -> dict[str, Any]:
    _, raw = _verify_governed_artifact(ref, blob_sha, "pit.dataset_artifact")
    matches = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("event_id") == event_id:
            matches.append(row)
    if len(matches) != 1:
        raise IntegrityValidationError("PIT_EVENT_NOT_UNIQUE", "pit.dataset_event_id", f"matches={len(matches)}")
    return matches[0]


def _yaml_scalar(raw: bytes, key: str) -> str | None:
    pattern = re.compile(rf"(?m)^\s*{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$")
    match = pattern.search(raw.decode("utf-8"))
    return match.group(1).strip() if match else None


@dataclass(frozen=True)
class TrialRecord:
    trial_id: str
    immutable_digest: str
    status: TrialStatus
    selection_affecting: bool = True
    rerun_of: str | None = None
    configuration_digest: str | None = None

    def __post_init__(self):
        _text(self.trial_id, "trial.trial_id")
        _sha(self.immutable_digest, "trial.immutable_digest")
        object.__setattr__(self, "status", _as_enum(self.status, TrialStatus, "trial.status"))
        if not isinstance(self.selection_affecting, bool):
            raise IntegrityValidationError("INVALID_BOOLEAN", "trial.selection_affecting", "boolean required")
        if self.rerun_of is not None:
            _text(self.rerun_of, "trial.rerun_of")
        if self.configuration_digest is not None:
            _sha(self.configuration_digest, "trial.configuration_digest")
        if not self.selection_affecting and self.rerun_of is None:
            raise IntegrityValidationError("NON_SELECTION_TRIAL_WITHOUT_RERUN_LINK", "trial.rerun_of", "rerun link required")
        if self.selection_affecting and self.rerun_of is not None:
            raise IntegrityValidationError("SELECTION_TRIAL_CANNOT_BE_RERUN_ALIAS", "trial.rerun_of", "new economic identity required")

    def row(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "immutable_digest": self.immutable_digest,
            "status": self.status.value,
            "selection_affecting": self.selection_affecting,
            "rerun_of": self.rerun_of,
            "configuration_digest": self.configuration_digest,
        }


@dataclass(frozen=True)
class ExperimentFamilySnapshot:
    experiment_family_ref: str
    expected_trial_digests: Mapping[str, str]
    trials: tuple[TrialRecord, ...]
    benchmark_ref: str
    metric_id: str
    horizon_id: str
    search_space_ref: str
    selection_rule_ref: str
    registered_family_digest: str
    selection_rule_registered_at: str
    selected_trial_id: str
    selected_at: str
    candidate_frozen_at: str
    family_frozen_at: str
    lockbox_id: str
    lockbox_access_history_complete: bool
    declared_trial_count: int | None = None
    required_method_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for name in (
            "experiment_family_ref", "benchmark_ref", "metric_id", "horizon_id",
            "search_space_ref", "selection_rule_ref", "selected_trial_id", "lockbox_id",
        ):
            _text(getattr(self, name), f"family.{name}")
        _sha(self.registered_family_digest, "family.registered_family_digest")
        if not isinstance(self.expected_trial_digests, Mapping) or not self.expected_trial_digests:
            raise IntegrityValidationError("EMPTY_TRIAL_MANIFEST", "family.expected_trial_digests", "non-empty W4 manifest required")
        for key, value in self.expected_trial_digests.items():
            _text(key, "family.expected_trial_digests.key")
            _sha(value, f"family.expected_trial_digests.{key}")
        if not isinstance(self.lockbox_access_history_complete, bool):
            raise IntegrityValidationError("INVALID_BOOLEAN", "family.lockbox_access_history_complete", "boolean required")
        if self.declared_trial_count is not None and (
            isinstance(self.declared_trial_count, bool)
            or not isinstance(self.declared_trial_count, int)
            or self.declared_trial_count < 0
        ):
            raise IntegrityValidationError("INVALID_COUNT", "family.declared_trial_count", "non-negative integer required")
        if len(set(self.required_method_ids)) != len(self.required_method_ids):
            raise IntegrityValidationError("DUPLICATE_METHOD_ID", "family.required_method_ids", "unique IDs required")
        for method in self.required_method_ids:
            _text(method, "family.required_method_ids")
        for name in ("selection_rule_registered_at", "selected_at", "candidate_frozen_at", "family_frozen_at"):
            _time(getattr(self, name), f"family.{name}")

    def family_material(self) -> dict[str, Any]:
        return {
            "experiment_family_ref": self.experiment_family_ref,
            "expected_trial_digests": dict(sorted(self.expected_trial_digests.items())),
            "benchmark_ref": self.benchmark_ref,
            "metric_id": self.metric_id,
            "horizon_id": self.horizon_id,
            "search_space_ref": self.search_space_ref,
            "selection_rule_ref": self.selection_rule_ref,
        }

    def computed_family_digest(self) -> str:
        return _digest(self.family_material())

    def snapshot_material(self) -> dict[str, Any]:
        return {
            **self.family_material(),
            "registered_family_digest": self.registered_family_digest,
            "selection_rule_registered_at": self.selection_rule_registered_at,
            "selected_trial_id": self.selected_trial_id,
            "selected_at": self.selected_at,
            "candidate_frozen_at": self.candidate_frozen_at,
            "family_frozen_at": self.family_frozen_at,
            "lockbox_id": self.lockbox_id,
            "lockbox_access_history_complete": self.lockbox_access_history_complete,
            "declared_trial_count": self.declared_trial_count,
            "required_method_ids": list(self.required_method_ids),
            "trials": [t.row() for t in self.trials],
        }

    def snapshot_digest(self) -> str:
        return _digest(self.snapshot_material())


def lockbox_configuration_material(
    *,
    dataset_artifact_ref: str,
    dataset_artifact_blob_sha: str,
    code_artifact_ref: str,
    code_artifact_blob_sha: str,
    parameter_artifact_ref: str,
    parameter_artifact_blob_sha: str,
    cost_artifact_ref: str,
    cost_artifact_blob_sha: str,
    rule_artifact_ref: str,
    rule_artifact_blob_sha: str,
    rule_snapshot_id: str,
    accessor_claim_ref: str,
    accessor_claim_blob_sha: str,
    authorization_witness_ref: str,
    authorization_witness_blob_sha: str,
    accessor_id: str,
    task_id: str,
    configuration_frozen_at: str,
) -> dict[str, str]:
    material = {
        "dataset_artifact_ref": _text(dataset_artifact_ref, "lockbox.dataset_artifact_ref"),
        "dataset_artifact_blob_sha": _git_sha(dataset_artifact_blob_sha, "lockbox.dataset_artifact_blob_sha"),
        "code_artifact_ref": _text(code_artifact_ref, "lockbox.code_artifact_ref"),
        "code_artifact_blob_sha": _git_sha(code_artifact_blob_sha, "lockbox.code_artifact_blob_sha"),
        "parameter_artifact_ref": _text(parameter_artifact_ref, "lockbox.parameter_artifact_ref"),
        "parameter_artifact_blob_sha": _git_sha(parameter_artifact_blob_sha, "lockbox.parameter_artifact_blob_sha"),
        "cost_artifact_ref": _text(cost_artifact_ref, "lockbox.cost_artifact_ref"),
        "cost_artifact_blob_sha": _git_sha(cost_artifact_blob_sha, "lockbox.cost_artifact_blob_sha"),
        "rule_artifact_ref": _text(rule_artifact_ref, "lockbox.rule_artifact_ref"),
        "rule_artifact_blob_sha": _git_sha(rule_artifact_blob_sha, "lockbox.rule_artifact_blob_sha"),
        "rule_snapshot_id": _text(rule_snapshot_id, "lockbox.rule_snapshot_id"),
        "accessor_claim_ref": _text(accessor_claim_ref, "lockbox.accessor_claim_ref"),
        "accessor_claim_blob_sha": _git_sha(accessor_claim_blob_sha, "lockbox.accessor_claim_blob_sha"),
        "authorization_witness_ref": _text(authorization_witness_ref, "lockbox.authorization_witness_ref"),
        "authorization_witness_blob_sha": _git_sha(authorization_witness_blob_sha, "lockbox.authorization_witness_blob_sha"),
        "accessor_id": _text(accessor_id, "lockbox.accessor_id"),
        "task_id": _text(task_id, "lockbox.task_id"),
        "configuration_frozen_at": _text(configuration_frozen_at, "lockbox.configuration_frozen_at"),
    }
    _time(configuration_frozen_at, "lockbox.configuration_frozen_at")
    return material


def lockbox_configuration_digest(**kwargs: str) -> str:
    return _digest(lockbox_configuration_material(**kwargs))


@dataclass(frozen=True)
class LockboxAccessReceipt:
    access_id: str
    lockbox_id: str
    opened_at: str
    candidate_id: str
    candidate_digest: str
    purpose: LockboxPurpose
    result_digest: str
    selection_consumed_after: bool
    dataset_artifact_ref: str | None = None
    dataset_artifact_blob_sha: str | None = None
    code_artifact_ref: str | None = None
    code_artifact_blob_sha: str | None = None
    parameter_artifact_ref: str | None = None
    parameter_artifact_blob_sha: str | None = None
    cost_artifact_ref: str | None = None
    cost_artifact_blob_sha: str | None = None
    rule_artifact_ref: str | None = None
    rule_artifact_blob_sha: str | None = None
    rule_snapshot_id: str | None = None
    accessor_claim_ref: str | None = None
    accessor_claim_blob_sha: str | None = None
    authorization_witness_ref: str | None = None
    authorization_witness_blob_sha: str | None = None
    accessor_id: str | None = None
    task_id: str | None = None
    configuration_frozen_at: str | None = None
    configuration_digest: str | None = None
    subsequent_action: str | None = None

    def __post_init__(self):
        for name in ("access_id", "lockbox_id", "candidate_id"):
            _text(getattr(self, name), f"lockbox.{name}")
        _time(self.opened_at, "lockbox.opened_at")
        _sha(self.candidate_digest, "lockbox.candidate_digest")
        object.__setattr__(self, "purpose", _as_enum(self.purpose, LockboxPurpose, "lockbox.purpose"))
        _sha(self.result_digest, "lockbox.result_digest")
        if not isinstance(self.selection_consumed_after, bool):
            raise IntegrityValidationError("INVALID_BOOLEAN", "lockbox.selection_consumed_after", "boolean required")
        if self.subsequent_action is not None:
            _text(self.subsequent_action, "lockbox.subsequent_action")
        if self.configuration_digest is not None:
            _sha(self.configuration_digest, "lockbox.configuration_digest")

    def configuration_kwargs(self) -> dict[str, str] | None:
        names = (
            "dataset_artifact_ref", "dataset_artifact_blob_sha", "code_artifact_ref", "code_artifact_blob_sha",
            "parameter_artifact_ref", "parameter_artifact_blob_sha", "cost_artifact_ref", "cost_artifact_blob_sha",
            "rule_artifact_ref", "rule_artifact_blob_sha", "rule_snapshot_id", "accessor_claim_ref",
            "accessor_claim_blob_sha", "authorization_witness_ref", "authorization_witness_blob_sha",
            "accessor_id", "task_id", "configuration_frozen_at",
        )
        values = {name: getattr(self, name) for name in names}
        if any(value is None for value in values.values()):
            return None
        return {name: str(value) for name, value in values.items()}

    def row(self) -> dict[str, Any]:
        return {
            "schema": LOCKBOX_SCHEMA,
            "access_id": self.access_id,
            "lockbox_id": self.lockbox_id,
            "opened_at": self.opened_at,
            "candidate_id": self.candidate_id,
            "candidate_digest": self.candidate_digest,
            "purpose": self.purpose.value,
            "result_digest": self.result_digest,
            "selection_consumed_after": self.selection_consumed_after,
            "dataset_artifact_ref": self.dataset_artifact_ref,
            "dataset_artifact_blob_sha": self.dataset_artifact_blob_sha,
            "code_artifact_ref": self.code_artifact_ref,
            "code_artifact_blob_sha": self.code_artifact_blob_sha,
            "parameter_artifact_ref": self.parameter_artifact_ref,
            "parameter_artifact_blob_sha": self.parameter_artifact_blob_sha,
            "cost_artifact_ref": self.cost_artifact_ref,
            "cost_artifact_blob_sha": self.cost_artifact_blob_sha,
            "rule_artifact_ref": self.rule_artifact_ref,
            "rule_artifact_blob_sha": self.rule_artifact_blob_sha,
            "rule_snapshot_id": self.rule_snapshot_id,
            "accessor_claim_ref": self.accessor_claim_ref,
            "accessor_claim_blob_sha": self.accessor_claim_blob_sha,
            "authorization_witness_ref": self.authorization_witness_ref,
            "authorization_witness_blob_sha": self.authorization_witness_blob_sha,
            "accessor_id": self.accessor_id,
            "task_id": self.task_id,
            "configuration_frozen_at": self.configuration_frozen_at,
            "configuration_digest": self.configuration_digest,
            "subsequent_action": self.subsequent_action,
        }

    def as_dict(self) -> dict[str, Any]:
        return self.row()


@dataclass(frozen=True)
class PITEvidence:
    dataset_lineage: PITStatus
    available_at_lineage: PITStatus
    rule_version: PITStatus
    revision_timing: PITStatus
    universe_membership: PITStatus
    future_information_findings: tuple[str, ...] = ()
    authority_source_ref: str | None = None
    authority_source_blob_sha: str | None = None
    dataset_artifact_ref: str | None = None
    dataset_artifact_blob_sha: str | None = None
    dataset_event_id: str | None = None
    symbol: str | None = None
    exchange: str | None = None
    board: str | None = None
    security_status: str | None = None
    trading_day: str | None = None
    rule_snapshot_id: str | None = None

    def __post_init__(self):
        for name in ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership"):
            object.__setattr__(self, name, _as_enum(getattr(self, name), PITStatus, f"pit.{name}"))
        for item in self.future_information_findings:
            _text(item, "pit.future_information_findings")

    def declared_statuses(self) -> dict[str, str]:
        return {
            name: getattr(self, name).value
            for name in ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership")
        }

    def binding_complete(self) -> bool:
        names = (
            "authority_source_ref", "authority_source_blob_sha", "dataset_artifact_ref",
            "dataset_artifact_blob_sha", "dataset_event_id", "symbol", "exchange",
            "board", "security_status", "trading_day", "rule_snapshot_id",
        )
        return all(getattr(self, name) is not None for name in names)


@dataclass(frozen=True)
class MethodResult:
    method_id: str
    status: MethodStatus
    computation_ref: str | None = None
    applicability_reason: str | None = None

    def __post_init__(self):
        _text(self.method_id, "method.method_id")
        object.__setattr__(self, "status", _as_enum(self.status, MethodStatus, "method.status"))
        if self.computation_ref is not None:
            _text(self.computation_ref, "method.computation_ref")
        if self.applicability_reason is not None:
            _text(self.applicability_reason, "method.applicability_reason")
        if self.status is MethodStatus.NOT_APPLICABLE and not self.applicability_reason:
            raise IntegrityValidationError("NOT_APPLICABLE_REQUIRES_REASON", "method.applicability_reason", "reason required")

    def row(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "status": self.status.value,
            "computation_ref": self.computation_ref,
            "applicability_reason": self.applicability_reason,
        }


def _reconcile_trials(s: ExperimentFamilySnapshot):
    f: list[dict[str, str]] = []
    seen: dict[str, TrialRecord] = {}
    dup = set()
    for t in s.trials:
        if t.trial_id in seen:
            dup.add(t.trial_id)
        else:
            seen[t.trial_id] = t
    for tid in sorted(dup):
        f.append(_finding("DUPLICATE_TRIAL_ID", "BLOCKING", f"trials.{tid}", "duplicate identity"))
    expected = dict(s.expected_trial_digests)
    economic = {k: v for k, v in seen.items() if v.selection_affecting}
    reruns = {k: v for k, v in seen.items() if not v.selection_affecting}
    missing = sorted(set(expected) - set(economic))
    unexpected = sorted(set(economic) - set(expected))
    mutated = []
    invalid_reruns = []
    for tid in missing:
        f.append(_finding("MISSING_EXPECTED_TRIAL", "BLOCKING", f"trials.{tid}", "manifested trial absent"))
    for tid in unexpected:
        f.append(_finding("UNREGISTERED_SELECTION_TRIAL", "BLOCKING", f"trials.{tid}", "selection trial absent from manifest"))
    for tid in sorted(set(expected) & set(economic)):
        if expected[tid] != economic[tid].immutable_digest:
            mutated.append(tid)
            f.append(_finding("TRIAL_IMMUTABLE_DIGEST_MISMATCH", "BLOCKING", f"trials.{tid}.immutable_digest", "trial mutated"))
    for tid, t in sorted(reruns.items()):
        if expected.get(t.rerun_of or "") != t.immutable_digest:
            invalid_reruns.append(tid)
            f.append(_finding("INVALID_REPRODUCIBILITY_RERUN", "BLOCKING", f"trials.{tid}", "rerun does not preserve original"))
    count = len(economic)
    if s.declared_trial_count is not None and s.declared_trial_count != count:
        f.append(_finding(
            "DECLARED_TRIAL_COUNT_MISMATCH", "WARNING", "family.declared_trial_count",
            f"declared={s.declared_trial_count}; observed={count}",
        ))
    counts = {x.value: 0 for x in TrialStatus}
    for t in economic.values():
        counts[t.status.value] += 1
    return {
        "expected_trial_count": len(expected),
        "declared_trial_count": s.declared_trial_count,
        "observed_trial_count": count,
        "successful_trial_count": counts["SUCCESS"],
        "failed_trial_count": counts["FAILURE"],
        "aborted_trial_count": counts["ABORTED"],
        "error_trial_count": counts["ERROR"],
        "reproducibility_rerun_count": len(reruns),
        "trial_id_set_digest": _digest(sorted(economic)),
        "expected_trial_manifest_digest": _digest(dict(sorted(expected.items()))),
        "missing_trial_ids": missing,
        "unexpected_selection_trial_ids": unexpected,
        "mutated_trial_ids": mutated,
        "invalid_rerun_ids": invalid_reruns,
    }, f


def _selection(s: ExperimentFamilySnapshot):
    f = []
    if s.computed_family_digest() != s.registered_family_digest:
        f.append(_finding(
            "FAMILY_DEFINITION_MUTATED_AFTER_REGISTRATION", "BLOCKING", "family.registered_family_digest",
            "registered benchmark/metric/horizon/search/selection material changed",
        ))
    if _time(s.selection_rule_registered_at, "family.selection_rule_registered_at") > _time(s.selected_at, "family.selected_at"):
        f.append(_finding("SELECTION_RULE_REGISTERED_AFTER_SELECTION", "BLOCKING", "family.selection_rule_registered_at", "rule post-dates winner"))
    if _time(s.family_frozen_at, "family.family_frozen_at") > _time(s.selected_at, "family.selected_at"):
        f.append(_finding("FAMILY_FROZEN_AFTER_SELECTION", "BLOCKING", "family.family_frozen_at", "family freeze post-dates winner"))
    if s.selected_trial_id not in s.expected_trial_digests:
        f.append(_finding("SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY", "BLOCKING", "family.selected_trial_id", "winner absent from manifest"))
    return f


def _selected_trial(s: ExperimentFamilySnapshot) -> TrialRecord | None:
    matches = [t for t in s.trials if t.selection_affecting and t.trial_id == s.selected_trial_id]
    return matches[0] if len(matches) == 1 else None


def _verify_lockbox_provenance(r: LockboxAccessReceipt, s: ExperimentFamilySnapshot, path: str) -> tuple[bool, list[dict[str, str]]]:
    f: list[dict[str, str]] = []
    kwargs = r.configuration_kwargs()
    if kwargs is None or r.configuration_digest is None:
        return False, [_finding(
            "LOCKBOX_CONFIGURATION_PROVENANCE_INCOMPLETE", "UNKNOWN", path,
            "final evaluation requires frozen dataset/code/params/cost/rule/accessor/task provenance",
        )]
    try:
        for ref_field, sha_field, label in (
            ("dataset_artifact_ref", "dataset_artifact_blob_sha", "dataset"),
            ("code_artifact_ref", "code_artifact_blob_sha", "code"),
            ("parameter_artifact_ref", "parameter_artifact_blob_sha", "parameters"),
            ("cost_artifact_ref", "cost_artifact_blob_sha", "cost"),
            ("rule_artifact_ref", "rule_artifact_blob_sha", "rule"),
            ("accessor_claim_ref", "accessor_claim_blob_sha", "accessor_claim"),
            ("authorization_witness_ref", "authorization_witness_blob_sha", "authorization_witness"),
        ):
            _verify_governed_artifact(str(getattr(r, ref_field)), str(getattr(r, sha_field)), f"{path}.{label}")
        _, claim_raw = _verify_governed_artifact(
            str(r.accessor_claim_ref), str(r.accessor_claim_blob_sha), f"{path}.accessor_claim",
        )
        _, witness_raw = _verify_governed_artifact(
            str(r.authorization_witness_ref), str(r.authorization_witness_blob_sha), f"{path}.authorization_witness",
        )
        claim_task = _yaml_scalar(claim_raw, "task_id")
        claim_slot = _yaml_scalar(claim_raw, "worker_slot_id")
        claim_role = _yaml_scalar(claim_raw, "claimant_role")
        witness_task = _yaml_scalar(witness_raw, "task_id")
        witness_slot = _yaml_scalar(witness_raw, "worker_slot_id")
        witness_role = _yaml_scalar(witness_raw, "executor_role")
        if (
            claim_task != r.task_id
            or witness_task != r.task_id
            or claim_slot != r.accessor_id
            or witness_slot != r.accessor_id
            or claim_role != "GPT_ENGINEERING_WORKER"
            or witness_role != "GPT_ENGINEERING_WORKER"
        ):
            f.append(_finding(
                "LOCKBOX_ACCESSOR_TASK_PROVENANCE_MISMATCH", "BLOCKING", path,
                "Work Claim / Authorization Witness do not bind the asserted accessor and task",
            ))
            return False, f
        computed = _digest(lockbox_configuration_material(**kwargs))
        if computed != r.configuration_digest:
            f.append(_finding(
                "LOCKBOX_CONFIGURATION_DIGEST_MISMATCH", "BLOCKING", f"{path}.configuration_digest",
                "configuration digest does not match frozen artifact/accessor material",
            ))
            return False, f
        selected = _selected_trial(s)
        if selected is None or selected.configuration_digest is None:
            return False, [_finding(
                "SELECTED_TRIAL_CONFIGURATION_IDENTITY_UNKNOWN", "UNKNOWN", path,
                "selected trial does not bind a configuration digest",
            )]
        if selected.configuration_digest != r.configuration_digest:
            f.append(_finding(
                "LOCKBOX_SELECTED_TRIAL_CONFIGURATION_MISMATCH", "BLOCKING", f"{path}.configuration_digest",
                "lockbox configuration is not the selected trial frozen configuration",
            ))
            return False, f
        if _time(str(r.configuration_frozen_at), f"{path}.configuration_frozen_at") != _time(
            s.candidate_frozen_at, "family.candidate_frozen_at",
        ):
            f.append(_finding(
                "LOCKBOX_CONFIGURATION_FREEZE_MISMATCH", "BLOCKING", f"{path}.configuration_frozen_at",
                "configuration freeze must match candidate freeze",
            ))
            return False, f
    except IntegrityValidationError as exc:
        f.append(_finding(exc.code, "BLOCKING", exc.path, exc.message))
        return False, f
    return True, f


def _lockbox(s: ExperimentFamilySnapshot, receipts: Sequence[LockboxAccessReceipt]):
    f: list[dict[str, str]] = []
    rows = sorted(receipts, key=lambda r: (_time(r.opened_at, "lockbox.opened_at"), r.access_id))
    out = [r.row() for r in rows]
    if len({r.access_id for r in rows}) != len(rows):
        return LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION, [
            _finding("DUPLICATE_LOCKBOX_ACCESS_ID", "BLOCKING", "lockbox_receipts", "duplicate access identity")
        ], out
    if not s.lockbox_access_history_complete:
        return LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN, [
            _finding("LOCKBOX_ACCESS_HISTORY_UNKNOWN", "UNKNOWN", "family.lockbox_access_history_complete", "absence of receipts is not proof of sealed state")
        ], out
    if not rows:
        return LockboxStatus.SEALED_UNUSED, f, out

    bad = len(rows) != 1
    unknown_provenance = False
    if bad:
        f.append(_finding("LOCKBOX_OPENED_MORE_THAN_ONCE", "BLOCKING", "lockbox_receipts", "final holdout may be revealed once"))
    selected_digest = s.expected_trial_digests.get(s.selected_trial_id)
    cf = _time(s.candidate_frozen_at, "family.candidate_frozen_at")
    ff = _time(s.family_frozen_at, "family.family_frozen_at")
    st = _time(s.selected_at, "family.selected_at")
    for i, r in enumerate(rows):
        p = f"lockbox_receipts.{i}"
        ot = _time(r.opened_at, f"{p}.opened_at")
        provenance_ok, provenance_findings = _verify_lockbox_provenance(r, s, p)
        f += provenance_findings
        if not provenance_ok:
            if any(x["severity"] == "BLOCKING" for x in provenance_findings):
                bad = True
            else:
                unknown_provenance = True
        checks = [
            (r.lockbox_id != s.lockbox_id, "LOCKBOX_IDENTITY_MISMATCH", "lockbox_id"),
            (
                r.candidate_id != s.selected_trial_id or r.candidate_digest != selected_digest,
                "LOCKBOX_CANDIDATE_IDENTITY_MISMATCH", "candidate_id",
            ),
            (cf > ot or ff > ot or st > ot, "LOCKBOX_OPENED_BEFORE_FREEZE", "opened_at"),
            (r.purpose is not LockboxPurpose.FINAL_EVAL, "LOCKBOX_USED_FOR_SELECTION_OR_TUNING", "purpose"),
            (r.selection_consumed_after, "LOCKBOX_RESULT_CONSUMED_BY_LATER_SELECTION", "selection_consumed_after"),
        ]
        for failed, code, field in checks:
            if failed:
                bad = True
                f.append(_finding(code, "BLOCKING", f"{p}.{field}", "final holdout boundary violated"))
    if bad:
        return LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION, f, out
    if unknown_provenance:
        return LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN, f, out
    return LockboxStatus.OPENED_ONCE_FINAL_EVAL, f, out


def _derive_pit(p: PITEvidence, decision_time: str):
    declared = p.declared_statuses()
    effective = {name: PITStatus.UNKNOWN for name in declared}
    f: list[dict[str, str]] = []
    fail = False
    unknown = False

    # Caller can always make the system more conservative. A caller-supplied
    # FAIL is retained, but a caller-supplied PASS is never authority.
    for name, state in declared.items():
        if state == PITStatus.FAIL.value:
            effective[name] = PITStatus.FAIL
            fail = True
            f.append(_finding(f"PIT_{name.upper()}_FAIL", "BLOCKING", f"pit.{name}", "caller reported a negative PIT finding"))

    if not p.binding_complete():
        for name, state in declared.items():
            if state == PITStatus.PASS.value:
                f.append(_finding(
                    "PIT_CALLER_DECLARED_PASS_UNTRUSTED", "UNKNOWN", f"pit.{name}",
                    "positive PIT status requires governed W2 artifact revalidation",
                ))
        unknown = True
    else:
        try:
            module = _load_verified_w2_rule_module(str(p.authority_source_ref), str(p.authority_source_blob_sha))
            row = _load_jsonl_event(str(p.dataset_artifact_ref), str(p.dataset_artifact_blob_sha), str(p.dataset_event_id))
            decision = _time(decision_time, "family.selected_at")
            actual_symbol = str(row.get("symbol", ""))
            actual_event_day = str(row.get("event_time", ""))[:10]
            if actual_symbol != p.symbol or actual_event_day != p.trading_day:
                effective["dataset_lineage"] = PITStatus.FAIL
                fail = True
                f.append(_finding("PIT_DATASET_LINEAGE_FAIL", "BLOCKING", "pit.dataset_lineage", "event identity does not match symbol/trading day"))
            else:
                effective["dataset_lineage"] = PITStatus.PASS

            available = _time(str(row.get("available_at")), "pit.dataset.available_at")
            if available <= decision:
                effective["available_at_lineage"] = PITStatus.PASS
            else:
                effective["available_at_lineage"] = PITStatus.FAIL
                fail = True
                f.append(_finding("PIT_AVAILABLE_AT_LINEAGE_FAIL", "BLOCKING", "pit.available_at_lineage", "dataset was not available at selection time"))

            resolved = module.DEFAULT_RULE_RESOLVER.resolve(
                str(p.exchange), str(p.board), str(p.security_status), str(p.trading_day),
                None, decision_time,
            )
            if resolved.rule_snapshot_id != p.rule_snapshot_id:
                effective["rule_version"] = PITStatus.FAIL
                fail = True
                f.append(_finding("PIT_RULE_VERSION_FAIL", "BLOCKING", "pit.rule_version", "governed W2 resolver returned a different rule snapshot"))
            else:
                effective["rule_version"] = PITStatus.PASS

            revision_candidates = [
                row.get("available_at"), row.get("observed_at"), row.get("receive_time"),
                row.get("entered_system_at"), row.get("as_of"),
            ]
            if all(item and _time(str(item), "pit.dataset.revision_time") <= decision for item in revision_candidates):
                effective["revision_timing"] = PITStatus.PASS
            else:
                effective["revision_timing"] = PITStatus.FAIL
                fail = True
                f.append(_finding("PIT_REVISION_TIMING_FAIL", "BLOCKING", "pit.revision_timing", "a recorded revision/ingestion time is after selection"))

            # In this P0A public-safe fixture, the admissible universe is the exact
            # symbol set physically present in the immutable dataset artifact.
            if actual_symbol == p.symbol:
                effective["universe_membership"] = PITStatus.PASS
            else:
                effective["universe_membership"] = PITStatus.FAIL
                fail = True
                f.append(_finding("PIT_UNIVERSE_MEMBERSHIP_FAIL", "BLOCKING", "pit.universe_membership", "symbol absent from governed dataset universe"))
        except IntegrityValidationError as exc:
            unknown = True
            f.append(_finding(exc.code, "UNKNOWN", exc.path, exc.message))
        except Exception as exc:
            unknown = True
            f.append(_finding("PIT_GOVERNED_REVALIDATION_FAILED", "UNKNOWN", "pit.authority_binding", type(exc).__name__))

    for i, item in enumerate(p.future_information_findings):
        fail = True
        f.append(_finding("FUTURE_INFORMATION_LEAKAGE", "BLOCKING", f"pit.future_information_findings.{i}", item))

    for name, state in effective.items():
        if state is PITStatus.UNKNOWN:
            unknown = True
            if not any(x["path"] == f"pit.{name}" and x["severity"] == "UNKNOWN" for x in f):
                f.append(_finding(f"PIT_{name.upper()}_UNKNOWN", "UNKNOWN", f"pit.{name}", "PIT evidence unresolved"))

    row = {
        "dataset_lineage": effective["dataset_lineage"].value,
        "available_at_lineage": effective["available_at_lineage"].value,
        "rule_version": effective["rule_version"].value,
        "revision_timing": effective["revision_timing"].value,
        "universe_membership": effective["universe_membership"].value,
        "declared_statuses": declared,
        "future_information_findings": list(p.future_information_findings),
        "authority_binding": {
            "authority_source_ref": p.authority_source_ref,
            "authority_source_blob_sha": p.authority_source_blob_sha,
            "dataset_artifact_ref": p.dataset_artifact_ref,
            "dataset_artifact_blob_sha": p.dataset_artifact_blob_sha,
            "dataset_event_id": p.dataset_event_id,
            "symbol": p.symbol,
            "exchange": p.exchange,
            "board": p.board,
            "security_status": p.security_status,
            "trading_day": p.trading_day,
            "rule_snapshot_id": p.rule_snapshot_id,
            "decision_time": decision_time,
        },
    }
    return row, f, fail, unknown


def _methods(required: Sequence[str], results: Sequence[MethodResult]):
    f = []
    index = {}
    blocked = False
    for r in results:
        if r.method_id in index:
            blocked = True
            f.append(_finding("DUPLICATE_METHOD_RESULT", "BLOCKING", f"methods.{r.method_id}", "duplicate result"))
        else:
            index[r.method_id] = r
    for mid in required:
        r = index.get(mid)
        if r is None:
            blocked = True
            f.append(_finding("REQUIRED_METHOD_MISSING", "BLOCKING", f"methods.{mid}", "explicit state required"))
        elif r.status in {
            MethodStatus.FAIL, MethodStatus.NOT_RUN, MethodStatus.INSUFFICIENT_DATA, MethodStatus.NUMERICAL_FAILURE,
        }:
            blocked = True
            f.append(_finding("REQUIRED_METHOD_NOT_CLEAR", "BLOCKING", f"methods.{mid}.status", f"status={r.status.value}"))
    return f, [index[k].row() for k in sorted(index)], blocked


def audit_research_integrity(
    snapshot: ExperimentFamilySnapshot,
    *,
    expected_w4_snapshot_digest: str | None,
    lockbox_receipts: Sequence[LockboxAccessReceipt],
    pit_evidence: PITEvidence,
    method_results: Sequence[MethodResult] = (),
    observed_at: str,
) -> dict[str, Any]:
    """P0A audit. Caller-supplied positive labels never mint W4/W2/lockbox authority."""
    observed = _time(observed_at, "audit.observed_at")
    snap_digest = snapshot.snapshot_digest()
    findings: list[dict[str, str]] = []
    match = False
    if expected_w4_snapshot_digest is None:
        findings.append(_finding("W4_SNAPSHOT_EXPECTED_DIGEST_MISSING", "UNKNOWN", "expected_w4_snapshot_digest", "content comparison absent"))
    else:
        _sha(expected_w4_snapshot_digest, "expected_w4_snapshot_digest")
        match = expected_w4_snapshot_digest == snap_digest
        if not match:
            findings.append(_finding("W4_SNAPSHOT_DIGEST_MISMATCH", "BLOCKING", "expected_w4_snapshot_digest", "snapshot differs from comparison digest"))
    findings.append(_finding(
        "W4_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", "UNKNOWN", "w4_authority_state",
        "canonical W4 provenance requires a separately governed read adapter",
    ))

    reconciliation, fs = _reconcile_trials(snapshot)
    findings += fs
    findings += _selection(snapshot)
    lock_state, fs, lock_rows = _lockbox(snapshot, lockbox_receipts)
    findings += fs
    pit_row, fs, pit_fail, pit_unknown = _derive_pit(pit_evidence, snapshot.selected_at)
    findings += fs
    fs, method_rows, methods_blocked = _methods(snapshot.required_method_ids, method_results)
    findings += fs

    codes = {x["code"] for x in findings}
    trial_codes = {
        "DUPLICATE_TRIAL_ID", "MISSING_EXPECTED_TRIAL", "UNREGISTERED_SELECTION_TRIAL",
        "TRIAL_IMMUTABLE_DIGEST_MISMATCH", "INVALID_REPRODUCIBILITY_RERUN",
    }
    selection_codes = {
        "FAMILY_DEFINITION_MUTATED_AFTER_REGISTRATION", "SELECTION_RULE_REGISTERED_AFTER_SELECTION",
        "FAMILY_FROZEN_AFTER_SELECTION", "SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY",
    }
    unknown = any(x["severity"] == "UNKNOWN" for x in findings)
    hard = any(x["severity"] == "BLOCKING" for x in findings)

    if pit_fail:
        disposition = Disposition.REJECT_POINT_IN_TIME_LEAKAGE
    elif codes & trial_codes:
        disposition = Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY
    elif codes & selection_codes:
        disposition = Disposition.RETEST_WITH_PREREGISTERED_FAMILY
    elif lock_state is LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION:
        disposition = Disposition.REJECT_LOCKBOX_CONTAMINATION
    elif methods_blocked:
        disposition = Disposition.INSUFFICIENT_EVIDENCE
    elif unknown or pit_unknown or lock_state is LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN:
        disposition = Disposition.ABSTAIN
    elif hard:
        disposition = Disposition.REJECT_SELECTION_BIAS
    else:
        disposition = Disposition.ELIGIBLE_FOR_W7_VALIDATION

    warning = any(x["severity"] == "WARNING" for x in findings)
    if disposition in {
        Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY, Disposition.REJECT_LOCKBOX_CONTAMINATION,
        Disposition.REJECT_POINT_IN_TIME_LEAKAGE, Disposition.REJECT_SELECTION_BIAS,
        Disposition.RETEST_WITH_PREREGISTERED_FAMILY,
    }:
        risk, grade = "HIGH", "BLOCKED"
    elif disposition in {Disposition.ABSTAIN, Disposition.INSUFFICIENT_EVIDENCE}:
        risk, grade = "UNKNOWN", "UNKNOWN"
    elif warning:
        risk, grade = "ELEVATED", "P0A_INTEGRITY_WARNING"
    else:
        risk, grade = "LOW_BOOKKEEPING_RISK", "P0A_INTEGRITY_CLEAR"

    authority = {
        k: False
        for k in (
            "experiment_registry_write_authority", "strategy_experiment_write_authority", "probability_authority",
            "final_validation_authority", "risk_override_authority", "position_authority", "order_authority",
            "trade_authority",
        )
    }
    out = {
        "schema": AUDIT_SCHEMA,
        "skill_id": SKILL_ID,
        "audit_version": "P0A",
        "audit_id": f"ds10-p0a-{snap_digest[:16]}",
        "observed_at": observed.isoformat(),
        "experiment_family_ref": snapshot.experiment_family_ref,
        "w4_snapshot_digest": snap_digest,
        "w4_snapshot_digest_matches_expected": match,
        "w4_authority_state": "EXTERNAL_CANONICAL_BINDING_REQUIRED",
        "registered_family_digest": snapshot.registered_family_digest,
        "computed_family_digest": snapshot.computed_family_digest(),
        "trial_reconciliation": reconciliation,
        "lockbox_status": lock_state.value,
        "lockbox_access_receipts": lock_rows,
        "pit_evidence": pit_row,
        "method_results": method_rows,
        "selection_bias_risk": risk,
        "adjusted_evidence_grade": grade,
        "research_integrity_disposition": disposition.value,
        "blocking_findings": sorted(
            (x for x in findings if x["severity"] == "BLOCKING"),
            key=lambda x: (x["code"], x["path"], x["detail"]),
        ),
        "nonblocking_findings": sorted(
            (x for x in findings if x["severity"] != "BLOCKING"),
            key=lambda x: (x["severity"], x["code"], x["path"], x["detail"]),
        ),
        "required_retest": disposition in {
            Disposition.RETEST_WITH_PREREGISTERED_FAMILY,
            Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY,
            Disposition.REJECT_LOCKBOX_CONTAMINATION,
            Disposition.REJECT_POINT_IN_TIME_LEAKAGE,
            Disposition.REJECT_SELECTION_BIAS,
        },
        "authority": authority,
        "w7_handoff_is_acceptance": False,
    }
    out["audit_digest"] = _digest(out)
    return out


def canonical_audit_digest(audit: Mapping[str, Any]) -> str:
    material = dict(audit)
    supplied = material.pop("audit_digest", None)
    computed = _digest(material)
    if supplied is not None and supplied != computed:
        raise IntegrityValidationError("AUDIT_DIGEST_MISMATCH", "audit.audit_digest", "audit content changed")
    return computed
