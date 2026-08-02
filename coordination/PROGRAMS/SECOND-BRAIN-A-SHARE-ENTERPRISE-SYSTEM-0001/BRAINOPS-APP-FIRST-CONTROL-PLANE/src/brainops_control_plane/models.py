"""Strict, non-executing contracts used by the E35 control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


class ValidationError(ValueError):
    """Raised when untrusted metadata violates a fail-closed contract."""


class CapabilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


class ExecutionOwner(str, Enum):
    APP_AUTOMATION = "APP_AUTOMATION"
    CLI_FALLBACK = "CLI_FALLBACK"
    MANUAL_APP = "MANUAL_APP"
    NONE = "NONE"


class RouteState(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class ShadowOutcome(str, Enum):
    WOULD_DISPATCH = "WOULD_DISPATCH"
    WOULD_BLOCK = "WOULD_BLOCK"
    WOULD_REQUIRE_MANUAL = "WOULD_REQUIRE_MANUAL"
    DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
    CANARY_ELIGIBLE_SHADOW_ONLY = "CANARY_ELIGIBLE_SHADOW_ONLY"


_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{1,127}$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_SHA1_HEX = re.compile(r"^[0-9a-f]{40}$")
_SENSITIVE_KEY = re.compile(r"(?:token|secret|password|cookie|credential|authorization|api[_-]?key)", re.I)
_FORBIDDEN_COMMAND_FIELD = re.compile(r"(?:command|executable|argument|shell|script|path)", re.I)
_VALUE_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}\b", re.I)),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)


def require_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValidationError(f"{label} must be a stable identifier")
    return value


def require_sha256(value: str, label: str) -> str:
    if not is_sha256_hex(value):
        raise ValidationError(f"{label} must be exactly 64 lowercase hexadecimal characters")
    return value


def require_sha1(value: str, label: str) -> str:
    if not isinstance(value, str) or _SHA1_HEX.fullmatch(value) is None:
        raise ValidationError(f"{label} must be exactly 40 lowercase hexadecimal characters")
    return value


def is_sha256_hex(value: object) -> bool:
    return isinstance(value, str) and _SHA256_HEX.fullmatch(value) is not None


def parse_rfc3339_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValidationError(f"{label} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{label} must be a valid RFC3339 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValidationError(f"{label} must be expressed in UTC")
    return parsed


def strict_json_loads(text: str) -> Any:
    """Parse JSON while rejecting duplicate keys at every nesting level."""

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=pairs_hook)
    except json.JSONDecodeError as exc:
        raise ValidationError("invalid JSON") from exc


@dataclass(frozen=True)
class SecretValueFinding:
    path: str
    category: str


def find_secret_values(value: Any, path: str = "$") -> tuple[SecretValueFinding, ...]:
    """Identify secret-shaped values without returning their contents."""
    findings: list[SecretValueFinding] = []
    if is_dataclass(value):
        return find_secret_values(asdict(value), path)
    if isinstance(value, Mapping):
        for key, item in value.items():
            findings.extend(find_secret_values(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(find_secret_values(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        for category, pattern in _VALUE_SECRET_PATTERNS:
            if pattern.search(value):
                findings.append(SecretValueFinding(path=path, category=category))
    return tuple(findings)


def redact(value: Any) -> Any:
    """Remove secret-like values before anything reaches SQLite or an API."""

    if is_dataclass(value):
        return redact(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str) and find_secret_values(value):
        return "[REDACTED]"
    return value


def canonical_hash(value: Any) -> str:
    payload = json.dumps(redact(value), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_database_path(root: Path, requested_name: str) -> Path:
    """Create no path outside the caller supplied metadata root."""

    if not isinstance(requested_name, str) or not requested_name.endswith(".sqlite"):
        raise ValidationError("database name must end in .sqlite")
    candidate = Path(requested_name)
    if candidate.is_absolute() or ".." in candidate.parts or len(candidate.parts) != 1:
        raise ValidationError("database name must be a single local filename")
    resolved_root = root.resolve()
    resolved_candidate = (resolved_root / candidate).resolve()
    if resolved_candidate.parent != resolved_root:
        raise ValidationError("database path escapes metadata root")
    return resolved_candidate


@dataclass(frozen=True)
class PortManifest:
    port: int
    bind_host: str = "127.0.0.1"
    protocol: str = "http"
    component_id: str = "brainops.console"

    def __post_init__(self) -> None:
        if self.bind_host != "127.0.0.1":
            raise ValidationError("only 127.0.0.1 loopback binding is permitted")
        if not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValidationError("port must be an integer between 1 and 65535")
        if self.protocol not in {"http", "https"}:
            raise ValidationError("unsupported control-plane protocol")
        require_identifier(self.component_id, "component_id")


@dataclass(frozen=True)
class ServiceManifest:
    service_id: str
    display_name: str
    port: PortManifest
    lifecycle: str = "MANUAL_ONLY"
    executable_ref: None = None
    arguments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_identifier(self.service_id, "service_id")
        if self.lifecycle != "MANUAL_ONLY":
            raise ValidationError("P1 services must remain MANUAL_ONLY")
        if self.executable_ref is not None or self.arguments:
            raise ValidationError("the read-only control plane does not accept executable or argument metadata")


@dataclass(frozen=True)
class DesiredState:
    route_state: RouteState
    automatic_dispatch_allowed: bool
    requested_owner: ExecutionOwner = ExecutionOwner.NONE


@dataclass(frozen=True)
class ObservedState:
    route_state: RouteState
    observed_epoch: int
    active_owner: ExecutionOwner = ExecutionOwner.NONE
    active_lease: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.observed_epoch, int) or self.observed_epoch < 0:
            raise ValidationError("observed_epoch must be a non-negative integer")


@dataclass(frozen=True)
class RouteRef:
    route_id: str
    target_agent: str
    route_epoch: int

    def __post_init__(self) -> None:
        require_identifier(self.route_id, "route_id")
        require_identifier(self.target_agent, "target_agent")
        if not isinstance(self.route_epoch, int) or self.route_epoch < 0:
            raise ValidationError("route_epoch must be a non-negative integer")


@dataclass(frozen=True)
class ActivationManifest:
    activation_id: str
    route: RouteRef
    expected_epoch: int
    idempotency_key: str
    canary_id: str
    task_id: str
    scope: str
    approval_nonce: str
    approval: "BoundCanaryApproval | None" = None

    def __post_init__(self) -> None:
        require_identifier(self.activation_id, "activation_id")
        require_identifier(self.idempotency_key, "idempotency_key")
        require_identifier(self.canary_id, "canary_id")
        require_identifier(self.task_id, "task_id")
        require_identifier(self.scope, "scope")
        require_identifier(self.approval_nonce, "approval_nonce")
        if self.expected_epoch != self.route.route_epoch:
            raise ValidationError("activation expected_epoch must equal its route epoch")


@dataclass(frozen=True)
class BoundCanaryApproval:
    """A non-secret, expiry-bound approval record for one exact canary."""

    canary_id: str
    task_id: str
    route_epoch: int
    scope: str
    expires_at: str
    nonce: str
    approval_ref: str
    repository: str | None = None
    issue_number: int | None = None
    comment_id: int | None = None
    actor: str | None = None
    issued_at: str | None = None
    body_sha256: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.canary_id, "canary_id")
        require_identifier(self.task_id, "task_id")
        require_identifier(self.scope, "scope")
        require_identifier(self.nonce, "nonce")
        if not isinstance(self.approval_ref, str) or not self.approval_ref:
            raise ValidationError("approval_ref must be a non-empty public reference")
        if not isinstance(self.route_epoch, int) or self.route_epoch < 0:
            raise ValidationError("approval route_epoch must be a non-negative integer")
        parse_rfc3339_utc(self.expires_at, "approval expires_at")

    def binding_payload_hash(self) -> str:
        """Hash only the exact approval bindings, never a raw comment body."""
        return canonical_hash(
            {
                "canary_id": self.canary_id,
                "task_id": self.task_id,
                "route_epoch": self.route_epoch,
                "scope": self.scope,
                "expires_at": self.expires_at,
                "nonce": self.nonce,
                "approval_ref": self.approval_ref,
            }
        )

    def validates(self, activation: ActivationManifest, now: str) -> str | None:
        now_value = parse_rfc3339_utc(now, "approval validation time")
        if self.canary_id != activation.canary_id:
            return "approval_canary_mismatch"
        if self.task_id != activation.task_id:
            return "approval_task_mismatch"
        if self.route_epoch != activation.expected_epoch:
            return "approval_epoch_mismatch"
        if self.scope != activation.scope:
            return "approval_scope_mismatch"
        if self.nonce != activation.approval_nonce:
            return "approval_nonce_mismatch"
        if now_value >= parse_rfc3339_utc(self.expires_at, "approval expires_at"):
            return "approval_expired"
        return None


@dataclass(frozen=True)
class CanaryEvent:
    event_id: str
    source: str
    route: RouteRef
    canary_id: str
    idempotency_key: str
    payload_hash: str

    def __post_init__(self) -> None:
        require_identifier(self.event_id, "event_id")
        require_identifier(self.canary_id, "canary_id")
        require_identifier(self.idempotency_key, "idempotency_key")
        if self.source != "GITHUB":
            raise ValidationError("canary event source must be GITHUB")
        require_sha256(self.payload_hash, "payload_hash")


@dataclass(frozen=True)
class RouteStateEvidence:
    """A single synchronized observation of the two authoritative route views."""

    route: RouteRef
    active_task_hash: str
    coordination_hash: str
    observed_at: str

    def __post_init__(self) -> None:
        require_sha256(self.active_task_hash, "active_task_hash")
        require_sha256(self.coordination_hash, "coordination_hash")
        parse_rfc3339_utc(self.observed_at, "route state observed_at")


@dataclass(frozen=True)
class AppAutomationIdentity:
    automation_id: str
    capability_status: CapabilityStatus
    observed_via: str

    def __post_init__(self) -> None:
        require_identifier(self.automation_id, "automation_id")
        if self.capability_status is CapabilityStatus.SUPPORTED and self.observed_via != "LOCAL_VERIFIED":
            raise ValidationError("App Automation support requires a local verification record")


@dataclass(frozen=True)
class CliSession:
    session_ref: str
    capability_status: CapabilityStatus
    authentication_state: str = "NOT_INSPECTED"

    def __post_init__(self) -> None:
        require_identifier(self.session_ref, "session_ref")
        if self.authentication_state != "NOT_INSPECTED":
            raise ValidationError("E35 must not inspect CLI authentication or session material")


@dataclass(frozen=True)
class Lease:
    lease_id: str
    route: RouteRef
    owner: ExecutionOwner
    fencing_generation: int
    acquired_at: str
    expires_at: str

    def __post_init__(self) -> None:
        require_identifier(self.lease_id, "lease_id")
        if self.owner is ExecutionOwner.NONE:
            raise ValidationError("NONE cannot acquire a lease")
        if not isinstance(self.fencing_generation, int) or self.fencing_generation < 1:
            raise ValidationError("fencing_generation must be positive")
        if parse_rfc3339_utc(self.expires_at, "lease expires_at") <= parse_rfc3339_utc(self.acquired_at, "lease acquired_at"):
            raise ValidationError("lease expires_at must be after acquired_at")


@dataclass(frozen=True)
class CapabilitySet:
    app_automation: CapabilityStatus = CapabilityStatus.UNKNOWN
    cli_fallback: CapabilityStatus = CapabilityStatus.UNKNOWN
    manual_app: CapabilityStatus = CapabilityStatus.UNKNOWN


@dataclass(frozen=True)
class ShadowDecision:
    outcome: ShadowOutcome
    reason_code: str
    selected_owner: ExecutionOwner
    route: RouteRef
    actual_dispatch_performed: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.actual_dispatch_performed:
            raise ValidationError("E35 shadow decisions can never perform a dispatch")
        require_identifier(self.reason_code, "reason_code")


def reject_command_like_fields(payload: Mapping[str, Any]) -> None:
    """Reject untrusted manifest fields that could become arbitrary execution."""

    for key, value in payload.items():
        if _FORBIDDEN_COMMAND_FIELD.search(str(key)):
            raise ValidationError(f"forbidden execution-shaped field: {key}")
        if isinstance(value, Mapping):
            reject_command_like_fields(value)
