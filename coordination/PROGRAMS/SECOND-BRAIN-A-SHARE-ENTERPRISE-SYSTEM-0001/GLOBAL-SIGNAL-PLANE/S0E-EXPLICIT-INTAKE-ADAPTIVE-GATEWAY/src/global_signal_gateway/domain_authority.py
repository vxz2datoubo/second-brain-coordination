"""R145 domain-neutral authority binding and Signal-to-Task domain guards.

This module is deliberately data-only.  It does not discover repositories, read
private bodies, mutate domain repositories, create tasks, or grant write
permissions.  Callers supply governed descriptors and public-safe canonical
observation metadata.  The resolver binds those records mechanically before a
retrospective candidate may make an owner-domain completion judgment.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CANONICAL_REF_KINDS = frozenset({
    "CANONICAL_MAIN", "IMMUTABLE_ACCEPTED_COMMIT", "APPROVED_AUTHORITY_SNAPSHOT",
})
OBSERVATION_MODES = frozenset({"READ_ONLY", "READ_ONLY_METADATA_ONLY", "LOCAL_CANONICAL_READ"})
SOURCE_KINDS = frozenset(CANONICAL_REF_KINDS | {"DRAFT_PR", "OPEN_BRANCH_CANDIDATE"})
ALLOWED_CROSS_DOMAIN_RELATIONS = frozenset({
    "RELATED_TO", "REINFORCES", "EXTENDS", "TRANSFERABLE_PATTERN_CANDIDATE",
    "CROSS_PROJECT_CAPABILITY_CANDIDATE",
})
PRIVATE_FIELD_NAMES = frozenset({
    "raw_source_body", "private_body", "body", "content", "private_chain_of_thought",
    "token", "password", "private_key", "secret", "api_key", "access_token",
})
DESCRIPTOR_FIELDS = frozenset({
    "domain_id", "project_id", "repository", "canonical_ref_kind", "canonical_commit",
    "authority_path_or_contract_ref", "authority_schema_version", "writeback_owner",
    "observation_mode", "repository_visibility",
})
OBSERVATION_FIELDS = frozenset({
    "domain_id", "project_id", "repository", "canonical_ref_kind", "canonical_commit",
    "authority_path_or_contract_ref", "authority_blob_sha", "authority_content_sha256",
    "authority_schema_version", "observation_mode", "source_kind", "observed_at",
    "evidence_refs", "repository_visibility",
})


class DomainAuthorityError(ValueError):
    """Stable fail-closed error; messages never echo private source bodies."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainAuthorityError("DOMAIN_AUTHORITY_INVALID_STRING", path)
    return value


