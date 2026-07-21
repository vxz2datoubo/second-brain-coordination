# Phase 3 Integrated Offline Memory

This package implements one research-only path from a manifest-bound local TDX `.day` artifact to P2 replay, a candidate LearningPacket, candidate memory retrieval and a governed ContextBundle.

## Boundaries

- `research_only / NO_TRADE / offline_only`
- no realtime, broker, account, order or service-lifecycle code
- no source data, SQLite runtime database or credential value in Git
- no automatic authority write
- ambiguous `amount`, `volume` unit and `reserved` fields remain non-authoritative

## Synthetic Tests

```powershell
python run_all_tests.py
```

The local `.day` validation CLI requires an explicit manifest, hash-bound activation policy and as-of time. It prints an aggregate receipt only.
