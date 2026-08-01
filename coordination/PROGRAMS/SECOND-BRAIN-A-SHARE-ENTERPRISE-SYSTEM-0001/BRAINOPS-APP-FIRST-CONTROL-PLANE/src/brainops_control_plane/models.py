"""Strict, non-executing contracts used by the E35 control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
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


_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{1,127}$")
_SENSITIVE_KEY = re.compile(r"(?:token|secret|password|cookie|credential|authorization|api[_-]?key)", re.I)
_FORBIDDEN_COMMAND_FIELD = re.compile(r"(?:command|executable|argument|shell|script|path)", re.I)


def require_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValidationError(f"{label} must be a stable identifier")
    return value


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
    user_approval_required: bool
    user_approval_granted: bool

    def __post_init__(self) -> None:
        require_identifier(self.activation_id, "activation_id")
        require_identifier(self.idempotency_key, "idempotency_key")
        if self.expected_epoch != self.route.route_epoch:
            raise ValidationError("activation expected_epoch must equal its route epoch")
        if self.user_approval_granted and not self.user_approval_required:
            raise ValidationError("approval cannot be granted when approval is not required")


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
