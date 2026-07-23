"""Knowledge-source and gateway contracts that wrap the Phase 3 runtime."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .canonical import content_hash, normalize_text
from .retrieval import QueryPlan
from .security import assert_no_credential_value, query_requests_credential_value


_HEX_64 = re.compile(r"[0-9a-f]{64}")
_FORMATS = {"markdown", "txt", "json", "jsonl"}
_SOURCE_KINDS = {"FILE", "DIRECTORY", "EXISTING_SERVICE"}
_CONTENT_CLASSES = {"PUBLIC_SAFE", "PRIVATE_LOCAL_ONLY", "LICENSED_LOCAL"}
_LICENSE_ALLOWED = {"PUBLIC", "LICENSED", "DECLARED_USER_AUTHORIZED"}
_LICENSE_WAITING = {"UNKNOWN", "UNDECLARED", "CONFLICT"}
_TRANSPORTS = {"PUBLIC_SAFE_BODY", "PRIVATE_LOCAL_ONLY"}


@dataclass(frozen=True)
class LocalKnowledgeReference:
    reference_id: str
    local_location_hint: str
    sha256: str
    size_bytes: int
    content_format: str
    content_class: str
    body_transport: str
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if not self.reference_id:
            raise ValueError("knowledge_reference_id_required")
        if not self.local_location_hint.startswith("local-ref://"):
            raise ValueError("knowledge_reference_hint_must_be_opaque")
        if not _HEX_64.fullmatch(self.sha256):
            raise ValueError("knowledge_reference_sha256_invalid")
        if self.size_bytes < 0:
            raise ValueError("knowledge_reference_size_invalid")
        if self.content_format not in _FORMATS | {"mixed", "service"}:
            raise ValueError("knowledge_reference_format_invalid")
        if self.content_class not in _CONTENT_CLASSES:
            raise ValueError("knowledge_reference_content_class_invalid")
        if self.body_transport not in _TRANSPORTS:
            raise ValueError("knowledge_reference_transport_invalid")
        if self.content_class != "PUBLIC_SAFE" and self.body_transport != "PRIVATE_LOCAL_ONLY":
            raise ValueError("private_knowledge_transport_must_be_local")
        _require_v1(self.schema_version)


@dataclass(frozen=True)
class KnowledgeSourceManifest:
    manifest_id: str
    source_id: str
    source_version: str
    source_kind: str
    local_reference: LocalKnowledgeReference
    owner_authorization: str
    license_status: str
    privacy_class: str
    content_category: str
    allowed_formats: tuple[str, ...]
    source_time_semantics: str
    gpt_access: str = "FULL_SEMANTIC_ACCESS"
    transport_visibility: str = "PRIVATE_LOCAL_ONLY"
    authority_level: str = "CANDIDATE_ONLY"
    revocable: bool = True
    read_only: bool = True
    schema_version: str = "1.0.0"

    def validate_structure(self) -> None:
        if not all((self.manifest_id, self.source_id, self.source_version, self.content_category)):
            raise ValueError("knowledge_manifest_identity_required")
        if self.source_kind not in _SOURCE_KINDS:
            raise ValueError("knowledge_manifest_source_kind_invalid")
        self.local_reference.validate()
        if self.owner_authorization not in {"USER_AUTHORIZED", "PUBLIC", "LICENSED"}:
            raise ValueError("knowledge_manifest_owner_authorization_invalid")
        if self.license_status not in _LICENSE_ALLOWED | _LICENSE_WAITING | {"PROHIBITED"}:
            raise ValueError("knowledge_manifest_license_status_invalid")
        if self.privacy_class not in _CONTENT_CLASSES:
            raise ValueError("knowledge_manifest_privacy_class_invalid")
        if not self.allowed_formats or not set(self.allowed_formats).issubset(_FORMATS):
            raise ValueError("knowledge_manifest_formats_invalid")
        if self.local_reference.content_format not in set(self.allowed_formats) | {"mixed", "service"}:
            raise ValueError("knowledge_manifest_format_mismatch")
        if self.gpt_access != "FULL_SEMANTIC_ACCESS":
            raise ValueError("knowledge_manifest_gpt_access_invalid")
        if self.transport_visibility not in _TRANSPORTS:
            raise ValueError("knowledge_manifest_transport_invalid")
        if self.privacy_class != "PUBLIC_SAFE" and self.transport_visibility != "PRIVATE_LOCAL_ONLY":
            raise ValueError("knowledge_manifest_private_transport_required")
        if self.authority_level != "CANDIDATE_ONLY":
            raise ValueError("knowledge_manifest_authority_promotion_denied")
        if not self.revocable or not self.read_only:
            raise ValueError("knowledge_manifest_revocable_readonly_required")
        _require_v1(self.schema_version)
        assert_no_credential_value(self.public_metadata())

    def activation_state(self) -> str:
        self.validate_structure()
        if self.license_status in _LICENSE_WAITING:
            return "WAITING_LOCAL_EVIDENCE"
        if self.license_status == "PROHIBITED":
            return "DENIED"
        return "ELIGIBLE"

    def public_metadata(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_formats"] = list(self.allowed_formats)
        payload["local_reference"] = asdict(self.local_reference)
        return payload

    @property
    def manifest_hash(self) -> str:
        return content_hash(self.public_metadata())


@dataclass(frozen=True)
class KnowledgeGatewayPolicy:
    policy_id: str
    manifest_id: str
    manifest_hash: str
    allowed_scopes: tuple[str, ...] = ()
    allowed_content_classes: tuple[str, ...] = ("PUBLIC_SAFE", "PRIVATE_LOCAL_ONLY", "LICENSED_LOCAL")
    gpt_access: str = "FULL_SEMANTIC_ACCESS"
    credential_values_denied: bool = True
    private_bodies_public: bool = False
    read_only: bool = True
    authority_write: bool = False
    no_trade_gate: bool = True
    active: bool = True
    schema_version: str = "1.0.0"

    def validate(self, manifest: KnowledgeSourceManifest) -> None:
        manifest.validate_structure()
        if not self.policy_id or self.manifest_id != manifest.manifest_id:
            raise ValueError("knowledge_policy_manifest_identity_mismatch")
        if self.manifest_hash != manifest.manifest_hash:
            raise ValueError("knowledge_policy_manifest_hash_mismatch")
        if not set(self.allowed_content_classes).issubset(_CONTENT_CLASSES):
            raise ValueError("knowledge_policy_content_class_invalid")
        if manifest.privacy_class not in set(self.allowed_content_classes):
            raise ValueError("knowledge_policy_content_class_denied")
        if self.gpt_access != "FULL_SEMANTIC_ACCESS":
            raise ValueError("knowledge_policy_access_invalid")
        if not self.credential_values_denied or self.private_bodies_public:
            raise ValueError("knowledge_policy_secret_or_transport_boundary")
        if not self.read_only or self.authority_write or not self.no_trade_gate:
            raise ValueError("knowledge_policy_governance_boundary")
        _require_v1(self.schema_version)

    @property
    def policy_hash(self) -> str:
        return content_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_scopes"] = list(self.allowed_scopes)
        payload["allowed_content_classes"] = list(self.allowed_content_classes)
        return payload


@dataclass(frozen=True)
class KnowledgeAccessDecision:
    decision_id: str
    status: str
    manifest_id: str
    policy_id: str
    reason_codes: tuple[str, ...]
    semantic_access: str
    body_transport: str
    source_hash: str
    manifest_hash: str
    policy_hash: str
    content_body_included: bool = False
    credential_value_included: bool = False
    authority_write: bool = False
    no_trade_gate: bool = True
    schema_version: str = "1.0.0"

    def to_public_receipt(self) -> dict[str, Any]:
        if self.content_body_included or self.credential_value_included or self.authority_write or not self.no_trade_gate:
            raise ValueError("knowledge_access_receipt_boundary_violation")
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        assert_no_credential_value(payload)
        return payload


@dataclass(frozen=True)
class KnowledgeQuery:
    query_text: str
    scopes: tuple[str, ...] = ()
    atom_types: tuple[str, ...] = ()
    source_manifest_ids: tuple[str, ...] = ()
    evidence_qualities: tuple[str, ...] = ()
    query_aliases: tuple[str, ...] = ()
    min_confidence: float = 0.0
    time_start: str | None = None
    time_end: str | None = None
    include_conflicts: bool = True
    include_unknowns: bool = True
    include_historical: bool = False
    relation_depth: int = 0
    budget: int = 50
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        _require_v1(self.schema_version)
        if query_requests_credential_value(self.query_text):
            raise ValueError("credential_value_query_denied")
        assert_no_credential_value(asdict(self))
        if not normalize_text(self.query_text) and not any((self.scopes, self.atom_types, self.source_manifest_ids)):
            raise ValueError("knowledge_query_text_or_filter_required")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("knowledge_query_confidence_invalid")
        if not 1 <= self.budget <= 1000 or not 0 <= self.relation_depth <= 4:
            raise ValueError("knowledge_query_budget_or_depth_invalid")

    def to_query_plan(self) -> QueryPlan:
        self.validate()
        truth_states = ("candidate", "approved", "conflict", "unknown")
        if self.include_historical:
            truth_states = (*truth_states, "superseded")
        return QueryPlan(
            query_text=self.query_text,
            scopes=self.scopes,
            atom_types=self.atom_types,
            truth_states=truth_states,
            source_manifest_ids=self.source_manifest_ids,
            evidence_qualities=self.evidence_qualities,
            query_aliases=self.query_aliases,
            min_confidence=self.min_confidence,
            time_start=self.time_start,
            time_end=self.time_end,
            include_conflicts=self.include_conflicts,
            include_unknowns=self.include_unknowns,
            history_mode="HISTORY" if self.include_historical else "CURRENT",
            relation_depth=self.relation_depth,
            budget=self.budget,
        )

    @property
    def query_hash(self) -> str:
        return self.to_query_plan().plan_hash


def evaluate_knowledge_access(
    manifest: KnowledgeSourceManifest,
    policy: KnowledgeGatewayPolicy,
    *,
    revoked: bool = False,
) -> KnowledgeAccessDecision:
    status = "DENIED"
    reasons: tuple[str, ...] = ()
    try:
        policy.validate(manifest)
        state = manifest.activation_state()
        if revoked:
            status, reasons = "REVOKED", ("source_revoked",)
        elif not policy.active:
            status, reasons = "DENIED", ("policy_inactive",)
        elif state == "WAITING_LOCAL_EVIDENCE":
            status, reasons = state, ("license_evidence_incomplete",)
        elif state == "DENIED":
            status, reasons = state, ("license_prohibited",)
        else:
            status, reasons = "GRANTED", ("hash_bound_readonly_access",)
    except ValueError as error:
        reasons = (str(error),)
    core = {
        "status": status,
        "manifest_id": manifest.manifest_id,
        "policy_id": policy.policy_id,
        "reasons": reasons,
        "source_hash": manifest.local_reference.sha256,
        "manifest_hash": manifest.manifest_hash,
        "policy_hash": policy.policy_hash,
    }
    return KnowledgeAccessDecision(
        decision_id="kad-" + content_hash(core)[:20],
        status=status,
        manifest_id=manifest.manifest_id,
        policy_id=policy.policy_id,
        reason_codes=reasons,
        semantic_access=manifest.gpt_access,
        body_transport=manifest.transport_visibility,
        source_hash=manifest.local_reference.sha256,
        manifest_hash=manifest.manifest_hash,
        policy_hash=policy.policy_hash,
    )


def _require_v1(version: str) -> None:
    if not re.fullmatch(r"1\.\d+\.\d+", version or ""):
        raise ValueError("knowledge_contract_schema_version_unsupported")

