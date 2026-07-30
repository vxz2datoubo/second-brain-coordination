"""Fail-closed project-authority resolution without vendor preferences."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .canonical import canonical_sha256, seal_contract
from .contracts import AuthorityResolution, ContractMeta


class AuthorityKind(str, Enum):
    USER_EXPLICIT_DECISION = "USER_EXPLICIT_DECISION"
    PROJECT_CHARTER = "PROJECT_CHARTER"
    ACTIVE_ROUTE = "ACTIVE_ROUTE"
    AGENT_ROLE = "AGENT_ROLE"
    SKILL_CONTRACT = "SKILL_CONTRACT"
    TOOL_CAPABILITY = "TOOL_CAPABILITY"
    MODEL_PROFILE = "MODEL_PROFILE"


_RESTRICTIVE_KINDS = frozenset(AuthorityKind)
_AUTHORIZATION_KINDS = frozenset(
    {
        AuthorityKind.USER_EXPLICIT_DECISION,
        AuthorityKind.PROJECT_CHARTER,
        AuthorityKind.ACTIVE_ROUTE,
    }
)
_EXECUTION_FEASIBILITY_KINDS = frozenset(
    {
        AuthorityKind.AGENT_ROLE,
        AuthorityKind.SKILL_CONTRACT,
        AuthorityKind.TOOL_CAPABILITY,
        AuthorityKind.MODEL_PROFILE,
    }
)


@dataclass(frozen=True)
class AuthorityDirective:
    kind: AuthorityKind
    source_id: str
    task_id: str | None = None
    allowed_paths: tuple[str, ...] = ()
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    approval_requirements: tuple[str, ...] = ()
    verified_approval_actions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.source_id) is not str or not self.source_id:
            raise ValueError("AUTHORITY_SOURCE_ID_REQUIRED")
        if set(self.allowed_actions) & set(self.forbidden_actions):
            raise ValueError("DIRECTIVE_ACTION_CONTRADICTION:" + self.source_id)
        for values in (
            self.allowed_paths,
            self.allowed_actions,
            self.forbidden_actions,
            self.approval_requirements,
            self.verified_approval_actions,
            self.evidence_refs,
        ):
            if len(set(values)) != len(values):
                raise ValueError("DIRECTIVE_DUPLICATE_VALUE:" + self.source_id)

        if self.verified_approval_actions and self.kind is not AuthorityKind.ACTIVE_ROUTE:
            raise ValueError("VERIFIED_APPROVALS_REQUIRE_ACTIVE_ROUTE")
        if not set(self.verified_approval_actions) <= set(self.approval_requirements):
            raise ValueError("VERIFIED_APPROVAL_NOT_REQUIRED")


def _normalise_scope(scope: str) -> str:
    return scope.rstrip("*").rstrip("/")


def _scope_overlap(left: str, right: str) -> str | None:
    left_normalised = _normalise_scope(left)
    right_normalised = _normalise_scope(right)
    if left_normalised == right_normalised:
        return left if len(left) >= len(right) else right
    if left_normalised.startswith(right_normalised + "/"):
        return left
    if right_normalised.startswith(left_normalised + "/"):
        return right
    return None


def _intersect_path_scopes(groups: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    nonempty = tuple(group for group in groups if group)
    if not nonempty:
        return ()
    candidates = tuple(sorted(set(nonempty[0])))
    for group in nonempty[1:]:
        candidates = tuple(
            sorted(
                {
                    overlap
                    for current in candidates
                    for requested in group
                    if (overlap := _scope_overlap(current, requested)) is not None
                }
            )
        )
        if not candidates:
            return ()
    return candidates


def _same_kind_conflicts(
    directives: tuple[AuthorityDirective, ...],
    *,
    attribute: str,
) -> tuple[str, ...]:
    conflicts: set[str] = set()
    actions = {
        action
        for directive in directives
        for action in directive.allowed_actions + directive.forbidden_actions
    }
    for kind in AuthorityKind:
        peers = tuple(item for item in directives if item.kind is kind)
        for action in actions:
            allowed = any(action in item.allowed_actions for item in peers)
            forbidden = any(action in item.forbidden_actions for item in peers)
            if allowed and forbidden:
                conflicts.add(
                    "BLOCKED_AUTHORITY_CONFLICT:SAME_RANK_"
                    + attribute
                    + ":"
                    + kind.value
                    + ":"
                    + action
                )
    return tuple(sorted(conflicts))


def is_action_executable(resolution: AuthorityResolution, action: str) -> bool:
    """Return whether a permitted action also has every required approval."""

    return (
        resolution.resolution_status == "READY"
        and action in resolution.allowed_actions
        and action not in resolution.forbidden_actions
        and (
            action not in resolution.approval_requirements
            or action in resolution.verified_approval_actions
        )
    )


def resolve_authority(
    meta: ContractMeta,
    directives: tuple[AuthorityDirective, ...],
    *,
    agent_id: str,
) -> AuthorityResolution:
    if not directives:
        raise ValueError("AUTHORITY_DIRECTIVES_REQUIRED")
    ordered = tuple(sorted(directives, key=lambda item: (item.kind.value, item.source_id)))
    conflicts: list[str] = list(_same_kind_conflicts(ordered, attribute="ACTION"))

    route_directives = tuple(item for item in ordered if item.kind is AuthorityKind.ACTIVE_ROUTE)
    route_tasks = tuple(sorted({item.task_id for item in route_directives if item.task_id}))
    if not route_tasks:
        raise ValueError("ACTIVE_ROUTE_TASK_REQUIRED")
    if len(route_tasks) != 1:
        effective_task = "UNRESOLVED"
        conflicts.append("BLOCKED_AUTHORITY_CONFLICT:ACTIVE_ROUTE_TASK")
    else:
        effective_task = route_tasks[0]

    authorization_directives = tuple(
        item for item in ordered if item.kind in _AUTHORIZATION_KINDS
    )
    paths = _intersect_path_scopes(
        tuple(item.allowed_paths for item in authorization_directives if item.allowed_paths)
    )
    if any(item.allowed_paths for item in authorization_directives) and not paths:
        conflicts.append("BLOCKED_AUTHORITY_CONFLICT:PATH_SCOPE_INTERSECTION_EMPTY")

    all_actions = tuple(
        sorted(
            {
                action
                for directive in ordered
                for action in directive.allowed_actions + directive.forbidden_actions
            }
        )
    )
    hard_forbidden = {
        action
        for directive in ordered
        if directive.kind in _RESTRICTIVE_KINDS
        for action in directive.forbidden_actions
    }
    allowed: list[str] = []
    for action in all_actions:
        route_allows = any(action in item.allowed_actions for item in route_directives)
        project_directives = tuple(
            item for item in ordered if item.kind is AuthorityKind.PROJECT_CHARTER
        )
        project_allows = not any(item.allowed_actions for item in project_directives) or any(
            action in item.allowed_actions for item in project_directives
        )
        user_directives = tuple(
            item for item in ordered if item.kind is AuthorityKind.USER_EXPLICIT_DECISION
        )
        user_allows = not any(item.allowed_actions for item in user_directives) or any(
            action in item.allowed_actions for item in user_directives
        )
        if route_allows and project_allows and user_allows and action not in hard_forbidden:
            allowed.append(action)

    feasibility_allows = {
        action
        for item in ordered
        if item.kind in _EXECUTION_FEASIBILITY_KINDS
        for action in item.allowed_actions
    }
    for action in sorted(feasibility_allows):
        if action not in allowed:
            conflicts.append("NONAUTHORITY_ALLOW_IGNORED:" + action)

    approvals = tuple(
        sorted(
            {
                action
                for item in ordered
                for action in item.approval_requirements
            }
        )
    )
    verified_approvals = tuple(
        sorted(
            {
                action
                for item in route_directives
                for action in item.verified_approval_actions
            }
        )
    )
    evidence = tuple(
        sorted(
            {
                ref
                for item in ordered
                for ref in ((item.source_id,) + item.evidence_refs)
            }
        )
    )
    resolution_payload = {
        "task_id": effective_task,
        "agent_id": agent_id,
        "allowed_paths": paths,
        "allowed_actions": allowed,
        "forbidden_actions": sorted(hard_forbidden),
        "approvals": approvals,
        "verified_approvals": verified_approvals,
        "directives": ordered,
    }
    status = "BLOCKED_AUTHORITY_CONFLICT" if any(
        item.startswith("BLOCKED_AUTHORITY_CONFLICT") for item in conflicts
    ) else "READY"
    result = AuthorityResolution(
        meta=meta,
        effective_task_id=effective_task,
        agent_id=agent_id,
        allowed_paths=tuple(paths),
        allowed_actions=tuple(allowed),
        forbidden_actions=tuple(sorted(hard_forbidden)),
        approval_requirements=approvals,
        verified_approval_actions=verified_approvals,
        conflicts=tuple(sorted(set(conflicts))),
        resolution_evidence=evidence,
        resolution_status=status,
        authority_hash=canonical_sha256(resolution_payload),
    )
    return seal_contract(result)
