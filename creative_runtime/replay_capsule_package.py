"""Fixed-layout package manifests for verified synthetic replay capsules.

The package intentionally contains a completed, canonical-choice replay only.
It is not a session export format and cannot be used as a route for customer
material, browser persistence, provider generation, or publication.
"""

from __future__ import annotations

from typing import Mapping

from .experience_package import sha256_hex


REPLAY_CAPSULE_PACKAGE_MANIFEST_NAME = "replay_capsule_package_manifest.json"
REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES = (
    "replay_capsule.json",
    "verified_replay_capsule_player.html",
    "README.md",
)


def build_replay_capsule_package_manifest(head_sha: str, members: Mapping[str, bytes]) -> dict[str, object]:
    """Bind the exact, synthetic-only three-file package to one source head."""

    if tuple(members) != REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES:
        raise ValueError("Replay capsule package members must be the fixed ordered synthetic-only set")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ValueError("Replay capsule package head_sha must be a full 40-character git SHA")
    return {
        "schema": "CreativeSyntheticReplayCapsulePackageManifest/v1",
        "status": "replay_capsule_package_verified",
        "head_sha": head_sha,
        "members": [
            {
                "path": name,
                "sha256": sha256_hex(members[name]),
                "size_bytes": len(members[name]),
            }
            for name in REPLAY_CAPSULE_PACKAGE_MEMBER_NAMES
        ],
        "boundary": {
            "synthetic_only": True,
            "customer_data_present": False,
            "caller_free_text_present": False,
            "external_provider_called": False,
            "publication_authorized": False,
            "client_story_authority": False,
        },
    }
