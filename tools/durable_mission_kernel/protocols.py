"""B6 — Reviewer / Canonicalizer independence protocols + no-self-merge enforcement.

Encodes the #618 canonicalizer hardening + the R188 independence contract:

- author != reviewer != canonicalizer (independence);
- author/orchestrator can never self-merge;
- canonicalizer READY requires actual capability evidence, not only a read-only gate;
- if the canonicalizer cannot perform the required mechanical action, fail closed
  or reroute to another legitimate canonicalizer carrier (never fall back to self-merge).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schemas import Role, ROLE_INDEPENDENCE_RULE


class ProtocolError(ValueError):
    """Raised on any independence / self-merge / capability violation (fail closed)."""


@dataclass(frozen=True)
class PrincipalSet:
    author: str
    reviewer: Optional[str] = None
    canonicalizer: Optional[str] = None


def assert_principal_independence(p: PrincipalSet) -> bool:
    """Enforce author != reviewer != canonicalizer (when roles are present)."""
    identities = [p.author]
    if p.reviewer is not None:
        identities.append(p.reviewer)
    if p.canonicalizer is not None:
        identities.append(p.canonicalizer)
    if len(set(identities)) != len(identities):
        raise ProtocolError(
            f"INDEPENDENCE_VIOLATION: {ROLE_INDEPENDENCE_RULE}; observed {p}"
        )
    return True


def assert_no_self_merge(author: str, canonicalizer: str) -> bool:
    """The author/orchestrator can never be the canonicalizer (no self-merge)."""
    if author == canonicalizer:
        raise ProtocolError("SELF_MERGE_FORBIDDEN: author == canonicalizer")
    return True


def assert_no_self_review(author: str, reviewer: str) -> bool:
    """The author can never be the reviewer (no self-review)."""
    if author == reviewer:
        raise ProtocolError("SELF_REVIEW_FORBIDDEN: author == reviewer")
    return True


@dataclass(frozen=True)
class CanonicalizerCapability:
    """Evidence that a canonicalizer can actually perform the mechanical merge."""

    principal: str
    can_merge: bool
    can_write: bool
    merge_permission_verified: bool
    evidence: str


def canonicalizer_ready(cap: CanonicalizerCapability) -> bool:
    """A canonicalizer is READY only with actual capability evidence.

    A read-only gate check is NOT sufficient (see EVIDENCE-CONTRACT
    ``canonicalizer_ready_requires``).
    """
    if not cap.can_merge or not cap.merge_permission_verified:
        raise ProtocolError(
            "CANONICALIZER_CAPABILITY_UNAVAILABLE: merge capability not evidenced"
        )
    return True


def reroute_or_fail_closed(
    *, author: str, canonicalizer: CanonicalizerCapability | None,
    fallback: CanonicalizerCapability | None,
) -> str:
    """Return the principal authorized to merge, or raise.

    - If the canonicalizer has real capability -> use it.
    - Else if a *legitimate independent* fallback has real capability -> use it.
    - Otherwise fail closed (never fall back to self-merge).
    """
    if canonicalizer is not None and _cap_ok(canonicalizer):
        assert_no_self_merge(author, canonicalizer.principal)
        return canonicalizer.principal
    if fallback is not None and _cap_ok(fallback):
        assert_no_self_merge(author, fallback.principal)
        return fallback.principal
    raise ProtocolError(
        "CANONICALIZER_CAPABILITY_UNAVAILABLE: no legitimate canonicalizer with merge capability; "
        "fail closed (self-merge permanently forbidden)"
    )


def _cap_ok(cap: CanonicalizerCapability) -> bool:
    return cap.can_merge and cap.merge_permission_verified
