"""Fail-closed receipt-only path policy used before receipt designation."""

from __future__ import annotations


_RECEIPT_PREFIX = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "BRAINOPS-APP-FIRST-CONTROL-PLANE/E48/RECEIPT/"
)
_EVIDENCE_SUFFIXES = (".md", ".yaml", ".json")


def receipt_paths_are_evidence_only(paths: tuple[str, ...]) -> bool:
    """Runtime, source, test and workflow files can never enter a receipt."""

    return bool(paths) and all(
        path.startswith(_RECEIPT_PREFIX) and path.endswith(_EVIDENCE_SUFFIXES)
        for path in paths
    )
