"""E59 public-safe synthetic canonical trust and process-lifecycle runtime.

The package intentionally exports value types and verifier consumers, but no
public bootstrap API. Harness-only construction lives in a private module and
is not a production trust root.
"""

from .process_tree import (
    OwnedProcessTree,
    ProcessIdentity,
    ResourceGate,
    ResourceViolation,
)
from .authority_client import AuthorityAnchor, AuthorityDescriptor, AuthorityError, CanonicalVerifier, Proposition

__all__ = [
    "OwnedProcessTree",
    "ProcessIdentity",
    "ResourceGate",
    "ResourceViolation",
    "AuthorityAnchor",
    "AuthorityDescriptor",
    "AuthorityError",
    "CanonicalVerifier",
    "Proposition",
]
