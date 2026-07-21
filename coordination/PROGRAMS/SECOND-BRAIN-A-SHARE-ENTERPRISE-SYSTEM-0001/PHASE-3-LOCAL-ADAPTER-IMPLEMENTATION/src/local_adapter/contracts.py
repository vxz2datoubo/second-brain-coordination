"""Contract-only adapters. They do not contact services, brokers, or real data sources."""

from __future__ import annotations

import abc
import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class ContractError(ValueError):
    """Raised for a deterministic, public-safe contract violation."""


class AdapterStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    PAYLOAD_SAMPLE_ONLY = "PAYLOAD_SAMPLE_ONLY"
    LEGACY_UNKNOWN = "LEGACY_UNKNOWN"
    REJECTED = "REJECTED"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"


_CAPABILITIES = {"HISTORICAL_BAR", "FIVE_LEVEL_SNAPSHOT", "TEN_LEVEL_SNAPSHOT", "L2_AGGREGATE"}
_CONTENT_CLASSES = {"PUBLIC_SAFE_SYNTHETIC", "PRIVATE_LOCAL_ONLY", "LICENSED_LOCAL", "PUBLIC_SAFE_REFERENCE"}
_LICENSE_STATUSES = {"DECLARED", "LICENSED", "UNKNOWN", "UNDECLARED", "CONFLICT"}
_SOURCE_CLASSES = {"synthetic", "historical_verified", "payload_sample_only", "legacy_unknown"}
_REAL_SECRET_VALUE = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
_CREDENTIAL_VALUE_FIELDS = {"credential_value", "secret_value", "access_token_value", "api_key_value", "password_value", "private_key_value"}


def canonical_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ContractError("invalid_timestamp") from error
    if result.tzinfo is None:
        raise ContractError("timezone_required")
    return result.astimezone(timezone.utc)


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _contains_actual_secret_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_REAL_SECRET_VALUE.search(value))
    if isinstance(value, list):
        return any(_contains_actual_secret_value(item) for item in value)
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = _normalize(str(key)).replace(" ", "_")
            if normalized_key in _CREDENTIAL_VALUE_FIELDS and item not in (None, ""):
                return True
            if _contains_actual_secret_value(item):
                return True
    return False


def _relevant(query: str, content: str) -> bool:
    """Deterministic normalized substring match with a Chinese bigram fallback."""
    query, content = _normalize(query), _normalize(content)
    if not query or not content:
        return False
    if query in content:
        return True
    q_terms = {term for term in query.split() if len(term) >= 2}
    c_terms = set(content.split())
    if q_terms.intersection(c_terms):
        return True
    def grams(value: str) -> set[str]:
        compact = "".join(char for char in value if "\u4e00" <= char <= "\u9fff")
        return {compact[index:index + 2] for index in range(max(0, len(compact) - 1))}
    return bool(grams(query).intersection(grams(content)))


@dataclass(frozen=True)
class LocalArtifactReference:
    reference_id: str
    local_location_hint: str
    sha256: str
    content_class: str = "PUBLIC_SAFE_SYNTHETIC"
    license_status: str = "DECLARED"
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if not self.reference_id or not self.local_location_hint or not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ContractError("invalid_local_artifact_reference")
        if self.content_class not in _CONTENT_CLASSES:
            raise ContractError("invalid_content_class")
        if self.license_status not in _LICENSE_STATUSES:
            raise ContractError("invalid_license_status")
        _require_v1(self.schema_version)


@dataclass(frozen=True)
class CredentialReference:
    reference_id: str
    purpose: str
    owning_system: str
    updated_at: str
    verification_digest: str
    local_location_hint: str
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if not all((self.reference_id, self.purpose, self.owning_system, self.verification_digest, self.local_location_hint)):
            raise ContractError("credential_reference_incomplete")
        _parse_time(self.updated_at)
        if not re.fullmatch(r"[0-9a-f]{16,64}", self.verification_digest):
            raise ContractError("credential_digest_invalid")
        _require_v1(self.schema_version)


