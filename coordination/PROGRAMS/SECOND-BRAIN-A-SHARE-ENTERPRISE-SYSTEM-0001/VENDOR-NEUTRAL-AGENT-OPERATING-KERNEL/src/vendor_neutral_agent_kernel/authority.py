"""Deterministic project-authority resolution without vendor preferences."""

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


_RANK = {
    AuthorityKind.USER_EXPLICIT_DECISION: 700,
    AuthorityKind.PROJECT_CHARTER: 600,
    AuthorityKind.ACTIVE_ROUTE: 500,
    AuthorityKind.AGENT_ROLE: 400,
    AuthorityKind.SKILL_CONTRACT: 300,
    AuthorityKind.TOOL_CAPABILITY: 200,
    AuthorityKind.MODEL_PROFILE: 100,
}


@dataclass(frozen=True)
class AuthorityDirective:
    kind: AuthorityKind
    source_id: str
    task_id: str | None = None
    allowed_paths: tuple[str, ...] = ()
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    approval_requirements: tuple[str, ...] = ()
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
            self.evidence_refs,
        ):
            if len(set(values)) != len(values):
                raise ValueError("DIRECTIVE_DUPLICATE_VALUE:" + self.source_id)

    @property
    def rank(self) -> int:
        return _RANK[self.kind]


def _first_ranked_value(
    directives: tuple[AuthorityDirective, ...],
    attribute: str,
) -> tuple[str, ...]:
    for directive in directives:
        value = getattr(directive, attribute)
        if value:
            return tuple(value)
    return ()


def resolve_authority(
    meta: ContractMeta,
    directives: tuple[AuthorityDirective, ...],
    *,
    agent_id: str,
) -> AuthorityResolution:
    if not directives:
        raise ValueError("AUTHORITY_DIRECTIVES_REQUIRED")
    ordered = tuple(sorted(directives, key=lambda item: (-item.rank, item.source_id)))
    conflicts: list[str] = []

    task_directives = tuple(item for item in ordered if item.task_id)
    if not task_directives:
        raise ValueError("EFFECTIVE_TASK_ID_UNRESOLVED")
    effective_task = task_directives[0].task_id
    assert effective_task is not None
    for item in task_directives[1:]:
        if item.task_id != effective_task:
            conflicts.append(
                "TASK_CONFLICT:"
                + task_directives[0].source_id
                + "="
                + effective_task
                + ":"
                + item.source_id
                + "="
                + str(item.task_id)
            )

    actions = sorted(
        {
            action
            for directive in ordered
            for action in directive.allowed_actions + directive.forbidden_actions
        }
    )
    allowed: list[str] = []
    forbidden: list[str] = []
    for action in actions:
        mentions = tuple(
            item
            for item in ordered
            if action in item.allowed_actions or action in item.forbidden_actions
        )
        top_rank = mentions[0].rank
        top = tuple(item for item in mentions if item.rank == top_rank)
        top_allows = any(action in item.allowed_actions for item in top)
        top_forbids = any(action in item.forbidden_actions for item in top)
        if top_allows and top_forbids:
            forbidden.append(action)
            conflicts.append("SAME_RANK_ACTION_CONFLICT:" + action)
        elif top_forbids:
            forbidden.append(action)
        else:
            allowed.append(action)
        for lower in mentions[len(top):]:
            lower_allows = action in lower.allowed_actions
            if lower_allows != top_allows:
                conflicts.append(
                    "OVERRIDDEN_ACTION:"
                    + action
                    + ":"
                    + top[0].source_id
                    + ">"
                    + lower.source_id
                )

    allowed_paths = _first_ranked_value(ordered, "allowed_paths")
    for item in ordered:
        if item.allowed_paths and tuple(item.allowed_paths) != allowed_paths:
            conflicts.append(
                "OVERRIDDEN_PATH_SCOPE:"
                + ordered[0].source_id
                + ">"
                + item.source_id
            )

    approvals = sorted(
        {
            action
            for item in ordered
            for action in item.approval_requirements
            if action not in allowed
        }
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
        "allowed_paths": allowed_paths,
        "allowed_actions": allowed,
        "forbidden_actions": forbidden,
        "approvals": approvals,
        "directives": ordered,
    }
    result = AuthorityResolution(
        meta=meta,
        effective_task_id=effective_task,
        agent_id=agent_id,
        allowed_paths=tuple(allowed_paths),
        allowed_actions=tuple(allowed),
        forbidden_actions=tuple(forbidden),
        approval_requirements=tuple(approvals),
        conflicts=tuple(sorted(set(conflicts))),
        resolution_evidence=evidence,
        authority_hash=canonical_sha256(resolution_payload),
    )
    return seal_contract(result)
