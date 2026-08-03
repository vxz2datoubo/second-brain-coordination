"""Fail-closed, read-only authority contracts for E38.

Only :mod:`github_transport` may create fetched documents.  This module never
opens a network connection, persists a comment body, or exposes a public
factory for a verified result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping

from .models import (
    BoundCanaryApproval,
    RouteRef,
    ValidationError,
    canonical_hash,
    parse_rfc3339_utc,
    require_identifier,
    require_sha1,
    require_sha256,
    strict_json_loads,
)


CANONICAL_REPOSITORY = "vxz2datoubo/second-brain-coordination"
CANONICAL_ACTIVE_TASK_PATH = "coordination/ACTIVE-CODEX-TASK.yaml"
CANONICAL_COORDINATION_PATH = "coordination/ACTIVE-THREE-AGENT-COORDINATION.yaml"
CANONICAL_MAIN_REF = "refs/heads/main"
DEFAULT_MAX_ROUTE_PROOF_AGE_SECONDS = 300

_APPROVAL_RESULT_SEAL = object()
_ROUTE_RESULT_SEAL = object()
_FETCHED_COMMENT_SEAL = object()
_FETCHED_ROUTE_SEAL = object()
_APPROVAL_BLOCK = re.compile(r"```brainops-approval-v1\n(?P<payload>[^\n]+)\n```", re.ASCII)
_YAML_KEY = re.compile(r"^(?P<indent> *)(?P<key>[A-Za-z][A-Za-z0-9_.-]*):(?: (?P<value>.*))?$", re.ASCII)
_REASON_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{1,127}$", re.ASCII)


class VerificationStatus(str, Enum):
    READ_ONLY_FETCH_VERIFIED = "READ_ONLY_FETCH_VERIFIED"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"


def canonical_approval_ref(repository: str, issue_number: int, comment_id: int) -> str:
    return f"github://{repository}/issues/{issue_number}/comments/{comment_id}"


def _require_repository(value: str) -> str:
    if value != CANONICAL_REPOSITORY:
        raise ValidationError("repository is not the canonical public repository")
    return value


def _require_positive(value: int, label: str) -> int:
    if not isinstance(value, int) or value < 1:
        raise ValidationError(f"{label} must be a positive integer")
    return value


def _git_blob_sha1(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()


@dataclass(frozen=True)
class CanonicalApprovalBinding:
    """The only six fields allowed inside a canonical approval body."""

    task_id: str
    route_epoch: int
    canary_id: str
    scope: str
    expires_at: str
    nonce: str

    def __post_init__(self) -> None:
        require_identifier(self.task_id, "approval task_id")
        if not isinstance(self.route_epoch, int) or self.route_epoch < 0:
            raise ValidationError("approval route_epoch must be a non-negative integer")
        require_identifier(self.canary_id, "approval canary_id")
        require_identifier(self.scope, "approval scope")
        require_identifier(self.nonce, "approval nonce")
        parse_rfc3339_utc(self.expires_at, "approval expires_at")

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "canary_id": self.canary_id,
                "expires_at": self.expires_at,
                "nonce": self.nonce,
                "route_epoch": self.route_epoch,
                "scope": self.scope,
                "task_id": self.task_id,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    def payload_sha256(self, approval_ref: str) -> str:
        """Hash bindings plus the fetched immutable comment reference."""
        if not isinstance(approval_ref, str) or not approval_ref:
            raise ValidationError("approval_ref must be a non-empty public reference")
        return canonical_hash(
            {
                "canary_id": self.canary_id,
                "task_id": self.task_id,
                "route_epoch": self.route_epoch,
                "scope": self.scope,
                "expires_at": self.expires_at,
                "nonce": self.nonce,
                "approval_ref": approval_ref,
            }
        )


def parse_canonical_approval_body(body: str) -> CanonicalApprovalBinding:
    """Parse exactly one compact JSON approval block and reject ambiguity."""

    if not isinstance(body, str):
        raise ValidationError("approval body must be text")
    matches = list(_APPROVAL_BLOCK.finditer(body))
    if len(matches) != 1:
        raise ValidationError("approval body must contain exactly one canonical approval block")
    raw = matches[0].group("payload")
    parsed = strict_json_loads(raw)
    if not isinstance(parsed, dict):
        raise ValidationError("canonical approval payload must be an object")
    expected = {"task_id", "route_epoch", "canary_id", "scope", "expires_at", "nonce"}
    if set(parsed) != expected:
        raise ValidationError("canonical approval payload has missing or extra binding fields")
    binding = CanonicalApprovalBinding(
        task_id=parsed["task_id"],
        route_epoch=parsed["route_epoch"],
        canary_id=parsed["canary_id"],
        scope=parsed["scope"],
        expires_at=parsed["expires_at"],
        nonce=parsed["nonce"],
    )
    if raw != binding.canonical_json():
        raise ValidationError("canonical approval payload must use exact compact sorted JSON")
    return binding


@dataclass(frozen=True, init=False)
class ReadOnlyApprovalDocument:
    """Ephemeral comment text produced only by the bounded transport."""

    repository: str
    issue_number: int
    comment_id: int
    actor: str
    issued_at: str
    body: str

    def __init__(
        self,
        repository: str,
        issue_number: int,
        comment_id: int,
        actor: str,
        issued_at: str,
        body: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _FETCHED_COMMENT_SEAL:
            raise ValidationError("approval documents must come from the bounded public transport")
        _require_repository(repository)
        _require_positive(issue_number, "issue_number")
        _require_positive(comment_id, "comment_id")
        require_identifier(actor, "approval actor")
        parse_rfc3339_utc(issued_at, "approval issued_at")
        if not isinstance(body, str):
            raise ValidationError("approval body must be text")
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "issue_number", issue_number)
        object.__setattr__(self, "comment_id", comment_id)
        object.__setattr__(self, "actor", actor)
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "body", body)

    @property
    def approval_ref(self) -> str:
        return canonical_approval_ref(self.repository, self.issue_number, self.comment_id)

    @property
    def body_sha256(self) -> str:
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()


def _fetched_approval_document(
    repository: str,
    issue_number: int,
    comment_id: int,
    actor: str,
    issued_at: str,
    body: str,
) -> ReadOnlyApprovalDocument:
    return ReadOnlyApprovalDocument(repository, issue_number, comment_id, actor, issued_at, body, _seal=_FETCHED_COMMENT_SEAL)


@dataclass(frozen=True)
class ApprovalEvidence:
    repository: str
    issue_number: int
    comment_id: int
    actor: str
    issued_at: str
    body_sha256: str
    approval_ref: str
    binding_payload_sha256: str

    def __post_init__(self) -> None:
        _require_repository(self.repository)
        _require_positive(self.issue_number, "issue_number")
        _require_positive(self.comment_id, "comment_id")
        require_identifier(self.actor, "approval actor")
        parse_rfc3339_utc(self.issued_at, "approval issued_at")
        require_sha256(self.body_sha256, "approval body_sha256")
        require_sha256(self.binding_payload_sha256, "approval binding_payload_sha256")
        if self.approval_ref != canonical_approval_ref(self.repository, self.issue_number, self.comment_id):
            raise ValidationError("approval_ref must bind the exact repository issue and comment")

    def validates(self, approval: BoundCanaryApproval, checked_at: str) -> str | None:
        checked = parse_rfc3339_utc(checked_at, "approval checked_at")
        if approval.repository != self.repository:
            return "approval_repository_mismatch"
        if approval.issue_number != self.issue_number or approval.comment_id != self.comment_id:
            return "approval_comment_mismatch"
        if approval.actor != self.actor:
            return "approval_actor_mismatch"
        if approval.issued_at != self.issued_at:
            return "approval_issued_at_mismatch"
        if approval.body_sha256 != self.body_sha256:
            return "approval_body_hash_mismatch"
        if approval.approval_ref != self.approval_ref:
            return "approval_ref_mismatch"
        if approval.binding_payload_hash() != self.binding_payload_sha256:
            return "approval_binding_payload_mismatch"
        if parse_rfc3339_utc(self.issued_at, "approval issued_at") > checked:
            return "approval_issued_in_future"
        return None


@dataclass(frozen=True, init=False)
class ApprovalVerificationResult:
    status: VerificationStatus
    evidence: ApprovalEvidence | None
    verified_at: str
    reason_code: str

    def __init__(
        self,
        status: VerificationStatus,
        evidence: ApprovalEvidence | None,
        verified_at: str,
        reason_code: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _APPROVAL_RESULT_SEAL:
            raise ValidationError("approval verification results are verifier-internal")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "reason_code", reason_code)
        parse_rfc3339_utc(verified_at, "approval verified_at")
        require_identifier(reason_code, "approval verification reason")
        if status is VerificationStatus.READ_ONLY_FETCH_VERIFIED and evidence is None:
            raise ValidationError("verified approval result requires immutable evidence")
        if status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED and evidence is not None:
            raise ValidationError("unverified approval result must not carry trusted evidence")

    @classmethod
    def rejected(cls, verified_at: str, reason_code: str) -> "ApprovalVerificationResult":
        return cls(VerificationStatus.REJECTED, None, verified_at, reason_code, _seal=_APPROVAL_RESULT_SEAL)

    @classmethod
    def unknown(cls, verified_at: str, reason_code: str) -> "ApprovalVerificationResult":
        return cls(VerificationStatus.UNKNOWN, None, verified_at, reason_code, _seal=_APPROVAL_RESULT_SEAL)

    def validates(self, approval: BoundCanaryApproval, checked_at: str) -> str | None:
        if self.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
            return "approval_read_only_verification_required"
        assert self.evidence is not None
        return self.evidence.validates(approval, checked_at)


def _verified_approval(evidence: ApprovalEvidence, verified_at: str) -> ApprovalVerificationResult:
    return ApprovalVerificationResult(
        VerificationStatus.READ_ONLY_FETCH_VERIFIED,
        evidence,
        verified_at,
        "trusted_comment_body_actor_and_route_policy_verified",
        _seal=_APPROVAL_RESULT_SEAL,
    )


@dataclass(frozen=True)
class RouteFileIdentity:
    path: str
    blob_sha1: str
    content_sha256: str

    def __post_init__(self) -> None:
        if self.path not in {CANONICAL_ACTIVE_TASK_PATH, CANONICAL_COORDINATION_PATH}:
            raise ValidationError("route proof path is not one of the two canonical route files")
        require_sha1(self.blob_sha1, "route blob_sha1")
        require_sha256(self.content_sha256, "route content_sha256")


@dataclass(frozen=True)
class RouteAuthority:
    task_id: str
    route_epoch: int
    status: str
    execution_allowed: bool
    automatic_dispatch_allowed: bool
    canary_execution_allowed: bool
    authorized_approval_actors: tuple[str, ...]

    def __post_init__(self) -> None:
        require_identifier(self.task_id, "route task_id")
        if not isinstance(self.route_epoch, int) or self.route_epoch < 0:
            raise ValidationError("route epoch must be a non-negative integer")
        if self.status != "READY" or not self.execution_allowed:
            raise ValidationError("route is not execution ready")
        if not self.authorized_approval_actors:
            raise ValidationError("route must declare at least one authorized approval actor")
        for actor in self.authorized_approval_actors:
            require_identifier(actor, "authorized approval actor")

    @property
    def policy_hash(self) -> str:
        return canonical_hash({"authorized_approval_actors": list(self.authorized_approval_actors)})


@dataclass(frozen=True)
class RouteStateEvidence:
    route: RouteRef
    repository: str
    ref: str
    main_commit_sha1: str
    main_tree_sha1: str
    active_task: RouteFileIdentity
    coordination: RouteFileIdentity
    authority: RouteAuthority
    observed_at: str

    def __post_init__(self) -> None:
        _require_repository(self.repository)
        if self.ref != CANONICAL_MAIN_REF:
            raise ValidationError("route proof ref must be refs/heads/main")
        require_sha1(self.main_commit_sha1, "route main_commit_sha1")
        require_sha1(self.main_tree_sha1, "route main_tree_sha1")
        if self.active_task.path != CANONICAL_ACTIVE_TASK_PATH:
            raise ValidationError("active task route path mismatch")
        if self.coordination.path != CANONICAL_COORDINATION_PATH:
            raise ValidationError("coordination route path mismatch")
        if self.authority.route_epoch != self.route.route_epoch:
            raise ValidationError("route evidence epoch must match authority epoch")
        parse_rfc3339_utc(self.observed_at, "route state observed_at")


@dataclass(frozen=True, init=False)
class FetchedRouteSnapshot:
    """Transient ref/commit/tree/blob observation created by public transport."""

    repository: str
    ref: str
    main_commit_sha1: str
    main_tree_sha1: str
    active_task: RouteFileIdentity
    coordination: RouteFileIdentity
    active_task_content: bytes
    coordination_content: bytes
    observed_at: str

    def __init__(
        self,
        repository: str,
        ref: str,
        main_commit_sha1: str,
        main_tree_sha1: str,
        active_task: RouteFileIdentity,
        coordination: RouteFileIdentity,
        active_task_content: bytes,
        coordination_content: bytes,
        observed_at: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _FETCHED_ROUTE_SEAL:
            raise ValidationError("route snapshots must come from the bounded public transport")
        _require_repository(repository)
        if ref != CANONICAL_MAIN_REF:
            raise ValidationError("route snapshot must use refs/heads/main")
        require_sha1(main_commit_sha1, "route main_commit_sha1")
        require_sha1(main_tree_sha1, "route main_tree_sha1")
        for identity, content in ((active_task, active_task_content), (coordination, coordination_content)):
            if not isinstance(content, bytes):
                raise ValidationError("route content must be bytes")
            if _git_blob_sha1(content) != identity.blob_sha1:
                raise ValidationError("route snapshot blob does not match tree identity")
            if hashlib.sha256(content).hexdigest() != identity.content_sha256:
                raise ValidationError("route snapshot content does not match content hash")
        parse_rfc3339_utc(observed_at, "route state observed_at")
        for key, value in locals().items():
            if key not in {"self", "_seal"}:
                object.__setattr__(self, key, value)


def _fetched_route_snapshot(
    repository: str,
    ref: str,
    main_commit_sha1: str,
    main_tree_sha1: str,
    active_task: RouteFileIdentity,
    coordination: RouteFileIdentity,
    active_task_content: bytes,
    coordination_content: bytes,
    observed_at: str,
) -> FetchedRouteSnapshot:
    return FetchedRouteSnapshot(
        repository,
        ref,
        main_commit_sha1,
        main_tree_sha1,
        active_task,
        coordination,
        active_task_content,
        coordination_content,
        observed_at,
        _seal=_FETCHED_ROUTE_SEAL,
    )


def _decode_yaml_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"0|[1-9][0-9]*", value):
        return int(value)
    if value.startswith("[") and value.endswith("]"):
        members = [member.strip() for member in value[1:-1].split(",") if member.strip()]
        return tuple(_decode_yaml_scalar(member) for member in members)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if not value or any(token in value for token in ("&", "*", "!", "${")):
        raise ValidationError("route scalar contains unsupported YAML indirection")
    return value


def _safe_reason(error: Exception, fallback: str) -> str:
    candidate = str(error)
    return candidate if _REASON_CODE.fullmatch(candidate) else fallback


def _parse_route_yaml(content: bytes, label: str) -> Mapping[str, Any]:
    """Parse the closed scalar mapping subset used by the two route files.

    Route files may contain explanatory blocks and lists outside the authority
    fields.  Those are ignored, while every mapped scalar path is duplicate
    checked.  Aliases, tags and unsupported indirection fail closed.
    """

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{label} is not UTF-8 YAML") from exc
    paths: dict[str, Any] = {}
    stack: list[tuple[int, str]] = []
    block_indent: int | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if "\t" in line[:indent + 1]:
            raise ValidationError(f"{label} uses tabs at line {number}")
        if block_indent is not None and indent > block_indent:
            continue
        block_indent = None
        match = _YAML_KEY.fullmatch(line)
        if match is None:
            if line.lstrip().startswith("- "):
                continue
            raise ValidationError(f"{label} has unsupported YAML at line {number}")
        if indent != len(match.group("indent")):
            raise ValidationError(f"{label} has malformed indentation at line {number}")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        key = match.group("key")
        value = match.group("value")
        full_path = ".".join([entry[1] for entry in stack] + [key])
        if value is None:
            stack.append((indent, key))
            continue
        if value.strip() in {"|", ">", "|-", ">-"}:
            block_indent = indent
            continue
        if full_path in paths:
            raise ValidationError(f"{label} has duplicate YAML key path: {full_path}")
        paths[full_path] = _decode_yaml_scalar(value)
    return paths


def parse_route_authority(
    active_task_content: bytes,
    coordination_content: bytes,
    *,
    executable_canary: bool = False,
) -> RouteAuthority:
    active = _parse_route_yaml(active_task_content, "active route")
    coordination = _parse_route_yaml(coordination_content, "coordination route")
    fields = (
        "task_id",
        "route_epoch",
        "status",
        "execution_allowed",
        "automatic_dispatch_allowed",
        "canary_execution_allowed",
    )
    values: dict[str, Any] = {}
    for field in fields:
        active_value = active.get(field)
        coordination_value = coordination.get(f"agents.CODEX.{field}")
        if active_value is None or coordination_value is None:
            raise ValidationError(f"route authority field missing: {field}")
        if active_value != coordination_value:
            raise ValidationError(f"route authority field mismatch: {field}")
        values[field] = active_value
    active_actors = active.get("authorized_approval_actors")
    coordination_actors = coordination.get("agents.CODEX.authorized_approval_actors")
    if active_actors is None or coordination_actors is None or active_actors == () or coordination_actors == ():
        raise ValidationError("route_authorized_actor_policy_missing")
    if active_actors != coordination_actors or not isinstance(active_actors, tuple):
        raise ValidationError("route authorized approval actor policy mismatch")
    if not all(isinstance(actor, str) for actor in active_actors):
        raise ValidationError("route authorized approval actor policy is invalid")
    authority = RouteAuthority(
        task_id=values["task_id"],
        route_epoch=values["route_epoch"],
        status=values["status"],
        execution_allowed=values["execution_allowed"],
        automatic_dispatch_allowed=values["automatic_dispatch_allowed"],
        canary_execution_allowed=values["canary_execution_allowed"],
        authorized_approval_actors=active_actors,
    )
    if executable_canary:
        if not authority.automatic_dispatch_allowed or not authority.canary_execution_allowed:
            raise ValidationError("executable_canary_route_flags_not_enabled")
    elif authority.automatic_dispatch_allowed or authority.canary_execution_allowed:
        raise ValidationError("pre_canary_route_flags_not_disabled")
    return authority


@dataclass(frozen=True, init=False)
class RouteProofVerification:
    status: VerificationStatus
    evidence: RouteStateEvidence | None
    verified_at: str
    reason_code: str

    def __init__(
        self,
        status: VerificationStatus,
        evidence: RouteStateEvidence | None,
        verified_at: str,
        reason_code: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _ROUTE_RESULT_SEAL:
            raise ValidationError("route proof results are verifier-internal")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "reason_code", reason_code)
        parse_rfc3339_utc(verified_at, "route proof verified_at")
        require_identifier(reason_code, "route proof reason")
        if status is VerificationStatus.READ_ONLY_FETCH_VERIFIED and evidence is None:
            raise ValidationError("verified route proof requires evidence")
        if status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED and evidence is not None:
            raise ValidationError("unverified route proof must not carry trusted evidence")

    @classmethod
    def rejected(cls, verified_at: str, reason_code: str) -> "RouteProofVerification":
        return cls(VerificationStatus.REJECTED, None, verified_at, reason_code, _seal=_ROUTE_RESULT_SEAL)

    @classmethod
    def unknown(cls, verified_at: str, reason_code: str) -> "RouteProofVerification":
        return cls(VerificationStatus.UNKNOWN, None, verified_at, reason_code, _seal=_ROUTE_RESULT_SEAL)

    def validates(self, route: RouteRef) -> str | None:
        if self.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
            return "route_read_only_verification_required"
        assert self.evidence is not None
        if self.evidence.route != route:
            return "route_proof_route_mismatch"
        return None


def _verified_route(evidence: RouteStateEvidence, verified_at: str) -> RouteProofVerification:
    return RouteProofVerification(
        VerificationStatus.READ_ONLY_FETCH_VERIFIED,
        evidence,
        verified_at,
        "trusted_main_ref_commit_tree_path_blob_content_and_route_flags_verified",
        _seal=_ROUTE_RESULT_SEAL,
    )


class ReadOnlyRouteProofVerifier:
    """Turn a sealed transport snapshot into a route proof, or reject it."""

    def verify(
        self,
        route: RouteRef,
        expected_task_id: str,
        snapshot: FetchedRouteSnapshot,
        checked_at: str,
        max_age_seconds: int = DEFAULT_MAX_ROUTE_PROOF_AGE_SECONDS,
    ) -> RouteProofVerification:
        checked = parse_rfc3339_utc(checked_at, "route proof checked_at")
        require_identifier(expected_task_id, "expected route task_id")
        if not isinstance(snapshot, FetchedRouteSnapshot):
            return RouteProofVerification.rejected(checked_at, "route_snapshot_not_transport_bound")
        if not isinstance(max_age_seconds, int) or max_age_seconds < 0:
            raise ValidationError("max route proof age must be a non-negative integer")
        observed = parse_rfc3339_utc(snapshot.observed_at, "route state observed_at")
        if observed > checked:
            return RouteProofVerification.rejected(checked_at, "route_observation_in_future")
        if checked - observed > timedelta(seconds=max_age_seconds):
            return RouteProofVerification.rejected(checked_at, "route_proof_stale")
        try:
            authority = parse_route_authority(snapshot.active_task_content, snapshot.coordination_content)
        except ValidationError as exc:
            return RouteProofVerification.rejected(checked_at, _safe_reason(exc, "route_authority_semantic_rejected"))
        if authority.route_epoch != route.route_epoch:
            return RouteProofVerification.rejected(checked_at, "route_epoch_mismatch")
        if authority.task_id != expected_task_id:
            return RouteProofVerification.rejected(checked_at, "route_task_id_mismatch")
        evidence = RouteStateEvidence(
            route=route,
            repository=snapshot.repository,
            ref=snapshot.ref,
            main_commit_sha1=snapshot.main_commit_sha1,
            main_tree_sha1=snapshot.main_tree_sha1,
            active_task=snapshot.active_task,
            coordination=snapshot.coordination,
            authority=authority,
            observed_at=snapshot.observed_at,
        )
        return _verified_route(evidence, checked_at)


class ExecutableCanaryRouteProofVerifier:
    """Verify the exact route form that is authorized for one executable Canary.

    This verifier is deliberately separate from :class:`ReadOnlyRouteProofVerifier`.
    Historical and pre-canary callers remain fail-closed whenever either execution
    switch is true; only a caller that explicitly selects this verifier can require
    both switches to be true.
    """

    def verify(
        self,
        route: RouteRef,
        expected_task_id: str,
        snapshot: FetchedRouteSnapshot,
        checked_at: str,
        max_age_seconds: int = DEFAULT_MAX_ROUTE_PROOF_AGE_SECONDS,
    ) -> RouteProofVerification:
        checked = parse_rfc3339_utc(checked_at, "route proof checked_at")
        require_identifier(expected_task_id, "expected route task_id")
        if not isinstance(snapshot, FetchedRouteSnapshot):
            return RouteProofVerification.rejected(checked_at, "route_snapshot_not_transport_bound")
        if not isinstance(max_age_seconds, int) or max_age_seconds < 0:
            raise ValidationError("max route proof age must be a non-negative integer")
        observed = parse_rfc3339_utc(snapshot.observed_at, "route state observed_at")
        if observed > checked:
            return RouteProofVerification.rejected(checked_at, "route_observation_in_future")
        if checked - observed > timedelta(seconds=max_age_seconds):
            return RouteProofVerification.rejected(checked_at, "route_proof_stale")
        try:
            authority = parse_route_authority(
                snapshot.active_task_content,
                snapshot.coordination_content,
                executable_canary=True,
            )
        except ValidationError as exc:
            return RouteProofVerification.rejected(checked_at, _safe_reason(exc, "route_authority_semantic_rejected"))
        if authority.route_epoch != route.route_epoch:
            return RouteProofVerification.rejected(checked_at, "route_epoch_mismatch")
        if authority.task_id != expected_task_id:
            return RouteProofVerification.rejected(checked_at, "route_task_id_mismatch")
        evidence = RouteStateEvidence(
            route=route,
            repository=snapshot.repository,
            ref=snapshot.ref,
            main_commit_sha1=snapshot.main_commit_sha1,
            main_tree_sha1=snapshot.main_tree_sha1,
            active_task=snapshot.active_task,
            coordination=snapshot.coordination,
            authority=authority,
            observed_at=snapshot.observed_at,
        )
        return _verified_route(evidence, checked_at)


class ReadOnlyApprovalVerifier:
    """Derive approval authority only from a sealed comment and sealed route proof."""

    def verify(
        self,
        approval: BoundCanaryApproval,
        document: ReadOnlyApprovalDocument,
        route_proof: RouteProofVerification,
        checked_at: str,
    ) -> ApprovalVerificationResult:
        parse_rfc3339_utc(checked_at, "approval checked_at")
        if not isinstance(document, ReadOnlyApprovalDocument):
            return ApprovalVerificationResult.rejected(checked_at, "approval_comment_not_transport_bound")
        if route_proof.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED or route_proof.evidence is None:
            return ApprovalVerificationResult.rejected(checked_at, "approval_route_authority_unverified")
        if document.repository != route_proof.evidence.repository:
            return ApprovalVerificationResult.rejected(checked_at, "approval_repository_mismatch")
        if document.actor not in route_proof.evidence.authority.authorized_approval_actors:
            return ApprovalVerificationResult.rejected(checked_at, "approval_actor_not_authorized_by_route")
        try:
            binding = parse_canonical_approval_body(document.body)
        except ValidationError as exc:
            return ApprovalVerificationResult.rejected(checked_at, _safe_reason(exc, "approval_body_canonical_parse_rejected"))
        if (
            binding.task_id != approval.task_id
            or binding.route_epoch != approval.route_epoch
            or binding.canary_id != approval.canary_id
            or binding.scope != approval.scope
            or binding.expires_at != approval.expires_at
            or binding.nonce != approval.nonce
        ):
            return ApprovalVerificationResult.rejected(checked_at, "approval_body_binding_mismatch")
        if parse_rfc3339_utc(binding.expires_at, "approval expires_at") <= parse_rfc3339_utc(checked_at, "approval checked_at"):
            return ApprovalVerificationResult.rejected(checked_at, "approval_expired")
        if binding.task_id != route_proof.evidence.authority.task_id or binding.route_epoch != route_proof.evidence.authority.route_epoch:
            return ApprovalVerificationResult.rejected(checked_at, "approval_route_binding_mismatch")
        evidence = ApprovalEvidence(
            repository=document.repository,
            issue_number=document.issue_number,
            comment_id=document.comment_id,
            actor=document.actor,
            issued_at=document.issued_at,
            body_sha256=document.body_sha256,
            approval_ref=document.approval_ref,
            binding_payload_sha256=binding.payload_sha256(document.approval_ref),
        )
        error = evidence.validates(approval, checked_at)
        if error is not None:
            return ApprovalVerificationResult.rejected(checked_at, error)
        return _verified_approval(evidence, checked_at)
