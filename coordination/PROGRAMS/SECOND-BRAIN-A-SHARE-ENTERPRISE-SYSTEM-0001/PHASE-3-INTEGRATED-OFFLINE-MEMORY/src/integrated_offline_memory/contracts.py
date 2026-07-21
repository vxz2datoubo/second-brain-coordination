"""Adapter-only contracts; existing P1/P2 and PR #51 types remain authoritative."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Any

from local_adapter.contracts import ContractError, canonical_hash


_HEX_64 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class SourceActivationPolicy:
    policy_id: str
    manifest_id: str
    artifact_sha256: str
    license_declaration: str
    license_evidence_ref: str
    distribution_allowed: bool
    purpose: str = "LOCAL_RESEARCH_ONLY"
    authority_write: bool = False
    no_trade_gate: bool = True
    realtime_enabled: bool = False
    raw_export_allowed: bool = False
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if not self.policy_id or not self.manifest_id:
            raise ContractError("activation_identity_required")
        if not _HEX_64.fullmatch(self.artifact_sha256):
            raise ContractError("activation_sha256_invalid")
        if self.license_declaration != "LOCAL_USER_HELD_NO_REDISTRIBUTION":
            raise ContractError("activation_license_not_eligible")
        if not self.license_evidence_ref.strip():
            raise ContractError("activation_license_evidence_required")
        evidence_ref = self.license_evidence_ref.replace("\\", "/")
        if not evidence_ref.startswith("coordination/EVIDENCE/") or ".." in PurePosixPath(evidence_ref).parts:
            raise ContractError("activation_license_evidence_not_governed")
        if self.distribution_allowed:
            raise ContractError("activation_distribution_denied")
        if self.purpose != "LOCAL_RESEARCH_ONLY":
            raise ContractError("activation_purpose_not_allowed")
        if self.authority_write:
            raise ContractError("activation_authority_write_denied")
        if not self.no_trade_gate:
            raise ContractError("activation_no_trade_gate_required")
        if self.realtime_enabled:
            raise ContractError("activation_realtime_denied")
        if self.raw_export_allowed:
            raise ContractError("activation_raw_export_denied")
        if not re.fullmatch(r"1\.\d+\.\d+", self.schema_version):
            raise ContractError("activation_schema_version_unsupported")

    def digest(self) -> str:
        self.validate()
        return canonical_hash(asdict(self))


@dataclass(frozen=True)
class FieldSemanticDecision:
    field_name: str
    status: str
    interpretation: str
    authority_feature_allowed: bool
    evidence_level: str
    notes: str = ""

    def validate(self) -> None:
        if self.status not in {"VERIFIED", "PARTIAL_FIELD_EVIDENCE", "UNKNOWN"}:
            raise ContractError("invalid_field_semantic_status")
        if self.status != "VERIFIED" and self.authority_feature_allowed:
            raise ContractError("ambiguous_field_cannot_be_authoritative")


@dataclass(frozen=True)
class TdxDayRawRecord:
    record_index: int
    byte_offset: int
    trade_date: str
    date_raw: int
    open_raw: int
    high_raw: int
    low_raw: int
    close_raw: int
    open: float
    high: float
    low: float
    close: float
    amount_raw_hex: str
    amount_float32_candidate: float | None
    amount_uint32_candidate: int
    volume_vendor_raw: int
    reserved_vendor_raw: int

    def stable_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParseIssue:
    code: str
    record_index: int | None = None
    detail: str = ""
    disposition: str = "QUARANTINED"


@dataclass(frozen=True)
class ParseReport:
    schema_version: str
    status: str
    source_manifest_id: str
    activation_policy_id: str
    artifact_sha256: str
    artifact_size: int
    record_width: int
    source_record_count: int
    accepted_record_count: int
    quarantined_record_count: int
    first_date: str | None
    last_date: str | None
    duplicate_date_count: int
    out_of_order_count: int
    nonzero_reserved_count: int
    amount_float_candidate_count: int
    amount_float_invalid_count: int
    zero_volume_count: int
    parse_core_hash: str
    field_semantics_version: str
    field_decisions: tuple[FieldSemanticDecision, ...]
    issues: tuple[ParseIssue, ...] = field(default_factory=tuple)
    authority_write: bool = False
    no_trade_gate: bool = True
    raw_records_exported: bool = False

    def validate(self) -> None:
        if self.record_width != 32:
            raise ContractError("unexpected_record_width")
        if self.status not in {"PARTIALLY_VERIFIED", "EMPTY", "REJECTED"}:
            raise ContractError("parse_report_status_invalid")
        if self.authority_write or not self.no_trade_gate or self.raw_records_exported:
            raise ContractError("parse_report_boundary_violation")
        for decision in self.field_decisions:
            decision.validate()

    def public_receipt(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["field_decisions"] = [asdict(item) for item in self.field_decisions]
        payload["issues"] = [asdict(item) for item in self.issues]
        return payload


def field_semantic_decisions() -> tuple[FieldSemanticDecision, ...]:
    return (
        FieldSemanticDecision("date", "VERIFIED", "uint32_yyyymmdd", True, "ACCEPTED_PARTIAL_FIELD_EVIDENCE"),
        FieldSemanticDecision("open", "VERIFIED", "uint32_price_divisor_100", True, "ACCEPTED_PARTIAL_FIELD_EVIDENCE"),
        FieldSemanticDecision("high", "VERIFIED", "uint32_price_divisor_100", True, "ACCEPTED_PARTIAL_FIELD_EVIDENCE"),
        FieldSemanticDecision("low", "VERIFIED", "uint32_price_divisor_100", True, "ACCEPTED_PARTIAL_FIELD_EVIDENCE"),
        FieldSemanticDecision("close", "VERIFIED", "uint32_price_divisor_100", True, "ACCEPTED_PARTIAL_FIELD_EVIDENCE"),
        FieldSemanticDecision("amount", "PARTIAL_FIELD_EVIDENCE", "raw_bytes_plus_float32_and_uint32_candidates", False, "EMPIRICAL_CANDIDATE_ONLY"),
        FieldSemanticDecision("volume", "UNKNOWN", "vendor_numeric_value_unit_unknown_excluded_from_standard_volume", False, "UNIT_NOT_PROVEN"),
        FieldSemanticDecision("reserved", "UNKNOWN", "vendor_reserved_preserved", False, "NO_ACCEPTED_SEMANTIC_DEFINITION"),
        FieldSemanticDecision("suspended", "UNKNOWN", "not_present_in_day_record", False, "NO_SOURCE_FIELD"),
        FieldSemanticDecision("is_st", "UNKNOWN", "not_present_in_day_record", False, "NO_SOURCE_FIELD"),
    )


_PHASE_CONTRACT_TYPES = {
    "SourceActivationPolicy": SourceActivationPolicy,
    "FieldSemanticDecision": FieldSemanticDecision,
    "ParseIssue": ParseIssue,
    "ParseReport": ParseReport,
}


def serialize_phase_contract(value: Any) -> dict[str, Any]:
    if type(value).__name__ not in _PHASE_CONTRACT_TYPES:
        raise ContractError("unsupported_phase_contract_type")
    if hasattr(value, "validate"):
        value.validate()
    return asdict(value)


def deserialize_phase_contract(name: str, payload: dict[str, Any]) -> Any:
    target = _PHASE_CONTRACT_TYPES.get(name)
    if target is None or not isinstance(payload, dict):
        raise ContractError("unknown_phase_contract_type")
    unknown = set(payload) - set(target.__dataclass_fields__)
    if unknown:
        raise ContractError("unknown_phase_contract_field")
    version = str(payload.get("schema_version", "1.0.0"))
    if not re.fullmatch(r"1\.\d+\.\d+", version):
        raise ContractError("phase_contract_schema_version_unsupported")
    data = dict(payload)
    if name == "ParseReport":
        data["field_decisions"] = tuple(FieldSemanticDecision(**item) for item in data.get("field_decisions", ()))
        data["issues"] = tuple(ParseIssue(**item) for item in data.get("issues", ()))
    result = target(**data)
    if hasattr(result, "validate"):
        result.validate()
    return result
