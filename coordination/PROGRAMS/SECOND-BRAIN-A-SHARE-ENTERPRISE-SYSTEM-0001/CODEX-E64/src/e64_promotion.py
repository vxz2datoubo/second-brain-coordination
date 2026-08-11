"""Public-safe E64 GitHub-native promotion candidate.

This is an application-level verifier and in-memory state model.  It has no
GitHub API client, credentials, signing key, or filesystem write path.  A
successful result is an auditable *candidate receipt*, never a real formal
knowledge write.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import re
from threading import Lock
from typing import Mapping


SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PromotionError(ValueError):
    """Fail-closed validation or state-transition failure."""


class ReplayRejected(PromotionError):
    """A one-time approval has already been claimed or consumed."""


class AdmissionClass(str, Enum):
    PUBLIC_SAFE = "PUBLIC_SAFE"
    PRIVATE_OR_SENSITIVE = "PRIVATE_OR_SENSITIVE"
    SECRET_CREDENTIAL = "SECRET_CREDENTIAL"


class PromotionState(str, Enum):
    APPROVED = "APPROVED"
    CLAIMED = "CLAIMED"
    PROMOTED_CANDIDATE = "PROMOTED_CANDIDATE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _require_sha256(name: str, value: str) -> None:
    if not SHA256.fullmatch(value):
        raise PromotionError(f"{name} must be a lowercase 64-hex SHA-256")


@dataclass(frozen=True)
class E48DigestBundle:
    """Typed producer boundary; E64 never recomputes semantic identity."""

    raw_artifact_sha256: str
    canonical_semantic_sha256: str
    l0_provenance_sha256: str

    def __post_init__(self) -> None:
        _require_sha256("raw_artifact_sha256", self.raw_artifact_sha256)
        _require_sha256("canonical_semantic_sha256", self.canonical_semantic_sha256)
        _require_sha256("l0_provenance_sha256", self.l0_provenance_sha256)

    def as_dict(self) -> dict[str, str]:
        return {
            "raw_artifact_sha256": self.raw_artifact_sha256,
            "canonical_semantic_sha256": self.canonical_semantic_sha256,
            "l0_provenance_sha256": self.l0_provenance_sha256,
        }


@dataclass(frozen=True)
class CandidateKnowledgePackage:
    candidate_package_id: str
    repository_id: str
    repository_slug: str
    task_id: str
    route_epoch: int
    digest_bundle: E48DigestBundle
    source_provenance_status: str
    target_scope: str
    admission_class: AdmissionClass
    expected_canonical_main_parent: str

    def __post_init__(self) -> None:
        if not all((self.candidate_package_id, self.repository_id, self.repository_slug, self.task_id)):
            raise PromotionError("candidate identity fields must be non-empty")
        if self.route_epoch < 1:
            raise PromotionError("route_epoch must be positive")
        if self.target_scope not in {"PROJECT", "GLOBAL"}:
            raise PromotionError("target_scope is not explicit")
        _require_sha256("expected_canonical_main_parent", self.expected_canonical_main_parent)

    def identity_payload(self) -> dict[str, object]:
        return {
            "candidate_package_id": self.candidate_package_id,
            "repository_id": self.repository_id,
            "repository_slug": self.repository_slug,
            "task_id": self.task_id,
            "route_epoch": self.route_epoch,
            "digest_bundle": self.digest_bundle.as_dict(),
            "source_provenance_status": self.source_provenance_status,
            "target_scope": self.target_scope,
            "admission_class": self.admission_class.value,
            "expected_canonical_main_parent": self.expected_canonical_main_parent,
        }

    @property
    def identity_sha256(self) -> str:
        return sha256(_canonical_bytes(self.identity_payload())).hexdigest()


@dataclass(frozen=True)
class ApprovalPacket:
    approval_id: str
    candidate_identity_sha256: str
    approval_actor_ref: str
    gpt_review_ref: str
    approved_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if not all((self.approval_id, self.approval_actor_ref, self.gpt_review_ref)):
            raise PromotionError("approval requires id, actor reference, and GPT review reference")
        _require_sha256("candidate_identity_sha256", self.candidate_identity_sha256)
        if self.approved_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise PromotionError("approval timestamps must be timezone-aware")
        if self.expires_at <= self.approved_at:
            raise PromotionError("approval expiry must follow approval time")


@dataclass(frozen=True)
class PromotionPolicy:
    repository_id: str
    repository_slug: str
    task_id: str
    route_epoch: int
    allowed_source_statuses: frozenset[str]

    def validate_candidate(self, candidate: CandidateKnowledgePackage) -> None:
        if candidate.admission_class is not AdmissionClass.PUBLIC_SAFE:
            raise PromotionError("only PUBLIC_SAFE packages may enter public promotion")
        if (candidate.repository_id, candidate.repository_slug) != (self.repository_id, self.repository_slug):
            raise PromotionError("candidate repository identity does not match policy")
        if (candidate.task_id, candidate.route_epoch) != (self.task_id, self.route_epoch):
            raise PromotionError("candidate task route identity does not match policy")
        if candidate.source_provenance_status not in self.allowed_source_statuses:
            raise PromotionError("source provenance status is not accepted")


@dataclass
class _LedgerEntry:
    approval: ApprovalPacket
    expected_parent: str
    state: PromotionState = PromotionState.APPROVED
    promotion_id: str | None = None


@dataclass(frozen=True)
class PromotionReceipt:
    promotion_id: str
    approval_id: str
    candidate_identity_sha256: str
    expected_parent: str
    observed_parent: str
    state: PromotionState
    formal_knowledge_written: bool = False


class GitHubNativePromotionAdapter:
    """Models a narrow promotion gate; caller must perform any future Git CAS."""

    def __init__(self, policy: PromotionPolicy) -> None:
        self._policy = policy
        self._entries: dict[str, _LedgerEntry] = {}
        self._lock = Lock()

    def register_approval(self, candidate: CandidateKnowledgePackage, approval: ApprovalPacket) -> None:
        self._policy.validate_candidate(candidate)
        if approval.candidate_identity_sha256 != candidate.identity_sha256:
            raise PromotionError("approval is not bound to this exact candidate identity")
        with self._lock:
            if approval.approval_id in self._entries:
                raise ReplayRejected("approval identifier already registered")
            self._entries[approval.approval_id] = _LedgerEntry(approval, candidate.expected_canonical_main_parent)

    def claim(self, candidate: CandidateKnowledgePackage, approval_id: str, now: datetime) -> str:
        self._policy.validate_candidate(candidate)
        if now.tzinfo is None:
            raise PromotionError("claim time must be timezone-aware")
        with self._lock:
            entry = self._entries.get(approval_id)
            if entry is None:
                raise PromotionError("approval was not registered")
            if entry.approval.candidate_identity_sha256 != candidate.identity_sha256:
                raise PromotionError("candidate changed after approval")
            if now >= entry.approval.expires_at:
                entry.state = PromotionState.EXPIRED
                raise PromotionError("approval has expired")
            if entry.state is not PromotionState.APPROVED:
                raise ReplayRejected("approval is no longer available for promotion")
            entry.state = PromotionState.CLAIMED
            entry.promotion_id = f"promotion:{approval_id}"
            return entry.promotion_id

    def revoke(self, approval_id: str) -> None:
        with self._lock:
            entry = self._entries.get(approval_id)
            if entry is None:
                raise PromotionError("approval was not registered")
            if entry.state is PromotionState.PROMOTED_CANDIDATE:
                raise ReplayRejected("promotion candidate is already consumed")
            entry.state = PromotionState.REVOKED

    def promote_candidate(self, approval_id: str, promotion_id: str, observed_canonical_main_parent: str) -> PromotionReceipt:
        """Validate CAS and consume one approval without writing a repository."""
        _require_sha256("observed_canonical_main_parent", observed_canonical_main_parent)
        with self._lock:
            entry = self._entries.get(approval_id)
            if entry is None or entry.promotion_id != promotion_id:
                raise PromotionError("promotion capability does not match approval")
            if entry.state is not PromotionState.CLAIMED:
                raise ReplayRejected("promotion capability has already been consumed or revoked")
            if observed_canonical_main_parent != entry.expected_parent:
                raise PromotionError("canonical main parent changed; CAS promotion rejected")
            entry.state = PromotionState.PROMOTED_CANDIDATE
            return PromotionReceipt(
                promotion_id=promotion_id,
                approval_id=approval_id,
                candidate_identity_sha256=entry.approval.candidate_identity_sha256,
                expected_parent=entry.expected_parent,
                observed_parent=observed_canonical_main_parent,
                state=entry.state,
            )
