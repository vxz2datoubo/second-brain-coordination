"""codex_boundary — D9 compatibility with Codex candidate/formal promotion boundary.

D9 pass criteria:
  - E50 emits the same candidate-package shape Codex expects (digest bundle + manifest)
  - no formal write attempted
  - promotion gate emits BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY

The candidate-package shape is the E48 6-digest bundle + a manifest declaring
CANDIDATE_ONLY + source_policy=PUBLIC_SAFE_GENERALIZATION_ONLY.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

from .ingestion import SourceArtifact


BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY = "BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY"


@dataclass(frozen=True)
class CandidatePackageShape:
    """The shape Codex expects from QCLAW candidate packages."""
    package_id: str
    schema_version: str
    source_class: str
    source_uri: str
    l0_size_bytes: int
    l0_sha256: str
    digests: dict  # {name -> 64-hex sha256}
    visibility: str = "CANDIDATE_ONLY"
    source_policy: str = "PUBLIC_SAFE_GENERALIZATION_ONLY"
    formal_persistence: str = BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY

    def to_manifest(self) -> dict:
        return {
            "package_id": self.package_id,
            "schema_version": self.schema_version,
            "source_class": self.source_class,
            "source_uri": self.source_uri,
            "l0_size_bytes": self.l0_size_bytes,
            "l0_sha256": self.l0_sha256,
            "digests": self.digests,
            "visibility": self.visibility,
            "source_policy": self.source_policy,
            "formal_persistence": self.formal_persistence,
        }


@dataclass
class CodexBoundaryGate:
    """Gate that refuses any formal write; only emits CANDIDATE_ONLY packages."""

    emitted: list = field(default_factory=list)

    def emit_candidate_package(self, *, artifact: SourceArtifact,
                                digests: dict, schema_version: str = "1.0",
                                package_id: Optional[str] = None) -> CandidatePackageShape:
        """Emit a candidate package. Never writes to formal storage."""
        if not artifact:
            raise ValueError("artifact required")
        if not digests:
            raise ValueError("digests dict required")
        pid = package_id or f"pkg-{artifact.l0_hash[:12]}"
        shape = CandidatePackageShape(
            package_id=pid,
            schema_version=schema_version,
            source_class=artifact.source_class.value,
            source_uri=artifact.source_uri,
            l0_size_bytes=artifact.l0_size_bytes(),
            l0_sha256=artifact.l0_hash,
            digests=dict(digests),
        )
        self.emitted.append(shape)
        return shape

    def attempt_formal_write(self) -> None:
        """Refuse any formal write attempt."""
        raise PermissionError(
            f"Formal write forbidden by E50 codex_boundary; "
            f"promotion remains {BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY}."
        )