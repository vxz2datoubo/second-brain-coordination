from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SOURCE_REGISTRY_SCHEMA = "SourceRegistry/v1"
EVENT_COVERAGE_REPORT_SCHEMA = "EventCoverageReport/v1"
CLAIM_EVIDENCE_LEDGER_SCHEMA = "ClaimEvidenceLedger/v1"
GATE_RESULT_SCHEMA = "EventCoverageGateResult/v1"

SOURCE_GRADES = frozenset({"A1", "A2", "B1", "B2", "C1", "C2", "D"})
SOURCE_CLASSES = frozenset(
    {
        "OFFICIAL_PRIMARY",
        "OFFICIAL_AUTHORIZED_MEDIA",
        "INSTITUTIONAL_PRIMARY",
        "PROFESSIONAL_MARKET_SOURCE",
        "MAJOR_MEDIA",
        "EXPERT_INTERPRETATION",
        "SOCIAL_OR_RUMOR",
    }
)
COVERAGE_ROLES = frozenset(
    {
        "FIRST_PARTY",
        "MARKET_WIRE",
        "COMPANY_DISCLOSURE",
        "TECHNOLOGY_RELEASE",
        "POLICY_REGULATORY",
        "OVERSEAS_PROXY",
    }
)
EVENT_TYPES = frozenset(
    {
        "DOMESTIC_TOP_LEVEL_POLICY",
        "MONETARY_POLICY",
        "FISCAL_POLICY",
        "REGULATORY_POLICY",
        "INDUSTRIAL_POLICY",
        "MACRO_DATA",
        "COMPANY_EVENT",
        "TECHNOLOGY_EVENT",
        "GEOPOLITICAL_EVENT",
        "GLOBAL_MACRO_POLICY",
        "COMMODITY_ENERGY",
        "FINANCIAL_STABILITY",
        "RUMOR_AND_LEAK",
    }
)
CLAIM_TYPES = frozenset(
    {"OBSERVED_FACT", "SOURCE_CLAIM", "MODEL_INFERENCE", "CAUSAL_HYPOTHESIS", "UNKNOWN"}
)
DATA_GRADES = frozenset({"A", "B", "C"})
DISPOSITIONS = frozenset(
    {"READY_FOR_SYNTHESIS", "EVENT_COVERAGE_INCOMPLETE", "PRICE_ANOMALY_UNRESOLVED", "ABSTAIN"}
)

MANDATORY_ROLES = {
    "MARKET_ATTRIBUTION": frozenset(
        {"FIRST_PARTY", "MARKET_WIRE", "COMPANY_DISCLOSURE", "TECHNOLOGY_RELEASE", "POLICY_REGULATORY"}
    ),
    "PORTFOLIO_LATEST": frozenset(
        {
            "FIRST_PARTY",
            "MARKET_WIRE",
            "COMPANY_DISCLOSURE",
            "TECHNOLOGY_RELEASE",
            "POLICY_REGULATORY",
            "OVERSEAS_PROXY",
        }
    ),
}

# R166 does not create these authorities. These constants are deliberately false and
# are used mechanically by tests and output construction.
CANONICAL_SOURCE_INSTANCE_AUTHORITY_AVAILABLE = False
TYPED_CAUSAL_AUTHORITY_AVAILABLE = False
TYPED_PARTICIPANT_INTENT_AUTHORITY_AVAILABLE = False
TYPED_FREE_TEXT_SEMANTIC_AUTHORITY_AVAILABLE = False
SOURCE_AUTHORITY_STATE = "CANONICAL_SOURCE_INSTANCE_AUTHORITY_UNAVAILABLE"

AUTHORITY = {
    "creates_task": False,
    "creates_route": False,
    "creates_work_claim": False,
    "grants_execution": False,
    "grants_write": False,
    "grants_review_accept": False,
    "grants_merge": False,
    "grants_release": False,
    "grants_domain_write": False,
    "grants_w3_write": False,
    "grants_trading": False,
    "expands_permissions": False,
    "accesses_secrets": False,
}

