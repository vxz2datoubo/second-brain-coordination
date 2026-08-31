"""Fixed-layout package manifest for an offline multi-scenario library."""

from __future__ import annotations

from typing import Mapping

from .experience_package import sha256_hex


LIBRARY_PACKAGE_MANIFEST_NAME = "library_package_manifest.json"
LIBRARY_PACKAGE_MEMBER_NAMES = (
    "experience_library.json",
    "verified_experience_player.html",
    "README.md",
)


def build_library_package_manifest(head_sha: str, members: Mapping[str, bytes]) -> dict[str, object]:
    """Describe the only permitted files in one local library package."""

    if tuple(members) != LIBRARY_PACKAGE_MEMBER_NAMES:
        raise ValueError("Experience library package members must be the fixed ordered public-safe set")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ValueError("Experience library package head_sha must be a full 40-character git SHA")
    return {
        "schema": "CreativeRuntimeExperienceLibraryPackageManifest/v1",
        "status": "experience_library_package_verified",
        "head_sha": head_sha,
        "members": [
            {
                "path": name,
                "sha256": sha256_hex(members[name]),
                "size_bytes": len(members[name]),
            }
            for name in LIBRARY_PACKAGE_MEMBER_NAMES
        ],
        "boundary": {
            "synthetic_only": True,
            "customer_data_present": False,
            "external_provider_called": False,
            "publication_authorized": False,
            "client_story_authority": False,
        },
    }