@dataclass(frozen=True)
class AdapterCapability:
    capability_id: str
    capability_level: str
    entitlement_status: str
    provider_semantics: str
    source_sequence_supported: bool = False
    exchange_time_supported: bool = False
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if not self.capability_id or self.capability_level not in _CAPABILITIES:
            raise ContractError("invalid_capability")
        if self.entitlement_status not in {"confirmed", "unknown", "not_entitled"}:
            raise ContractError("invalid_entitlement_status")
        if self.capability_level == "L2_AGGREGATE" and self.provider_semantics in {"RAW_TRADE_TICK", "RAW_ORDER_EVENT", "ORDER_QUEUE", "AUCTION_TRAJECTORY"}:
            raise ContractError("l2_aggregate_cannot_promote_to_raw_event")
        _require_v1(self.schema_version)


@dataclass(frozen=True)
class SourceManifest:
    manifest_id: str
    source_id: str
    source_class: str
    artifact: LocalArtifactReference
    license: str
    privacy_class: str
    timezone: str
    time_semantics: str
    available_at: str
    adjusted: bool
    adjustment_method: str
    suspension_policy: str
    st_policy: str
    limit_rule_version: str
    corporate_action_policy: str
    capability: AdapterCapability
    schema_version: str = "1.0.0"
    synthetic: bool = True
    field_semantics_version: str = "1.0.0"


@dataclass(frozen=True)
class AdapterResult:
    status: AdapterStatus
    reason_codes: tuple[str, ...] = ()
    remediation_hints: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    authority_write: bool = False
    no_trade_gate: bool = True
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if self.authority_write:
            raise ContractError("adapter_result_cannot_write_authority")
        if not self.no_trade_gate:
            raise ContractError("no_trade_gate_required")
        _require_v1(self.schema_version)


class ManifestValidator:
    """Cross-field gate. Missing evidence returns a status; unsafe semantics are rejected."""

    def validate(self, manifest: SourceManifest, requested_as_of: str) -> AdapterResult:
        try:
            manifest.artifact.validate()
            manifest.capability.validate()
            _require_v1(manifest.schema_version)
            if manifest.source_class not in _SOURCE_CLASSES:
                return self._result(AdapterStatus.REJECTED, "invalid_source_class", "declare a supported source class")
            if not manifest.manifest_id or not manifest.source_id or not manifest.license:
                return self._result(AdapterStatus.LEGACY_UNKNOWN, "missing_identity_or_license", "supply source and license manifest")
            if manifest.license.upper() in {"UNKNOWN", "UNDECLARED"} or manifest.artifact.license_status in {"UNKNOWN", "UNDECLARED"}:
                return self._result(AdapterStatus.LEGACY_UNKNOWN, "license_unknown_or_undeclared", "supply a declared license and artifact license status")
            if manifest.artifact.license_status == "CONFLICT":
                return self._result(AdapterStatus.PARTIALLY_VERIFIED, "license_status_conflict", "resolve source and artifact license conflict")
            if manifest.privacy_class not in {"PUBLIC_SAFE", "PRIVATE_LOCAL_ONLY"}:
                return self._result(AdapterStatus.REJECTED, "invalid_privacy_class", "declare privacy class")
            if manifest.timezone not in {"UTC", "Asia/Shanghai"}:
                return self._result(AdapterStatus.REJECTED, "unsupported_timezone", "declare UTC or Asia/Shanghai")
            if manifest.time_semantics not in {"EVENT_TIME", "END_OF_BAR", "UNKNOWN"}:
                return self._result(AdapterStatus.REJECTED, "invalid_time_semantics", "declare a supported time semantic")
            if manifest.time_semantics == "UNKNOWN":
                return self._result(AdapterStatus.PAYLOAD_SAMPLE_ONLY, "time_semantics_unknown", "document event/bar availability semantics")
            if _parse_time(manifest.available_at) > _parse_time(requested_as_of):
                return self._result(AdapterStatus.REJECTED, "future_available_at", "use point-in-time available data")
            if manifest.adjusted and manifest.adjustment_method in {"", "none", "UNKNOWN"}:
                return self._result(AdapterStatus.REJECTED, "undeclared_adjustment", "declare adjustment method")
            policies = (manifest.suspension_policy, manifest.st_policy, manifest.limit_rule_version, manifest.corporate_action_policy)
            if any(value in {"", "UNKNOWN"} for value in policies):
                return self._result(AdapterStatus.PARTIALLY_VERIFIED, "ashare_policy_incomplete", "supply suspension/ST/limit/corporate-action policy")
            if not manifest.synthetic:
                return self._result(AdapterStatus.BLOCKED_BY_POLICY, "real_source_binding_not_activated", "wait for accepted WorkBuddy evidence and later activation")
            if manifest.artifact.content_class != "PUBLIC_SAFE_SYNTHETIC":
                return self._result(AdapterStatus.REJECTED, "synthetic_content_class_mismatch", "use PUBLIC_SAFE_SYNTHETIC only for synthetic artifacts")
            if manifest.capability.entitlement_status != "confirmed":
                return self._result(AdapterStatus.PARTIALLY_VERIFIED, "entitlement_not_confirmed", "obtain entitlement evidence")
            return self._result(AdapterStatus.VERIFIED, payload={"manifest_hash": canonical_hash(asdict(manifest))})
        except ContractError as error:
            return self._result(AdapterStatus.REJECTED, str(error), "correct contract fields")

    @staticmethod
    def _result(status: AdapterStatus, *codes: str, payload: dict[str, Any] | None = None) -> AdapterResult:
        reasons = (codes[0],) if codes else ()
        hints = (codes[1],) if len(codes) > 1 else ()
        return AdapterResult(status, reasons, hints, payload or {})


