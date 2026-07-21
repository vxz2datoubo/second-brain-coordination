# Cross-System Validation Report

`agent_id: CODEX`

`task_id: CODEX-P3-INTEGRATED-OFFLINE-MEMORY-SYSTEM-0006`

`boundary: research_only / NO_TRADE / offline_only`

## Closed path

The implemented path is:

`SourceManifest + SourceActivationPolicy -> TDX .day parser -> existing P2 Bar -> deterministic replay and ValidationReport -> candidate LearningPacket -> PR #46-derived candidate MemoryStore -> QueryPlan -> ContextBundle`

No second `PriceBar`, market-data authority, memory authority or trading path was created.

## Local aggregate evidence

- Artifact SHA256: `c3ed79d2ffaa75ab254442df7ddc591d551e559a61b9d89ef68c86ff1ec595b9`
- Accepted daily bars: 1200
- Date boundary: 2021-08-02 through 2026-07-16
- Parser and replay quarantine: 0 / 0
- Parse core hash: `bc529ac857568fe77553bce0b9c9b14c26017faf8f49f2ead73be63212636ba8`
- Replay core hash: `fe7091f312e7ad61cb397c2f88e1b2fb80bc1e649c0e6c00cce5476dd59cf1d8`
- Candidate packet: `lp-865c7cf302d94aca439b`
- Packet content hash: `6ee7aba09d3087e2616a76f2e50602f2ee28043324d814447d6ff2f02d374605`
- QueryPlan hash: `b5cb5e5c21d8e7a5c6deba55c1e47ab1e6d3ae7986f0ce360ee26b53cad7dd79`
- ContextBundle semantic hash: `b492415d8c7f82ea1dc08d79e54234e853a852e7588a2199845a59e1e188440d`
- Two independent runs matched all preceding semantic identifiers and hashes.
- License activation is explicitly `LOCAL_USER_HELD_NO_REDISTRIBUTION`, bound to local evidence and `distribution_allowed=false`; UNKNOWN or undeclared licenses are rejected.
- Vendor volume remains in parser evidence only. It is mapped to P2 standard volume as `None`, while absent suspension and ST fields also remain `None`.
- Signal generation and portfolio simulation therefore abstain; the local sample produced zero simulated actions and strategy status `ABSTAIN`.
- Empty files are `EMPTY` and rejected by the adapter. Out-of-order `.day` datasets are `REJECTED` and cannot enter P2 replay.

Only aggregate metadata was retained. The source file, bars and in-memory SQLite database were not exported.

## XT acceptance

| Test | Result | Evidence |
|---|---|---|
| XT-001 hash stability | PASS | packet ID/content hash and semantic context hash stable across independent stores |
| XT-002 packet roundtrip | PASS | JSON roundtrip plus duplicate import returns `IDEMPOTENT_DUPLICATE` |
| XT-003 conflict propagation | PASS | explicit semantic conflict survives import and ContextBundle assembly |
| XT-004 UNKNOWN preservation | PASS | all six replay UNKNOWNs remain query-visible |
| XT-005 credential isolation | PASS | credential-value field rejected before any packet write |
| XT-006 512 atom scale | PASS | 512 atoms retrieved with integrity check clean |

## Calibration

This validates plumbing, reproducibility, lineage and governance. It does not validate `amount`, `reserved`, the unit of `volume`, historical ST/suspension status, strategy alpha, profitability, production fitness, or a right to redistribute the local source.
