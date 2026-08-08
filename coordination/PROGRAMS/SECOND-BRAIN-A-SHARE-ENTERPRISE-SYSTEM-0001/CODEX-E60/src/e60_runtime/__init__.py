"""E60 synthetic-only verification boundary.

This package verifies externally attested synthetic fixtures. It does not ship
an issuer, bootstrap harness, signing key, or production trust-root claim.
"""

from .attestation import (
    AttestationError,
    CanonicalVerifier,
    ExternalAttestation,
    SourceSpanGrant,
    runtime_identity_digest,
)

__all__ = [
    "AttestationError",
    "CanonicalVerifier",
    "ExternalAttestation",
    "SourceSpanGrant",
    "runtime_identity_digest",
]
