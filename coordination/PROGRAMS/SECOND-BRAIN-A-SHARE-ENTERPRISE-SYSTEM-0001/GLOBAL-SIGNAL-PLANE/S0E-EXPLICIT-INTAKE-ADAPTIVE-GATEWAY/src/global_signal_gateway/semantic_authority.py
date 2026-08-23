"""Sealed semantic authority binding layered on the existing R136 exact-read seam.

This module is not a registry, discovery service, or live observation provider.
It reuses ``exact_git_read_proofs`` to establish repository/HEAD/tree/blob/
payload identity, then derives the owner-domain semantic identity from that
same verified payload. Caller supplied labels never enter the sealed semantic
identity.

Only public-safe identity fields are retained. Raw authority bodies are never
stored in the proof.
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
    """R136 exact-read proof plus semantics derived from its verified payload."""

    semantic_authority_identity: tuple[tuple[str, str], ...]
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


def exact_semantic_authority_proof(
    root: str | Path,
    *,
    repository: str,
    commit: str,
    path: str,
    execution_id: str,
) -> SemanticExactReadProof:
    """Mint semantic authority only after the existing sealed exact Git read.

    ``exact_git_read_proofs`` already verifies repository root, exact HEAD,
    commit:path tree identity, Git blob identity, and worktree equality. After
    that succeeds, this function reads only that already-verified local payload,
    rechecks its digest against the sealed proof, parses its authority
    declaration, and seals the semantic fields derived from the payload itself.
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
    return SemanticExactReadProof(
        exact.repository,
        exact.commit,
        exact.path,
        exact.blob_sha,
        exact.content_sha256,
        exact.execution_id,
        exact._seal,
        identity,
        _SEMANTIC_AUTHORITY_SEAL,
    )


def validate_semantic_exact_read_proof(
    proof: Any,
    *,
    expected_identity: Mapping[str, str] | None = None,
) -> bool:
    """Accept only semantic identity sealed from the verified source payload."""
    if not isinstance(proof, SemanticExactReadProof):
        return False
    if proof._semantic_authority_seal is not _SEMANTIC_AUTHORITY_SEAL:
        return False
    if not validate_exact_read_proof(proof):
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
    """Public-safe immutable ref binding exact Git identity to semantic identity."""
    if not validate_semantic_exact_read_proof(proof):
        raise GatewayError("SEMANTIC_AUTHORITY_PROOF_REQUIRED")
    semantic_digest = hashlib.sha256(
        yaml.safe_dump(proof.semantic_dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return (
        f"semantic-authority://{proof.repository}@{proof.commit}/{proof.path}"
        f"#blob={proof.blob_sha};sha256={proof.content_sha256};semantic={semantic_digest};"
        f"execution={proof.execution_id}"
    )
