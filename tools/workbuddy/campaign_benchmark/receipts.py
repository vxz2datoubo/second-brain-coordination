"""Hashed receipts and the offline benchmark runner for WB-S1.

Receipts intentionally store SHA-256 digests and counts rather than copying
measurement bodies, matching the WorkBuddy verification runbook rule that
captured stdout/stderr are represented by hashes.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from creative_runtime.ledger import CreativeLedger

from . import REPLAY_EVENT_STRATA, STORAGE_CORPORA_SIZES, SCHEMA, metrics, storage, synthetic

# Timings are wall-clock and therefore environment dependent; the receipt always
# records the hardware/runtime declaration so a reader can tell whether two runs
# are comparable at all.
DEFAULT_SAMPLES = 11

# Corpora up to this size are accounted campaign by campaign. Larger corpora are
# derived by multiplication and explicitly flagged as extrapolated, because
# snapshotting every campaign individually is O(campaigns x events) hashing and
# adds no information once the per-campaign shape is known to be fixed.
REAL_CORPUS_LIMIT = 10


def sha256_of(payload: Any) -> str:
    """Return the SHA-256 of a canonical JSON rendering of ``payload``."""

    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def environment() -> dict[str, Any]:
    """Declare the local runtime used for one benchmark run."""

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "machine": platform.machine(),
        "schema": SCHEMA,
    }


def _reconstruct_and_replay(records: list[dict[str, Any]]) -> float:
    """Time one full reconstruct-then-replay cycle and return milliseconds."""

    start = time.perf_counter()
    rebuilt = CreativeLedger.from_records(records)
    rebuilt.replay()
    return (time.perf_counter() - start) * 1000.0


def measure_replay_latency(
    ledger: CreativeLedger,
    samples: int = DEFAULT_SAMPLES,
    warmup: int = 2,
) -> list[float]:
    """Time ``replay()`` on a reconstructed ledger, ``samples`` times.

    Each sample rebuilds the ledger from serialized records so the measurement
    covers the real reconstruct-then-replay path (init -> resume -> replay)
    instead of replaying an already warm in-memory object.

    ``warmup`` runs are discarded. Measured on this machine, a cold first run can
    be roughly 3x slower than a warmed run, so skipping warmup manufactures a
    latency number that no steady-state caller would ever observe.
    """

    if samples < 1:
        raise ValueError("samples must be >= 1")
    if warmup < 0:
        raise ValueError("warmup must be >= 0")
    records = ledger.to_records()
    for _ in range(warmup):
        _reconstruct_and_replay(records)
    return [_reconstruct_and_replay(records) for _ in range(samples)]


def variation(samples: Sequence[float]) -> float:
    """Return the coefficient of variation (stddev / mean) of a sample set."""

    if len(samples) < 2:
        return 0.0
    mean = sum(samples) / len(samples)
    if mean == 0:
        return 0.0
    variance = sum((sample - mean) ** 2 for sample in samples) / (len(samples) - 1)
    return round((variance ** 0.5) / mean, 6)


def run_replay_probe(
    strata: Sequence[int] = REPLAY_EVENT_STRATA,
    rounds: int = DEFAULT_SAMPLES,
    warmup: int = 2,
    style: str = "noir_chamber",
) -> dict[str, Any]:
    """Run the M-CAMPAIGN-REPLAY-P95-v1 discovery plan across event strata.

    Strata are measured **interleaved** (round-robin, one sample per stratum per
    round) rather than one stratum at a time. Sequential measurement was observed
    to bias later, larger strata by well over 40% on this machine, which would
    make the 10000-event stratum look superlinear when it is in fact near-linear.
    """

    if rounds < 1:
        raise ValueError("rounds must be >= 1")
    records_by_stratum: dict[int, list[dict[str, Any]]] = {}
    for event_count in strata:
        ledger = synthetic.build_campaign(seed=event_count, event_count=event_count, style=style)
        records_by_stratum[event_count] = ledger.to_records()

    for event_count in strata:
        for _ in range(warmup):
            _reconstruct_and_replay(records_by_stratum[event_count])

    samples_by_stratum: dict[int, list[float]] = {event_count: [] for event_count in strata}
    for _ in range(rounds):
        for event_count in strata:
            samples_by_stratum[event_count].append(
                _reconstruct_and_replay(records_by_stratum[event_count])
            )

    rows: list[dict[str, Any]] = []
    for event_count in strata:
        samples = samples_by_stratum[event_count]
        ledger_bytes = len(json.dumps(records_by_stratum[event_count], sort_keys=True).encode("utf-8"))
        row = dict(
            metrics.replay_measurement(
                event_count=event_count,
                style=style,
                samples=samples,
                ledger_bytes=ledger_bytes,
            )
        )
        row["coefficient_of_variation"] = variation(samples)
        rows.append(row)

    body = {
        "metric_id": "M-CAMPAIGN-REPLAY-P95-v1",
        "environment": environment(),
        "rows": rows,
        "method": {
            "warmup_runs": warmup,
            "rounds": rounds,
            "sampling": "interleaved_round_robin",
            "note": "wall-clock on a shared local machine; absolute values are environment specific",
        },
    }
    return {**body, "receipt_sha256": sha256_of(rows), "sample_policy": rounds}


def run_storage_probe(
    corpora_sizes: Sequence[int] = STORAGE_CORPORA_SIZES,
    style: str = "noir_chamber",
    event_count: int = 120,
) -> dict[str, Any]:
    """Run the M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1 discovery plan.

    ``event_count`` is fixed per campaign so a corpus of N campaigns differs only
    by campaign count, which keeps the per-campaign-hour denominator honest.
    """

    rows: list[dict[str, Any]] = []

    for campaign_count in corpora_sizes:
        if campaign_count <= REAL_CORPUS_LIMIT:
            # Account every campaign individually with its own deterministic seed.
            breakdowns = [
                storage.account_campaign(
                    synthetic.build_campaign(seed=seed, event_count=event_count, style=style),
                    seed=seed,
                    style=style,
                )
                for seed in range(1, campaign_count + 1)
            ]
            breakdown = storage.aggregate(breakdowns)
            hours = sum(
                synthetic.simulate_campaign_hours(seed=seed, event_count=event_count)
                for seed in range(1, campaign_count + 1)
            )
            extrapolated = False
        else:
            # Above the real-accounting limit the per-campaign shape is fixed by
            # construction, so the corpus total is a pure multiple. Flagged as
            # extrapolated so nobody reads it as an independently measured total.
            per_campaign = storage.account_campaign(
                synthetic.build_campaign(seed=1, event_count=event_count, style=style),
                seed=1,
                style=style,
            )
            breakdown = {bucket: value * campaign_count for bucket, value in per_campaign.items()}
            hours = synthetic.simulate_campaign_hours(seed=1, event_count=event_count) * campaign_count
            extrapolated = True

        row = dict(
            metrics.storage_measurement(
                campaign_count=campaign_count,
                breakdown=breakdown,
                total_bytes=storage.total_bytes(breakdown),
                campaign_hours=hours,
            )
        )
        row["extrapolated"] = extrapolated
        rows.append(row)

    per_campaign_breakdown = storage.account_campaign(
        synthetic.build_campaign(seed=1, event_count=event_count, style=style), seed=1, style=style
    )
    body = {
        "metric_id": "M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1",
        "environment": environment(),
        "per_campaign_event_count": event_count,
        "per_campaign_bytes": storage.total_bytes(per_campaign_breakdown),
        "per_campaign_hours": synthetic.simulate_campaign_hours(seed=1, event_count=event_count),
        "real_accounting_limit": REAL_CORPUS_LIMIT,
        "rows": rows,
    }
    return {**body, "receipt_sha256": sha256_of(rows)}


def render(report: Mapping[str, Any]) -> str:
    """Render a probe report as canonical JSON text."""

    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)


def _main(argv: Sequence[str]) -> int:
    """CLI entry: ``python -m campaign_benchmark.receipts [replay|storage|all]``."""

    which = argv[1] if len(argv) > 1 else "all"
    reports: dict[str, Any] = {"schema": SCHEMA, "environment": environment()}
    if which in ("replay", "all"):
        reports["replay"] = run_replay_probe()
    if which in ("storage", "all"):
        reports["storage"] = run_storage_probe()
    print(render(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
