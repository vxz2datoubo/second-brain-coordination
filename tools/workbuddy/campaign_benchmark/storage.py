"""Storage-growth accounting for M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1.

The discovery plan requires the five buckets below to be reported separately
instead of one opaque total:

    immutable package bytes | ledger bytes | snapshots | private refs | media metadata

Every byte count is the UTF-8 length of a canonical JSON rendering, so the
numbers are reproducible in any clean clone without touching a real filesystem.

Private refs are references only. Real media binaries, real paths and real user
assets are never materialized here; ``guard_private_ref`` fails closed on
anything that looks like a real local path or a remote locator.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from creative_runtime.contracts import canonical_json
from creative_runtime.ledger import CreativeLedger

from . import synthetic

BUCKETS: tuple[str, ...] = (
    "immutable_package_bytes",
    "ledger_bytes",
    "snapshot_bytes",
    "private_refs_bytes",
    "media_metadata_bytes",
)

# Anything that could smuggle a real asset out of the clean room is rejected.
_FORBIDDEN_REF_PATTERNS: tuple[str, ...] = (
    r"^[a-zA-Z]:[\\/]",       # C:\ or C:/
    r"^\\\\",                  # UNC
    r"^file://",
    r"^https?://",
    r"(^|/)Users(/|$)",
    r"(^|/)home(/|$)",
    r"^\.{1,2}[\\/]",          # relative traversal
)


class StorageAccountingError(ValueError):
    """Raised when a storage input is malformed or attempts a real-asset reference."""


def guard_private_ref(ref: str) -> str:
    """Validate one synthetic private reference and return it unchanged."""

    if not isinstance(ref, str) or not ref:
        raise StorageAccountingError("private ref must be a non-empty string")
    for pattern in _FORBIDDEN_REF_PATTERNS:
        if re.search(pattern, ref):
            raise StorageAccountingError("private ref must stay synthetic: " + ref)
    return ref


def _byte_length(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def immutable_package(style: str) -> dict[str, Any]:
    """Return deterministic synthetic immutable package content for one style."""

    if style not in synthetic.STYLES:
        raise StorageAccountingError("unknown style: " + str(style))
    return {
        "schema": "SyntheticImmutablePackage/v1",
        "style": style,
        "scenes": list(synthetic.SCENE_POOL),
        "beats": list(synthetic.BEAT_POOL),
        "characters": list(synthetic.CHARACTERS),
        "fact_pool": list(synthetic.FACT_POOL),
        "note": "synthetic offline content; no licensed or private material",
    }


def snapshot_at(ledger: CreativeLedger, index: int) -> dict[str, Any]:
    """Return a deterministic state snapshot after ``index`` events."""

    if index < 0 or index > len(ledger.events):
        raise StorageAccountingError("snapshot index out of range")
    prefix = CreativeLedger.from_records(ledger.to_records()[:index])
    if not prefix.events:
        raise StorageAccountingError("cannot snapshot an empty prefix")
    state = prefix.replay()
    return {
        "schema": "SyntheticStateSnapshot/v1",
        "event_index": index,
        "head_event_hash": prefix.events[-1].event_hash,
        "state": state.to_dict(),
    }


def private_refs(seed: int, event_count: int) -> list[str]:
    """Return synthetic private references (locators only, never real assets)."""

    return [
        guard_private_ref("synth://private/%d/%d/ref-%04d" % (seed, event_count, index))
        for index in range(min(event_count, 16))
    ]


def media_metadata(seed: int, event_count: int) -> list[dict[str, Any]]:
    """Return simulated media metadata describing bytes without any binary payload."""

    return [
        {
            "schema": "SyntheticMediaMetadata/v1",
            "shot_index": index,
            "kind": "simulated_still" if index % 2 else "simulated_clip",
            "nominal_bytes": 4096 + (index * 512) % 65536,
            "provider": "none_offline_simulation",
            "generated": False,
        }
        for index in range(min(event_count, 24))
    ]


def account_campaign(ledger: CreativeLedger, seed: int, style: str) -> dict[str, int]:
    """Return the five-bucket byte breakdown for one synthetic campaign."""

    event_count = len(ledger.events)
    if event_count < 1:
        raise StorageAccountingError("cannot account for an empty campaign")
    if style not in synthetic.STYLES:
        raise StorageAccountingError("unknown style: " + str(style))

    snapshots = [
        snapshot_at(ledger, index)
        for index in _snapshot_indices(event_count)
    ]
    return {
        "immutable_package_bytes": _byte_length(immutable_package(style)),
        "ledger_bytes": _byte_length(ledger.to_records()),
        "snapshot_bytes": sum(_byte_length(snapshot) for snapshot in snapshots),
        "private_refs_bytes": _byte_length(private_refs(seed, event_count)),
        "media_metadata_bytes": _byte_length(media_metadata(seed, event_count)),
    }


def _snapshot_indices(event_count: int) -> list[int]:
    """Return deterministic snapshot positions (cadence probe input)."""

    step = max(1, event_count // 4)
    return sorted({min(event_count, index) for index in range(step, event_count + 1, step)})


def total_bytes(breakdown: Mapping[str, int]) -> int:
    """Return the summed total of a five-bucket breakdown."""

    unknown = set(breakdown) - set(BUCKETS)
    if unknown:
        raise StorageAccountingError("unknown storage buckets: " + ", ".join(sorted(unknown)))
    missing = set(BUCKETS) - set(breakdown)
    if missing:
        raise StorageAccountingError("missing storage buckets: " + ", ".join(sorted(missing)))
    return int(sum(breakdown[bucket] for bucket in BUCKETS))


def aggregate(breakdowns: Sequence[Mapping[str, int]]) -> dict[str, int]:
    """Sum several campaign breakdowns bucket by bucket."""

    if not breakdowns:
        raise StorageAccountingError("aggregate requires at least one breakdown")
    totals = {bucket: 0 for bucket in BUCKETS}
    for breakdown in breakdowns:
        for bucket in BUCKETS:
            totals[bucket] += int(breakdown.get(bucket, 0))
    return totals
