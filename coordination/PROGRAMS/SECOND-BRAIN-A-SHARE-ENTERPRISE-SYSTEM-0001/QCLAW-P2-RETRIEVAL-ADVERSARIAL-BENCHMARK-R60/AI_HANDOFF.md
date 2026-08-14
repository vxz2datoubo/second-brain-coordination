# R60 AI_HANDOFF

## Task
`QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60`

## Status
READY_FOR_GPT_REVIEW — completion_signal `QCLAW_P2_RETRIEVAL_ADVERSARIAL_BENCHMARK_R60_READY_FOR_GPT_REVIEW`.

## What this is
A **CANDIDATE_ONLY** benchmark + read-only harness. It is NOT a runtime, NOT a
semantic authority, NOT a merge request. It exists so GPT can test Codex P2.1/P2.2.

## Key numbers
- 90 total cases (within 80–120 baseline), 90 unique case_ids (dedup = primary key).
- 60 runnable (graded PASS today), 30 spec-pending (await Codex P2.2+ + GPT freeze).
- 11/11 required dimensions covered, 4/4 slices covered.
- 0 FAIL, 0 ERROR on runnable cases.

## What GPT must decide (escalated UNKNOWN items)
1. Where `aggregate_equivalence_key` is assigned (P2.2) — UNKNOWN-001.
2. Semantic provider transport contract (P2.4) — UNKNOWN-002.
3. Structural analogy representation (P2.4) — UNKNOWN-003.
4. Memory Palace migration route (P2.3) — UNKNOWN-004.
5. Cross-source semantic near-dup identity hash scope (P2.x) — UNKNOWN-005.
6. Whether stdlib-only single-process satisfies postflight instrumentation — UNKNOWN-006.

## Boundaries held
Read-only vs Phase-3; no Codex branch touch; PUBLIC_SAFE_SYNTHETIC only; no
private execution; no formal promotion; no trading; no self-merge.

## Where to look
- `README.md` — full scale/coverage/contract-traceability summary.
- `benchmark/cases/benchmark_cases.json` — the corpus.
- `evidence/harness_results.json` — machine evidence.
- `UNKNOWN-REGISTRY.md`, `DISCOVERY-LEDGER.md` — gaps.
- `AMED_RECEIPT.md`, `WPDCR.md` — receipts.
