from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

AUDIT_SCHEMA = "ResearchIntegrityAudit/v1"
LOCKBOX_SCHEMA = "LockboxAccessReceipt/v1"
SKILL_ID = "RESEARCH-MULTIPLE-TESTING-OVERFITTING-AUDIT-SKILL-0012J"
_SHA = re.compile(r"^[0-9a-f]{64}$")


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


@dataclass(frozen=True)
class TrialRecord:
    trial_id: str
    immutable_digest: str
    status: TrialStatus
    selection_affecting: bool = True
    rerun_of: str | None = None

    def __post_init__(self):
        _text(self.trial_id, "trial.trial_id")
        _sha(self.immutable_digest, "trial.immutable_digest")
        object.__setattr__(self, "status", _as_enum(self.status, TrialStatus, "trial.status"))
        if not isinstance(self.selection_affecting, bool):
            raise IntegrityValidationError("INVALID_BOOLEAN", "trial.selection_affecting", "boolean required")
        if self.rerun_of is not None:
            _text(self.rerun_of, "trial.rerun_of")
        if not self.selection_affecting and self.rerun_of is None:
            raise IntegrityValidationError("NON_SELECTION_TRIAL_WITHOUT_RERUN_LINK", "trial.rerun_of", "rerun link required")
        if self.selection_affecting and self.rerun_of is not None:
            raise IntegrityValidationError("SELECTION_TRIAL_CANNOT_BE_RERUN_ALIAS", "trial.rerun_of", "new economic identity required")

    def row(self) -> dict[str, Any]:
        return {"trial_id": self.trial_id, "immutable_digest": self.immutable_digest, "status": self.status.value,
                "selection_affecting": self.selection_affecting, "rerun_of": self.rerun_of}


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
    code_digest: str
    parameter_digest: str
    cost_model_digest: str
    rule_snapshot_digest: str
    dataset_snapshot_digest: str
    lockbox_accessor_id: str
    lockbox_task_id: str
    declared_trial_count: int | None = None
    required_method_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("experiment_family_ref", "benchmark_ref", "metric_id", "horizon_id", "search_space_ref",
                     "selection_rule_ref", "selected_trial_id", "lockbox_id", "lockbox_accessor_id", "lockbox_task_id"):
            _text(getattr(self, name), f"family.{name}")
        for name in ("registered_family_digest", "code_digest", "parameter_digest", "cost_model_digest",
                     "rule_snapshot_digest", "dataset_snapshot_digest"):
            _sha(getattr(self, name), f"family.{name}")
        if not isinstance(self.expected_trial_digests, Mapping) or not self.expected_trial_digests:
            raise IntegrityValidationError("EMPTY_TRIAL_MANIFEST", "family.expected_trial_digests", "non-empty W4 manifest required")
        for key, value in self.expected_trial_digests.items():
            _text(key, "family.expected_trial_digests.key")
            _sha(value, f"family.expected_trial_digests.{key}")
        if not isinstance(self.lockbox_access_history_complete, bool):
            raise IntegrityValidationError("INVALID_BOOLEAN", "family.lockbox_access_history_complete", "boolean required")
        if self.declared_trial_count is not None and (isinstance(self.declared_trial_count, bool) or
                                                       not isinstance(self.declared_trial_count, int) or self.declared_trial_count < 0):
            raise IntegrityValidationError("INVALID_COUNT", "family.declared_trial_count", "non-negative integer required")
        if len(set(self.required_method_ids)) != len(self.required_method_ids):
            raise IntegrityValidationError("DUPLICATE_METHOD_ID", "family.required_method_ids", "unique IDs required")
        for method in self.required_method_ids:
            _text(method, "family.required_method_ids")
        for name in ("selection_rule_registered_at", "selected_at", "candidate_frozen_at", "family_frozen_at"):
            _time(getattr(self, name), f"family.{name}")

    def family_material(self) -> dict[str, Any]:
        return {"experiment_family_ref": self.experiment_family_ref,
                "expected_trial_digests": dict(sorted(self.expected_trial_digests.items())),
                "benchmark_ref": self.benchmark_ref, "metric_id": self.metric_id, "horizon_id": self.horizon_id,
                "search_space_ref": self.search_space_ref, "selection_rule_ref": self.selection_rule_ref,
                "code_digest": self.code_digest, "parameter_digest": self.parameter_digest,
                "cost_model_digest": self.cost_model_digest, "rule_snapshot_digest": self.rule_snapshot_digest,
                "dataset_snapshot_digest": self.dataset_snapshot_digest, "lockbox_accessor_id": self.lockbox_accessor_id,
                "lockbox_task_id": self.lockbox_task_id}

    def computed_family_digest(self) -> str:
        return _digest(self.family_material())

    def lockbox_configuration_material(self) -> dict[str, Any]:
        return {"lockbox_id": self.lockbox_id, "candidate_id": self.selected_trial_id,
                "candidate_digest": self.expected_trial_digests.get(self.selected_trial_id),
                "code_digest": self.code_digest, "parameter_digest": self.parameter_digest,
                "cost_model_digest": self.cost_model_digest, "rule_snapshot_digest": self.rule_snapshot_digest,
                "dataset_snapshot_digest": self.dataset_snapshot_digest, "accessor_id": self.lockbox_accessor_id,
                "task_id": self.lockbox_task_id}

    def lockbox_configuration_digest(self) -> str:
        return _digest(self.lockbox_configuration_material())

    def snapshot_material(self) -> dict[str, Any]:
        return {**self.family_material(), "registered_family_digest": self.registered_family_digest,
                "selection_rule_registered_at": self.selection_rule_registered_at, "selected_trial_id": self.selected_trial_id,
                "selected_at": self.selected_at, "candidate_frozen_at": self.candidate_frozen_at,
                "family_frozen_at": self.family_frozen_at, "lockbox_id": self.lockbox_id,
                "lockbox_access_history_complete": self.lockbox_access_history_complete,
                "declared_trial_count": self.declared_trial_count, "required_method_ids": list(self.required_method_ids),
                "trials": [t.row() for t in self.trials]}

    def snapshot_digest(self) -> str:
        return _digest(self.snapshot_material())


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
    task_id: str
    accessor_id: str
    code_digest: str
    parameter_digest: str
    cost_model_digest: str
    rule_snapshot_digest: str
    dataset_snapshot_digest: str
    frozen_configuration_digest: str
    subsequent_action: str | None = None

    def __post_init__(self):
        for name in ("access_id", "lockbox_id", "candidate_id", "task_id", "accessor_id"):
            _text(getattr(self, name), f"lockbox.{name}")
        _time(self.opened_at, "lockbox.opened_at")
        for name in ("candidate_digest", "result_digest", "code_digest", "parameter_digest", "cost_model_digest",
                     "rule_snapshot_digest", "dataset_snapshot_digest", "frozen_configuration_digest"):
            _sha(getattr(self, name), f"lockbox.{name}")
        object.__setattr__(self, "purpose", _as_enum(self.purpose, LockboxPurpose, "lockbox.purpose"))
        if not isinstance(self.selection_consumed_after, bool):
            raise IntegrityValidationError("INVALID_BOOLEAN", "lockbox.selection_consumed_after", "boolean required")
        if self.subsequent_action is not None:
            _text(self.subsequent_action, "lockbox.subsequent_action")

    def configuration_material(self) -> dict[str, Any]:
        return {"lockbox_id": self.lockbox_id, "candidate_id": self.candidate_id, "candidate_digest": self.candidate_digest,
                "code_digest": self.code_digest, "parameter_digest": self.parameter_digest,
                "cost_model_digest": self.cost_model_digest, "rule_snapshot_digest": self.rule_snapshot_digest,
                "dataset_snapshot_digest": self.dataset_snapshot_digest, "accessor_id": self.accessor_id,
                "task_id": self.task_id}

    def row(self) -> dict[str, Any]:
        return {"schema": LOCKBOX_SCHEMA, "access_id": self.access_id, "lockbox_id": self.lockbox_id,
                "opened_at": self.opened_at, "candidate_id": self.candidate_id, "candidate_digest": self.candidate_digest,
                "purpose": self.purpose.value, "result_digest": self.result_digest,
                "selection_consumed_after": self.selection_consumed_after, "task_id": self.task_id,
                "accessor_id": self.accessor_id, "code_digest": self.code_digest,
                "parameter_digest": self.parameter_digest, "cost_model_digest": self.cost_model_digest,
                "rule_snapshot_digest": self.rule_snapshot_digest, "dataset_snapshot_digest": self.dataset_snapshot_digest,
                "frozen_configuration_digest": self.frozen_configuration_digest,
                "subsequent_action": self.subsequent_action}

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

    def __post_init__(self):
        for name in ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership"):
            object.__setattr__(self, name, _as_enum(getattr(self, name), PITStatus, f"pit.{name}"))
        for item in self.future_information_findings:
            _text(item, "pit.future_information_findings")

    def row(self) -> dict[str, Any]:
        return {name: getattr(self, name).value for name in
                ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership")} | {
                "future_information_findings": list(self.future_information_findings)}


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
        return {"method_id": self.method_id, "status": self.status.value, "computation_ref": self.computation_ref,
                "applicability_reason": self.applicability_reason}


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
    mutated, invalid_reruns = [], []
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
        f.append(_finding("DECLARED_TRIAL_COUNT_MISMATCH", "WARNING", "family.declared_trial_count",
                          f"declared={s.declared_trial_count}; observed={count}"))
    counts = {x.value: 0 for x in TrialStatus}
    for t in economic.values():
        counts[t.status.value] += 1
    return {"expected_trial_count": len(expected), "declared_trial_count": s.declared_trial_count,
            "observed_trial_count": count, "successful_trial_count": counts["SUCCESS"],
            "failed_trial_count": counts["FAILURE"], "aborted_trial_count": counts["ABORTED"],
            "error_trial_count": counts["ERROR"], "reproducibility_rerun_count": len(reruns),
            "trial_id_set_digest": _digest(sorted(economic)),
            "expected_trial_manifest_digest": _digest(dict(sorted(expected.items()))), "missing_trial_ids": missing,
            "unexpected_selection_trial_ids": unexpected, "mutated_trial_ids": mutated,
            "invalid_rerun_ids": invalid_reruns}, f


