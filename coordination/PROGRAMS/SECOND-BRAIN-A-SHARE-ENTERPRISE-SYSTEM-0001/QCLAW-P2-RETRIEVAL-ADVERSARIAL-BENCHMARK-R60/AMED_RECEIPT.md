# R60 AMED Execution Receipt — executor substitution remediation

## Provenance
Historical benchmark author/executor: QCLAW, preserved in Git history. Current remediation executor: `GPT_ENGINEERING_WORKER`; model `GPT-5.6 Sol`; repository I/O via OpenAI GitHub connector / GitHub App; bounded local behavior execution via isolated Python 3.13.5. Final reviewer is a separate GPT window.

## Reconciliation
- canonical main: `d7591b123c72f012f20149337a3ae914db56d29d`
- reviewed head: `ec5b7dc1fcdfdd5f379ae3c2f2f0410e5ec7013b`
- non-destructive current-main merge: `ad80d5432585335ff38c24ee87f2415d8a656f70`
- no reset/rebase/force/history rewrite; post-merge PR remained Draft/open/unmerged and R60-only in substantive diff.

## Blockers
**B01:** complete observable-surface REJECT oracle, including relations/conflicts/unknowns/provenance/trust/telemetry, with a relation-target-only leak regression.

**B02:** mutated lifecycle/freshness objects are actually imported and re-read; derived supersession uses canonical correction/import; invalid visibility mutation reaches verification and fails closed.

**B03:** forbidden identities derive from real persisted canonical IDs and current query policy; optional `id_hint` is not an oracle.

## Current behavior evidence
Canonical 90-case corpus blob retained: `5b84ec894f7f94d6a408dfd0d0744fbfaeca01ba`.

- runnable: 60
- PASS: 58
- FAIL: 2 (`r60-013`, `r60-025`)
- ERROR: 0
- targeted regressions: 5 PASS / 0 FAIL / 0 ERROR
- spec-pending retained: 30
- historical 60/60: **REJECTED_INVALID_FALSE_GREEN**

`r60-019`: PASS with actual forbidden endpoint `at-915e364b8719ad76582f` and empty complete-surface leak set.

`r60-013` and `r60-025` are preserved as `NEEDS_REVALIDATION`; expected outcomes were not changed to manufacture green evidence.

## Validation boundary
Local run was one synchronous Python 3.13.5 process, no pool/daemon/subprocess/network/private data. Four load-bearing runtime modules were blob-byte verified; retrieval behavior was locally projected and cross-checked against canonical source. GitHub Phase-3 CI is the exact merged-runtime/full-regression authority. Final exact head and CI IDs are externally bound in PR/Issue evidence.

## Locks / rollback
All remediation writes remain inside the R60 program root. No Phase-3 source, Control Tower, Codex/R142, secrets/permissions, scheduler, production, W3/domain authority, trading/funds, or merge authority. Rollback is a normal revert on the same branch; no destructive history operation is required.
