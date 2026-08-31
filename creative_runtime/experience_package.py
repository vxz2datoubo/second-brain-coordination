"""Deterministic metadata for a public-safe interactive experience package.

This module handles only bytes that are already approved for GitHub's synthetic
demonstration lane.  It never reads a workspace, customer material, provider
configuration, or a network resource.
"""

from __future__ import annotations

import hashlib
from typing import Mapping


PACKAGE_MANIFEST_NAME = "package_manifest.json"
PACKAGE_MEMBER_NAMES = (
    "experience.json",
    "verified_experience_player.html",
    "README.md",
)


def sha256_hex(value: bytes) -> str:
    """Return the stable, lowercase digest used in package manifests."""

    return hashlib.sha256(value).hexdigest()


def build_package_manifest(head_sha: str, members: Mapping[str, bytes]) -> dict[str, object]:
    """Describe exactly the three public-safe files in a demonstration package."""

    if tuple(members) != PACKAGE_MEMBER_NAMES:
        raise ValueError("Experience package members must be the fixed ordered public-safe set")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ValueError("Experience package head_sha must be a full 40-character git SHA")
    return {
        "schema": "CreativeRuntimeExperiencePackageManifest/v1",
        "status": "experience_package_verified",
        "head_sha": head_sha,
        "members": [
            {
                "path": name,
                "sha256": sha256_hex(members[name]),
                "size_bytes": len(members[name]),
            }
            for name in PACKAGE_MEMBER_NAMES
        ],
        "boundary": {
            "synthetic_only": True,
            "customer_data_present": False,
            "external_provider_called": False,
            "publication_authorized": False,
        },
    }
