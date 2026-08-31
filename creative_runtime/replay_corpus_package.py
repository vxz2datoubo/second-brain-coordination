"""Fixed-layout package metadata for exhaustive synthetic replay corpora.

The package contains source-bound synthetic regression evidence and a local
read-only index viewer.  It is intentionally not a session export, a browser
story engine, a media generator, or a customer-data format.
"""

from __future__ import annotations

from typing import Mapping

from .experience_package import sha256_hex


REPLAY_CORPUS_PACKAGE_MANIFEST_NAME = "replay_corpus_package_manifest.json"
REPLAY_CORPUS_PACKAGE_MEMBER_NAMES = (
    "replay_corpus.json",
    "replay_review_board.json",
    "verified_replay_corpus_viewer.html",
    "README.md",
)


def build_replay_corpus_package_manifest(head_sha: str, members: Mapping[str, bytes]) -> dict[str, object]:
    """Bind the fixed, synthetic-only corpus package members to one exact head."""

    if tuple(members) != REPLAY_CORPUS_PACKAGE_MEMBER_NAMES:
        raise ValueError("Replay corpus package members must be the fixed ordered synthetic-only set")
    if not isinstance(head_sha, str) or len(head_sha) != 40:
        raise ValueError("Replay corpus package head_sha must be a full 40-character Git SHA")
    return {
        "schema": "CreativeSyntheticReplayCorpusPackageManifest/v1",
        "status": "replay_corpus_package_verified",
        "head_sha": head_sha,
        "members": [
            {"path": name, "sha256": sha256_hex(members[name]), "size_bytes": len(members[name])}
            for name in REPLAY_CORPUS_PACKAGE_MEMBER_NAMES
        ],
        "boundary": {
            "synthetic_only": True,
            "customer_data_present": False,
            "caller_free_text_present": False,
            "external_provider_called": False,
            "publication_authorized": False,
            "canonical_knowledge_write": False,
            "client_story_authority": False,
        },
    }
