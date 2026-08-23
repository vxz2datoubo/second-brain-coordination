"""Sealed semantic authority binding layered on the existing R136/R137 trust seams.

This module is not a registry, discovery service, or live observation provider.
It reuses ``exact_git_read_proofs`` to establish repository/HEAD/tree/blob/
payload identity, derives owner-domain semantics from that same verified
payload, and then requires an already-governed live provider to attest the
*same exact repository authority source object* before the semantic proof can
be minted.

A file therefore cannot become canonical owner truth merely by declaring
``source_authority: this_file``.  The self-declaration is necessary but not
sufficient: the governed provider's sealed ``exact_refs`` must independently
name the same repo/commit/path/blob/content object.  Only public-safe identity
fields and proof references are retained; raw authority bodies are never stored.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
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


@dataclass(frozen=True)
class SemanticExactReadProof(ExactReadProof):
    """R136 exact-read + source semantics + governed source-object attestation."""

    semantic_authority_identity: tuple[tuple[str, str], ...]
    governed_source_ref: str
    governed_source_provider_ref: str
    governed_source_evidence_digest: str
    _semantic_authority_seal: object = field(repr=False, compare=False)

    def semantic_dict(self) -> dict[str, str]:
        return dict(self.semantic_authority_identity)


def _semantic_identity(document: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(document, Mapping):
        raise GatewayError("SEMANTIC_AUTHORITY_DOCUMENT_NOT_OBJECT")
    if document.get("source_authority") != "this_file":
        raise GatewayError("SEMANTIC_AUTHORITY_DECLARATION_INVALID")
    values: dict[str, str] = {}
    for field_name in SEMANTIC_AUTHORITY_FIELDS:
        value = document.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise GatewayError("SEMANTIC_AUTHORITY_IDENTITY_INCOMPLETE", f"/{field_name}")
        values[field_name] = value
    return tuple(sorted(values.items()))


def governed_authority_source_ref(proof: Any) -> str:
    """Provider-compatible exact-object ref for a sealed R136 source read."""
    if not validate_exact_read_proof(proof):
        raise GatewayError("EXACT_AUTHORITY_SOURCE_PROOF_REQUIRED")
    return (
        f"github://{proof.repository}@{proof.commit}/{proof.path}"
        f"#blob={proof.blob_sha};sha256={proof.content_sha256}"
    )


def _governed_source_attestation(exact: ExactReadProof, governed_source_proof: Any) -> tuple[str, str, str]:
    """Bind one exact source object to an existing sealed governed provider proof."""
    if not validate_live_observation_proof(governed_source_proof):
        raise GatewayError("GOVERNED_AUTHORITY_SOURCE_PROOF_REQUIRED")
    source_ref = governed_authority_source_ref(exact)
    if source_ref not in tuple(governed_source_proof.exact_refs):
        raise GatewayError("GOVERNED_AUTHORITY_SOURCE_UNVERIFIED")
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
) -> SemanticExactReadProof:
    """Mint semantic authority only from a governed exact repository source.

    ``exact_git_read_proofs`` verifies repository root, exact HEAD, commit:path
    tree identity, Git blob identity, and worktree equality.  The semantic
    declaration is then parsed from that verified payload.  Finally, an
    existing R137-compatible governed live proof must independently attest the
    same exact source object in its sealed ``exact_refs``.  Caller-selected
    paths or self-declared semantics alone can never mint this proof.
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
    try:
        document = yaml.safe_load(payload.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise GatewayError("SEMANTIC_AUTHORITY_PARSE_FAILED") from exc
    identity = _semantic_identity(document)
    source_ref, provider_ref, evidence_digest = _governed_source_attestation(exact, governed_source_proof)
    return SemanticExactReadProof(
        exact.repository,
        exact.commit,
        exact.path,
        exact.blob_sha,
        exact.content_sha256,
        exact.execution_id,
        exact._seal,
        identity,
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
    """Accept only semantics sealed after independent governed source attestation."""
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
        or any(character not in "0123456789abcdef" for character in proof.governed_source_evidence_digest)
    ):
        return False
    semantic = proof.semantic_dict()
    if set(semantic) != set(SEMANTIC_AUTHORITY_FIELDS):
        return False
    if expected_identity is not None:
        expected = {field: expected_identity.get(field) for field in SEMANTIC_AUTHORITY_FIELDS}
        if any(not isinstance(value, str) or not value for value in expected.values()):
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
