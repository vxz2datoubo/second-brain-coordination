"""Offline synthetic campaign benchmark probe (WorkBuddy R175 / WB-S1).

Purpose
-------
Implement the discovery plans for:

* ``M-CAMPAIGN-REPLAY-P95-v1``  -- campaign state reconstruction p95 latency
  (formula_revision ``p95_wall_clock_replay/v1``).
* ``M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1`` -- incremental persistent storage per
  campaign-hour (formula_revision ``ledger_plus_snapshot_plus_metadata_bytes/v1``).

Scope boundaries (hard)
-----------------------
* Synthetic, offline, deterministic, credential-free, network-free.
* This package is a **consumer** of ``creative_runtime``. It never mutates
  runtime behaviour, metric formulas, contracts or existing acceptance tests.
* ``campaign_hours`` are SIMULATED durations computed from deterministic
  synthetic inputs. They are not wall-clock play time and must never be
  reported as real user session data.
"""

from __future__ import annotations

SCHEMA: str = "WorkBuddyCampaignBenchmarkProbe/v1"

METRIC_IDS: tuple[str, ...] = (
    "M-CAMPAIGN-REPLAY-P95-v1",
    "M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1",
)

# discovery_plan for M-CAMPAIGN-REPLAY-P95-v1:
#   "Benchmark at 10, 100, 1000 and 10000 events on declared local hardware;
#    record median, p95, bytes and sample count."
REPLAY_EVENT_STRATA: tuple[int, ...] = (10, 100, 1000, 10000)

# discovery_plan for M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1:
#   "Generate deterministic 1, 10, 100 and 1000 campaign corpora; separate
#    immutable package bytes, ledger bytes, snapshots, private refs and
#    simulated media metadata."
STORAGE_CORPORA_SIZES: tuple[int, ...] = (1, 10, 100, 1000)

__all__ = [
    "SCHEMA",
    "METRIC_IDS",
    "REPLAY_EVENT_STRATA",
    "STORAGE_CORPORA_SIZES",
]
