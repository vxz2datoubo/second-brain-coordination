# Phase 3 Integrated Offline Memory

This package implements one research-only path from a manifest-bound local TDX `.day` artifact to P2 replay, a candidate LearningPacket, candidate memory retrieval and a governed ContextBundle.

## Boundaries

- `research_only / NO_TRADE / offline_only`
- no realtime, broker, account, order or service-lifecycle code
- no source data, SQLite runtime database or credential value in Git
- no automatic authority write
- ambiguous `amount`, `volume` unit and `reserved` fields remain non-authoritative
- missing ST and suspension fields remain explicit `UNKNOWN`, never `False`
- vendor volume is retained only in parser evidence and excluded from P2 standard-volume signals and simulation
- empty or out-of-order `.day` datasets cannot enter replay
- local activation requires an explicit no-redistribution license declaration and evidence reference

## Synthetic Tests

```powershell
python run_all_tests.py
```

The local `.day` validation CLI requires an explicit manifest, hash-bound activation policy and as-of time. It prints an aggregate receipt only.

The `integrated-day` command extends that read-only path through P2 replay, a candidate LearningPacket, an in-memory SQLite candidate store, QueryPlan retrieval and a ContextBundle. It still prints only an aggregate receipt and never persists the source data or runtime database.

```powershell
python public_safety_scan.py
```

The public safety scan rejects raw market files, runtime databases, logs, compiled or binary artifacts, and secret-shaped values from this delivery surface.