def _selection(s: ExperimentFamilySnapshot):
    f = []
    if s.computed_family_digest() != s.registered_family_digest:
        f.append(_finding("FAMILY_DEFINITION_MUTATED_AFTER_REGISTRATION", "BLOCKING", "family.registered_family_digest",
                          "registered benchmark/metric/horizon/search/selection/configuration material changed"))
    if _time(s.selection_rule_registered_at, "family.selection_rule_registered_at") > _time(s.selected_at, "family.selected_at"):
        f.append(_finding("SELECTION_RULE_REGISTERED_AFTER_SELECTION", "BLOCKING", "family.selection_rule_registered_at",
                          "rule post-dates winner"))
    if _time(s.family_frozen_at, "family.family_frozen_at") > _time(s.selected_at, "family.selected_at"):
        f.append(_finding("FAMILY_FROZEN_AFTER_SELECTION", "BLOCKING", "family.family_frozen_at", "family freeze post-dates winner"))
    if s.selected_trial_id not in s.expected_trial_digests:
        f.append(_finding("SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY", "BLOCKING", "family.selected_trial_id", "winner absent from manifest"))
    return f


def _lockbox(s: ExperimentFamilySnapshot, receipts: Sequence[LockboxAccessReceipt]):
    f: list[dict[str, str]] = []
    rows = sorted(receipts, key=lambda r: (_time(r.opened_at, "lockbox.opened_at"), r.access_id))
    out = [r.row() for r in rows]
    if len({r.access_id for r in rows}) != len(rows):
        return LockboxStatus.CONTAMINATED_REUSED_FOR_SELECTION, [
            _finding("DUPLICATE_LOCKBOX_ACCESS_ID", "BLOCKING", "lockbox_receipts", "duplicate access identity")], out
    if not s.lockbox_access_history_complete:
        return LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN, [
            _finding("LOCKBOX_ACCESS_HISTORY_UNKNOWN", "UNKNOWN", "family.lockbox_access_history_complete",
                     "absence of receipts is not proof of sealed state")], out
    if not rows:
        return LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN, [
            _finding("LOCKBOX_POSITIVE_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", "UNKNOWN", "lockbox_receipts",
                     "caller-declared complete/empty history is not W4 authority")], out
    bad = len(rows) != 1
    if bad:
        f.append(_finding("LOCKBOX_OPENED_MORE_THAN_ONCE", "BLOCKING", "lockbox_receipts", "final holdout may be revealed once"))
    selected_digest = s.expected_trial_digests.get(s.selected_trial_id)
    cf, ff, st = (_time(s.candidate_frozen_at, "family.candidate_frozen_at"),
                  _time(s.family_frozen_at, "family.family_frozen_at"), _time(s.selected_at, "family.selected_at"))
    expected_config = s.lockbox_configuration_digest()
    for i, r in enumerate(rows):
        p = f"lockbox_receipts.{i}"
        ot = _time(r.opened_at, f"{p}.opened_at")
        checks = [
            (r.lockbox_id != s.lockbox_id, "LOCKBOX_IDENTITY_MISMATCH", "lockbox_id"),
            (r.candidate_id != s.selected_trial_id or r.candidate_digest != selected_digest,
             "LOCKBOX_CANDIDATE_IDENTITY_MISMATCH", "candidate_id"),
            (r.code_digest != s.code_digest, "LOCKBOX_CODE_IDENTITY_MISMATCH", "code_digest"),
            (r.parameter_digest != s.parameter_digest, "LOCKBOX_PARAMETER_IDENTITY_MISMATCH", "parameter_digest"),
            (r.cost_model_digest != s.cost_model_digest, "LOCKBOX_COST_MODEL_IDENTITY_MISMATCH", "cost_model_digest"),
            (r.rule_snapshot_digest != s.rule_snapshot_digest, "LOCKBOX_RULE_SNAPSHOT_IDENTITY_MISMATCH", "rule_snapshot_digest"),
            (r.dataset_snapshot_digest != s.dataset_snapshot_digest, "LOCKBOX_DATASET_IDENTITY_MISMATCH", "dataset_snapshot_digest"),
            (r.accessor_id != s.lockbox_accessor_id, "LOCKBOX_ACCESSOR_IDENTITY_MISMATCH", "accessor_id"),
            (r.task_id != s.lockbox_task_id, "LOCKBOX_TASK_IDENTITY_MISMATCH", "task_id"),
            (r.frozen_configuration_digest != expected_config or _digest(r.configuration_material()) != r.frozen_configuration_digest,
             "LOCKBOX_FROZEN_CONFIGURATION_MISMATCH", "frozen_configuration_digest"),
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
    f.append(_finding("LOCKBOX_POSITIVE_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", "UNKNOWN", "lockbox_receipts",
                      "internally consistent caller receipt is not canonical W4 lockbox authority"))
    return LockboxStatus.IDENTITY_OR_ACCESS_HISTORY_UNKNOWN, f, out


def _pit(p: PITEvidence):
    f: list[dict[str, str]] = []
    fail = unknown = False
    effective: dict[str, Any] = {}
    dims = ("dataset_lineage", "available_at_lineage", "rule_version", "revision_timing", "universe_membership")
    for name in dims:
        state = getattr(p, name)
        if state is PITStatus.FAIL:
            effective[name] = PITStatus.FAIL.value
            fail = True
            f.append(_finding(f"PIT_{name.upper()}_FAIL", "BLOCKING", f"pit.{name}", "PIT evidence failed"))
        elif state is PITStatus.UNKNOWN:
            effective[name] = PITStatus.UNKNOWN.value
            unknown = True
            f.append(_finding(f"PIT_{name.upper()}_UNKNOWN", "UNKNOWN", f"pit.{name}", "PIT evidence unresolved"))
        else:
            effective[name] = PITStatus.UNKNOWN.value
            unknown = True
            f.append(_finding(f"PIT_{name.upper()}_POSITIVE_AUTHORITY_UNVERIFIED", "UNKNOWN", f"pit.{name}",
                              "caller PASS cannot mint governed PIT provenance"))
    for i, item in enumerate(p.future_information_findings):
        fail = True
        f.append(_finding("FUTURE_INFORMATION_LEAKAGE", "BLOCKING", f"pit.future_information_findings.{i}", item))
    if any(getattr(p, name) is PITStatus.PASS for name in dims):
        f.append(_finding("PIT_POSITIVE_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", "UNKNOWN", "pit",
                          "positive PIT state requires a separately governed W2/PIT adapter"))
    effective["future_information_findings"] = list(p.future_information_findings)
    return f, fail, unknown, effective


def _methods(required: Sequence[str], results: Sequence[MethodResult]):
    f, index, blocked = [], {}, False
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
        elif r.status in {MethodStatus.FAIL, MethodStatus.NOT_RUN, MethodStatus.INSUFFICIENT_DATA, MethodStatus.NUMERICAL_FAILURE}:
            blocked = True
            f.append(_finding("REQUIRED_METHOD_NOT_CLEAR", "BLOCKING", f"methods.{mid}.status", f"status={r.status.value}"))
    return f, [index[k].row() for k in sorted(index)], blocked


def audit_research_integrity(snapshot: ExperimentFamilySnapshot, *, expected_w4_snapshot_digest: str | None,
                             lockbox_receipts: Sequence[LockboxAccessReceipt], pit_evidence: PITEvidence,
                             method_results: Sequence[MethodResult] = (), observed_at: str) -> dict[str, Any]:
    """P0A audit. Caller-supplied positive labels never mint upstream authority."""
    observed = _time(observed_at, "audit.observed_at")
    snap_digest = snapshot.snapshot_digest()
    findings: list[dict[str, str]] = []
    match = False
    if expected_w4_snapshot_digest is None:
        findings.append(_finding("W4_SNAPSHOT_EXPECTED_DIGEST_MISSING", "UNKNOWN", "expected_w4_snapshot_digest",
                                 "content comparison absent"))
    else:
        _sha(expected_w4_snapshot_digest, "expected_w4_snapshot_digest")
        match = expected_w4_snapshot_digest == snap_digest
        if not match:
            findings.append(_finding("W4_SNAPSHOT_DIGEST_MISMATCH", "BLOCKING", "expected_w4_snapshot_digest",
                                     "snapshot differs from comparison digest"))
    findings.append(_finding("W4_AUTHORITY_BINDING_NOT_IMPLEMENTED_P0A", "UNKNOWN", "w4_authority_state",
                             "canonical W4 provenance requires a separately governed read adapter"))
    reconciliation, fs = _reconcile_trials(snapshot); findings += fs
    findings += _selection(snapshot)
    lock_state, fs, lock_rows = _lockbox(snapshot, lockbox_receipts); findings += fs
    fs, pit_fail, pit_unknown, pit_row = _pit(pit_evidence); findings += fs
    fs, method_rows, methods_blocked = _methods(snapshot.required_method_ids, method_results); findings += fs
    codes = {x["code"] for x in findings}
    trial_codes = {"DUPLICATE_TRIAL_ID", "MISSING_EXPECTED_TRIAL", "UNREGISTERED_SELECTION_TRIAL",
                   "TRIAL_IMMUTABLE_DIGEST_MISMATCH", "INVALID_REPRODUCIBILITY_RERUN"}
    selection_codes = {"FAMILY_DEFINITION_MUTATED_AFTER_REGISTRATION", "SELECTION_RULE_REGISTERED_AFTER_SELECTION",
                       "FAMILY_FROZEN_AFTER_SELECTION", "SELECTED_TRIAL_NOT_IN_REGISTERED_FAMILY"}
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
    elif unknown or pit_unknown:
        disposition = Disposition.ABSTAIN
    elif hard:
        disposition = Disposition.REJECT_SELECTION_BIAS
    else:
        disposition = Disposition.ELIGIBLE_FOR_W7_VALIDATION
    warning = any(x["severity"] == "WARNING" for x in findings)
    if disposition in {Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY, Disposition.REJECT_LOCKBOX_CONTAMINATION,
                       Disposition.REJECT_POINT_IN_TIME_LEAKAGE, Disposition.REJECT_SELECTION_BIAS,
                       Disposition.RETEST_WITH_PREREGISTERED_FAMILY}:
        risk, grade = "HIGH", "BLOCKED"
    elif disposition in {Disposition.ABSTAIN, Disposition.INSUFFICIENT_EVIDENCE}:
        risk, grade = "UNKNOWN", "UNKNOWN"
    elif warning:
        risk, grade = "ELEVATED", "P0A_INTEGRITY_WARNING"
    else:
        risk, grade = "LOW_BOOKKEEPING_RISK", "P0A_INTEGRITY_CLEAR"
    authority = {k: False for k in ("experiment_registry_write_authority", "strategy_experiment_write_authority",
                                     "probability_authority", "final_validation_authority", "risk_override_authority",
                                     "position_authority", "order_authority", "trade_authority")}
    out = {
        "schema": AUDIT_SCHEMA, "skill_id": SKILL_ID, "audit_version": "P0A",
        "audit_id": f"ds10-p0a-{snap_digest[:16]}", "observed_at": observed.isoformat(),
        "experiment_family_ref": snapshot.experiment_family_ref, "w4_snapshot_digest": snap_digest,
        "w4_snapshot_digest_matches_expected": match, "w4_authority_state": "EXTERNAL_CANONICAL_BINDING_REQUIRED",
        "registered_family_digest": snapshot.registered_family_digest,
        "computed_family_digest": snapshot.computed_family_digest(), "trial_reconciliation": reconciliation,
        "lockbox_status": lock_state.value, "lockbox_access_receipts": lock_rows, "pit_evidence": pit_row,
        "method_results": method_rows, "selection_bias_risk": risk, "adjusted_evidence_grade": grade,
        "research_integrity_disposition": disposition.value,
        "blocking_findings": sorted((x for x in findings if x["severity"] == "BLOCKING"),
                                     key=lambda x: (x["code"], x["path"], x["detail"])),
        "nonblocking_findings": sorted((x for x in findings if x["severity"] != "BLOCKING"),
                                        key=lambda x: (x["severity"], x["code"], x["path"], x["detail"])),
        "required_retest": disposition in {Disposition.RETEST_WITH_PREREGISTERED_FAMILY,
                                             Disposition.REJECT_INCOMPLETE_TRIAL_HISTORY,
                                             Disposition.REJECT_LOCKBOX_CONTAMINATION,
                                             Disposition.REJECT_POINT_IN_TIME_LEAKAGE,
                                             Disposition.REJECT_SELECTION_BIAS},
        "authority": authority, "w7_handoff_is_acceptance": False,
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