def _timestamp(value: Any, path: str) -> str:
    text = _string(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DomainAuthorityError("DOMAIN_AUTHORITY_INVALID_TIMESTAMP", path) from exc
    if parsed.tzinfo is None:
        raise DomainAuthorityError("DOMAIN_AUTHORITY_NAIVE_TIMESTAMP_FORBIDDEN", path)
    return text


def _reject_private_or_extra(value: Mapping[str, Any], allowed: frozenset[str], path: str) -> None:
    for key in value:
        folded = str(key).casefold()
        if folded in PRIVATE_FIELD_NAMES or "body" in folded or "secret" in folded:
            raise DomainAuthorityError("DOMAIN_AUTHORITY_PRIVATE_BODY_FORBIDDEN", f"{path}{key}")
    extra = sorted(set(value) - allowed)
    if extra:
        raise DomainAuthorityError("DOMAIN_AUTHORITY_UNRECOGNIZED_FIELD", f"{path}{extra[0]}")


@dataclass(frozen=True)
class DomainAuthorityDescriptor:
    domain_id: str
    project_id: str
    repository: str
    canonical_ref_kind: str
    canonical_commit: str
    authority_path_or_contract_ref: str
    authority_schema_version: str
    writeback_owner: str
    observation_mode: str
    repository_visibility: str = "PUBLIC_OR_METADATA_ONLY"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DomainAuthorityDescriptor":
        if not isinstance(value, Mapping):
            raise DomainAuthorityError("DOMAIN_AUTHORITY_DESCRIPTOR_NOT_OBJECT")
        _reject_private_or_extra(value, DESCRIPTOR_FIELDS, "/domain_authority_descriptors/")
        required = DESCRIPTOR_FIELDS - {"repository_visibility"}
        missing = sorted(required - set(value))
        if missing:
            raise DomainAuthorityError("DOMAIN_AUTHORITY_DESCRIPTOR_FIELD_MISSING", f"/domain_authority_descriptors/{missing[0]}")
        domain_id = _string(value["domain_id"], "/domain_id")
        project_id = _string(value["project_id"], "/project_id")
        repository = _string(value["repository"], "/repository")
        ref_kind = _string(value["canonical_ref_kind"], "/canonical_ref_kind")
        commit = _string(value["canonical_commit"], "/canonical_commit")
        authority_path = _string(value["authority_path_or_contract_ref"], "/authority_path_or_contract_ref")
        schema = _string(value["authority_schema_version"], "/authority_schema_version")
        owner = _string(value["writeback_owner"], "/writeback_owner")
        mode = _string(value["observation_mode"], "/observation_mode")
        visibility = _string(value.get("repository_visibility", "PUBLIC_OR_METADATA_ONLY"), "/repository_visibility")
        if ref_kind not in CANONICAL_REF_KINDS:
            raise DomainAuthorityError("DOMAIN_CANONICAL_REF_KIND_INVALID", "/canonical_ref_kind")
        if not SHA40.fullmatch(commit):
            raise DomainAuthorityError("DOMAIN_CANONICAL_COMMIT_INVALID", "/canonical_commit")
        if mode not in OBSERVATION_MODES:
            raise DomainAuthorityError("DOMAIN_OBSERVATION_MODE_INVALID", "/observation_mode")
        return cls(domain_id, project_id, repository, ref_kind, commit, authority_path, schema, owner, mode, visibility)

    def public_dict(self) -> dict[str, str]:
        return {
            "domain_id": self.domain_id,
            "project_id": self.project_id,
            "repository": self.repository,
            "canonical_ref_kind": self.canonical_ref_kind,
            "canonical_commit": self.canonical_commit,
            "authority_path_or_contract_ref": self.authority_path_or_contract_ref,
            "authority_schema_version": self.authority_schema_version,
            "writeback_owner": self.writeback_owner,
            "observation_mode": self.observation_mode,
            "repository_visibility": self.repository_visibility,
        }

    def descriptor_ref(self) -> str:
        return f"domain-authority://{self.domain_id}#sha256={_digest(self.public_dict())}"


@dataclass(frozen=True)
class DomainAuthorityObservation:
    domain_id: str
    project_id: str
    repository: str
    canonical_ref_kind: str
    canonical_commit: str
    authority_path_or_contract_ref: str
    authority_blob_sha: str
    authority_content_sha256: str
    authority_schema_version: str
    observation_mode: str
    source_kind: str
    observed_at: str
    evidence_refs: tuple[str, ...]
    repository_visibility: str = "PUBLIC_OR_METADATA_ONLY"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DomainAuthorityObservation":
        if not isinstance(value, Mapping):
            raise DomainAuthorityError("DOMAIN_AUTHORITY_OBSERVATION_NOT_OBJECT")
        _reject_private_or_extra(value, OBSERVATION_FIELDS, "/domain_authority_observations/")
        required = OBSERVATION_FIELDS - {"repository_visibility"}
        missing = sorted(required - set(value))
        if missing:
            raise DomainAuthorityError("DOMAIN_AUTHORITY_OBSERVATION_FIELD_MISSING", f"/domain_authority_observations/{missing[0]}")
        domain_id = _string(value["domain_id"], "/domain_id")
        project_id = _string(value["project_id"], "/project_id")
        repository = _string(value["repository"], "/repository")
        ref_kind = _string(value["canonical_ref_kind"], "/canonical_ref_kind")
        commit = _string(value["canonical_commit"], "/canonical_commit")
        authority_path = _string(value["authority_path_or_contract_ref"], "/authority_path_or_contract_ref")
        blob = _string(value["authority_blob_sha"], "/authority_blob_sha")
        content_sha = _string(value["authority_content_sha256"], "/authority_content_sha256")
        schema = _string(value["authority_schema_version"], "/authority_schema_version")
        mode = _string(value["observation_mode"], "/observation_mode")
        source_kind = _string(value["source_kind"], "/source_kind")
        observed_at = _timestamp(value["observed_at"], "/observed_at")
        refs = value["evidence_refs"]
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
            raise DomainAuthorityError("DOMAIN_AUTHORITY_EVIDENCE_REFS_INVALID", "/evidence_refs")
        visibility = _string(value.get("repository_visibility", "PUBLIC_OR_METADATA_ONLY"), "/repository_visibility")
        if ref_kind not in CANONICAL_REF_KINDS:
            raise DomainAuthorityError("DOMAIN_CANONICAL_REF_KIND_INVALID", "/canonical_ref_kind")
        if source_kind not in SOURCE_KINDS:
            raise DomainAuthorityError("DOMAIN_AUTHORITY_SOURCE_KIND_INVALID", "/source_kind")
        if mode not in OBSERVATION_MODES:
            raise DomainAuthorityError("DOMAIN_OBSERVATION_MODE_INVALID", "/observation_mode")
        if not SHA40.fullmatch(commit) or not SHA40.fullmatch(blob) or not SHA256.fullmatch(content_sha):
            raise DomainAuthorityError("DOMAIN_AUTHORITY_HASH_INVALID")
        return cls(domain_id, project_id, repository, ref_kind, commit, authority_path, blob, content_sha, schema, mode, source_kind, observed_at, tuple(refs), visibility)

    def opaque_ref(self) -> str:
        return (
            f"git://{self.repository}@{self.canonical_commit}/{self.authority_path_or_contract_ref}"
            f"#blob={self.authority_blob_sha};sha256={self.authority_content_sha256}"
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "project_id": self.project_id,
            "repository": self.repository,
            "canonical_ref_kind": self.canonical_ref_kind,
            "canonical_commit": self.canonical_commit,
            "authority_path_or_contract_ref": self.authority_path_or_contract_ref,
            "authority_blob_sha": self.authority_blob_sha,
            "authority_content_sha256": self.authority_content_sha256,
            "authority_schema_version": self.authority_schema_version,
            "observation_mode": self.observation_mode,
            "source_kind": self.source_kind,
            "observed_at": self.observed_at,
            "evidence_refs": sorted(self.evidence_refs),
            "repository_visibility": self.repository_visibility,
            "opaque_ref": self.opaque_ref(),
        }


class DomainAuthorityResolver:
    """Descriptor-driven resolver; adding a domain requires data, not resolver code."""

    def __init__(self, descriptors: Sequence[Mapping[str, Any]]) -> None:
        parsed = [DomainAuthorityDescriptor.from_mapping(item) for item in descriptors]
        self._by_domain: dict[str, DomainAuthorityDescriptor] = {}
        for item in parsed:
            if item.domain_id in self._by_domain:
                raise DomainAuthorityError("DOMAIN_ROUTE_AMBIGUOUS", f"/domain/{item.domain_id}")
            self._by_domain[item.domain_id] = item

    def resolve(self, domain_id: str, observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        descriptor = self._by_domain.get(domain_id)
        if descriptor is None:
            return {"valid": False, "reason": "DOMAIN_ROUTE_UNRESOLVED", "authority_refs": []}
        try:
            candidates = [DomainAuthorityObservation.from_mapping(item) for item in observations if isinstance(item, Mapping) and item.get("domain_id") == domain_id]
        except DomainAuthorityError as exc:
            return {"valid": False, "reason": exc.code, "authority_refs": [descriptor.descriptor_ref()]}
        if not candidates:
            return {"valid": False, "reason": "DOMAIN_AUTHORITY_UNAVAILABLE", "authority_refs": [descriptor.descriptor_ref()]}
        if any(item.project_id != descriptor.project_id for item in candidates):
            return {"valid": False, "reason": "DOMAIN_PROJECT_ID_MISMATCH", "authority_refs": [descriptor.descriptor_ref()]}
        canonical = [item for item in candidates if item.source_kind in CANONICAL_REF_KINDS]
        if not canonical:
            return {"valid": False, "reason": "NON_CANONICAL_SOURCE_ONLY", "authority_refs": [descriptor.descriptor_ref()]}
        exact = [item for item in canonical if (
            item.repository == descriptor.repository
            and item.canonical_ref_kind == descriptor.canonical_ref_kind
            and item.canonical_commit == descriptor.canonical_commit
            and item.authority_path_or_contract_ref == descriptor.authority_path_or_contract_ref
            and item.authority_schema_version == descriptor.authority_schema_version
            and item.observation_mode == descriptor.observation_mode
        )]
        if not exact:
            return {"valid": False, "reason": "DOMAIN_CANONICAL_DRIFT", "authority_refs": [descriptor.descriptor_ref()]}
        fingerprints = {_digest(item.public_dict()) for item in exact}
        if len(fingerprints) != 1:
            return {"valid": False, "reason": "DOMAIN_AUTHORITY_OBSERVATION_AMBIGUOUS", "authority_refs": [descriptor.descriptor_ref()]}
        observation = exact[0]
        refs = sorted({descriptor.descriptor_ref(), observation.opaque_ref(), *observation.evidence_refs})
        return {
            "valid": True,
            "reason": "DOMAIN_CANONICAL_AUTHORITY_BOUND",
            "domain_id": descriptor.domain_id,
            "project_id": descriptor.project_id,
            "repository": descriptor.repository,
            "canonical_commit": descriptor.canonical_commit,
            "writeback_owner": descriptor.writeback_owner,
            "authority_refs": refs,
            "binding_digest": _digest({"descriptor": descriptor.public_dict(), "observation": observation.public_dict()}),
            "legacy_compatibility": False,
        }


def resolve_candidate_domain_authority(candidate: Mapping[str, Any], snapshot: Mapping[str, Any], *, expected_canonical_main: str, coordinator_repository: str) -> dict[str, Any]:
    """Resolve owner authority, retaining only the existing R142 local-domain compatibility seam."""
    domain_id = str(candidate.get("proposed_primary_domain", ""))
    descriptors = snapshot.get("domain_authority_descriptors")
    observations = snapshot.get("domain_authority_observations")
    if descriptors is not None or observations is not None:
        if not isinstance(descriptors, list) or not isinstance(observations, list):
            return {"valid": False, "reason": "DOMAIN_AUTHORITY_BUNDLE_INVALID", "authority_refs": []}
        try:
            return DomainAuthorityResolver(descriptors).resolve(domain_id, observations)
        except DomainAuthorityError as exc:
            return {"valid": False, "reason": exc.code, "authority_refs": []}

    # R142 already treats SHARED_COGNITIVE_OS as local Second Brain canonical
    # truth.  Preserve that single historical seam without turning repository
    # identity into a generic domain fallback.  Every other domain requires a
    # governed descriptor bundle.
    if domain_id != "SHARED_COGNITIVE_OS":
        return {"valid": False, "reason": "DOMAIN_ROUTE_UNRESOLVED", "authority_refs": []}
    if snapshot.get("canonical_main") != expected_canonical_main:
        return {"valid": False, "reason": "DOMAIN_CANONICAL_DRIFT", "authority_refs": []}
    coverage = snapshot.get("scan_coverage") if isinstance(snapshot.get("scan_coverage"), Mapping) else {}
    domain_scan = coverage.get("domain_canonical") if isinstance(coverage.get("domain_canonical"), Mapping) else {}
    refs = domain_scan.get("evidence_refs")
    if domain_scan.get("status") != "SCANNED" or not isinstance(refs, list) or not refs:
        return {"valid": False, "reason": "DOMAIN_AUTHORITY_UNAVAILABLE", "authority_refs": []}
    descriptor = DomainAuthorityDescriptor(
        domain_id="SHARED_COGNITIVE_OS",
        project_id="SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001",
        repository=coordinator_repository,
        canonical_ref_kind="CANONICAL_MAIN",
        canonical_commit=expected_canonical_main,
        authority_path_or_contract_ref="coordination/PROGRAM-CONTROL-TOWER.md",
        authority_schema_version="R142_CURRENT_CANONICAL_SNAPSHOT/v1",
        writeback_owner="SECOND_BRAIN_SYSTEM",
        observation_mode="LOCAL_CANONICAL_READ",
    )
    authority_refs = sorted({descriptor.descriptor_ref(), *map(str, refs)})
    return {
        "valid": True,
        "reason": "LEGACY_R142_LOCAL_DOMAIN_BOUND_TO_CANONICAL_SNAPSHOT",
        "domain_id": descriptor.domain_id,
        "project_id": descriptor.project_id,
        "repository": descriptor.repository,
        "canonical_commit": descriptor.canonical_commit,
        "writeback_owner": descriptor.writeback_owner,
        "authority_refs": authority_refs,
        "binding_digest": _digest({"descriptor": descriptor.public_dict(), "evidence_refs": authority_refs}),
        "legacy_compatibility": True,
    }


def authority_evidence_is_bound(evidence: Mapping[str, Any], binding: Mapping[str, Any]) -> bool:
    if binding.get("legacy_compatibility") is True:
        return True
    if evidence.get("authority_domain_id") != binding.get("domain_id"):
        return False
    refs = evidence.get("authority_evidence_refs")
    if not isinstance(refs, list) or not refs:
        return False
    return bool(set(map(str, refs)).intersection(map(str, binding.get("authority_refs", []))))


def evaluate_signal_task_route_domain_guard(*, signal_primary_domain: str, task_target_domain: str, route_authority_domain: str, writeback_owner_domain: str, governed_cross_domain_task_ref: str | None = None) -> dict[str, Any]:
    """Validate compatibility only; this function cannot create a task or authority."""
    domains = tuple(_string(value, "/domain") for value in (
        signal_primary_domain, task_target_domain, route_authority_domain, writeback_owner_domain,
    ))
    same_domain = len(set(domains)) == 1
    governed_cross_domain = bool(
        governed_cross_domain_task_ref
        and task_target_domain == route_authority_domain == writeback_owner_domain
    )
    eligible = same_domain or governed_cross_domain
    reason = "DOMAIN_IDENTITY_MATCH" if same_domain else (
        "GOVERNED_CROSS_DOMAIN_SHARED_CAPABILITY_TASK" if governed_cross_domain else "DOMAIN_IDENTITY_MISMATCH_BLOCK"
    )
    return {
        "eligible_for_normal_release_gates": eligible,
        "reason": reason,
        "signal_primary_domain": signal_primary_domain,
        "task_target_domain": task_target_domain,
        "route_authority_domain": route_authority_domain,
        "writeback_owner_domain": writeback_owner_domain,
        "governed_cross_domain_task_ref": governed_cross_domain_task_ref or "NONE",
        "automatic_task_created": False,
        "write_permission_created": False,
        "ownership_transferred": False,
    }


def project_cross_domain_relation(*, relation: str, source_domain: str, related_domain: str, accepted_as_shared_capability: bool = False) -> dict[str, Any]:
    if relation not in ALLOWED_CROSS_DOMAIN_RELATIONS:
        raise DomainAuthorityError("CROSS_DOMAIN_RELATION_INVALID", "/relation")
    return {
        "relation": relation,
        "source_domain": _string(source_domain, "/source_domain"),
        "related_domain": _string(related_domain, "/related_domain"),
        "shared_capability_candidate": bool(accepted_as_shared_capability),
        "ownership_transferred": False,
        "write_permission_created": False,
        "automatic_task_created": False,
    }


def deterministic_domain_evidence_receipt(*, descriptors: Sequence[Mapping[str, Any]], observations: Sequence[Mapping[str, Any]], checks: Mapping[str, Any]) -> dict[str, Any]:
    """Public-safe deterministic evidence identity for replay/audit."""
    parsed_descriptors = [DomainAuthorityDescriptor.from_mapping(item).public_dict() for item in descriptors]
    parsed_observations = [DomainAuthorityObservation.from_mapping(item).public_dict() for item in observations]
    body = {
        "schema_version": "R145DomainAuthorityEvidence/v1",
        "descriptors": sorted(parsed_descriptors, key=lambda item: item["domain_id"]),
        "observations": sorted(parsed_observations, key=lambda item: (item["domain_id"], item["canonical_commit"], item["source_kind"])),
        "checks": json.loads(_canonical(dict(checks))),
        "private_body_persisted": False,
        "cross_repo_mutation_available": False,
        "automatic_task_created": False,
    }
    return {**body, "receipt_sha256": _digest(body)}
