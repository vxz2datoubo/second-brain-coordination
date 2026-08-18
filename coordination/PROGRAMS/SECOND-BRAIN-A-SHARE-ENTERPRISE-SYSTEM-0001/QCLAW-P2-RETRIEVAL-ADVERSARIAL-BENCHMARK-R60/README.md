# R60 — P2 Retrieval Adversarial Benchmark

## Governed identity
Task `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60`; Issue #296; Draft PR #304; route_epoch 60; goal mode; branch `qclaw/p2-retrieval-adversarial-benchmark-r60`.

Historical author/executor provenance remains QCLAW. Current remediation executor is `GPT_ENGINEERING_WORKER`, model `GPT-5.6 Sol`. Final acceptance belongs to an independent GPT reviewer. Merge is not authorized.

## Reconciliation
- canonical main: `d7591b123c72f012f20149337a3ae914db56d29d`
- reviewed predecessor: `ec5b7dc1fcdfdd5f379ae3c2f2f0410e5ec7013b`
- non-destructive current-main merge: `ad80d5432585335ff38c24ee87f2415d8a656f70`
- retained canonical 90-case corpus blob: `5b84ec894f7f94d6a408dfd0d0744fbfaeca01ba`

## Evidence status
The original `60/60 PASS` was formally rejected by GPT Review `4936644607` as `REJECTED_INVALID_FALSE_GREEN`; it is never restored as valid evidence.

Current rerun of all 60 `runnable=true` cases, with expected outcomes unchanged:
- **58 PASS / 2 FAIL / 0 ERROR**
- FAIL: `r60-013`, `r60-025`, both `NEEDS_REVALIDATION`
- 30 original spec-pending cases retained
- 5 targeted regressions: **5/5 PASS**

## B01
REJECT grading scans complete caller-observable bundle and telemetry surfaces rather than atoms only. Hidden relation/conflict/unknown/provenance/trust IDs are detectable. `r60-019` now passes only because current R119 endpoint-safe runtime emits zero forbidden-ID leak surfaces.

## B02
Lifecycle/freshness mutations are persisted through canonical packet/import and re-read. Derived supersession/closure uses canonical correction/import. Invalid visibility mutation reaches verification and fails closed; the harness no longer describes one object while testing an unmodified copy.

## B03
Forbidden identities come from persisted canonical objects and current query policy. `id_hint` is only fixture aliasing. A no-hint revoked fixture regression resolves a real stored ID into the forbidden set.

## Current canonical regressions
- R118 public-report oracle equivalence: PASS.
- R119/P2.2 endpoint-safe base bundle + `GPTSecondBrainContextBundle/v1` projection: PASS.

## Evidence boundary
Local behavior execution used single-process Python 3.13.5 in an isolated container with no checkout/network. Four load-bearing runtime modules were byte-verified against GitHub; retrieval was a logic-preserving projection cross-checked against canonical source. GitHub Phase-3 CI is the exact merged-runtime regression/public-safety authority.

## Hard locks
No Phase-3 runtime source edit, Control Tower edit, R142 start, private data, formal promotion, production, scheduler/MCP runtime, permission/secret expansion, W3/domain authority, trading/accounts/orders/funds, destructive history rewrite, self-review, or merge.
