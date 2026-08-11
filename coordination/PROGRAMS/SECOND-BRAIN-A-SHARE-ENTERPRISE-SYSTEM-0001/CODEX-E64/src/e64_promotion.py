"""E64 R2 public-safe GitHub-native promotion verification model.

No GitHub API client, credential, signing key, or formal-knowledge writer is
included.  Production integrations must supply a read-only canonical GitHub
evidence resolver and an atomic Git marker/CAS store.  Test doubles below are
strictly in-memory models of those external boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
import re
from threading import Lock
from typing import Protocol


SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class PromotionError(ValueError):
    """Fail-closed validation failure; messages never include source content."""


class ReplayRejected(PromotionError):
    """A durable marker has already consumed or conflicts with the request."""


class UnknownOutcome(PromotionError):
    """A caller must reconcile durable state rather than retry a write."""


class AdmissionClass(str, Enum):
    PUBLIC_SAFE = "PUBLIC_SAFE"
    PRIVATE_OR_SENSITIVE = "PRIVATE_OR_SENSITIVE"
    SECRET_CREDENTIAL = "SECRET_CREDENTIAL"


class MarkerState(str, Enum):
    COMPLETED = "COMPLETED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _require_sha256(name: str, value: str) -> None:
    if not SHA256.fullmatch(value):
        raise PromotionError(f"{name} must be a lowercase 64-hex SHA-256")


def _require_commit(name: str, value: str) -> None:
    if not GIT_COMMIT.fullmatch(value):
        raise PromotionError(f"{name} must be a lowercase 40-hex Git commit")


@dataclass(frozen=True)
class E48DigestBundle:
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
    classification_evidence_ref: str
    classification_evidence_object_sha256: str
    expected_canonical_main_parent: str

    def __post_init__(self) -> None:
        if not all((self.candidate_package_id, self.repository_id, self.repository_slug, self.task_id, self.classification_evidence_ref)):
            raise PromotionError("candidate identity fields must be non-empty")
        if self.route_epoch < 1 or self.target_scope not in {"PROJECT", "GLOBAL"}:
            raise PromotionError("candidate route or target is invalid")
        _require_sha256("classification_evidence_object_sha256", self.classification_evidence_object_sha256)
        _require_commit("expected_canonical_main_parent", self.expected_canonical_main_parent)

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
            "classification_evidence_ref": self.classification_evidence_ref,
            "classification_evidence_object_sha256": self.classification_evidence_object_sha256,
            "expected_canonical_main_parent": self.expected_canonical_main_parent,
        }

    def pre_admission_subject_payload(self) -> dict[str, object]:
        """Fields that exist before an admission-evidence object is created."""
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
    def pre_admission_subject_sha256(self) -> str:
        return sha256(_canonical_bytes(self.pre_admission_subject_payload())).hexdigest()

    @property
    def identity_sha256(self) -> str:
        return sha256(_canonical_bytes(self.identity_payload())).hexdigest()


@dataclass(frozen=True)
class ApprovalPacket:
    """Untrusted locator/hash supplied by caller; resolver is the authority."""

    approval_id: str
    approval_evidence_ref: str
    approval_evidence_object_sha256: str

    def __post_init__(self) -> None:
        if not all((self.approval_id, self.approval_evidence_ref)):
            raise PromotionError("approval requires immutable id and evidence reference")
        _require_sha256("approval_evidence_object_sha256", self.approval_evidence_object_sha256)


@dataclass(frozen=True)
class CanonicalGitHubApprovalEvidence:
    approval_id: str
    evidence_ref: str
    evidence_object_sha256: str
    repository_id: str
    repository_slug: str
    task_id: str
    route_epoch: int
    candidate_identity_sha256: str
    decision: str
    github_control_object_id: str
    canonical_main_commit: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if not all((self.approval_id, self.evidence_ref, self.repository_id, self.repository_slug, self.task_id, self.github_control_object_id)):
            raise PromotionError("canonical approval evidence is partial")
        _require_sha256("evidence_object_sha256", self.evidence_object_sha256)
        _require_sha256("candidate_identity_sha256", self.candidate_identity_sha256)
        _require_commit("canonical_main_commit", self.canonical_main_commit)
        if self.expires_at.tzinfo is None:
            raise PromotionError("approval evidence expiry must be timezone-aware")


@dataclass(frozen=True)
class CanonicalAdmissionEvidence:
    evidence_ref: str
    repository_id: str
    pre_admission_subject_sha256: str
    decision: AdmissionClass

    def __post_init__(self) -> None:
        if not self.evidence_ref or not self.repository_id:
            raise PromotionError("admission evidence is partial")
        _require_sha256("pre_admission_subject_sha256", self.pre_admission_subject_sha256)

    def canonical_payload(self) -> dict[str, str]:
        return {
            "evidence_ref": self.evidence_ref,
            "repository_id": self.repository_id,
            "pre_admission_subject_sha256": self.pre_admission_subject_sha256,
            "decision": self.decision.value,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.canonical_payload())

    @property
    def evidence_object_sha256(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()


class ApprovalEvidenceResolver(Protocol):
    """Production implementation must read canonical GitHub state, not prose."""

    def resolve_approval(self, evidence_ref: str) -> CanonicalGitHubApprovalEvidence | None: ...

    def resolve_admission(self, evidence_ref: str) -> CanonicalAdmissionEvidence | None: ...


@dataclass(frozen=True)
class PromotionPolicy:
    repository_id: str
    repository_slug: str
    task_id: str
    route_epoch: int
    required_control_record_id: str
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


@dataclass(frozen=True)
class PromotionRequest:
    approval_id: str
    promotion_id: str
    candidate_identity_sha256: str
    expected_parent: str
    approval_evidence_object_sha256: str
    classification_evidence_object_sha256: str


@dataclass(frozen=True)
class PromotionReceipt:
    promotion_id: str
    approval_id: str
    candidate_identity_sha256: str
    expected_parent: str
    observed_parent: str
    marker_state: MarkerState
    consumed_now: bool
    formal_knowledge_written: bool = False


class DurablePromotionStore(Protocol):
    """Future implementation must atomically use Git expected-parent CAS."""

    def consume_if_absent(self, request: PromotionRequest, observed_parent: str) -> PromotionReceipt | None: ...


@dataclass(frozen=True)
class _StoredMarker:
    request: PromotionRequest
    state: MarkerState
    receipt: PromotionReceipt | None


class InMemoryDurablePromotionStore:
    """Synthetic shared-CAS store for tests only; never a production backend."""

    def __init__(self) -> None:
        self._markers: dict[str, _StoredMarker] = {}
        self._lock = Lock()
        self.force_unknown_once = False

    def consume_if_absent(self, request: PromotionRequest, observed_parent: str) -> PromotionReceipt | None:
        _require_commit("observed_canonical_main_parent", observed_parent)
        with self._lock:
            if observed_parent != request.expected_parent:
                raise PromotionError("canonical main parent changed; durable CAS rejected")
            existing = self._markers.get(request.approval_id)
            if existing is not None:
                if existing.request != request:
                    raise ReplayRejected("durable marker already exists for this approval")
                if existing.state is MarkerState.UNKNOWN_OUTCOME:
                    raise UnknownOutcome("durable outcome is unknown; reconcile before retry")
                assert existing.receipt is not None
                return PromotionReceipt(**{**existing.receipt.__dict__, "consumed_now": False})
            if self.force_unknown_once:
                self.force_unknown_once = False
                self._markers[request.approval_id] = _StoredMarker(request, MarkerState.UNKNOWN_OUTCOME, None)
                raise UnknownOutcome("durable outcome is unknown; no retry capability issued")
            receipt = PromotionReceipt(
                promotion_id=request.promotion_id,
                approval_id=request.approval_id,
                candidate_identity_sha256=request.candidate_identity_sha256,
                expected_parent=request.expected_parent,
                observed_parent=observed_parent,
                marker_state=MarkerState.COMPLETED,
                consumed_now=True,
            )
            self._markers[request.approval_id] = _StoredMarker(request, MarkerState.COMPLETED, receipt)
            return receipt

    def seed_conflicting_marker(self, request: PromotionRequest) -> None:
        with self._lock:
            self._markers[request.approval_id] = _StoredMarker(request, MarkerState.UNKNOWN_OUTCOME, None)


class GitHubNativePromotionAdapter:
    """Verifies canonical evidence then delegates one-time semantics to CAS."""

    def __init__(self, policy: PromotionPolicy, resolver: ApprovalEvidenceResolver, store: DurablePromotionStore) -> None:
        self._policy = policy
        self._resolver = resolver
        self._store = store

    def prepare(self, candidate: CandidateKnowledgePackage, packet: ApprovalPacket, now: datetime) -> PromotionRequest:
        if now.tzinfo is None:
            raise PromotionError("verification time must be timezone-aware")
        self._policy.validate_candidate(candidate)
        admission = self._resolver.resolve_admission(candidate.classification_evidence_ref)
        if admission is None:
            raise PromotionError("classification evidence was not found in canonical control state")
        if (admission.evidence_object_sha256 != candidate.classification_evidence_object_sha256
                or admission.repository_id != candidate.repository_id
                or admission.pre_admission_subject_sha256 != candidate.pre_admission_subject_sha256
                or admission.decision is not AdmissionClass.PUBLIC_SAFE):
            raise PromotionError("classification evidence does not bind this public-safe subject")
        evidence = self._resolver.resolve_approval(packet.approval_evidence_ref)
        if evidence is None:
            raise PromotionError("approval evidence was not found in canonical GitHub state")
        if (evidence.approval_id != packet.approval_id
                or evidence.evidence_ref != packet.approval_evidence_ref
                or evidence.evidence_object_sha256 != packet.approval_evidence_object_sha256):
            raise PromotionError("approval packet does not match canonical evidence identity")
        if (evidence.repository_id, evidence.repository_slug, evidence.task_id, evidence.route_epoch) != (
                candidate.repository_id, candidate.repository_slug, candidate.task_id, candidate.route_epoch):
            raise PromotionError("approval evidence control-plane identity does not match candidate")
        if (evidence.candidate_identity_sha256 != candidate.identity_sha256
                or evidence.decision != "APPROVE"
                or evidence.github_control_object_id != self._policy.required_control_record_id
                or evidence.canonical_main_commit != candidate.expected_canonical_main_parent
                or now >= evidence.expires_at):
            raise PromotionError("approval evidence is not an active exact approval")
        promotion_id = sha256(_canonical_bytes({
            "approval_id": packet.approval_id,
            "candidate_identity_sha256": candidate.identity_sha256,
            "approval_evidence_object_sha256": evidence.evidence_object_sha256,
        })).hexdigest()
        return PromotionRequest(
            approval_id=packet.approval_id,
            promotion_id=promotion_id,
            candidate_identity_sha256=candidate.identity_sha256,
            expected_parent=candidate.expected_canonical_main_parent,
            approval_evidence_object_sha256=evidence.evidence_object_sha256,
            classification_evidence_object_sha256=admission.evidence_object_sha256,
        )

    def consume_candidate(self, request: PromotionRequest, observed_canonical_main_parent: str) -> PromotionReceipt:
        receipt = self._store.consume_if_absent(request, observed_canonical_main_parent)
        if receipt is None:  # Protocol permits a future store to expose unresolved state this way.
            raise UnknownOutcome("durable store returned no completion receipt")
        return receipt
