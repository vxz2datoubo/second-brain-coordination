from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
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
        self.code = code
        self.path = path
        self.message = message


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
    module_name = f"_ds10_verified_w2_rules_{blob_sha}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise IntegrityValidationError("W2_RULE_MODULE_LOAD_FAILED", "pit.authority_source_ref", "module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _load_jsonl_event(ref: str, blob_sha: str, event_id: str) -> dict[str, Any]:
    _, raw = _verify_governed_artifact(ref, blob_sha, "pit.dataset_artifact")
    matches = []
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
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


def _exchange_code(value: str) -> str:
    normalized = str(value).upper()
    return {"SH": "SSE", "SSE": "SSE", "SZ": "SZSE", "SZSE": "SZSE", "BJ": "BSE", "BSE": "BSE"}.get(normalized, normalized)


def _board_for_symbol(symbol: str, exchange: str) -> str:
    # This mirrors the exact canonical W2 engine mapping only after the engine
    # artifact itself is re-read and verified against its fixed Git blob below.
    code = symbol.split(".", 1)[0]
    ex = _exchange_code(exchange)
    if ex == "SSE" and code.startswith("688"):
        return "STAR"
    if ex == "SZSE" and code.startswith(("300", "301")):
        return "CHINEXT"
    return "MAIN"


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
        for name in ("experiment_family_ref", "benchmark_ref", "metric_id", "horizon_id", "search_space_ref", "selection_rule_ref", "selected_trial_id", "lockbox_id"):
            _text(getattr(self, name), f"family.{name}")
        _sha(self.registered_family_digest, "family.registered_family_digest")
        if not isinstance(self.expected_trial_digests, Mapping) or not self.expected_trial_digests:
            raise IntegrityValidationError("EMPTY_TRIAL_MANIFEST", "family.expected_trial_digests", "non-empty W4 manifest required")
        for key, value in self.expected_trial_digests.items():
            _text(key, "family.expected_trial_digests.key")
            _sha(value, f"family.expected_trial_digests.{key}")
        if not isinstance(self.lockbox_access_history_complete, bool):
            raise IntegrityValidationError("INVALID_BOOLEAN", "family.lockbox_access_history_complete", "boolean required")
        if self.declared_trial_count is not None and (isinstance(self.declared_trial_count, bool) or not isinstance(self.declared_trial_count, int) or self.declared_trial_count < 0):
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
            "trials": [trial.row() for trial in self.trials],
        }

    def snapshot_digest(self) -> str:
        return _digest(self.snapshot_material())


