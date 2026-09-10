"""Deterministic Bailey--Borwein--Lopez de Prado--Zhu CSCV/PBO reference.

This is a read-only DS-10 research calculation.  It verifies the canonical W4
experiment-family read receipt and the P0A integrity audit before accepting a
complete synchronous performance matrix.  It deliberately owns no experiment
ledger, read-receipt store, validation decision, probability registry, market
truth, allocation, order, or trade authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


METHOD_ID = "DS10-PBO-CSCV/Bailey-Borwein-LopezDePrado-Zhu-2015"
METHOD_VERSION = "1.1.0"
INPUT_SCHEMA = "CSCVInput/v1"
SPLIT_SCHEMA = "CSCVSplitResult/v1"
RESULT_SCHEMA = "PBOResult/v1"
TIE_ABSOLUTE_TOLERANCE = 1e-12
TIE_RELATIVE_TOLERANCE = 1e-12
ORDERING_POLICY = "TRIAL_ID_ASCENDING__OBSERVATION_ROW_ORDER_PRESERVED"
COMBINATION_POLICY = "LEXICOGRAPHIC_ORIENTED_IS_HALVES"
TIE_POLICY = "STRICT_NO_MATERIAL_TIES"
MISSINGNESS_POLICY = "COMPLETE_SYNCHRONOUS_MATRIX_REQUIRED"
GROSS_NET_SEMANTICS = "NET_OF_DECLARED_COSTS_REQUIRED"


@dataclass(frozen=True)
class _PerformanceMeasure:
    """A frozen scorer implementation, addressed by governed metric identity."""

    metric_id: str
    metric_version: str
    scorer_semantics: str


# This P0C reference release supports exactly one W4-exposed metric identity.
# Adding another measure is a semantic change: it must be registered here and
# released under a new METHOD_VERSION, never accepted merely by a caller label.
_SUPPORTED_PERFORMANCE_MEASURES = {
    ("METRIC.PUBLIC.SYNTHETIC.V1", "1.0.0"): _PerformanceMeasure(
        "METRIC.PUBLIC.SYNTHETIC.V1", "1.0.0", "ARITHMETIC_MEAN/V1"
    ),
}


class ComputationState(str, Enum):
    PASS_COMPUTED = "PASS_COMPUTED"
    INSUFFICIENT_STRATEGIES = "INSUFFICIENT_STRATEGIES"
    INSUFFICIENT_OBSERVATIONS = "INSUFFICIENT_OBSERVATIONS"
    INVALID_PARTITION_DESIGN = "INVALID_PARTITION_DESIGN"
    COMBINATORIAL_BUDGET_EXCEEDED = "COMBINATORIAL_BUDGET_EXCEEDED"
    MISSINGNESS_UNRESOLVED = "MISSINGNESS_UNRESOLVED"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"
    INPUT_INTEGRITY_BLOCKED = "INPUT_INTEGRITY_BLOCKED"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class CSCVInput:
    """One complete synchronous T x N performance matrix and its governed chain."""

    w4_read_receipt: Mapping[str, Any]
    p0a_audit: Mapping[str, Any]
    trial_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    performance_matrix: tuple[tuple[float, ...], ...]
    performance_measure_id: str
    performance_measure_version: str
    higher_is_better: bool
    group_count: int
    max_combinations: int
    performance_evidence_refs: tuple[str, ...]
    cost_semantics: str
    family_revision_ref: str
    family_revision_digest: str
    canonical_read_receipt_ref: str
    canonical_read_receipt_digest: str
    integrity_audit_ref: str
    integrity_audit_digest: str
    observation_axis_id: str
    observation_time_index_digest: str
    performance_matrix_digest: str
    tie_policy: str
    missingness_policy: str
    gross_net_semantics: str
    pit_evidence_ref: str
    rule_snapshot_ref: str
    data_snapshot_ref: str
    method_id: str
    method_version: str
    method_code_digest: str
    ordering_policy: str = ORDERING_POLICY
    combination_policy: str = COMBINATION_POLICY


@dataclass(frozen=True)
class CSCVSplitResult:
    split_id: str
    is_group_ids: tuple[int, ...]
    oos_group_ids: tuple[int, ...]
    selected_trial_id: str
    selected_trial_identity_digest: str
    is_score: float
    oos_score: float
    is_score_vector_digest: str
    oos_score_vector_digest: str
    oos_rank: int
    omega: float
    logit: float
    split_overfit: bool
    median_mass: bool
    tie_diagnostic: str
    missingness_diagnostic: str
    split_digest_semantics: str
    computation_digest: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema"] = SPLIT_SCHEMA
        value["is_group_ids"] = list(self.is_group_ids)
        value["oos_group_ids"] = list(self.oos_group_ids)
        return value


@dataclass(frozen=True)
class PBOResult:
    result_id: str
    method_id: str
    method_version: str
    family_ref: str | None
    family_content_digest: str | None
    family_revision_ref: str | None
    family_revision_digest: str | None
    canonical_read_receipt_ref: str | None
    canonical_read_receipt_digest: str | None
    integrity_audit_ref: str | None
    integrity_audit_digest: str | None
    input_chain_digest: str
    strategy_count: int | None
    observation_count: int | None
    group_count: int | None
    group_sizes: tuple[int, ...]
    combination_count: int | None
    evaluated_split_count: int
    performance_measure_id: str | None
    performance_measure_version: str | None
    higher_is_better: bool | None
    ordering_policy: str
    combination_policy: str
    cost_semantics: str | None
    gross_net_semantics: str | None
    tie_policy: str
    missingness_policy: str
    performance_matrix_digest: str | None
    observation_axis_id: str | None
    observation_time_index_digest: str | None
    pit_evidence_ref: str | None
    rule_snapshot_ref: str | None
    data_snapshot_ref: str | None
    method_code_digest: str | None
    applicability_state: str
    pbo_estimate: float | None
    pbo_numerator: int
    pbo_denominator: int
    median_mass_count: int
    combination_manifest_digest: str
    ordered_split_ledger_digest: str
    logit_distribution_digest: str
    split_results: tuple[CSCVSplitResult, ...]
    numerical_diagnostics: Mapping[str, Any]
    uncertainties: tuple[str, ...]
    authority: Mapping[str, bool]
    computation_digest: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema"] = RESULT_SCHEMA
        value["group_sizes"] = list(self.group_sizes)
        value["split_results"] = [item.to_dict() for item in self.split_results]
        value["uncertainties"] = list(self.uncertainties)
        return value


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _code_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _input_chain_digest(input_value: CSCVInput) -> str:
    """Bind all caller-supplied provenance, method, and matrix material."""
    return _digest({
        "family_revision_ref": input_value.family_revision_ref,
        "family_revision_digest": input_value.family_revision_digest,
        "canonical_read_receipt_ref": input_value.canonical_read_receipt_ref,
        "canonical_read_receipt_digest": input_value.canonical_read_receipt_digest,
        "integrity_audit_ref": input_value.integrity_audit_ref,
        "integrity_audit_digest": input_value.integrity_audit_digest,
        "trial_ids": list(input_value.trial_ids),
        "observation_axis_id": input_value.observation_axis_id,
        "observation_ids": list(input_value.observation_ids),
        "observation_time_index_digest": input_value.observation_time_index_digest,
        "performance_matrix_digest": input_value.performance_matrix_digest,
        "performance_measure_id": input_value.performance_measure_id,
        "performance_measure_version": input_value.performance_measure_version,
        "tie_policy": input_value.tie_policy,
        "missingness_policy": input_value.missingness_policy,
        "cost_semantics": input_value.cost_semantics,
        "gross_net_semantics": input_value.gross_net_semantics,
        "pit_evidence_ref": input_value.pit_evidence_ref,
        "rule_snapshot_ref": input_value.rule_snapshot_ref,
        "data_snapshot_ref": input_value.data_snapshot_ref,
        "method_id": input_value.method_id,
        "method_version": input_value.method_version,
        "method_code_digest": input_value.method_code_digest,
    })


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _authority() -> dict[str, bool]:
    return {
        "experiment_registry_write_authority": False,
        "strategy_experiment_write_authority": False,
        "trial_ledger_authority": False,
        "read_receipt_store_authority": False,
        "market_data_truth_authority": False,
        "probability_authority": False,
        "w7_validation_authority": False,
        "risk_authority": False,
        "position_authority": False,
        "order_authority": False,
        "trade_authority": False,
        "pbo_result_is_w7_accept": False,
    }


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "coordination").is_dir():
            return parent
    raise RuntimeError("REPOSITORY_ROOT_UNRESOLVED")


def _load_w4_binding():
    root = _repo_root()
    source = root / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/W4-STRATEGY-EXPERIMENT-FAMILY-P0/src"
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from w4_experiment_family import read_binding
    return read_binding


def _load_p0a():
    path = _repo_root() / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/DS10-RESEARCH-INTEGRITY-P0A/src/offline_research/research_integrity.py"
    name = "_ds10_p0c_canonical_p0a"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("P0A_MODULE_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _result(input_value: CSCVInput, state: ComputationState, *, uncertainties: Sequence[str] = (),
            strategy_count: int | None = None, observation_count: int | None = None,
            group_sizes: Sequence[int] = (), combination_count: int | None = None,
            split_results: Sequence[CSCVSplitResult] = (), diagnostics: Mapping[str, Any] | None = None) -> PBOResult:
    family = input_value.w4_read_receipt if isinstance(input_value.w4_read_receipt, Mapping) else {}
    split_rows = [item.to_dict() for item in split_results]
    combination_manifest = [
        {"split_id": item.split_id, "is_group_ids": list(item.is_group_ids),
         "oos_group_ids": list(item.oos_group_ids)}
        for item in split_results
    ]
    numerator = sum(item.split_overfit for item in split_results)
    denominator = len(split_results)
    input_chain_digest = _input_chain_digest(input_value)
    material = {
        "method_id": METHOD_ID, "method_version": METHOD_VERSION, "family_ref": family.get("experiment_family_ref"),
        "family_content_digest": family.get("family_content_digest"),
        "family_revision_ref": input_value.family_revision_ref, "family_revision_digest": input_value.family_revision_digest,
        "canonical_read_receipt_ref": input_value.canonical_read_receipt_ref,
        "canonical_read_receipt_digest": input_value.canonical_read_receipt_digest,
        "integrity_audit_ref": input_value.integrity_audit_ref,
        "integrity_audit_digest": input_value.integrity_audit_digest,
        "input_chain_digest": input_chain_digest, "strategy_count": strategy_count,
        "observation_count": observation_count, "group_count": input_value.group_count,
        "group_sizes": list(group_sizes), "combination_count": combination_count,
        "performance_measure_id": input_value.performance_measure_id,
        "performance_measure_version": input_value.performance_measure_version,
        "higher_is_better": input_value.higher_is_better, "ordering_policy": input_value.ordering_policy,
        "combination_policy": input_value.combination_policy, "cost_semantics": input_value.cost_semantics,
        "gross_net_semantics": input_value.gross_net_semantics, "tie_policy": input_value.tie_policy,
        "missingness_policy": input_value.missingness_policy, "performance_matrix_digest": input_value.performance_matrix_digest,
        "observation_axis_id": input_value.observation_axis_id,
        "observation_time_index_digest": input_value.observation_time_index_digest,
        "pit_evidence_ref": input_value.pit_evidence_ref, "rule_snapshot_ref": input_value.rule_snapshot_ref,
        "data_snapshot_ref": input_value.data_snapshot_ref, "method_code_digest": input_value.method_code_digest,
        "applicability_state": state.value, "split_results": split_rows,
        "pbo_numerator": numerator, "pbo_denominator": denominator,
        "combination_manifest_digest": _digest(combination_manifest),
        "ordered_split_ledger_digest": _digest(split_rows),
        "logit_distribution_digest": _digest([item.logit for item in split_results]),
        "uncertainties": list(uncertainties), "diagnostics": dict(diagnostics or {}),
    }
    digest = _digest(material)
    pbo = None if not split_results else sum(item.split_overfit for item in split_results) / len(split_results)
    median_count = sum(item.median_mass for item in split_results)
    return PBOResult(
        result_id=f"ds10-pbo-cscv-{digest[:16]}", method_id=METHOD_ID, method_version=METHOD_VERSION,
        family_ref=family.get("experiment_family_ref"), family_content_digest=family.get("family_content_digest"),
        family_revision_ref=input_value.family_revision_ref, family_revision_digest=input_value.family_revision_digest,
        canonical_read_receipt_ref=input_value.canonical_read_receipt_ref,
        canonical_read_receipt_digest=input_value.canonical_read_receipt_digest,
        integrity_audit_ref=input_value.integrity_audit_ref, integrity_audit_digest=input_value.integrity_audit_digest,
        input_chain_digest=input_chain_digest,
        strategy_count=strategy_count, observation_count=observation_count, group_count=input_value.group_count,
        group_sizes=tuple(group_sizes), combination_count=combination_count, evaluated_split_count=len(split_results),
        performance_measure_id=input_value.performance_measure_id, performance_measure_version=input_value.performance_measure_version,
        higher_is_better=input_value.higher_is_better if isinstance(input_value.higher_is_better, bool) else None,
        ordering_policy=input_value.ordering_policy, combination_policy=input_value.combination_policy,
        cost_semantics=input_value.cost_semantics, gross_net_semantics=input_value.gross_net_semantics,
        tie_policy=input_value.tie_policy, missingness_policy=input_value.missingness_policy,
        performance_matrix_digest=input_value.performance_matrix_digest, observation_axis_id=input_value.observation_axis_id,
        observation_time_index_digest=input_value.observation_time_index_digest,
        pit_evidence_ref=input_value.pit_evidence_ref, rule_snapshot_ref=input_value.rule_snapshot_ref,
        data_snapshot_ref=input_value.data_snapshot_ref, method_code_digest=input_value.method_code_digest,
        applicability_state=state.value, pbo_estimate=pbo, pbo_numerator=numerator, pbo_denominator=denominator,
        median_mass_count=median_count, combination_manifest_digest=_digest(combination_manifest),
        ordered_split_ledger_digest=_digest(split_rows), logit_distribution_digest=_digest([item.logit for item in split_results]),
        split_results=tuple(split_results), numerical_diagnostics=dict(diagnostics or {}),
        uncertainties=tuple(uncertainties), authority=_authority(), computation_digest=digest,
    )


def _input_integrity(input_value: CSCVInput) -> tuple[str | None, tuple[str, ...]]:
    """Verify P0A/W4 provenance and reject caller-minted or incomplete families."""
    try:
        binding = _load_w4_binding()
        verification = binding.verify_canonical_family_receipt(input_value.w4_read_receipt)
        if verification.get("primary") not in {
            binding.ReadVerificationState.CANONICAL_W4_READ_VERIFIED.value,
            binding.ReadVerificationState.CANONICAL_W4_READ_VERIFIED_POINTER_ADVANCED.value,
        }:
            return "W4_READ_RECEIPT_UNVERIFIED", (str(verification.get("primary")),)
        handle = binding.resolve_canonical_w4_store_v1()
        authorization = binding.ReadAuthorization(
            binding.GOVERNED_TASK_ID, binding.GOVERNED_ROUTE_EPOCH, binding.GOVERNED_EXECUTOR_ROLE,
            binding.GOVERNED_WORK_CLAIM_REF, binding.GOVERNED_AUTH_WITNESS_REF,
        )
        snapshot, _ = binding.read_canonical_family(handle.family_id, handle.family_revision_id,
                                                    authorization=authorization,
                                                    observed_at="2026-09-10T00:00:00Z")
        p0a = _load_p0a()
        if p0a.canonical_audit_digest(input_value.p0a_audit) != input_value.p0a_audit.get("audit_digest"):
            return "P0A_AUDIT_DIGEST_INVALID", ()
    except Exception as exc:
        return "CANONICAL_CHAIN_VERIFICATION_FAILED", (type(exc).__name__,)
    receipt = input_value.w4_read_receipt
    audit = input_value.p0a_audit
    expected_ids = tuple(sorted(item["trial_id"] for item in snapshot.get("trials", ()) if item.get("selection_affecting") is True))
    pit_binding = audit.get("pit_evidence", {}).get("authority_binding", {})
    expected_receipt_ref = f"CanonicalExperimentFamilyReadReceipt/v1:{receipt.get('receipt_digest', '')}"
    expected_audit_ref = f"ResearchIntegrityAudit/v1:{audit.get('audit_id', '')}"
    required = (
        # W4's closed snapshot contract represents completion as the literal
        # state string, not a truthy boolean.  Do not accept other states.
        snapshot.get("completeness_state") == "COMPLETE",
        tuple(input_value.trial_ids) == expected_ids,
        receipt.get("experiment_family_ref") == snapshot.get("exact_family_revision"),
        receipt.get("family_content_digest") == snapshot.get("family_snapshot_digest"),
        receipt.get("trial_count") == len(expected_ids),
        input_value.family_revision_ref == receipt.get("experiment_family_ref"),
        input_value.family_revision_digest == receipt.get("family_content_digest"),
        input_value.canonical_read_receipt_digest == receipt.get("receipt_digest"),
        input_value.canonical_read_receipt_ref == expected_receipt_ref,
        audit.get("schema") == "ResearchIntegrityAudit/v1",
        audit.get("audit_version") == "P0A",
        input_value.integrity_audit_digest == audit.get("audit_digest"),
        input_value.integrity_audit_ref == expected_audit_ref,
        audit.get("research_integrity_disposition") == "ELIGIBLE_FOR_W7_VALIDATION",
        audit.get("w4_authority_state") == "CANONICAL_W4_BINDING_VERIFIED",
        audit.get("w7_handoff_is_acceptance") is False,
        audit.get("experiment_family_ref") == receipt.get("experiment_family_ref"),
        audit.get("w4_snapshot_digest") == receipt.get("family_content_digest"),
        audit.get("trial_reconciliation", {}).get("observed_trial_count") == len(expected_ids),
        isinstance(audit.get("authority"), Mapping) and all(value is False for value in audit["authority"].values()),
        input_value.performance_measure_id == receipt.get("metric_id"),
        input_value.pit_evidence_ref == pit_binding.get("authority_source_ref"),
        input_value.rule_snapshot_ref == pit_binding.get("rule_snapshot_id"),
        input_value.data_snapshot_ref == pit_binding.get("dataset_artifact_ref"),
    )
    if not all(required):
        return "FAMILY_MATRIX_INCOMPLETE_OR_CHAIN_MISMATCH", ()
    return None, ()


def _material_tie(values: Sequence[float]) -> bool:
    ordered = sorted(float(value) for value in values)
    return any(math.isclose(left, right, rel_tol=TIE_RELATIVE_TOLERANCE, abs_tol=TIE_ABSOLUTE_TOLERANCE)
               for left, right in zip(ordered, ordered[1:]))


def _mean(matrix: Sequence[Sequence[float]], rows: Sequence[int], column: int) -> float:
    value = math.fsum(float(matrix[row][column]) for row in rows) / len(rows)
    if not math.isfinite(value):
        raise ArithmeticError("NON_FINITE_SCORE")
    return value


def _performance_scorer(input_value: CSCVInput):
    """Resolve the only supported measure before any split is evaluated."""
    measure = _SUPPORTED_PERFORMANCE_MEASURES.get(
        (input_value.performance_measure_id, input_value.performance_measure_version)
    )
    if measure is None:
        return None
    # The mapping is the semantic binding.  A future scorer must be added with
    # an explicit frozen identity and a new method version.
    if measure.scorer_semantics == "ARITHMETIC_MEAN/V1":
        return _mean
    return None


def _trial_identity_digests() -> dict[str, str]:
    """Read immutable W4 trial identities; do not accept caller substitutions."""
    binding = _load_w4_binding()
    handle = binding.resolve_canonical_w4_store_v1()
    authorization = binding.ReadAuthorization(
        binding.GOVERNED_TASK_ID, binding.GOVERNED_ROUTE_EPOCH, binding.GOVERNED_EXECUTOR_ROLE,
        binding.GOVERNED_WORK_CLAIM_REF, binding.GOVERNED_AUTH_WITNESS_REF,
    )
    snapshot, _ = binding.read_canonical_family(
        handle.family_id, handle.family_revision_id, authorization=authorization,
        observed_at="2026-09-10T00:00:00Z"
    )
    return {str(row["trial_id"]): str(row["immutable_digest"]) for row in snapshot["trials"]
            if row.get("selection_affecting") is True and isinstance(row.get("immutable_digest"), str)}


def compute_pbo_cscv(input_value: CSCVInput) -> PBOResult:
    """Compute exact oriented CSCV PBO or emit an explicit non-pass state.

    No random sampling, early stopping, winner-list reconstruction, clipping, or
    lexical tie fallback is available on this frozen P0 path.
    """
    if not isinstance(input_value, CSCVInput):
        raise TypeError("CSCVInput_REQUIRED")
    integrity_error, integrity_detail = _input_integrity(input_value)
    if integrity_error:
        return _result(input_value, ComputationState.INPUT_INTEGRITY_BLOCKED,
                       uncertainties=(integrity_error, *integrity_detail))
    n, t = len(input_value.trial_ids), len(input_value.observation_ids)
    scorer = _performance_scorer(input_value)
    if scorer is None:
        return _result(input_value, ComputationState.ABSTAIN,
                       uncertainties=("PERFORMANCE_MEASURE_UNSUPPORTED_OR_UNRESOLVED",),
                       strategy_count=n, observation_count=t)
    if n < 2:
        return _result(input_value, ComputationState.INSUFFICIENT_STRATEGIES,
                       uncertainties=("AT_LEAST_TWO_STRATEGIES_REQUIRED",), strategy_count=n, observation_count=t)
    if (not isinstance(input_value.higher_is_better, bool) or input_value.higher_is_better is not True or
            not isinstance(input_value.cost_semantics, str) or not input_value.cost_semantics or
            not isinstance(input_value.performance_measure_id, str) or not input_value.performance_measure_id or
            not isinstance(input_value.performance_measure_version, str) or not input_value.performance_measure_version or
            not input_value.performance_evidence_refs or
            input_value.tie_policy != TIE_POLICY or input_value.missingness_policy != MISSINGNESS_POLICY or
            input_value.gross_net_semantics != GROSS_NET_SEMANTICS or
            input_value.method_id != METHOD_ID or input_value.method_version != METHOD_VERSION or
            input_value.method_code_digest != _code_digest()):
        return _result(input_value, ComputationState.ABSTAIN, uncertainties=("PERFORMANCE_MEASURE_OR_EVIDENCE_INVALID",),
                       strategy_count=n, observation_count=t)
    if input_value.ordering_policy != ORDERING_POLICY or input_value.combination_policy != COMBINATION_POLICY:
        return _result(input_value, ComputationState.ABSTAIN, uncertainties=("CANONICAL_ORDERING_POLICY_REQUIRED",),
                       strategy_count=n, observation_count=t)
    if tuple(input_value.trial_ids) != tuple(sorted(input_value.trial_ids)) or len(set(input_value.trial_ids)) != n:
        return _result(input_value, ComputationState.INPUT_INTEGRITY_BLOCKED, uncertainties=("TRIAL_ORDER_OR_IDENTITY_INVALID",),
                       strategy_count=n, observation_count=t)
    if len(set(input_value.observation_ids)) != t or not all(isinstance(item, str) and item for item in input_value.observation_ids):
        return _result(input_value, ComputationState.ABSTAIN, uncertainties=("OBSERVATION_AXIS_UNRESOLVED",),
                       strategy_count=n, observation_count=t)
    if (not isinstance(input_value.observation_axis_id, str) or not input_value.observation_axis_id or
            input_value.observation_time_index_digest != _digest(list(input_value.observation_ids))):
        return _result(input_value, ComputationState.ABSTAIN, uncertainties=("OBSERVATION_TIME_INDEX_UNRESOLVED",),
                       strategy_count=n, observation_count=t)
    if t == 0 or len(input_value.performance_matrix) != t or any(len(row) != n for row in input_value.performance_matrix):
        return _result(input_value, ComputationState.MISSINGNESS_UNRESOLVED, uncertainties=("MATRIX_NOT_COMPLETE_T_BY_N",),
                       strategy_count=n, observation_count=t)
    if not all(_finite(value) for row in input_value.performance_matrix for value in row):
        return _result(input_value, ComputationState.MISSINGNESS_UNRESOLVED, uncertainties=("NON_FINITE_MATRIX_VALUE",),
                       strategy_count=n, observation_count=t)
    if input_value.performance_matrix_digest != _digest([list(row) for row in input_value.performance_matrix]):
        return _result(input_value, ComputationState.INPUT_INTEGRITY_BLOCKED,
                       uncertainties=("PERFORMANCE_MATRIX_DIGEST_MISMATCH",), strategy_count=n, observation_count=t)
    s = input_value.group_count
    if not isinstance(s, int) or isinstance(s, bool) or s < 2 or s % 2 or t % s:
        return _result(input_value, ComputationState.INVALID_PARTITION_DESIGN,
                       uncertainties=("EVEN_S_GE_2_AND_T_MOD_S_ZERO_REQUIRED",), strategy_count=n, observation_count=t)
    group_size = t // s
    if group_size < 1:
        return _result(input_value, ComputationState.INSUFFICIENT_OBSERVATIONS, uncertainties=("EMPTY_GROUP",),
                       strategy_count=n, observation_count=t)
    count = math.comb(s, s // 2)
    if not isinstance(input_value.max_combinations, int) or isinstance(input_value.max_combinations, bool) or input_value.max_combinations < 1:
        return _result(input_value, ComputationState.ABSTAIN, uncertainties=("COMBINATION_BUDGET_INVALID",),
                       strategy_count=n, observation_count=t, group_sizes=(group_size,) * s, combination_count=count)
    if count > input_value.max_combinations:
        return _result(input_value, ComputationState.COMBINATORIAL_BUDGET_EXCEEDED,
                       uncertainties=("EXACT_ENUMERATION_REQUIRED_NO_SAMPLING",), strategy_count=n, observation_count=t,
                       group_sizes=(group_size,) * s, combination_count=count,
                       diagnostics={"requested_combinations": count, "max_combinations": input_value.max_combinations})
    matrix = input_value.performance_matrix
    splits: list[CSCVSplitResult] = []
    all_groups = tuple(range(s))
    try:
        trial_identity_digests = _trial_identity_digests()
        if set(trial_identity_digests) != set(input_value.trial_ids):
            return _result(input_value, ComputationState.INPUT_INTEGRITY_BLOCKED,
                           uncertainties=("W4_TRIAL_IDENTITY_MANIFEST_MISMATCH",), strategy_count=n, observation_count=t)
        for sequence, is_groups in enumerate(itertools.combinations(all_groups, s // 2), 1):
            oos_groups = tuple(group for group in all_groups if group not in is_groups)
            is_rows = tuple(row for group in is_groups for row in range(group * group_size, (group + 1) * group_size))
            oos_rows = tuple(row for group in oos_groups for row in range(group * group_size, (group + 1) * group_size))
            is_scores = tuple(scorer(matrix, is_rows, column) for column in range(n))
            oos_scores = tuple(scorer(matrix, oos_rows, column) for column in range(n))
            if _material_tie(is_scores) or _material_tie(oos_scores):
                return _result(input_value, ComputationState.ABSTAIN,
                               uncertainties=("RANK_TIE_UNRESOLVED",), strategy_count=n, observation_count=t,
                               group_sizes=(group_size,) * s, combination_count=count,
                               diagnostics={"split_id": f"split-{sequence:05d}", "tie_policy": TIE_POLICY,
                                            "missingness_policy": MISSINGNESS_POLICY})
            selected_index = max(range(n), key=is_scores.__getitem__)
            ascending_oos = tuple(sorted(range(n), key=oos_scores.__getitem__))
            rank = ascending_oos.index(selected_index) + 1  # 1=worst, N=best
            omega = rank / (n + 1)
            logit = math.log(omega / (1.0 - omega))
            if not math.isfinite(logit):
                return _result(input_value, ComputationState.NUMERICAL_FAILURE, uncertainties=("LOGIT_DOMAIN_FAILURE",),
                               strategy_count=n, observation_count=t, group_sizes=(group_size,) * s, combination_count=count)
            material = {"split_id": f"split-{sequence:05d}", "is_group_ids": list(is_groups), "oos_group_ids": list(oos_groups),
                        "selected_trial_id": input_value.trial_ids[selected_index],
                        "selected_trial_identity_digest": trial_identity_digests[input_value.trial_ids[selected_index]],
                        "is_score": is_scores[selected_index], "oos_score": oos_scores[selected_index],
                        "is_score_vector_digest": _digest(is_scores), "oos_score_vector_digest": _digest(oos_scores),
                        "oos_rank": rank, "omega": omega, "logit": logit, "tie_diagnostic": "NO_MATERIAL_TIES",
                        "missingness_diagnostic": "COMPLETE_SYNCHRONOUS_MATRIX", "split_digest_semantics": "CSCV_SPLIT_V1"}
            splits.append(CSCVSplitResult(f"split-{sequence:05d}", is_groups, oos_groups,
                                          input_value.trial_ids[selected_index], trial_identity_digests[input_value.trial_ids[selected_index]],
                                          is_scores[selected_index], oos_scores[selected_index], _digest(is_scores), _digest(oos_scores),
                                          rank, omega, logit, logit < 0.0, 2 * rank == n + 1,
                                          "NO_MATERIAL_TIES", "COMPLETE_SYNCHRONOUS_MATRIX", "CSCV_SPLIT_V1", _digest(material)))
    except (ArithmeticError, OverflowError, ValueError):
        return _result(input_value, ComputationState.NUMERICAL_FAILURE, uncertainties=("SCORE_COMPUTATION_FAILED",),
                       strategy_count=n, observation_count=t, group_sizes=(group_size,) * s, combination_count=count)
    return _result(input_value, ComputationState.PASS_COMPUTED, strategy_count=n, observation_count=t,
                   group_sizes=(group_size,) * s, combination_count=count, split_results=splits,
                   diagnostics={"tie_policy": TIE_POLICY, "missingness_policy": MISSINGNESS_POLICY,
                                "scorer_semantics": _SUPPORTED_PERFORMANCE_MEASURES[(input_value.performance_measure_id, input_value.performance_measure_version)].scorer_semantics,
                                "rank_convention": "1=WORST,N=BEST",
                                "logit_formula": "ln(omega/(1-omega))", "omega_formula": "oos_rank/(N+1)",
                                "oriented_split_count": count, "pbo_is_not_w7_accept": True})
