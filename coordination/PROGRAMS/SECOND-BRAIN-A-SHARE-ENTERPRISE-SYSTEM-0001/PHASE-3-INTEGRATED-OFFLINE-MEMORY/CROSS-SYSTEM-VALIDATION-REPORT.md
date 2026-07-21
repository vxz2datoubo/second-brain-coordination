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
- Replay core hash: `704e6585518936f202835e860438834e41893d6c5fb4f88529ad72e6cae33d8b`
- Candidate packet: `lp-6c3be4cbef415221a660`
- Packet content hash: `867b2890cbbac5d25cbb82f9bffd0ca948955c9039efa0f191999903ac228a86`
- QueryPlan hash: `b5cb5e5c21d8e7a5c6deba55c1e47ab1e6d3ae7986f0ce360ee26b53cad7dd79`
- ContextBundle semantic hash: `881e874baebb7038ad032bd9d47048ccdcbd6da2f0fbe60f3e663649f03ef573`
- Two independent runs matched all preceding semantic identifiers and hashes.

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

This validates plumbing, reproducibility, lineage and governance. It does not validate `amount`, `reserved`, the unit of `volume`, strategy alpha, profitability, production fitness, or a right to redistribute the local source.