def lockbox_configuration_material(
    *, dataset_artifact_ref: str, dataset_artifact_blob_sha: str,
    code_artifact_ref: str, code_artifact_blob_sha: str,
    parameter_artifact_ref: str, parameter_artifact_blob_sha: str,
    cost_artifact_ref: str, cost_artifact_blob_sha: str,
    rule_artifact_ref: str, rule_artifact_blob_sha: str, rule_snapshot_id: str,
    accessor_claim_ref: str, accessor_claim_blob_sha: str,
    authorization_witness_ref: str, authorization_witness_blob_sha: str,
    accessor_id: str, task_id: str, configuration_frozen_at: str,
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
        return {name: getattr(self, name).value for name in ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership")}

    def binding_complete(self) -> bool:
        names = ("authority_source_ref", "authority_source_blob_sha", "dataset_artifact_ref", "dataset_artifact_blob_sha", "dataset_event_id", "symbol", "exchange", "board", "security_status", "trading_day", "rule_snapshot_id")
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
        return {"method_id": self.method_id, "status": self.status.value, "computation_ref": self.computation_ref, "applicability_reason": self.applicability_reason}


def _reconcile_trials(snapshot: ExperimentFamilySnapshot):
    findings: list[dict[str, str]] = []
    seen: dict[str, TrialRecord] = {}
    duplicates: set[str] = set()
    for record in snapshot.trials:
        if record.trial_id in seen:
            duplicates.add(record.trial_id)
        else:
            seen[record.trial_id] = record
    for trial_id in sorted(duplicates):
        findings.append(_finding("DUPLICATE_TRIAL_ID", "BLOCKING", f"trials.{trial_id}", "duplicate identity"))
    expected = dict(snapshot.expected_trial_digests)
    economic = {key: value for key, value in seen.items() if value.selection_affecting}
    reruns = {key: value for key, value in seen.items() if not value.selection_affecting}
    missing = sorted(set(expected) - set(economic))
    unexpected = sorted(set(economic) - set(expected))
    mutated: list[str] = []
    invalid_reruns: list[str] = []
    for trial_id in missing:
        findings.append(_finding("MISSING_EXPECTED_TRIAL", "BLOCKING", f"trials.{trial_id}", "manifested trial absent"))
    for trial_id in unexpected:
        findings.append(_finding("UNREGISTERED_SELECTION_TRIAL", "BLOCKING", f"trials.{trial_id}", "selection trial absent from manifest"))
    for trial_id in sorted(set(expected) & set(economic)):
        if expected[trial_id] != economic[trial_id].immutable_digest:
            mutated.append(trial_id)
            findings.append(_finding("TRIAL_IMMUTABLE_DIGEST_MISMATCH", "BLOCKING", f"trials.{trial_id}.immutable_digest", "trial mutated"))
    for trial_id, record in sorted(reruns.items()):
        if expected.get(record.rerun_of or "") != record.immutable_digest:
            invalid_reruns.append(trial_id)
            findings.append(_finding("INVALID_REPRODUCIBILITY_RERUN", "BLOCKING", f"trials.{trial_id}", "rerun does not preserve original"))
    count = len(economic)
    if snapshot.declared_trial_count is not None and snapshot.declared_trial_count != count:
        findings.append(_finding("DECLARED_TRIAL_COUNT_MISMATCH", "WARNING", "family.declared_trial_count", f"declared={snapshot.declared_trial_count}; observed={count}"))
    counts = {status.value: 0 for status in TrialStatus}
    for record in economic.values():
        counts[record.status.value] += 1
    return {
        "expected_trial_count": len(expected),
        "declared_trial_count": snapshot.declared_trial_count,
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
    }, findings


def _selection(snapshot: ExperimentFamilySnapshot):
    findings: list[dict[str, str]] = []
    if snapshot.computed_family_digest() != snapshot.registered_family_digest:
        findings.append(_finding("FAMILY_DEFINITION_MUTATED_AFTER_REGISTRATION", "BLOCKING", "family.registered_family_digest", "registered benchmark/metric/horizon/search/selection material changed"))
    if _time(snapshot.selection_rule_registered_at, "family.selection_rule_registered_at") > _time(snapshot.selected_at, "family.selected_at"):
        findings.append(_finding("SELECTION_RULE_REGISTERED_AFTER_SELECTION", "BLOCKING", "family.selection_rule_registered_at", "rule post-dates winner"))
    if _time(snapshot.family_frozen_at, "family.family_frozen_at") > _time(snapshot.selected_at, "family.selected_at"):
        findings.append(_finding("FAMILY_FROZEN_AFTER_SELECTION", "BLOCKING", "family.family_frozen_at", "family freeze post-dates winner"))
    if snapshot.selected_trial_id not in snapshot.expected_trial_digests:
        findings.append(_finding("SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY", "BLOCKING", "family.selected_trial_id", "winner absent from manifest"))
    return findings


def _selected_trial(snapshot: ExperimentFamilySnapshot) -> TrialRecord | None:
    matches = [record for record in snapshot.trials if record.selection_affecting and record.trial_id == snapshot.selected_trial_id]
    return matches[0] if len(matches) == 1 else None


def _verify_lockbox_provenance(receipt: LockboxAccessReceipt, snapshot: ExperimentFamilySnapshot, path: str) -> tuple[bool, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    kwargs = receipt.configuration_kwargs()
    if kwargs is None or receipt.configuration_digest is None:
        return False, [_finding("LOCKBOX_CONFIGURATION_PROVENANCE_INCOMPLETE", "UNKNOWN", path, "final evaluation requires frozen dataset/code/params/cost/rule/accessor/task provenance")]
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
            _verify_governed_artifact(str(getattr(receipt, ref_field)), str(getattr(receipt, sha_field)), f"{path}.{label}")
        _, claim_raw = _verify_governed_artifact(str(receipt.accessor_claim_ref), str(receipt.accessor_claim_blob_sha), f"{path}.accessor_claim")
        _, witness_raw = _verify_governed_artifact(str(receipt.authorization_witness_ref), str(receipt.authorization_witness_blob_sha), f"{path}.authorization_witness")
        if (
            _yaml_scalar(claim_raw, "task_id") != receipt.task_id
            or _yaml_scalar(witness_raw, "task_id") != receipt.task_id
            or _yaml_scalar(claim_raw, "worker_slot_id") != receipt.accessor_id
            or _yaml_scalar(witness_raw, "worker_slot_id") != receipt.accessor_id
            or _yaml_scalar(claim_raw, "claimant_role") != "GPT_ENGINEERING_WORKER"
            or _yaml_scalar(witness_raw, "executor_role") != "GPT_ENGINEERING_WORKER"
        ):
            findings.append(_finding("LOCKBOX_ACCESSOR_TASK_PROVENANCE_MISMATCH", "BLOCKING", path, "Work Claim / Authorization Witness do not bind the asserted accessor and task"))
            return False, findings
        valid = True
        computed = _digest(lockbox_configuration_material(**kwargs))
        if computed != receipt.configuration_digest:
            valid = False
            findings.append(_finding("LOCKBOX_CONFIGURATION_DIGEST_MISMATCH", "BLOCKING", f"{path}.configuration_digest", "configuration digest does not match frozen artifact/accessor material"))
        selected = _selected_trial(snapshot)
        if selected is None or selected.configuration_digest is None:
            return False, [_finding("SELECTED_TRIAL_CONFIGURATION_IDENTITY_UNKNOWN", "UNKNOWN", path, "selected trial does not bind a configuration digest")]
        if selected.configuration_digest != receipt.configuration_digest:
            valid = False
            findings.append(_finding("LOCKBOX_SELECTED_TRIAL_CONFIGURATION_MISMATCH", "BLOCKING", f"{path}.configuration_digest", "lockbox configuration is not the selected trial frozen configuration"))
        if _time(str(receipt.configuration_frozen_at), f"{path}.configuration_frozen_at") != _time(snapshot.candidate_frozen_at, "family.candidate_frozen_at"):
            valid = False
            findings.append(_finding("LOCKBOX_CONFIGURATION_FREEZE_MISMATCH", "BLOCKING", f"{path}.configuration_frozen_at", "configuration freeze must match candidate freeze"))
        return valid, findings
    except IntegrityValidationError as exc:
        findings.append(_finding(exc.code, "BLOCKING", exc.path, exc.message))
        return False, findings


def _lockbox(snapshot: ExperimentFamilySnapshot, receipts: Sequence[LockboxAccessReceipt]):
    findings: list[dict[str, str]] = []
    ordered = sorted(receipts, key=lambda receipt: (_time(receipt.opened_at, "lockbox.opened_at"), receipt.access_id))
    rows = [receipt.row() for receipt in ordered]
    if len({receipt.access_id for receipt in ordered}) != len(ordered):
        return LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION, [_finding("DUPLICATE_LOCKBOX_ACCESS_ID", "BLOCKING", "lockbox_receipts", "duplicate access identity")], rows
    if not snapshot.lockbox_access_history_complete:
        return LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN, [_finding("LOCKBOX_ACCESS_HISTORY_UNKNOWN", "UNKNOWN", "family.lockbox_access_history_complete", "absence of receipts is not proof of sealed state")], rows
    if not ordered:
        return LockboxStatus.SEALED_UNUSED, findings, rows
    contaminated = len(ordered) != 1
    unknown_provenance = False
    if contaminated:
        findings.append(_finding("LOCKBOX_OPENED_MORE_THAN_ONCE", "BLOCKING", "lockbox_receipts", "final holdout may be revealed once"))
    selected_digest = snapshot.expected_trial_digests.get(snapshot.selected_trial_id)
    candidate_freeze = _time(snapshot.candidate_frozen_at, "family.candidate_frozen_at")
    family_freeze = _time(snapshot.family_frozen_at, "family.family_frozen_at")
    selected_at = _time(snapshot.selected_at, "family.selected_at")
    for index, receipt in enumerate(ordered):
        path = f"lockbox_receipts.{index}"
        opened = _time(receipt.opened_at, f"{path}.opened_at")
        provenance_ok, provenance_findings = _verify_lockbox_provenance(receipt, snapshot, path)
        findings += provenance_findings
        if not provenance_ok:
            if any(item["severity"] == "BLOCKING" for item in provenance_findings):
                contaminated = True
            else:
                unknown_provenance = True
        checks = (
            (receipt.lockbox_id != snapshot.lockbox_id, "LOCKBOX_IDENTITY_MISMATCH", "lockbox_id"),
            (receipt.candidate_id != snapshot.selected_trial_id or receipt.candidate_digest != selected_digest, "LOCKBOX_CANDIDATE_IDENTITY_MISMATCH", "candidate_id"),
            (candidate_freeze > opened or family_freeze > opened or selected_at > opened, "LOCKBOX_OPENED_BEFORE_FREEZE", "opened_at"),
            (receipt.purpose is not LockboxPurpose.FINAL_EVAL, "LOCKBOX_USED_FOR_SELECTION_OR_TUNING", "purpose"),
            (receipt.selection_consumed_after, "LOCKBOX_RESULT_CONSUMED_BY_LATER_SELECTION", "selection_consumed_after"),
        )
        for failed, code, field in checks:
            if failed:
                contaminated = True
                findings.append(_finding(code, "BLOCKING", f"{path}.{field}", "final holdout boundary violated"))
    if contaminated:
        return LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION, findings, rows
    if unknown_provenance:
        return LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN, findings, rows
    return LockboxStatus.OPENED_ONCE_FINAL_EVAL, findings, rows


def _derive_pit(pit: PITEvidence, decision_time: str):
    declared = pit.declared_statuses()
    effective = {name: PITStatus.UNKNOWN for name in declared}
    findings: list[dict[str, str]] = []
    fail = False
    unknown = False
    for name, state in declared.items():
        if state == PITStatus.FAIL.value:
            effective[name] = PITStatus.FAIL
            fail = True
            findings.append(_finding(f"PIT_{name.upper()}_FAIL", "BLOCKING", f"pit.{name}", "caller reported a negative PIT finding"))
    if not pit.binding_complete():
        for name, state in declared.items():
            if state == PITStatus.PASS.value:
                findings.append(_finding("PIT_CALLER_DECLARED_PASS_UNTRUSTED", "UNKNOWN", f"pit.{name}", "positive PIT status requires governed W2 artifact revalidation"))
        unknown = True
    else:
        try:
            module = _load_verified_w2_rule_module(str(pit.authority_source_ref), str(pit.authority_source_blob_sha))
            row = _load_jsonl_event(str(pit.dataset_artifact_ref), str(pit.dataset_artifact_blob_sha), str(pit.dataset_event_id))
            _verify_governed_artifact(W2_ENGINE_REF, _GOVERNED_ARTIFACTS[W2_ENGINE_REF], "pit.engine_semantics")
            decision = _time(decision_time, "family.selected_at")
            actual_symbol = str(row.get("symbol", ""))
            actual_day = str(row.get("event_time", ""))[:10]
            actual_exchange = _exchange_code(str(row.get("exchange", "")))
            derived_board = _board_for_symbol(actual_symbol, actual_exchange)
            derived_status = "RISK_WARNING" if row.get("is_st") is True else "NORMAL"
            claimed_exchange = _exchange_code(str(pit.exchange))
            identity_match = (
                actual_symbol == pit.symbol
                and actual_day == pit.trading_day
                and actual_exchange == claimed_exchange
                and derived_board == str(pit.board).upper()
                and derived_status == str(pit.security_status).upper()
            )
            if identity_match:
                effective["dataset_lineage"] = PITStatus.PASS
                effective["universe_membership"] = PITStatus.PASS
            else:
                effective["dataset_lineage"] = PITStatus.FAIL
                effective["universe_membership"] = PITStatus.FAIL
                fail = True
                findings.append(_finding("PIT_DATASET_LINEAGE_FAIL", "BLOCKING", "pit.dataset_lineage", "governed dataset identity disagrees with symbol/date/exchange/board/status claim"))
                findings.append(_finding("PIT_UNIVERSE_MEMBERSHIP_FAIL", "BLOCKING", "pit.universe_membership", "claimed universe identity is not the governed event identity"))
            available = _time(str(row.get("available_at")), "pit.dataset.available_at")
            if available <= decision:
                effective["available_at_lineage"] = PITStatus.PASS
            else:
                effective["available_at_lineage"] = PITStatus.FAIL
                fail = True
                findings.append(_finding("PIT_AVAILABLE_AT_LINEAGE_FAIL", "BLOCKING", "pit.available_at_lineage", "dataset was not available at selection time"))
            resolved = module.DEFAULT_RULE_RESOLVER.resolve(actual_exchange, derived_board, derived_status, actual_day, None, decision_time)
            if resolved.rule_snapshot_id == pit.rule_snapshot_id:
                effective["rule_version"] = PITStatus.PASS
            else:
                effective["rule_version"] = PITStatus.FAIL
                fail = True
                findings.append(_finding("PIT_RULE_VERSION_FAIL", "BLOCKING", "pit.rule_version", "governed W2 resolver returned a different rule snapshot"))
            revision_fields = ("available_at", "observed_at", "receive_time", "entered_system_at", "as_of")
            if all(row.get(field) and _time(str(row[field]), f"pit.dataset.{field}") <= decision for field in revision_fields):
                effective["revision_timing"] = PITStatus.PASS
            else:
                effective["revision_timing"] = PITStatus.FAIL
                fail = True
                findings.append(_finding("PIT_REVISION_TIMING_FAIL", "BLOCKING", "pit.revision_timing", "a recorded revision/ingestion time is after selection"))
        except IntegrityValidationError as exc:
            unknown = True
            findings.append(_finding(exc.code, "UNKNOWN", exc.path, exc.message))
        except Exception as exc:
            unknown = True
            findings.append(_finding("PIT_GOVERNED_REVALIDATION_FAILED", "UNKNOWN", "pit.authority_binding", f"{type(exc).__name__}:{exc}"))
    for index, item in enumerate(pit.future_information_findings):
        fail = True
        findings.append(_finding("FUTURE_INFORMATION_LEAKAGE", "BLOCKING", f"pit.future_information_findings.{index}", item))
    for name, state in effective.items():
        if state is PITStatus.UNKNOWN:
            unknown = True
            if not any(item["path"] == f"pit.{name}" and item["severity"] == "UNKNOWN" for item in findings):
                findings.append(_finding(f"PIT_{name.upper()}_UNKNOWN", "UNKNOWN", f"pit.{name}", "PIT evidence unresolved"))
    row = {
        "dataset_lineage": effective["dataset_lineage"].value,
        "available_at_lineage": effective["available_at_lineage"].value,
        "rule_version": effective["rule_version"].value,
        "revision_timing": effective["revision_timing"].value,
        "universe_membership": effective["universe_membership"].value,
        "declared_statuses": declared,
        "future_information_findings": list(pit.future_information_findings),
        "authority_binding": {
            "authority_source_ref": pit.authority_source_ref,
            "authority_source_blob_sha": pit.authority_source_blob_sha,
            "dataset_artifact_ref": pit.dataset_artifact_ref,
            "dataset_artifact_blob_sha": pit.dataset_artifact_blob_sha,
            "dataset_event_id": pit.dataset_event_id,
            "symbol": pit.symbol,
            "exchange": pit.exchange,
            "board": pit.board,
            "security_status": pit.security_status,
            "trading_day": pit.trading_day,
            "rule_snapshot_id": pit.rule_snapshot_id,
            "decision_time": decision_time,
        },
    }
    return row, findings, fail, unknown


def _methods(required: Sequence[str], results: Sequence[MethodResult]):
    findings: list[dict[str, str]] = []
    index: dict[str, MethodResult] = {}
    blocked = False
    for result in results:
        if result.method_id in index:
            blocked = True
            findings.append(_finding("DUPLICATE_METHOD_RESULT", "BLOCKING", f"methods.{result.method_id}", "duplicate result"))
        else:
            index[result.method_id] = result
    for method_id in required:
        result = index.get(method_id)
        if result is None:
            blocked = True
            findings.append(_finding("REQUIRED_METHOD_MISSING", "BLOCKING", f"methods.{method_id}", "explicit state required"))
        elif result.status in {MethodStatus.FAIL, MethodStatus.NOT_RUN, MethodStatus.INSUFFICIENT_DATA, MethodStatus.NUMERICAL_FAILURE}:
            blocked = True
            findings.append(_finding("REQUIRED_METHOD_NOT_CLEAR", "BLOCKING", f"methods.{method_id}.status", f"status={result.status.value}"))
    return findings, [index[key].row() for key in sorted(index)], blocked


def audit_research_integrity(
    snapshot: ExperimentFamilySnapshot,
    *,
    expected_w4_snapshot_digest: str | None,
    lockbox_receipts: Sequence[LockboxAccessReceipt],
    pit_evidence: PITEvidence,
    method_results: Sequence[MethodResult] = (),
    observed_at: str,
) -> dict[str, Any]:
    observed = _time(observed_at, "audit.observed_at")
    snapshot_digest = snapshot.snapshot_digest()
    findings: list[dict[str, str]] = []
    digest_match = False
    if expected_w4_snapshot_digest is None:
        findings.append(_finding("W4_SNAPSHOT_EXPECTED_DIGEST_MISSING", "UNKNOWN", "expected_w4_snapshot_digest", "content comparison absent"))
    else:
        _sha(expected_w4_snapshot_digest, "expected_w4_snapshot_digest")
        digest_match = expected_w4_snapshot_digest == snapshot_digest
        if not digest_match:
            findings.append(_finding("W4_SNAPSHOT_DIGEST_MISMATCH", "BLOCKING", "expected_w4_snapshot_digest", "snapshot differs from comparison digest"))
    findings.append(_finding("W4_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", "UNKNOWN", "w4_authority_state", "canonical W4 provenance requires a separately governed read adapter"))

    reconciliation, more = _reconcile_trials(snapshot)
    findings += more
    findings += _selection(snapshot)
    lockbox_state, more, lockbox_rows = _lockbox(snapshot, lockbox_receipts)
    findings += more
    pit_row, more, pit_fail, pit_unknown = _derive_pit(pit_evidence, snapshot.selected_at)
    findings += more
    more, method_rows, methods_blocked = _methods(snapshot.required_method_ids, method_results)
    findings += more

    codes = {item["code"] for item in findings}
    trial_codes = {"DUPLICATE_TRIAL_ID", "MISSING_EXPECTED_TRIAL", "UNREGISTERED_SELECTION_TRIAL", "TRIAL_IMMUTABLE_DIGEST_MISMATCH", "INVALID_REPRODUCIBILITY_RERUN"}
    selection_codes = {"FAMILY_DEFINITION_MUTATED_AFTER_REGISTRATION", "SELECTION_RULE_REGISTERED_AFTER_SELECTION", "FAMILY_FROZEN_AFTER_SELECTION", "SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY"}
    unknown = any(item["severity"] == "UNKNOWN" for item in findings)
    hard = any(item["severity"] == "BLOCKING" for item in findings)

    if pit_fail:
        disposition = Disposition.REJECT_POINT_IN_TIME_LEAKAGE
    elif codes & trial_codes:
        disposition = Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY
    elif codes & selection_codes:
        disposition = Disposition.RETEST_WITH_PREREGISTERED_FAMILY
    elif lockbox_state is LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION:
        disposition = Disposition.REJECT_LOCKBOX_CONTAMINATION
    elif methods_blocked:
        disposition = Disposition.INSUFFICIENT_EVIDENCE
    elif unknown or pit_unknown or lockbox_state is LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN:
        disposition = Disposition.ABSTAIN
    elif hard:
        disposition = Disposition.REJECT_SELECTION_BIAS
    else:
        disposition = Disposition.ELIGIBLE_FOR_W7_VALIDATION

    warning = any(item["severity"] == "WARNING" for item in findings)
    if disposition in {Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY, Disposition.REJECT_LOCKBOX_CONTAMINATION, Disposition.REJECT_POINT_IN_TIME_LEAKAGE, Disposition.REJECT_SELECTION_BIAS, Disposition.RETEST_WITH_PREREGISTERED_FAMILY}:
        risk, grade = "HIGH", "BLOCKED"
    elif disposition in {Disposition.ABSTAIN, Disposition.INSUFFICIENT_EVIDENCE}:
        risk, grade = "UNKNOWN", "UNKNOWN"
    elif warning:
        risk, grade = "ELEVATED", "P0A_INTEGRITY_WARNING"
    else:
        risk, grade = "LOW_BOOKKEEPING_RISK", "P0A_INTEGRITY_CLEAR"

    authority = {key: False for key in ("experiment_registry_write_authority", "strategy_experiment_write_authority", "probability_authority", "final_validation_authority", "risk_override_authority", "position_authority", "order_authority", "trade_authority")}
    output = {
        "schema": AUDIT_SCHEMA,
        "skill_id": SKILL_ID,
        "audit_version": "P0A",
        "audit_id": f"ds10-p0a-{snapshot_digest[:16]}",
        "observed_at": observed.isoformat(),
        "experiment_family_ref": snapshot.experiment_family_ref,
        "w4_snapshot_digest": snapshot_digest,
        "w4_snapshot_digest_matches_expected": digest_match,
        "w4_authority_state": "EXTERNAL_CANONICAL_BINDING_REQUIRED",
        "registered_family_digest": snapshot.registered_family_digest,
        "computed_family_digest": snapshot.computed_family_digest(),
        "trial_reconciliation": reconciliation,
        "lockbox_status": lockbox_state.value,
        "lockbox_access_receipts": lockbox_rows,
        "pit_evidence": pit_row,
        "method_results": method_rows,
        "selection_bias_risk": risk,
        "adjusted_evidence_grade": grade,
        "research_integrity_disposition": disposition.value,
        "blocking_findings": sorted((item for item in findings if item["severity"] == "BLOCKING"), key=lambda item: (item["code"], item["path"], item["detail"])),
        "nonblocking_findings": sorted((item for item in findings if item["severity"] != "BLOCKING"), key=lambda item: (item["severity"], item["code"], item["path"], item["detail"])),
        "required_retest": disposition in {Disposition.RETEST_WITH_PREREGISTERED_FAMILY, Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY, Disposition.REJECT_LOCKBOX_CONTAMINATION, Disposition.REJECT_POINT_IN_TIME_LEAKAGE, Disposition.REJECT_SELECTION_BIAS},
        "authority": authority,
        "w7_handoff_is_acceptance": False,
    }
    output["audit_digest"] = _digest(output)
    return output


def canonical_audit_digest(audit: Mapping[str, Any]) -> str:
    material = dict(audit)
    supplied = material.pop("audit_digest", None)
    computed = _digest(material)
    if supplied is not None and supplied != computed:
        raise IntegrityValidationError("AUDIT_DIGEST_MISMATCH", "audit.audit_digest", "audit content changed")
    return computed
