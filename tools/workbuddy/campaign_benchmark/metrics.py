"""Deterministic statistics for the two WorkBuddy discovery metrics.

Both helpers are pure functions so any clean clone reproduces the same numbers
from the same latency samples. The percentile convention is documented
explicitly because "p95" is ambiguous otherwise.

Convention: nearest-rank percentile on the ascending-sorted sample
``sorted[min(n - 1, ceil(q * n) - 1)]``. Nearest-rank is chosen over
interpolation because it always returns an observed sample, which keeps the
reported value reproducible from a small, auditable sample count.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


def percentile(samples: Sequence[float], quantile: float) -> float:
    """Return the nearest-rank percentile of ``samples``."""

    if not samples:
        raise ValueError("percentile requires at least one sample")
    if not 0.0 < quantile <= 1.0:
        raise ValueError("quantile must be in (0, 1]")
    ordered = sorted(float(sample) for sample in samples)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return ordered[rank - 1]


def median(samples: Sequence[float]) -> float:
    """Return the median using the same nearest-rank convention."""

    if not samples:
        raise ValueError("median requires at least one sample")
    ordered = sorted(float(sample) for sample in samples)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def describe(samples: Sequence[float]) -> dict[str, Any]:
    """Return median, p95, min, max and sample count for one latency stratum."""

    if not samples:
        raise ValueError("describe requires at least one sample")
    return {
        "sample_count": len(samples),
        "min_ms": round(min(samples), 6),
        "median_ms": round(median(samples), 6),
        "p95_ms": round(percentile(samples, 0.95), 6),
        "max_ms": round(max(samples), 6),
    }


def bytes_per_campaign_hour(total_bytes: int, campaign_hours: float) -> float:
    """Return bytes per simulated campaign-hour (``LOWER_IS_BETTER_WITHOUT_LOSS``)."""

    if campaign_hours <= 0:
        raise ValueError("campaign_hours must be > 0")
    return round(total_bytes / campaign_hours, 6)


def replay_measurement(
    *,
    event_count: int,
    style: str,
    samples: Sequence[float],
    ledger_bytes: int,
) -> Mapping[str, Any]:
    """Build one M-CAMPAIGN-REPLAY-P95-v1 measurement row."""

    stats = describe(samples)
    return {
        "metric_id": "M-CAMPAIGN-REPLAY-P95-v1",
        "formula_revision": "p95_wall_clock_replay/v1",
        "unit": "milliseconds",
        "direction": "LOWER_IS_BETTER",
        "event_count": event_count,
        "style": style,
        "ledger_bytes": ledger_bytes,
        **stats,
        "percentile_convention": "nearest_rank",
        "evidence_class": "WORKBUDDY_EXECUTOR_VERIFIED",
    }


def storage_measurement(
    *,
    campaign_count: int,
    breakdown: Mapping[str, int],
    total_bytes: int,
    campaign_hours: float,
) -> Mapping[str, Any]:
    """Build one M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1 measurement row."""

    return {
        "metric_id": "M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1",
        "formula_revision": "ledger_plus_snapshot_plus_metadata_bytes/v1",
        "unit": "bytes_per_campaign_hour",
        "direction": "LOWER_IS_BETTER_WITHOUT_LOSS",
        "campaign_count": campaign_count,
        "simulated_campaign_hours": campaign_hours,
        "breakdown": dict(breakdown),
        "total_bytes": total_bytes,
        "bytes_per_campaign_hour": bytes_per_campaign_hour(total_bytes, campaign_hours),
        "evidence_class": "WORKBUDDY_EXECUTOR_VERIFIED",
    }
