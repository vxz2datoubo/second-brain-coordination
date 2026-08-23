"""Sealed semantic authority binding layered on the existing R135/R136/R137 trust seams.

This module is not a registry, discovery service, or live observation provider.
It reuses R136 exact Git reads, reuses the native authority representations that
already exist in owner repositories, and requires a governed live provider to
attest the same exact source object before normalized owner-domain semantics can
be minted.

A source repository is never required to adopt an R145-only synthetic schema.
For example, AI Film keeps ``PROJECT_INDEX.yaml`` as its own source of truth and
World Model keeps its canonical architecture master.  Missing or unavailable
native authority fails closed.  Only public-safe identities, hashes and opaque
proof refs are retained; raw authority bodies are never stored in proofs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

import yaml

from .gateway import (
    ExactReadProof,
    GatewayError,
    exact_git_read_proofs,
    validate_exact_read_proof,
    validate_live_observation_proof,
)


SEMANTIC_AUTHORITY_FIELDS = (
    "domain_id",
    "project_id",
    "authority_schema_version",
    "writeback_owner",
    "observation_mode",
)
_SEMANTIC_AUTHORITY_SEAL = object()
_ARCHITECTURE_TITLE = re.compile(r"^#\s+([A-Za-z0-9_.-]+)\s+Canonical Architecture\s*$", re.MULTILINE)
_ARCHITECTURE_ROLE = re.compile(r"^Authority role:\s*`([^`]+)`\.?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class SemanticExactReadProof(ExactReadProof):
    """R136 exact-read + native/source semantics + governed source attestation."""

    semantic_authority_identity: tuple[tuple[str, str], ...]
    governed_source_ref: str
    governed_source_provider_ref: str
    governed_source_evidence_digest: str
    _semantic_authority_seal: object = field(repr=False, compare=False)

    def semantic_dict(self) -> dict[str, str]:
        return dict(self.semantic_authority_identity)


def _required_identity(identity: Mapping[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field_name in SEMANTIC_AUTHORITY_FIELDS:
        value = identity.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise GatewayError("SEMANTIC_AUTHORITY_IDENTITY_INCOMPLETE", f"/{field_name}")
        values[field_name] = value
    return values


def native_semantic_authority_identity(payload: bytes, *, path: str) -> dict[str, str]:
    """Extract only identity asserted by an existing native owner authority surface.

    This is representation-aware rather than domain-aware. It has no domain
    registry and no repository switch. YAML project indexes reuse the R135
    ``AI_FILM_PROJECT_INDEX/v1`` representation identity; canonical architecture
    Markdown is recognized by its own master-role declaration. Unknown formats
    fail closed instead of being guessed.
    """
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GatewayError("SEMANTIC_AUTHORITY_PARSE_FAILED") from exc

    suffix = PurePosixPath(path).suffix.casefold()
    try:
        yaml_document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        if suffix in {".yaml", ".yml"}:
            raise GatewayError("SEMANTIC_AUTHORITY_PARSE_FAILED") from exc
        yaml_document = None

    # Some historical synthetic regressions intentionally bind a YAML authority
    # body to a path whose production counterpart is Markdown. Preserve that
    # stronger source-complete case without treating arbitrary Markdown as YAML.
    if isinstance(yaml_document, Mapping) and "source_authority" in yaml_document:
        document = yaml_document
        if document.get("source_authority") != "this_file":
            raise GatewayError("SEMANTIC_AUTHORITY_DECLARATION_INVALID")
        project_id = document.get("project_id")
        if not isinstance(project_id, str) or not project_id.strip():
            raise GatewayError("SEMANTIC_AUTHORITY_IDENTITY_INCOMPLETE", "/project_id")

        schema = document.get("authority_schema_version") or document.get("schema_version")
        if not isinstance(schema, str) or not schema.strip():
            if PurePosixPath(path).name == "PROJECT_INDEX.yaml":
                # This name is the already-existing R135 schema identity, not a
                # new global R145 domain schema.
                schema = "AI_FILM_PROJECT_INDEX/v1"
            else:
                raise GatewayError("SEMANTIC_AUTHORITY_SCHEMA_UNAVAILABLE")

        result = {
            "project_id": project_id,
            "authority_schema_version": schema,
        }
        for field_name in ("domain_id", "writeback_owner", "observation_mode"):
            value = document.get(field_name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise GatewayError("SEMANTIC_AUTHORITY_IDENTITY_INCOMPLETE", f"/{field_name}")
                result[field_name] = value
        return result

    if suffix in {".yaml", ".yml"}:
        raise GatewayError("SEMANTIC_AUTHORITY_DOCUMENT_NOT_OBJECT")

    if suffix == ".md":
        title = _ARCHITECTURE_TITLE.search(text)
        role = _ARCHITECTURE_ROLE.search(text)
        if title is None or role is None or role.group(1) != "CANONICAL_ARCHITECTURE_MASTER":
            raise GatewayError("SEMANTIC_AUTHORITY_DECLARATION_INVALID")
        return {
            "project_id": title.group(1),
            "authority_schema_version": "CANONICAL_ARCHITECTURE_MARKDOWN/v1",
        }

    raise GatewayError("SEMANTIC_AUTHORITY_REPRESENTATION_UNSUPPORTED")


def governed_authority_source_ref(proof: Any) -> str:
    """Provider-compatible exact-object ref for a sealed R136 source read."""
    if not validate_exact_read_proof(proof):
        raise GatewayError("EXACT_AUTHORITY_SOURCE_PROOF_REQUIRED")
    return (
        f"github://{proof.repository}@{proof.commit}/{proof.path}"
        f"#blob={proof.blob_sha};sha256={proof.content_sha256}"
    )


def governed_semantic_authority_ref(source_ref: str, identity: Mapping[str, Any]) -> str:
    """Opaque provider attestation over one exact source object and normalized identity."""
    if not isinstance(source_ref, str) or not source_ref.startswith("github://"):
        raise GatewayError("GOVERNED_AUTHORITY_SOURCE_PROOF_REQUIRED")
    normalized = _required_identity(identity)
    semantic_digest = hashlib.sha256(
        yaml.safe_dump(
            {"source_ref": source_ref, "identity": normalized},
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"governed-semantic-authority://sha256={semantic_digest}"


def _resolved_identity(
    native: Mapping[str, str],
    expected_identity: Mapping[str, str] | None,
) -> tuple[dict[str, str], bool]:
    """Return normalized identity and whether provider semantic attestation is required."""
    if expected_identity is None:
        # Backward compatibility for genuinely source-complete authority files:
        # every normalized field must itself be in the verified source body.
        normalized = _required_identity(native)
        return normalized, False

    normalized = _required_identity(expected_identity)
    if native.get("project_id") != normalized["project_id"]:
        raise GatewayError("SEMANTIC_AUTHORITY_PROJECT_ID_MISMATCH")
    if native.get("authority_schema_version") != normalized["authority_schema_version"]:
        raise GatewayError("SEMANTIC_AUTHORITY_SCHEMA_MISMATCH")
    for field_name in ("domain_id", "writeback_owner", "observation_mode"):
        source_value = native.get(field_name)
        if source_value is not None and source_value != normalized[field_name]:
            raise GatewayError("SEMANTIC_AUTHORITY_IDENTITY_MISMATCH", f"/{field_name}")
    # A native source such as PROJECT_INDEX does not invent R145 routing fields.
    # Those missing fields must therefore be independently attested by the
    # governed provider from canonical coordinator contracts.
    provider_semantic_required = any(
        field_name not in native for field_name in SEMANTIC_AUTHORITY_FIELDS
    )
    return normalized, provider_semantic_required


def _governed_source_attestation(
    exact: ExactReadProof,
    governed_source_proof: Any,
    *,
    identity: Mapping[str, str],
    provider_semantic_required: bool,
) -> tuple[str, str, str]:
    """Bind one exact source object to an existing sealed governed provider proof."""
    if not validate_live_observation_proof(governed_source_proof):
        raise GatewayError("GOVERNED_AUTHORITY_SOURCE_PROOF_REQUIRED")
    source_ref = governed_authority_source_ref(exact)
    exact_refs = tuple(governed_source_proof.exact_refs)
    if source_ref not in exact_refs:
        raise GatewayError("GOVERNED_AUTHORITY_SOURCE_UNVERIFIED")
    if provider_semantic_required:
        semantic_ref = governed_semantic_authority_ref(source_ref, identity)
        if semantic_ref not in exact_refs:
            raise GatewayError("GOVERNED_AUTHORITY_SEMANTICS_UNVERIFIED")
    provider_ref = governed_source_proof.provider_attribution_ref
    evidence_digest = governed_source_proof.evidence_digest
    if not isinstance(provider_ref, str) or not provider_ref.startswith("provider://"):
        raise GatewayError("GOVERNED_AUTHORITY_SOURCE_PROOF_REQUIRED")
    if (
        not isinstance(evidence_digest, str)
        or len(evidence_digest) != 64
        or any(character not in "0123456789abcdef" for character in evidence_digest)
    ):
        raise GatewayError("GOVERNED_AUTHORITY_SOURCE_PROOF_REQUIRED")
    return source_ref, provider_ref, evidence_digest


def exact_semantic_authority_proof(
    root: str | Path,
    *,
    repository: str,
    commit: str,
    path: str,
    execution_id: str,
    governed_source_proof: Any,
    expected_identity: Mapping[str, str] | None = None,
) -> SemanticExactReadProof:
    """Mint semantic authority only from a governed exact repository source.

    R136 verifies repository root, exact HEAD, commit:path tree identity, Git
    blob identity and worktree equality. Native source semantics are then
    parsed from that verified payload. If the native representation does not
    itself carry all normalized R145 routing fields, the existing governed live
    provider must independently attest the normalized identity from canonical
    coordinator contracts as well as the same exact source object.
    """
    exact = exact_git_read_proofs(
        root,
        repository=repository,
        commit=commit,
        paths=(path,),
        execution_id=execution_id,
    )[0]
    source = Path(root).resolve()
    try:
        payload = (source / path).read_bytes()
    except OSError as exc:
        raise GatewayError("SOURCE_PATH_UNREADABLE") from exc
    if hashlib.sha256(payload).hexdigest() != exact.content_sha256:
        raise GatewayError("SOURCE_WORKTREE_PAYLOAD_MISMATCH")

    native = native_semantic_authority_identity(payload, path=path)
    identity, provider_semantic_required = _resolved_identity(native, expected_identity)
    source_ref, provider_ref, evidence_digest = _governed_source_attestation(
        exact,
        governed_source_proof,
        identity=identity,
        provider_semantic_required=provider_semantic_required,
    )
    return SemanticExactReadProof(
        exact.repository,
        exact.commit,
        exact.path,
        exact.blob_sha,
        exact.content_sha256,
        exact.execution_id,
        exact._seal,
        tuple(sorted(identity.items())),
        source_ref,
        provider_ref,
        evidence_digest,
        _SEMANTIC_AUTHORITY_SEAL,
    )


def validate_semantic_exact_read_proof(
    proof: Any,
    *,
    expected_identity: Mapping[str, str] | None = None,
) -> bool:
    """Accept only semantics sealed after governed source validation."""
    if not isinstance(proof, SemanticExactReadProof):
        return False
    if proof._semantic_authority_seal is not _SEMANTIC_AUTHORITY_SEAL:
        return False
    if not validate_exact_read_proof(proof):
        return False
    try:
        expected_source_ref = governed_authority_source_ref(proof)
    except GatewayError:
        return False
    if proof.governed_source_ref != expected_source_ref:
        return False
    if not proof.governed_source_provider_ref.startswith("provider://"):
        return False
    if (
        len(proof.governed_source_evidence_digest) != 64
        or any(
            character not in "0123456789abcdef"
            for character in proof.governed_source_evidence_digest
        )
    ):
        return False
    semantic = proof.semantic_dict()
    if set(semantic) != set(SEMANTIC_AUTHORITY_FIELDS):
        return False
    if expected_identity is not None:
        try:
            expected = _required_identity(expected_identity)
        except GatewayError:
            return False
        if semantic != expected:
            return False
    return True


def semantic_authority_ref(proof: Any) -> str:
    """Public-safe immutable ref binding Git, semantics and governed source proof."""
    if not validate_semantic_exact_read_proof(proof):
        raise GatewayError("SEMANTIC_AUTHORITY_PROOF_REQUIRED")
    semantic_digest = hashlib.sha256(
        yaml.safe_dump(proof.semantic_dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()
    governed_digest = hashlib.sha256(
        yaml.safe_dump(
            {
                "source_ref": proof.governed_source_ref,
                "provider_ref": proof.governed_source_provider_ref,
                "evidence_digest": proof.governed_source_evidence_digest,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return (
        f"semantic-authority://{proof.repository}@{proof.commit}/{proof.path}"
        f"#blob={proof.blob_sha};sha256={proof.content_sha256};semantic={semantic_digest};"
        f"governed_source={governed_digest};execution={proof.execution_id}"
    )
