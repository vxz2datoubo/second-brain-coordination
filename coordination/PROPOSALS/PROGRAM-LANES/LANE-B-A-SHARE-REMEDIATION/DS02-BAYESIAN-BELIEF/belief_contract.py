from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping, Sequence

import jsonschema

VALIDATION_SCHEMA = "DS02BeliefContractValidation/v1"
PASS = "PASS_PROPOSAL_ONLY"
REVALIDATE = "REVALIDATION_REQUIRED"
REJECT = "REJECTED"

RULE_MISMATCH = "RULE_BINDING_MISMATCH"
RULE_DEFERRED = "RULE_CLAUSE_DEFERRED"
PIT_VIOLATION = "PIT_VIOLATION"
KNOWLEDGE_CUTOFF_VIOLATION = "KNOWLEDGE_CUTOFF_VIOLATION"
TEMPORAL_ORDER_INVALID = "TEMPORAL_ORDER_INVALID"
PRIOR_NOT_EX_ANTE = "PRIOR_NOT_EX_ANTE"
REVISION_LINEAGE_MISSING = "REVISION_LINEAGE_MISSING"
DEPENDENCE_COLLISION = "DEPENDENCE_COLLAPSE_REQUIRED"
INDEPENDENCE_UNVERIFIED = "INDEPENDENCE_UNVERIFIED"
POSTERIOR_INCONSISTENT = "POSTERIOR_MATH_INCONSISTENT"
SMALL_SAMPLE_SHRINKAGE_REQUIRED = "SMALL_SAMPLE_SHRINKAGE_REQUIRED"
CANONICAL_DIGEST_MISMATCH = "CANONICAL_DIGEST_MISMATCH"
VALIDATED_AUTHORITY_FORBIDDEN = "VALIDATED_AUTHORITY_FORBIDDEN_PHASE1"
SCHEMA_REJECT = "SCHEMA_REJECT"
CALIBRATION_REQUIRED = "CALIBRATION_REQUIRED"
FORBIDDEN_AUTHORITY = "FORBIDDEN_AUTHORITY"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_packet_digest(packet: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(packet))
    numeric = payload.get("numeric_integrity")
    if isinstance(numeric, dict):
        numeric.pop("canonical_digest", None)
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def _logistic(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def expected_posterior(prior_probability: float, cumulative_log_bayes_factor: float) -> float:
    prior = float(prior_probability)
    if prior <= 0.0:
        return 0.0
    if prior >= 1.0:
        return 1.0
    return _logistic(_logit(prior) + float(cumulative_log_bayes_factor))


def _authority_false(packet: Mapping[str, Any]) -> bool:
    authority = packet.get("authority")
    return isinstance(authority, Mapping) and bool(authority) and all(
        value is False for value in authority.values()
    )


def _rule_binding_codes(identity: Mapping[str, Any], registry: Mapping[str, Any]) -> list[str]:
    compatibility = registry.get("market_rule_compatibility", {})
    bindings = compatibility.get("bindings", [])
    requested = {
        "exchange": identity.get("exchange"),
        "board": identity.get("board"),
        "security_type": identity.get("security_type"),
        "market_rule_version": identity.get("market_rule_version"),
        "market_rule_clause_state_version": identity.get("market_rule_clause_state_version"),
    }
    matched = None
    for row in bindings:
        if all(row.get(key) == value for key, value in requested.items()):
            matched = row
            break
    if matched is None:
        return [RULE_MISMATCH]
    requested_clauses = set(identity.get("rule_clause_ids") or [])
    deferred = set(matched.get("deferred_clause_ids") or [])
    return [RULE_DEFERRED] if requested_clauses & deferred else []


def _temporal_codes(packet: Mapping[str, Any]) -> list[str]:
    identity = packet["identity"]
    decision_time = _parse_time(packet["temporal_provenance"]["decision_time"])
    knowledge_cutoff = _parse_time(identity["knowledge_cutoff"])
    as_of_time = _parse_time(identity["as_of_time"])
    codes: list[str] = []

    if not (knowledge_cutoff <= as_of_time <= decision_time):
        codes.append(TEMPORAL_ORDER_INVALID)

    for evidence in packet.get("evidence", []):
        available_at = _parse_time(evidence["available_at"])
        if available_at > decision_time:
            codes.append(PIT_VIOLATION)
        if available_at > knowledge_cutoff:
            codes.append(KNOWLEDGE_CUTOFF_VIOLATION)
        revision = evidence.get("revision_provenance", {})
        if revision.get("is_revised") is True and not revision.get("supersedes_snapshot_hashes"):
            codes.append(REVISION_LINEAGE_MISSING)
    return codes


def _prior_codes(packet: Mapping[str, Any]) -> list[str]:
    prior = packet["prior"]
    cutoff = _parse_time(packet["identity"]["knowledge_cutoff"])
    window = prior["training_window"]
    start = _parse_time(window["start"])
    end = _parse_time(window["end"])
    effective_from = _parse_time(prior["effective_from"])
    if start > end or end > cutoff or effective_from > cutoff:
        return [PRIOR_NOT_EX_ANTE]
    return []


def _lineage_tokens(item: Mapping[str, Any]) -> dict[str, set[str]]:
    dep = item.get("dependence_provenance", {})
    return {
        "source_instance": {str(dep.get("source_instance_id"))}
        if dep.get("source_instance_id")
        else set(),
        "ancestry": set(map(str, dep.get("ancestry_refs") or [])),
        "feed": set(map(str, dep.get("shared_feed_group_ids") or [])),
        "feature": set(map(str, dep.get("shared_feature_group_ids") or [])),
        "training": set(map(str, dep.get("shared_training_data_group_ids") or [])),
        "model": set(map(str, dep.get("shared_model_lineage_ids") or [])),
    }


def _dependence_codes(evidence: Sequence[Mapping[str, Any]]) -> list[str]:
    admitted = [row for row in evidence if row.get("status") == "ADMITTED"]
    codes: list[str] = []
    for index, left in enumerate(admitted):
        left_tokens = _lineage_tokens(left)
        for right in admitted[index + 1 :]:
            right_tokens = _lineage_tokens(right)
            direct_ancestry = bool(
                left_tokens["source_instance"] & right_tokens["ancestry"]
                or right_tokens["source_instance"] & left_tokens["ancestry"]
                or left_tokens["ancestry"] & right_tokens["ancestry"]
            )
            shared_lineage = any(
                left_tokens[key] & right_tokens[key]
                for key in ("source_instance", "feed", "feature", "training", "model")
            )
            if direct_ancestry or shared_lineage:
                codes.append(DEPENDENCE_COLLISION)
                break
        if DEPENDENCE_COLLISION in codes:
            break

    if len(admitted) > 1 and DEPENDENCE_COLLISION not in codes:
        if any(
            row.get("dependence_provenance", {}).get("independence_status")
            != "VERIFIED_BY_CANONICAL_AUTHORITY"
            for row in admitted
        ):
            codes.append(INDEPENDENCE_UNVERIFIED)
    return codes


def _posterior_codes(packet: Mapping[str, Any], tolerance: float) -> list[str]:
    validation = packet.get("validation", {})
    update = packet.get("update", {})
    codes: list[str] = []
    if (
        validation.get("authority_state") != "UNAVAILABLE_PHASE1"
        or validation.get("packet_status") != "UNVALIDATED_PROPOSAL"
        or validation.get("validated_computation_receipt") is not None
        or update.get("belief_state") == "VALID"
    ):
        codes.append(VALIDATED_AUTHORITY_FORBIDDEN)

    expected = expected_posterior(
        update["prior_probability"], update["cumulative_log_bayes_factor"]
    )
    actual = float(update["posterior_probability"])
    if not math.isclose(expected, actual, rel_tol=0.0, abs_tol=float(tolerance)):
        codes.append(POSTERIOR_INCONSISTENT)
    return codes


def _shrinkage_codes(packet: Mapping[str, Any], registry: Mapping[str, Any]) -> list[str]:
    policy = registry.get("shrinkage", {})
    shrinkage = packet["shrinkage"]
    sample_size = float(shrinkage["effective_sample_size"])
    minimum = float(policy["minimum_effective_sample_size_for_extreme_probability"])
    threshold = float(policy["extreme_probability_threshold"])
    posterior = float(packet["update"]["posterior_probability"])
    extreme = posterior >= threshold or posterior <= (1.0 - threshold)
    if sample_size < minimum and extreme:
        return [SMALL_SAMPLE_SHRINKAGE_REQUIRED]
    return []


def _digest_codes(packet: Mapping[str, Any]) -> list[str]:
    declared = packet["numeric_integrity"]["canonical_digest"]
    return [] if declared == canonical_packet_digest(packet) else [CANONICAL_DIGEST_MISMATCH]


def validate_packet(
    packet: Mapping[str, Any],
    *,
    schema: Mapping[str, Any],
    numeric_registry: Mapping[str, Any],
) -> dict[str, Any]:
    codes: list[str] = []
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    schema_errors = sorted(
        validator.iter_errors(packet), key=lambda err: list(err.absolute_path)
    )
    if schema_errors:
        codes.append(SCHEMA_REJECT)
        return {
            "schema": VALIDATION_SCHEMA,
            "classification": REJECT,
            "codes": codes,
            "schema_error_count": len(schema_errors),
            "proposal_only": True,
            "canonical_belief_authorized": False,
            "trade_authorized": False,
        }

    codes.extend(_rule_binding_codes(packet["identity"], numeric_registry))
    codes.extend(_temporal_codes(packet))
    codes.extend(_prior_codes(packet))
    codes.extend(_dependence_codes(packet.get("evidence", [])))
    tolerance = float(numeric_registry["tolerances"]["analytic_reference_absolute_error"])
    codes.extend(_posterior_codes(packet, tolerance))
    codes.extend(_shrinkage_codes(packet, numeric_registry))
    codes.extend(_digest_codes(packet))

    if not _authority_false(packet):
        codes.append(FORBIDDEN_AUTHORITY)

    if packet.get("diagnostics", {}).get("calibration_status") == "FAIL":
        codes.append(CALIBRATION_REQUIRED)

    codes = sorted(set(codes))
    if any(
        code in codes
        for code in (
            SCHEMA_REJECT,
            POSTERIOR_INCONSISTENT,
            VALIDATED_AUTHORITY_FORBIDDEN,
            FORBIDDEN_AUTHORITY,
            TEMPORAL_ORDER_INVALID,
            PRIOR_NOT_EX_ANTE,
            CANONICAL_DIGEST_MISMATCH,
        )
    ):
        classification = REJECT
    elif codes:
        classification = REVALIDATE
    else:
        classification = PASS

    return {
        "schema": VALIDATION_SCHEMA,
        "classification": classification,
        "codes": codes,
        "schema_error_count": 0,
        "proposal_only": True,
        "canonical_belief_authorized": False,
        "trade_authorized": False,
    }