class OfflineDatasetAdapter(abc.ABC):
    @abc.abstractmethod
    def load(self, manifest: SourceManifest, requested_as_of: str) -> AdapterResult: ...


class KnowledgeGatewayAdapter(abc.ABC):
    @abc.abstractmethod
    def query(self, text: str, budget: int) -> AdapterResult: ...


class LearningPacketAdapter(abc.ABC):
    @abc.abstractmethod
    def emit(self, packet: dict[str, Any]) -> AdapterResult: ...


class CapabilityProbeAdapter(abc.ABC):
    @abc.abstractmethod
    def probe(self, capability: AdapterCapability) -> AdapterResult: ...


class SyntheticOfflineDatasetAdapter(OfflineDatasetAdapter):
    """Reads only synthetic CSV/JSON/JSONL fixtures and produces a deterministic projection."""

    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path = artifact_path

    def load(self, manifest: SourceManifest, requested_as_of: str) -> AdapterResult:
        gate = ManifestValidator().validate(manifest, requested_as_of)
        if gate.status is not AdapterStatus.VERIFIED:
            return gate
        if not self.artifact_path.exists():
            return AdapterResult(AdapterStatus.REJECTED, ("synthetic_fixture_not_found",))
        text = self.artifact_path.read_text(encoding="utf-8")
        actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual_hash != manifest.artifact.sha256:
            return AdapterResult(AdapterStatus.REJECTED, ("artifact_hash_mismatch",))
        try:
            rows = self._rows(text)
        except (ValueError, json.JSONDecodeError) as error:
            return AdapterResult(AdapterStatus.REJECTED, ("parse_error", str(error)))
        return AdapterResult(AdapterStatus.VERIFIED, payload={"records": rows, "record_count": len(rows), "core_hash": canonical_hash(rows), "source_class": "synthetic"})

    def _rows(self, text: str) -> list[dict[str, Any]]:
        suffix = self.artifact_path.suffix.lower()
        if suffix == ".csv":
            return list(csv.DictReader(text.splitlines()))
        if suffix == ".jsonl":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        if suffix == ".json":
            data = json.loads(text)
            return data["records"] if isinstance(data, dict) else data
        raise ValueError("unsupported_synthetic_format")


