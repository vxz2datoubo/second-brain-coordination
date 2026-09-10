"""Deterministic, read-only Deflated Sharpe Ratio reference calculation.

This module is deliberately an evidence calculator, not a validation, risk, or
trading decision engine.  It consumes the canonical P0A/W4 trial-family chain
and never accepts a caller-created ``number_of_trials`` as an authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import types
from typing import Any, Mapping


METHOD_ID = "DS10-DeflatedSharpe/Bailey-LopezDePrado-2014"
METHOD_VERSION = "1.0.0"
RESULT_SCHEMA = "DeflatedSharpeResult/v1"
EULER_MASCHERONI = 0.5772156649015329
NORMAL_LIBRARY = "statistics.NormalDist/python-stdlib"
NUMERICAL_TOLERANCE = {"absolute": 1e-12, "relative": 1e-12, "ulp": 16}

W4_REGISTRY_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/W4-STRATEGY-EXPERIMENT-FAMILY-P0/src/w4_experiment_family/registry.py"
W4_BINDING_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/W4-STRATEGY-EXPERIMENT-FAMILY-P0/src/w4_experiment_family/read_binding.py"
P0A_REF = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/DS10-RESEARCH-INTEGRITY-P0A/src/offline_research/research_integrity.py"
SOURCE_REF = "a341bfc0dd114bf333dfc385707be31993babf80"

# Both Git blob and SHA-256 identities are frozen from `git show <HEAD>:<path>`.
_PINS = {
    W4_REGISTRY_REF: ("0f6b197c500412f814c38aee347f5a86d8fa8632", "c38e480694852579a2fc2b9afbb0dbcd00614314566fd2109c766b4e6642cd31"),
    W4_BINDING_REF: ("0e2640d3135553435ec06d99ed9f25c9d146a1e4", "a2dcaa73c8a2e55102e291f7d2243a51ddf08696e5bcae8f848fb4f6f257228a"),
}


class MethodState(str, Enum):
    PASS_COMPUTED = "PASS_COMPUTED"
    NOT_APPLICABLE_SINGLE_TRIAL = "NOT_APPLICABLE_SINGLE_TRIAL"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    EFFECTIVE_TRIAL_COUNT_UNRESOLVED = "EFFECTIVE_TRIAL_COUNT_UNRESOLVED"
    MOMENTS_INVALID = "MOMENTS_INVALID"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"
    INPUT_INTEGRITY_BLOCKED = "INPUT_INTEGRITY_BLOCKED"
    ABSTAIN = "ABSTAIN"


class KurtosisSemantics(str, Enum):
    PEARSON = "PEARSON"
    EXCESS = "EXCESS"


class InputIntegrityState(str, Enum):
    CANONICAL_CHAIN_VERIFIED = "CANONICAL_CHAIN_VERIFIED"
    INPUT_INTEGRITY_BLOCKED = "INPUT_INTEGRITY_BLOCKED"
    EFFECTIVE_TRIAL_COUNT_UNRESOLVED = "EFFECTIVE_TRIAL_COUNT_UNRESOLVED"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class ObservedSharpeEvidence:
    observed_sharpe: float
    sample_count: int
    return_frequency: str
    annualization_policy: str
    return_definition_ref: str
    net_or_gross_metric: str
    cost_model_ref: str | None
    selected_trial_id: str
    source_precision: str = "GOVERNED_DECIMAL_TO_FLOAT64"


@dataclass(frozen=True)
class SharpeSamplingMoments:
    sample_skewness: float
    sample_kurtosis: float
    kurtosis_semantics: KurtosisSemantics

    def pearson_kurtosis(self) -> float:
        if self.kurtosis_semantics is KurtosisSemantics.PEARSON:
            return self.sample_kurtosis
        if self.kurtosis_semantics is KurtosisSemantics.EXCESS:
            return self.sample_kurtosis + 3.0
        raise ValueError("KURTOSIS_SEMANTICS_UNSUPPORTED")


@dataclass(frozen=True)
class IndependentTrialEstimate:
    experiment_family_ref: str
    family_revision: str
    family_content_digest: str
    selected_trial_id: str
    raw_trial_count: int
    effective_trial_count: float | None
    trial_count_method_ref: str
    dependence_evidence_ref: str | None
    sharpe_cross_section_variance: float
    p0a_audit: Mapping[str, Any] | None
    w4_read_receipt: Mapping[str, Any] | None
    dependence_resolved: bool = True


@dataclass(frozen=True)
class ExpectedMaxSharpeBenchmark:
    effective_trial_count: float
    cross_section_variance: float
    cross_section_dispersion: float
    quantile_one: float
    quantile_two: float
    expected_max_sharpe: float


@dataclass(frozen=True)
class ProbabilisticSharpeResult:
    benchmark_sharpe: float
    denominator_squared: float
    denominator: float
    z_score: float
    probability: float


@dataclass(frozen=True)
class DeflatedSharpeResult:
    result_id: str
    method_id: str
    method_version: str
    experiment_family_ref: str | None
    family_revision: str | None
    family_content_digest: str | None
    selected_trial_id: str | None
    observed_sharpe: float | None
    sample_count: int | None
    skewness: float | None
    kurtosis: float | None
    raw_trial_count: int | None
    effective_trial_count: float | None
    trial_count_method_ref: str | None
    sharpe_cross_section_variance: float | None
    expected_max_sharpe_benchmark: float | None
    probabilistic_sharpe_against_benchmark: float | None
    deflated_sharpe_probability: float | None
    numerical_diagnostics: Mapping[str, Any]
    input_integrity_state: str
    method_state: str
    uncertainties: tuple[str, ...]
    computation_digest: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["uncertainties"] = list(self.uncertainties)
        return value


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _safe_for_digest(value: Any) -> Any:
    """Preserve deterministic identity without serializing NaN/Inf on a guard path."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"non_finite": "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")}
    if isinstance(value, Mapping):
        return {str(key): _safe_for_digest(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_safe_for_digest(item) for item in value]
    return value


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "coordination").is_dir():
            return parent
    raise RuntimeError("REPOSITORY_ROOT_UNRESOLVED")


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_pinned_source(ref: str, blob_sha: str, sha256: str) -> Path:
    """Verify the pinned Git object and local bytes before executing it."""
    root = _repo_root()
    try:
        frozen = subprocess.run(["git", "-C", str(root), "show", f"{SOURCE_REF}:{ref}"], check=True,
                                capture_output=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("GOVERNED_SOURCE_UNAVAILABLE") from exc
    if _git_blob_sha(frozen) != blob_sha or hashlib.sha256(frozen).hexdigest() != sha256:
        raise RuntimeError("GOVERNED_SOURCE_PIN_MISMATCH")
    path = (root / ref).resolve()
    if root.resolve() not in path.parents:
        raise RuntimeError("GOVERNED_SOURCE_PATH_ESCAPE")
    try:
        local = path.read_bytes()
    except OSError as exc:
        raise RuntimeError("GOVERNED_SOURCE_UNAVAILABLE") from exc
    if local != frozen:
        raise RuntimeError("GOVERNED_SOURCE_BYTES_DRIFTED")
    return path


def _load_verified_w4_binding_module():
    registry_path = _verify_pinned_source(W4_REGISTRY_REF, *_PINS[W4_REGISTRY_REF])
    binding_path = _verify_pinned_source(W4_BINDING_REF, *_PINS[W4_BINDING_REF])
    package_name = "_ds10_p0b_verified_w4"
    registry_name = f"{package_name}.registry"
    binding_name = f"{package_name}.read_binding"
    package = types.ModuleType(package_name)
    package.__package__ = package_name
    package.__path__ = [str(registry_path.parent)]
    sys.modules[package_name] = package
    try:
        registry_spec = importlib.util.spec_from_file_location(registry_name, registry_path)
        binding_spec = importlib.util.spec_from_file_location(binding_name, binding_path)
        if not registry_spec or not registry_spec.loader or not binding_spec or not binding_spec.loader:
            raise RuntimeError("W4_READ_BINDING_MODULE_LOAD_FAILED")
        registry = importlib.util.module_from_spec(registry_spec)
        sys.modules[registry_name] = registry
        registry_spec.loader.exec_module(registry)
        binding = importlib.util.module_from_spec(binding_spec)
        sys.modules[binding_name] = binding
        binding_spec.loader.exec_module(binding)
        return binding
    except Exception:
        sys.modules.pop(binding_name, None); sys.modules.pop(registry_name, None); sys.modules.pop(package_name, None)
        raise


def _load_verified_p0a_module():
    root = _repo_root(); path = root / P0A_REF
    raw = path.read_bytes()
    name = f"_ds10_p0b_p0a_{hashlib.sha256(raw).hexdigest()[:16]}"
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError("P0A_MODULE_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None); raise
    return module


def _authority_failure(trials: IndependentTrialEstimate) -> tuple[InputIntegrityState, MethodState, tuple[str, ...]] | None:
    if not trials.dependence_resolved or not trials.dependence_evidence_ref:
        return (InputIntegrityState.EFFECTIVE_TRIAL_COUNT_UNRESOLVED, MethodState.EFFECTIVE_TRIAL_COUNT_UNRESOLVED,
                ("DEPENDENCE_EVIDENCE_REQUIRED",))
    if trials.effective_trial_count is None:
        return (InputIntegrityState.EFFECTIVE_TRIAL_COUNT_UNRESOLVED, MethodState.EFFECTIVE_TRIAL_COUNT_UNRESOLVED,
                ("EFFECTIVE_TRIAL_COUNT_REQUIRED",))
    if (not _finite(trials.effective_trial_count) or trials.effective_trial_count <= 0 or
            not isinstance(trials.raw_trial_count, int) or isinstance(trials.raw_trial_count, bool) or trials.raw_trial_count <= 0 or
            trials.effective_trial_count > trials.raw_trial_count):
        return (InputIntegrityState.INPUT_INTEGRITY_BLOCKED, MethodState.INPUT_INTEGRITY_BLOCKED,
                ("EFFECTIVE_TRIAL_COUNT_INVALID",))
    if not all(isinstance(value, str) and value for value in (trials.experiment_family_ref, trials.family_revision,
                                                                trials.family_content_digest, trials.selected_trial_id,
                                                                trials.trial_count_method_ref)):
        return (InputIntegrityState.INPUT_INTEGRITY_BLOCKED, MethodState.INPUT_INTEGRITY_BLOCKED,
                ("TRIAL_AUTHORITY_IDENTITY_INCOMPLETE",))
    try:
        binding = _load_verified_w4_binding_module()
        verification = binding.verify_canonical_family_receipt(trials.w4_read_receipt)
        p0a = _load_verified_p0a_module()
        p0a.canonical_audit_digest(trials.p0a_audit or {})
    except Exception as exc:
        return (InputIntegrityState.INPUT_INTEGRITY_BLOCKED, MethodState.INPUT_INTEGRITY_BLOCKED,
                (f"CANONICAL_CHAIN_VERIFICATION_FAILED:{type(exc).__name__}",))
    verified = {"CANONICAL_W4_READ_VERIFIED", "CANONICAL_W4_READ_VERIFIED_POINTER_ADVANCED"}
    audit = trials.p0a_audit or {}; receipt = trials.w4_read_receipt or {}
    if (not isinstance(verification, Mapping) or verification.get("primary") not in verified or
            audit.get("schema") != "ResearchIntegrityAudit/v1" or audit.get("audit_version") != "P0A" or
            audit.get("research_integrity_disposition") != "ELIGIBLE_FOR_W7_VALIDATION" or
            audit.get("w4_authority_state") != "CANONICAL_W4_BINDING_VERIFIED" or
            audit.get("w7_handoff_is_acceptance") is not False or
            receipt.get("experiment_family_ref") != trials.experiment_family_ref or
            receipt.get("family_revision_id") != trials.family_revision or
            receipt.get("family_content_digest") != trials.family_content_digest or
            receipt.get("selected_trial_id") != trials.selected_trial_id or
            receipt.get("trial_count") != trials.raw_trial_count or
            audit.get("experiment_family_ref") != trials.experiment_family_ref or
            audit.get("trial_reconciliation", {}).get("observed_trial_count") != trials.raw_trial_count):
        return (InputIntegrityState.INPUT_INTEGRITY_BLOCKED, MethodState.INPUT_INTEGRITY_BLOCKED,
                ("CANONICAL_TRIAL_FAMILY_MISMATCH",))
    if trials.effective_trial_count == 1:
        return (InputIntegrityState.CANONICAL_CHAIN_VERIFIED, MethodState.NOT_APPLICABLE_SINGLE_TRIAL,
                ("SINGLE_INDEPENDENT_TRIAL",))
    return None


def expected_max_sharpe_benchmark(trials: IndependentTrialEstimate) -> ExpectedMaxSharpeBenchmark:
    """Bailey--Lopez de Prado extreme-value expected maximum, assuming mean SR=0."""
    n = float(trials.effective_trial_count)
    variance = float(trials.sharpe_cross_section_variance)
    if not math.isfinite(n) or n <= 1 or not math.isfinite(variance) or variance < 0:
        raise ValueError("EXPECTED_MAX_INPUT_INVALID")
    q1_p, q2_p = 1.0 - 1.0 / n, 1.0 - 1.0 / (n * math.e)
    if not (0.0 < q1_p < 1.0 and 0.0 < q2_p < 1.0):
        raise ValueError("NORMAL_CDF_DOMAIN_INVALID")
    normal = statistics.NormalDist()
    q1, q2 = normal.inv_cdf(q1_p), normal.inv_cdf(q2_p)
    dispersion = math.sqrt(variance)
    benchmark = dispersion * ((1.0 - EULER_MASCHERONI) * q1 + EULER_MASCHERONI * q2)
    if not all(math.isfinite(value) for value in (q1, q2, dispersion, benchmark)):
        raise ValueError("EXPECTED_MAX_NUMERICAL_FAILURE")
    return ExpectedMaxSharpeBenchmark(n, variance, dispersion, q1, q2, benchmark)


def probabilistic_sharpe_ratio(observed: ObservedSharpeEvidence, moments: SharpeSamplingMoments,
                                benchmark: ExpectedMaxSharpeBenchmark) -> ProbabilisticSharpeResult:
    if observed.sample_count < 2:
        raise ValueError("INSUFFICIENT_SAMPLE")
    pearson = moments.pearson_kurtosis()
    if not all(_finite(value) for value in (observed.observed_sharpe, moments.sample_skewness, pearson)) or pearson < 1.0:
        raise ValueError("MOMENTS_INVALID")
    sr = float(observed.observed_sharpe)
    denominator_squared = 1.0 - float(moments.sample_skewness) * sr + ((pearson - 1.0) / 4.0) * sr * sr
    if not math.isfinite(denominator_squared) or denominator_squared <= 0:
        raise ValueError("PSR_DENOMINATOR_INVALID")
    denominator = math.sqrt(denominator_squared)
    z_score = (sr - benchmark.expected_max_sharpe) * math.sqrt(observed.sample_count - 1.0) / denominator
    probability = statistics.NormalDist().cdf(z_score)
    if not all(math.isfinite(value) for value in (denominator, z_score, probability)) or not 0.0 <= probability <= 1.0:
        raise ValueError("PSR_NUMERICAL_FAILURE")
    return ProbabilisticSharpeResult(benchmark.expected_max_sharpe, denominator_squared, denominator, z_score, probability)


def _result(observed: ObservedSharpeEvidence, moments: SharpeSamplingMoments, trials: IndependentTrialEstimate,
            integrity: InputIntegrityState, state: MethodState, uncertainties: tuple[str, ...],
            benchmark: ExpectedMaxSharpeBenchmark | None = None, psr: ProbabilisticSharpeResult | None = None,
            diagnostics: Mapping[str, Any] | None = None) -> DeflatedSharpeResult:
    material = {
        "method_id": METHOD_ID, "method_version": METHOD_VERSION, "family": trials.experiment_family_ref,
        "family_revision": trials.family_revision, "family_digest": trials.family_content_digest,
        "selected_trial": observed.selected_trial_id, "observed": observed.observed_sharpe,
        "sample_count": observed.sample_count, "moments": asdict(moments), "raw_trials": trials.raw_trial_count,
        "effective_trials": trials.effective_trial_count, "variance": trials.sharpe_cross_section_variance,
        "integrity": integrity.value, "state": state.value, "benchmark": None if benchmark is None else benchmark.expected_max_sharpe,
        "probability": None if psr is None else psr.probability, "uncertainties": list(uncertainties),
    }
    digest = _digest(_safe_for_digest(material))
    try:
        canonical_kurtosis = moments.pearson_kurtosis() if _finite(moments.sample_kurtosis) else None
    except (TypeError, ValueError):
        canonical_kurtosis = None
    return DeflatedSharpeResult(
        result_id=f"ds10-dsr-{digest[:16]}", method_id=METHOD_ID, method_version=METHOD_VERSION,
        experiment_family_ref=trials.experiment_family_ref, family_revision=trials.family_revision,
        family_content_digest=trials.family_content_digest, selected_trial_id=observed.selected_trial_id,
        observed_sharpe=observed.observed_sharpe if _finite(observed.observed_sharpe) else None,
        sample_count=observed.sample_count if isinstance(observed.sample_count, int) and not isinstance(observed.sample_count, bool) else None,
        skewness=moments.sample_skewness if _finite(moments.sample_skewness) else None,
        kurtosis=canonical_kurtosis,
        raw_trial_count=trials.raw_trial_count, effective_trial_count=trials.effective_trial_count,
        trial_count_method_ref=trials.trial_count_method_ref,
        sharpe_cross_section_variance=trials.sharpe_cross_section_variance if _finite(trials.sharpe_cross_section_variance) else None,
        expected_max_sharpe_benchmark=None if benchmark is None else benchmark.expected_max_sharpe,
        probabilistic_sharpe_against_benchmark=None if psr is None else psr.probability,
        deflated_sharpe_probability=None if psr is None else psr.probability,
        numerical_diagnostics=dict(diagnostics or {"normal_distribution": NORMAL_LIBRARY, "tolerance": NUMERICAL_TOLERANCE}),
        input_integrity_state=integrity.value, method_state=state.value, uncertainties=uncertainties,
        computation_digest=digest,
    )


def compute_deflated_sharpe(observed: ObservedSharpeEvidence, moments: SharpeSamplingMoments,
                            trials: IndependentTrialEstimate) -> DeflatedSharpeResult:
    """Compute DSR evidence only after canonical trial provenance verifies.

    Guard failures produce an explicit state and null probability fields; no numeric
    fallback is fabricated.
    """
    authority = _authority_failure(trials)
    if authority is not None:
        return _result(observed, moments, trials, *authority)
    if observed.selected_trial_id != trials.selected_trial_id:
        return _result(observed, moments, trials, InputIntegrityState.INPUT_INTEGRITY_BLOCKED,
                       MethodState.INPUT_INTEGRITY_BLOCKED, ("SELECTED_TRIAL_ID_MISMATCH",))
    if (not _finite(observed.observed_sharpe) or observed.source_precision != "GOVERNED_DECIMAL_TO_FLOAT64" or
            observed.annualization_policy not in {"NATIVE_HORIZON", "ANNUALIZED_FROM_GOVERNED_PERIODIC_RETURNS"} or
            not all(isinstance(item, str) and item for item in (observed.return_frequency, observed.return_definition_ref,
                                                                  observed.net_or_gross_metric, observed.selected_trial_id)) or
            (observed.net_or_gross_metric == "NET" and not observed.cost_model_ref)):
        return _result(observed, moments, trials, InputIntegrityState.ABSTAIN, MethodState.ABSTAIN,
                       ("OBSERVED_SHARPE_EVIDENCE_INVALID",))
    if observed.sample_count < 2:
        return _result(observed, moments, trials, InputIntegrityState.CANONICAL_CHAIN_VERIFIED,
                       MethodState.INSUFFICIENT_SAMPLE, ("SAMPLE_COUNT_BELOW_TWO",))
    try:
        benchmark = expected_max_sharpe_benchmark(trials)
    except ValueError as exc:
        return _result(observed, moments, trials, InputIntegrityState.CANONICAL_CHAIN_VERIFIED,
                       MethodState.NUMERICAL_FAILURE, (str(exc),))
    try:
        psr = probabilistic_sharpe_ratio(observed, moments, benchmark)
    except ValueError as exc:
        state = MethodState.MOMENTS_INVALID if str(exc) == "MOMENTS_INVALID" else MethodState.NUMERICAL_FAILURE
        return _result(observed, moments, trials, InputIntegrityState.CANONICAL_CHAIN_VERIFIED, state, (str(exc),), benchmark)
    return _result(observed, moments, trials, InputIntegrityState.CANONICAL_CHAIN_VERIFIED,
                   MethodState.PASS_COMPUTED, (), benchmark, psr,
                   {"normal_distribution": NORMAL_LIBRARY, "tolerance": NUMERICAL_TOLERANCE,
                    "kurtosis_canonical_semantics": KurtosisSemantics.PEARSON.value,
                    "expected_max_components": asdict(benchmark), "psr": asdict(psr)})
