from __future__ import annotations

from _iagl_primitives import *

@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    event_class: str
    source: str
    repository: str
    observed_at: int
    target_ref: str
    target_identity: str
    payload_digest: str
    supplied_idempotency_key: str
    semantic_kind: str
    semantic_key: str
    priority_hint: Priority
    class_priority_hint: Priority
    risk_markers: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "NormalizedEvent":
        names = ("event_id", "event_class", "source", "repository", "observed_at", "target_ref", "target_identity", "payload", "idempotency_key")
        missing = [name for name in names if name not in raw]
        if missing or not _nonempty([raw[n] for n in names if n not in {"observed_at", "payload"}]):
            raise SupervisorError("EVENT_INVALID:" + ",".join(missing))
        if not isinstance(raw["observed_at"], int) or raw["observed_at"] < 0:
            raise SupervisorError("EVENT_INVALID_OBSERVED_AT")
        try:
            priority_hint = Priority(int(raw.get("priority_hint", Priority.P4_RESEARCH)))
        except (TypeError, ValueError) as exc:
            raise SupervisorError("EVENT_INVALID_PRIORITY") from exc
        event_class = str(raw["event_class"])
        normalized_class = event_class.upper()
        payload_digest = digest(raw["payload"])
        risk_markers = _risk_markers(raw["payload"])
        if normalized_class in _HEAD_OBSERVATION_CLASSES:
            semantic_kind = "HEAD_OBSERVATION"
            semantic_key = _head_semantic_key(str(raw["repository"]), str(raw["target_ref"]), str(raw["target_identity"]))
        else:
            semantic_kind = normalized_class
            semantic_key = digest({
                "repository": raw["repository"], "semantic_kind": semantic_kind,
                "target_ref": raw["target_ref"], "target_identity": raw["target_identity"],
                "payload": payload_digest,
            })
        return cls(
            str(raw["event_id"]), event_class, str(raw["source"]), str(raw["repository"]), int(raw["observed_at"]),
            str(raw["target_ref"]), str(raw["target_identity"]), payload_digest, str(raw["idempotency_key"]),
            semantic_kind, semantic_key, priority_hint, _class_priority_hint(event_class), risk_markers,
        )


@dataclass(frozen=True)
class P0Disposition:
    event_key: str
    decision: str
    decision_ref: str
    authority_source: str = "USER_DECISION"

    def validate(self) -> None:
        if not _nonempty((self.event_key, self.decision, self.decision_ref, self.authority_source)):
            raise SupervisorError("P0_DISPOSITION_INCOMPLETE")
        if self.decision not in _P0_DISPOSITIONS or self.authority_source != "USER_DECISION":
            raise SupervisorError("P0_DISPOSITION_UNTRUSTED_OR_INVALID")


@dataclass(frozen=True)
class P2Resolution:
    event_key: str
    resolution_ref: str
    authority_source: str = "AUTHORITATIVE_RECONCILIATION"

    def validate(self) -> None:
        if not _nonempty((self.event_key, self.resolution_ref, self.authority_source)):
            raise SupervisorError("P2_RESOLUTION_INCOMPLETE")
        if self.authority_source != "AUTHORITATIVE_RECONCILIATION":
            raise SupervisorError("P2_RESOLUTION_UNTRUSTED")


@dataclass(frozen=True)
class ReconciliationSnapshot:
    repository: str
    exact_head: str
    route_id: str
    governance_mode: GovernanceMode
    allowed_write_paths: tuple[str, ...]
    observed_at: int
    pending_p0: bool = False
    domain_revision: str = "synthetic-domain-v1"
    trusted: bool = True
    eligible_work_queue_complete: bool = False
    allowed_tools: tuple[str, ...] = ("stdlib-only",)
    allowed_data_classes: tuple[str, ...] = ("PUBLIC_SAFE_SYNTHETIC",)
    allowed_risk_classes: tuple[str, ...] = ("P3_SYNTHETIC", "P4_SYNTHETIC")
    allowed_writeback_plans: tuple[str, ...] = ("NO_CANONICAL_WRITE",)
    active_p2_event_keys: tuple[str, ...] = ()
    active_p2_classes: tuple[str, ...] = ()
    p0_dispositions: tuple[P0Disposition, ...] = ()
    p2_observation_status: str = "PARTIAL_OBSERVATION"
    p2_observation_ref: str = ""
    p2_resolutions: tuple[P2Resolution, ...] = ()

    def validate(self, expected_repository: str) -> None:
        if not self.trusted or self.repository != expected_repository or not _nonempty((self.exact_head, self.route_id, self.domain_revision)):
            raise SupervisorError("RECONCILIATION_INCOMPLETE_OR_UNTRUSTED")
        if not self.allowed_write_paths or any(not item or item.startswith("/") or ".." in item.replace("\\", "/").split("/") for item in self.allowed_write_paths):
            raise SupervisorError("RECONCILIATION_INVALID_ALLOWLIST")
        if not all((self.allowed_tools, self.allowed_data_classes, self.allowed_risk_classes, self.allowed_writeback_plans)):
            raise SupervisorError("RECONCILIATION_POLICY_INCOMPLETE")
        if not set(self.allowed_tools).issubset(_STAGE_A_TOOL_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_TOOL_CEILING")
        if not set(self.allowed_data_classes).issubset(_STAGE_A_DATA_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_DATA_CEILING")
        if not set(self.allowed_risk_classes).issubset(_STAGE_A_RISK_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_RISK_CEILING")
        if not set(self.allowed_writeback_plans).issubset(_STAGE_A_WRITEBACK_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_WRITEBACK_CEILING")
        if any(not isinstance(item, str) or not item for item in self.active_p2_event_keys + self.active_p2_classes):
            raise SupervisorError("RECONCILIATION_P2_OBSERVATION_INVALID")
        for disposition in self.p0_dispositions:
            disposition.validate()
        if self.p2_observation_status not in _P2_OBSERVATION_STATES:
            raise SupervisorError("RECONCILIATION_P2_OBSERVATION_STATUS_INVALID")
        if self.p2_observation_status == "AUTHORITATIVE_COMPLETE" and not self.p2_observation_ref:
            raise SupervisorError("RECONCILIATION_P2_COMPLETE_REF_REQUIRED")
        for resolution in self.p2_resolutions:
            resolution.validate()
        active = set(self.active_p2_event_keys)
        resolved = {item.event_key for item in self.p2_resolutions}
        if active & resolved:
            raise SupervisorError("RECONCILIATION_P2_ACTIVE_RESOLVED_CONFLICT")

    def identity(self) -> str:
        return digest({
            "repository": self.repository, "head": self.exact_head, "route": self.route_id,
            "governance": self.governance_mode.value, "allowed": self.allowed_write_paths,
            "p0": self.pending_p0, "domain": self.domain_revision,
            "queue_complete": self.eligible_work_queue_complete,
            "allowed_tools": self.allowed_tools, "allowed_data_classes": self.allowed_data_classes,
            "allowed_risk_classes": self.allowed_risk_classes, "allowed_writeback_plans": self.allowed_writeback_plans,
            "active_p2_event_keys": self.active_p2_event_keys, "active_p2_classes": self.active_p2_classes,
            "p0_dispositions": tuple(asdict(item) for item in self.p0_dispositions),
            "p2_observation_status": self.p2_observation_status, "p2_observation_ref": self.p2_observation_ref,
            "p2_resolutions": tuple(asdict(item) for item in self.p2_resolutions),
        })



__all__ = tuple(name for name in globals() if not name.startswith("__"))