_MICROSTRUCTURE_STRONG = re.compile(
    r"(?:\bCVD\b|\bDelta\b|footprint|absorption|订单簿|order[- ]?book|盘口意图|主动买卖)",
    re.IGNORECASE,
)
_PARTICIPANT_INTENT_LITERAL = re.compile(r"(?:主力|吸筹|洗盘|出货|庄家|机构意图)", re.IGNORECASE)
_UNIQUE_CAUSAL = re.compile(r"(?:唯一原因|就是因为|主要因为|唯一因果)", re.IGNORECASE)
_SUPPLY_DEMAND_NARRATIVE = re.compile(r"(?:抛压|卖压|承接|买盘|供给很强)", re.IGNORECASE)
_FORBIDDEN_CALLER_AUTHORITY_FIELDS = frozenset(
    {"causal_identification_evidence", "participant_intent_evidence"}
)


class EventCoverageError(ValueError):
    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value))


def _nonempty(value: Any, code: str, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EventCoverageError(code, path)
    return value.strip()


def _string_list(value: Any, code: str, path: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise EventCoverageError(code, path)
    if len(value) != len(set(value)):
        raise EventCoverageError(f"{code}_DUPLICATE", path)
    return list(value)


def _parse_time(value: Any, code: str, path: str) -> datetime:
    text = _nonempty(value, code, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventCoverageError(code, path) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EventCoverageError(f"{code}_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def _time_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_source_registry(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize caller-supplied source metadata as evidence-only candidate data.

    Validation proves shape, not authority. No caller field in this object may satisfy
    canonical W5 source coverage while the canonical source-instance authority is absent.
    """
    if not isinstance(value, Mapping):
        raise EventCoverageError("SOURCE_REGISTRY_NOT_OBJECT")
    if set(value) != {"schema_version", "sources"}:
        raise EventCoverageError("SOURCE_REGISTRY_FIELDS_INVALID")
    if value.get("schema_version") != SOURCE_REGISTRY_SCHEMA:
        raise EventCoverageError("SOURCE_REGISTRY_SCHEMA_INVALID")

    raw_sources = value.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise EventCoverageError("SOURCE_REGISTRY_EMPTY", "/sources")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    required = {"source_id", "source_class", "source_grade", "coverage_roles", "enabled"}

    for index, raw in enumerate(raw_sources):
        path = f"/sources/{index}"
        if not isinstance(raw, Mapping):
            raise EventCoverageError("SOURCE_NOT_OBJECT", path)
        if set(raw) != required:
            raise EventCoverageError("SOURCE_FIELDS_INVALID", path)

        source_id = _nonempty(raw.get("source_id"), "SOURCE_ID_INVALID", f"{path}/source_id")
        if source_id in seen_ids:
            raise EventCoverageError("SOURCE_ID_DUPLICATE", f"{path}/source_id")
        seen_ids.add(source_id)

        source_class = raw.get("source_class")
        source_grade = raw.get("source_grade")
        if source_class not in SOURCE_CLASSES:
            raise EventCoverageError("SOURCE_CLASS_INVALID", f"{path}/source_class")
        if source_grade not in SOURCE_GRADES:
            raise EventCoverageError("SOURCE_GRADE_INVALID", f"{path}/source_grade")

        roles = _string_list(raw.get("coverage_roles"), "COVERAGE_ROLES_INVALID", f"{path}/coverage_roles")
        if not roles or any(role not in COVERAGE_ROLES for role in roles):
            raise EventCoverageError("COVERAGE_ROLE_INVALID", f"{path}/coverage_roles")
        if not isinstance(raw.get("enabled"), bool):
            raise EventCoverageError("SOURCE_ENABLED_INVALID", f"{path}/enabled")

        normalized.append(
            {
                "source_id": source_id,
                "source_class": source_class,
                "source_grade": source_grade,
                "coverage_roles": sorted(roles),
                "enabled": raw["enabled"],
            }
        )

    result = {
        "schema_version": SOURCE_REGISTRY_SCHEMA,
        "sources": sorted(normalized, key=lambda item: item["source_id"]),
        "trust_class": "CALLER_CANDIDATE_EVIDENCE_ONLY",
        "authority": _copy(AUTHORITY),
    }
    result["registry_digest"] = _digest(result)
    return result


def _validate_intent(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EventCoverageError("INTENT_NOT_OBJECT")

    required = {
        "intent_class",
        "target_symbols",
        "proxy_symbols",
        "previous_close_at",
        "anomaly_or_query_at",
        "data_grade",
        "price_anomaly_unexplained",
    }
    if set(value) != required:
        raise EventCoverageError("INTENT_FIELDS_INVALID")

    intent_class = value.get("intent_class")
    if intent_class not in MANDATORY_ROLES:
        raise EventCoverageError("INTENT_CLASS_INVALID", "/intent_class")

    target_symbols = _string_list(value.get("target_symbols"), "TARGET_SYMBOLS_INVALID", "/target_symbols")
    if not target_symbols:
        raise EventCoverageError("TARGET_SYMBOLS_EMPTY", "/target_symbols")

    proxy_symbols = _string_list(value.get("proxy_symbols"), "PROXY_SYMBOLS_INVALID", "/proxy_symbols")
    if intent_class == "PORTFOLIO_LATEST" and not proxy_symbols:
        raise EventCoverageError("PORTFOLIO_PROXY_SYMBOLS_REQUIRED", "/proxy_symbols")

    query_at = _parse_time(value.get("anomaly_or_query_at"), "QUERY_TIME_INVALID", "/anomaly_or_query_at")
    previous_close_raw = value.get("previous_close_at")
    if intent_class == "MARKET_ATTRIBUTION":
        previous_close = _parse_time(previous_close_raw, "PREVIOUS_CLOSE_INVALID", "/previous_close_at")
        if previous_close > query_at:
            raise EventCoverageError("PREVIOUS_CLOSE_AFTER_QUERY", "/previous_close_at")
    else:
        if previous_close_raw is not None:
            _parse_time(previous_close_raw, "PREVIOUS_CLOSE_INVALID", "/previous_close_at")
        previous_close = query_at - timedelta(hours=24)

    data_grade = value.get("data_grade")
    if data_grade not in DATA_GRADES:
        raise EventCoverageError("DATA_GRADE_INVALID", "/data_grade")
    if not isinstance(value.get("price_anomaly_unexplained"), bool):
        raise EventCoverageError("PRICE_ANOMALY_FLAG_INVALID", "/price_anomaly_unexplained")

    return {
        "intent_class": intent_class,
        "target_symbols": target_symbols,
        "proxy_symbols": proxy_symbols,
        "window_start": previous_close,
        "query_at": query_at,
        "data_grade": data_grade,
        "price_anomaly_unexplained": value["price_anomaly_unexplained"],
    }


def _validate_events(
    events: Sequence[Mapping[str, Any]], candidate_registry: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        raise EventCoverageError("EVENTS_NOT_SEQUENCE")

    candidate_sources = {item["source_id"]: item for item in candidate_registry["sources"]}
    required = {
        "event_id",
        "event_type",
        "source_id",
        "source_chain_id",
        "available_at",
        "market_effective_at",
        "target_symbols",
        "proxy_symbols",
        "mechanism",
        "evidence_refs",
    }
    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for index, raw in enumerate(events):
        path = f"/events/{index}"
        if not isinstance(raw, Mapping) or set(raw) != required:
            raise EventCoverageError("EVENT_FIELDS_INVALID", path)

        event_id = _nonempty(raw.get("event_id"), "EVENT_ID_INVALID", f"{path}/event_id")
        if event_id in seen_ids:
            raise EventCoverageError("EVENT_ID_DUPLICATE", f"{path}/event_id")
        seen_ids.add(event_id)

        event_type = raw.get("event_type")
        if event_type not in EVENT_TYPES:
            raise EventCoverageError("EVENT_TYPE_INVALID", f"{path}/event_type")

        source_id = _nonempty(raw.get("source_id"), "EVENT_SOURCE_INVALID", f"{path}/source_id")
        source = candidate_sources.get(source_id)
        if source is None or not source["enabled"]:
            raise EventCoverageError("EVENT_SOURCE_NOT_IN_CALLER_CANDIDATE_SET", f"{path}/source_id")

        available_at = _parse_time(raw.get("available_at"), "AVAILABLE_AT_INVALID", f"{path}/available_at")
        market_effective_at = _parse_time(
            raw.get("market_effective_at"), "MARKET_EFFECTIVE_AT_INVALID", f"{path}/market_effective_at"
        )
        if market_effective_at < available_at:
            raise EventCoverageError("MARKET_EFFECTIVE_BEFORE_AVAILABLE", f"{path}/market_effective_at")

        evidence_refs = _string_list(
            raw.get("evidence_refs"), "EVENT_EVIDENCE_REFS_INVALID", f"{path}/evidence_refs"
        )
        if not evidence_refs:
            raise EventCoverageError("EVENT_EVIDENCE_REFS_EMPTY", f"{path}/evidence_refs")

        normalized.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "source_id": source_id,
                "source_chain_id": _nonempty(
                    raw.get("source_chain_id"), "SOURCE_CHAIN_INVALID", f"{path}/source_chain_id"
                ),
                "available_at": available_at,
                "market_effective_at": market_effective_at,
                "target_symbols": _string_list(
                    raw.get("target_symbols"), "EVENT_TARGETS_INVALID", f"{path}/target_symbols"
                ),
                "proxy_symbols": _string_list(
                    raw.get("proxy_symbols"), "EVENT_PROXIES_INVALID", f"{path}/proxy_symbols"
                ),
                "mechanism": _nonempty(
                    raw.get("mechanism"), "EVENT_MECHANISM_INVALID", f"{path}/mechanism"
                ),
                "evidence_refs": evidence_refs,
            }
        )

    return normalized


def _build_coverage_report(
    *,
    intent: Mapping[str, Any],
    registry: Mapping[str, Any],
    scanned_source_ids: Sequence[str],
    scanned_proxy_symbols: Sequence[str],
    events: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    normalized_intent = _validate_intent(intent)
    candidate_registry = validate_source_registry(registry)
    normalized_events = _validate_events(events, candidate_registry)

    candidate_source_ids = {
        item["source_id"] for item in candidate_registry["sources"] if item["enabled"]
    }
    scanned_sources = _string_list(
        list(scanned_source_ids), "SCANNED_SOURCE_IDS_INVALID", "/scanned_source_ids"
    )
    if any(source_id not in candidate_source_ids for source_id in scanned_sources):
        raise EventCoverageError(
            "SCANNED_SOURCE_NOT_IN_CALLER_CANDIDATE_SET", "/scanned_source_ids"
        )
    scanned_proxies = _string_list(
        list(scanned_proxy_symbols), "SCANNED_PROXY_SYMBOLS_INVALID", "/scanned_proxy_symbols"
    )

    required_roles = set(MANDATORY_ROLES[normalized_intent["intent_class"]])
    # Caller metadata cannot establish canonical source coverage. Until a separately
    # governed instance authority exists, observed canonical roles remain empty.
    observed_roles: set[str] = set()
    unresolved_roles = sorted(required_roles)

    required_proxies = (
        set(normalized_intent["proxy_symbols"])
        if normalized_intent["intent_class"] == "PORTFOLIO_LATEST"
        else set()
    )
    unresolved_proxies = sorted(required_proxies - set(scanned_proxies))

    targets = set(normalized_intent["target_symbols"])
    proxies = set(normalized_intent["proxy_symbols"])
    window_start = normalized_intent["window_start"]
    query_at = normalized_intent["query_at"]

    point_in_time_candidates: list[dict[str, Any]] = []
    future_ids: list[str] = []
    outside_window_ids: list[str] = []
    irrelevant_ids: list[str] = []

    for event in normalized_events:
        if event["available_at"] > query_at:
            future_ids.append(event["event_id"])
            continue
        if event["available_at"] < window_start:
            outside_window_ids.append(event["event_id"])
            continue
        if not (
            targets.intersection(event["target_symbols"])
            or proxies.intersection(event["proxy_symbols"])
        ):
            irrelevant_ids.append(event["event_id"])
            continue
        point_in_time_candidates.append(event)

    # One candidate per caller-provided source chain. The chain label is candidate
    # grouping/dedup evidence only; it cannot attest source independence or trust.
    chain_choice: dict[str, dict[str, Any]] = {}
    for event in sorted(
        point_in_time_candidates,
        key=lambda item: (item["available_at"], item["event_id"]),
    ):
        chain_choice.setdefault(event["source_chain_id"], event)

    candidate_ids = [event["event_id"] for event in chain_choice.values()]

    report = {
        "schema_version": EVENT_COVERAGE_REPORT_SCHEMA,
        "intent_class": normalized_intent["intent_class"],
        "target_symbols": sorted(normalized_intent["target_symbols"]),
        "proxy_symbols": sorted(normalized_intent["proxy_symbols"]),
        "window_start": _time_text(window_start),
        "anomaly_or_query_at": _time_text(query_at),
        "source_authority_state": SOURCE_AUTHORITY_STATE,
        "required_coverage_roles": sorted(required_roles),
        "observed_coverage_roles": sorted(observed_roles),
        "scanned_source_ids": sorted(scanned_sources),
        "scanned_proxy_symbols": sorted(scanned_proxies),
        "unresolved_source_gaps": unresolved_roles,
        "unresolved_proxy_gaps": unresolved_proxies,
        "candidate_event_ids": candidate_ids,
        "candidate_source_chain_count": len(chain_choice),
        "future_event_ids_ignored": sorted(future_ids),
        "outside_window_event_ids_ignored": sorted(outside_window_ids),
        "irrelevant_event_ids_ignored": sorted(irrelevant_ids),
        "event_backfill_required": bool(
            normalized_intent["price_anomaly_unexplained"] and not candidate_ids
        ),
        "coverage_grade": "INCOMPLETE",
        "disposition": "EVENT_COVERAGE_INCOMPLETE",
        "authority": _copy(AUTHORITY),
    }
    report["report_digest"] = _digest(report)
    return report, {event["event_id"]: event for event in normalized_events}


def _validate_claims(claims: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        raise EventCoverageError("CLAIMS_NOT_SEQUENCE")

    required = {"claim_id", "claim_type", "text", "evidence_event_ids", "evidence_refs"}
    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for index, raw in enumerate(claims):
        path = f"/claims/{index}"
        if not isinstance(raw, Mapping):
            raise EventCoverageError("CLAIM_NOT_OBJECT", path)

        forbidden = set(raw).intersection(_FORBIDDEN_CALLER_AUTHORITY_FIELDS)
        if forbidden:
            raise EventCoverageError(
                "CALLER_CLAIM_AUTHORITY_FLAG_FORBIDDEN", f"{path}/{sorted(forbidden)[0]}"
            )
        if set(raw) != required:
            raise EventCoverageError("CLAIM_FIELDS_INVALID", path)

        claim_id = _nonempty(raw.get("claim_id"), "CLAIM_ID_INVALID", f"{path}/claim_id")
        if claim_id in seen_ids:
            raise EventCoverageError("CLAIM_ID_DUPLICATE", f"{path}/claim_id")
        seen_ids.add(claim_id)

        claim_type = raw.get("claim_type")
        if claim_type not in CLAIM_TYPES:
            raise EventCoverageError("CLAIM_TYPE_INVALID", f"{path}/claim_type")

        normalized.append(
            {
                "claim_id": claim_id,
                "claim_type": claim_type,
                "text": _nonempty(raw.get("text"), "CLAIM_TEXT_INVALID", f"{path}/text"),
                "evidence_event_ids": _string_list(
                    raw.get("evidence_event_ids"),
                    "CLAIM_EVENT_EVIDENCE_INVALID",
                    f"{path}/evidence_event_ids",
                ),
                "evidence_refs": _string_list(
                    raw.get("evidence_refs"),
                    "CLAIM_EVIDENCE_REFS_INVALID",
                    f"{path}/evidence_refs",
                ),
            }
        )

    return normalized


def _build_claim_ledger(
    *,
    claims: Sequence[Mapping[str, Any]],
    report: Mapping[str, Any],
    event_by_id: Mapping[str, Mapping[str, Any]],
    data_grade: str,
) -> dict[str, Any]:
    normalized_claims = _validate_claims(claims)
    point_in_time_candidate_ids = set(report["candidate_event_ids"])
    rows: list[dict[str, Any]] = []
    any_block = False
    any_downgrade = False

    for claim in normalized_claims:
        outcome = "ALLOW"
        reasons: list[str] = []
        text = claim["text"]
        referenced = set(claim["evidence_event_ids"])
        rejected_event_ids = sorted(
            event_id for event_id in referenced if event_id not in point_in_time_candidate_ids
        )

        if rejected_event_ids:
            outcome = "BLOCK"
            reasons.append("EVIDENCE_NOT_POINT_IN_TIME_RELEVANT_OR_DEDUPLICATED")

        if _UNIQUE_CAUSAL.search(text):
            outcome = "BLOCK"
            reasons.append("CANONICAL_CAUSAL_IDENTIFICATION_AUTHORITY_UNAVAILABLE")

        if claim["claim_type"] == "CAUSAL_HYPOTHESIS" and report["disposition"] != "READY_FOR_SYNTHESIS":
            outcome = "BLOCK"
            reasons.append("CAUSAL_CLAIM_BEFORE_COVERAGE_READY")

        if _MICROSTRUCTURE_STRONG.search(text) and data_grade != "A":
            outcome = "BLOCK"
            reasons.append("MICROSTRUCTURE_TERM_EXCEEDS_DATA_GRADE")

        if _PARTICIPANT_INTENT_LITERAL.search(text):
            outcome = "BLOCK"
            reasons.append("CANONICAL_PARTICIPANT_INTENT_AUTHORITY_UNAVAILABLE")

        # Two independent fail-closed reasons cap all other free text at DOWNGRADE:
        # the source instances are not canonically trusted, and no typed semantic
        # classifier/evidence authority exists. Caller claim_type is intentionally
        # irrelevant to this trust decision.
        if outcome != "BLOCK" and not CANONICAL_SOURCE_INSTANCE_AUTHORITY_AVAILABLE:
            outcome = "DOWNGRADE"
            reasons.append("CANONICAL_SOURCE_INSTANCE_AUTHORITY_UNAVAILABLE")

        if outcome != "BLOCK" and not TYPED_FREE_TEXT_SEMANTIC_AUTHORITY_AVAILABLE:
            outcome = "DOWNGRADE"
            reasons.append("UNTYPED_FREE_TEXT_SEMANTICS_UNVERIFIED")

        if _SUPPLY_DEMAND_NARRATIVE.search(text) and data_grade == "C" and outcome != "BLOCK":
            outcome = "DOWNGRADE"
            reasons.append("SUPPLY_DEMAND_LANGUAGE_REQUIRES_PRICE_BEHAVIOR_DOWNGRADE")

        if claim["claim_type"] in {"SOURCE_CLAIM", "CAUSAL_HYPOTHESIS"} and not (
            claim["evidence_event_ids"] or claim["evidence_refs"]
        ):
            if outcome != "BLOCK":
                outcome = "DOWNGRADE"
            reasons.append("EVIDENCE_REFS_MISSING")

        source_chain_ids = sorted(
            {
                str(event_by_id[event_id]["source_chain_id"])
                for event_id in referenced
                if event_id in point_in_time_candidate_ids and event_id in event_by_id
            }
        )

        any_block = any_block or outcome == "BLOCK"
        any_downgrade = any_downgrade or outcome == "DOWNGRADE"
        rows.append(
            {
                "claim_id": claim["claim_id"],
                "claim_type": claim["claim_type"],
                "outcome": outcome,
                "reason_codes": sorted(set(reasons)),
                "eligible_evidence_event_ids": sorted(
                    referenced.intersection(point_in_time_candidate_ids)
                ),
                "rejected_evidence_event_ids": rejected_event_ids,
                "candidate_source_chain_ids": source_chain_ids,
            }
        )

    if any_block:
        disposition = "ABSTAIN"
    elif report["disposition"] != "READY_FOR_SYNTHESIS":
        disposition = report["disposition"]
    else:
        disposition = "READY_FOR_SYNTHESIS"

    ledger = {
        "schema_version": CLAIM_EVIDENCE_LEDGER_SCHEMA,
        "coverage_report_digest": report["report_digest"],
        "data_grade": data_grade,
        "claims": rows,
        "has_blocking_claim": any_block,
        "has_downgrade_claim": any_downgrade,
        "disposition": disposition,
        "authority": _copy(AUTHORITY),
    }
    ledger["ledger_digest"] = _digest(ledger)
    return ledger


def run_event_coverage_gate(
    *,
    intent: Mapping[str, Any],
    source_registry: Mapping[str, Any],
    scanned_source_ids: Sequence[str],
    scanned_proxy_symbols: Sequence[str],
    events: Sequence[Mapping[str, Any]],
    claims: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Run the bounded deterministic W5 P0-VS1 pre-synthesis gate.

    This function does not create source, causal, participant, task, route, write,
    review, merge, knowledge, domain or trading authority. In the current R166 slice
    source-instance authority and typed free-text semantic authority are deliberately
    unavailable, so caller metadata and prose can never manufacture READY/ALLOW truth.
    """
    normalized_intent = _validate_intent(intent)
    report, event_by_id = _build_coverage_report(
        intent=intent,
        registry=source_registry,
        scanned_source_ids=scanned_source_ids,
        scanned_proxy_symbols=scanned_proxy_symbols,
        events=events,
    )
    ledger = _build_claim_ledger(
        claims=claims,
        report=report,
        event_by_id=event_by_id,
        data_grade=normalized_intent["data_grade"],
    )

    disposition = ledger["disposition"]
    if disposition not in DISPOSITIONS:
        raise EventCoverageError("INTERNAL_DISPOSITION_INVALID")

    result = {
        "schema_version": GATE_RESULT_SCHEMA,
        "event_coverage_report": report,
        "claim_evidence_ledger": ledger,
        "disposition": disposition,
        "authority": _copy(AUTHORITY),
    }
    result["result_digest"] = _digest(result)
    return result


__all__ = [
    "AUTHORITY",
    "CANONICAL_SOURCE_INSTANCE_AUTHORITY_AVAILABLE",
    "CLAIM_EVIDENCE_LEDGER_SCHEMA",
    "DATA_GRADES",
    "DISPOSITIONS",
    "EVENT_COVERAGE_REPORT_SCHEMA",
    "EventCoverageError",
    "GATE_RESULT_SCHEMA",
    "MANDATORY_ROLES",
    "SOURCE_AUTHORITY_STATE",
    "SOURCE_REGISTRY_SCHEMA",
    "TYPED_FREE_TEXT_SEMANTIC_AUTHORITY_AVAILABLE",
    "run_event_coverage_gate",
    "validate_source_registry",
]
