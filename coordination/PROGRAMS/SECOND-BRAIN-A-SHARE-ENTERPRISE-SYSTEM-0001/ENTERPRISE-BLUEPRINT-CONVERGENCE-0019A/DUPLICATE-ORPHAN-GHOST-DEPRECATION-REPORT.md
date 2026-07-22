# Duplicate, Orphan, Ghost and Deprecation Report

> agent_id: `CODEX`
>
> status: `CANDIDATE_DISPOSITIONS_PENDING_GPT`
>
> boundary: `research_only / NO_TRADE`

## Runtime and schema overlap

| Item | Finding | Disposition | Gate |
|---|---|---|---|
| Local `brain_core` SQLite/JSONL vs public Phase 3 `MemoryStore` | one logical W3 owner, but two physical candidates and no proven migration | `MIGRATION_DECISION_REQUIRED`; preserve both | inventory, dry-run migration, count/hash reconciliation, rollback, GPT decision |
| P2 `KnowledgeGateway` | synthetic replay facade with an in-file `KnowledgeAtom` | `REFERENCE_ONLY_TEST_FACADE` | must not be imported as W3 canonical storage |
| P3 local-adapter in-memory gateway | adapter test/compatibility path | `REFERENCE_ONLY_ADAPTER` | no authority claim |
| PR #64 | documentation/candidate mapping with unresolved identifiers and compatibility evidence | `REMEDIATE_OR_REFERENCE_ONLY` | corrected IDs, hashes, tests and explicit absorption map |
| PR #65 | frozen proposal duplicates query/index/gateway/runtime concerns | `REJECT_AS_PARALLEL_RUNTIME`; retain historical record | a new M0 route is required before any selective reuse |
| PR #8 | useful time/evidence concepts but historical architecture | `MIGRATION_INPUT` | field-by-field mapping, no direct merge |
| PR #34 | timestamped local evidence, potentially stale and privacy-sensitive | `REFERENCE_ONLY` | reverify path, scope, license and current hashes before use |
| 0018 supplemental queue/registration files | now represented in PROGRAM-INDEX and execution sequence | `DEPRECATE_PENDING_GPT` | confirm no external router still consumes them |

## Naming drift

Canonical names for new governance files are:

- `MODULE_0017` for the embedded liquidity validation capability;
- `MODULE_0018` for the embedded house-edge capability;
- `W12_DS02` for the write authority and `W12/DS-02` in human-readable text;
- full task IDs only in task/forecast/handoff objects.

Existing aliases remain readable until a separately tested migration. This task does not bulk-rewrite historical records.

## Ghost-capability ledger

| Claimed or easily implied capability | Reality | Disposition |
|---|---|---|
| raw exchange trade ticks, order events, queues or individual cancellations | no current evidence in the converged public runtime | `NOT_IMPLEMENTED`; never infer from L2 aggregates |
| true institution, retail or hot-money account identity | W13/W6 may hold evidence or hypotheses, not identity facts | `PROHIBITED_OVERCLAIM` |
| exact hidden stop-loss line created by a dominant trader | 0017 can test observable reference-zone breach/reclaim only | `HYPOTHESIS_NOT_FACT` |
| calibrated production probability fusion | PR #66 has a candidate schema; no main runtime or calibration evidence | `DRAFT_NOT_IMPLEMENTED` |
| operational `DecisionEpisode` ledger | blueprinted in W10, no canonical runtime on main | `CONTRACTED_NOT_IMPLEMENTED` |
| robust A-share Kelly allocation | blueprinted in W11; probability/rule/risk inputs are not frozen and validated | `BLOCKED_NOT_IMPLEMENTED` |
| automatic self-evolution that modifies production rules | governance allows candidate learning and review, not autonomous production mutation | `HUMAN_GATED_ONLY` |

## Orphans and stale references

- The W12 outcome-review reference expected by earlier routing is not present on current `main`; record as `UNKNOWN_STALE_REFERENCE`, not as completed evidence.
- Placeholder and negative-test paths containing `DOES-NOT-EXIST` or `...v1.0.yaml` are intentional fixtures/placeholders and are excluded from broken-production-reference counts.
- Installed local Codex skills and the old trading skill catalog are capability aids, not proof that DS-01 through DS-13 runtimes exist.

## Deprecation policy

Nothing is deleted in Issue #72. A deprecation needs an owner, replacement, consumer search, compatibility window, rollback and GPT approval. Historical PRs and reports remain evidence even when their runtime proposal is rejected.