class InMemoryKnowledgeGateway(KnowledgeGatewayAdapter):
    def __init__(self, atoms: Iterable[dict[str, Any]], revision: str = "synthetic-r1") -> None:
        self.atoms = list(atoms)
        self.revision = revision

    def query(self, text: str, budget: int) -> AdapterResult:
        if budget < 1:
            return AdapterResult(AdapterStatus.REJECTED, ("invalid_context_budget",))
        chosen, omitted, used = [], [], 0
        for atom in sorted(self.atoms, key=lambda item: str(item.get("atom_id", ""))):
            if atom.get("status") not in {"candidate", "approved", "conflict", "superseded", "unknown"}:
                continue
            if atom.get("gpt_access", "FULL_SEMANTIC_ACCESS") != "FULL_SEMANTIC_ACCESS":
                continue
            if _contains_actual_secret_value(atom):
                continue
            if not _relevant(text, str(atom.get("content", ""))):
                continue
            cost = max(1, len(str(atom.get("content", ""))) // 4)
            if used + cost > budget:
                omitted.append(atom.get("atom_id"))
                continue
            chosen.append(dict(atom))
            used += cost
        payload = {"query_id": canonical_hash({"text": text, "budget": budget})[:16], "knowledge_revision": self.revision, "atoms": chosen, "omitted_due_to_context_budget": omitted, "gpt_access": "FULL_SEMANTIC_ACCESS", "authority_write": False}
        return AdapterResult(AdapterStatus.VERIFIED, payload=payload)


class InMemoryLearningPacketAdapter(LearningPacketAdapter):
    def emit(self, packet: dict[str, Any]) -> AdapterResult:
        if packet.get("authority_write") or packet.get("status") != "candidate":
            return AdapterResult(AdapterStatus.REJECTED, ("candidate_authority_promotion_denied",))
        if _contains_actual_secret_value(packet):
            return AdapterResult(AdapterStatus.BLOCKED_BY_POLICY, ("credential_value_payload_denied",))
        required = {"packet_id", "packet_content_hash", "idempotency_key", "base_knowledge_revision", "status"}
        if required - packet.keys():
            return AdapterResult(AdapterStatus.REJECTED, ("learning_packet_incomplete",))
        return AdapterResult(AdapterStatus.VERIFIED, payload={"packet_id": packet["packet_id"], "candidate_only": True, "hash": canonical_hash(packet)})


class InMemoryCapabilityProbe(CapabilityProbeAdapter):
    def probe(self, capability: AdapterCapability) -> AdapterResult:
        try:
            capability.validate()
        except ContractError as error:
            return AdapterResult(AdapterStatus.REJECTED, (str(error),))
        if capability.entitlement_status != "confirmed":
            return AdapterResult(AdapterStatus.PARTIALLY_VERIFIED, ("entitlement_not_confirmed",))
        return AdapterResult(AdapterStatus.VERIFIED, payload={"capability_id": capability.capability_id, "probe": "synthetic_in_memory_only"})


def _require_v1(version: str) -> None:
    if not re.fullmatch(r"1\.\d+\.\d+", version or ""):
        raise ContractError("unsupported_schema_version")


_CONTRACT_TYPES = {
    "LocalArtifactReference": LocalArtifactReference,
    "CredentialReference": CredentialReference,
    "AdapterCapability": AdapterCapability,
    "AdapterResult": AdapterResult,
    "SourceManifest": SourceManifest,
}


def serialize_contract(value: Any) -> dict[str, Any]:
    """Stable public-safe contract projection; values are caller-validated first."""
    if type(value).__name__ not in _CONTRACT_TYPES:
        raise ContractError("unsupported_contract_type")
    if isinstance(value, SourceManifest):
        return {**asdict(value), "artifact": serialize_contract(value.artifact), "capability": serialize_contract(value.capability)}
    if isinstance(value, AdapterResult):
        return {**asdict(value), "status": value.status.value}
    return asdict(value)


def deserialize_contract(name: str, payload: dict[str, Any]) -> Any:
    """Reject unknown fields and incompatible major versions before constructing a contract."""
    target = _CONTRACT_TYPES.get(name)
    if target is None or not isinstance(payload, dict):
        raise ContractError("unknown_contract_type")
    allowed = set(target.__dataclass_fields__)
    unknown = set(payload) - allowed
    if unknown:
        raise ContractError("unknown_contract_field")
    data = dict(payload)
    _require_v1(str(data.get("schema_version", "")))
    if name == "SourceManifest":
        data["artifact"] = deserialize_contract("LocalArtifactReference", data["artifact"])
        data["capability"] = deserialize_contract("AdapterCapability", data["capability"])
    if name == "AdapterResult":
        data["status"] = AdapterStatus(data["status"])
    return target(**data)
