# 0017 D0 repository and local-reality audit

`agent_id: CODEX`
`status: VERIFIED_REPOSITORY_PLUS_PARTIAL_LOCAL_EVIDENCE`
`boundary: research_only / NO_TRADE`

## Verified repository facts

| Area | Evidence | Verdict |
|---|---|---|
| Active route | `coordination/ACTIVE-CODEX-TASK.yaml` at `701e935a...` | Issue #69 is READY, D0 is planning only. |
| Existing 0017 definition | Three `A-SHARE-LIQUIDITY-SWEEP-RECLAIM-*v1.0` blueprints and one skill YAML | `REGISTERED_CANDIDATE`; no claimed implementation or backtest. |
| P2/P3 reuse candidate | `PHASE-2-OFFLINE-VERTICAL-SLICE` and `PHASE-3-INTEGRATED-OFFLINE-MEMORY` | Reuse only their manifest/PIT/replay patterns after interface review; do not create a second data or memory authority. |
| QCLAW assessment | PR #77 head `70ed222e...`; 42 frozen questions | Read-only independent acceptance instrument, not an implementation dependency. |
| Public repository runtime | No `brain_core` directory in this coordination repository | Any local `brain_core` capability is not a publicly reproducible repository fact. |

## Accessible-local evidence, sanitized

| Alias | Type | Coverage / shape | SHA-256 | Evidence state | Permitted D0 use |
|---|---|---|---|---|---|
| `LOCAL_TDX_DAY_300418` | vendor-local `.day` | 1,200 fixed 32-byte records; 2021-08-02 to 2026-07-16 | `c3ed79d2ffaa75ab254442df7ddc591d551e559a61b9d89ef68c86ff1ec595b9` | `PARTIAL_FIELD_EVIDENCE` | Structural inventory only. |
| `LOCAL_TDX_LC1_300418` | vendor-local `.lc1` | 783,360 bytes; format semantics not parsed in D0 | `776b77aea6df29fcc6b917dd01e57ca4913ec7628a6a444c22925aee28d6c71b` | `UNKNOWN_FORMAT_SEMANTICS` | Inventory only; not an input. |
| `LOCAL_JSON_300418` | legacy JSON bars | 250 daily-shaped records; 2025-06-24 to 2026-07-03 | `a817890b` prefix recorded in local receipt only | `LEGACY_UNKNOWN_PROVENANCE` | Not a validation dataset. |
| `SYNTHETIC_SAMPLE_BARS` | CSV fixture/sample | 36 data rows, daily-shaped | `10ad23` prefix recorded in local receipt only | `SYNTHETIC_ONLY` | Future fixture design only. |

The full local paths, raw records, private data bodies, databases and licenses are deliberately absent. The vendor-local inventory does **not** prove point-in-time availability, adjustment semantics, market-data entitlement, calendar completeness, suspension status, board/status history, or public reproducibility.

## Local code observations, not public-runtime claims

The private local workspace contains contracts named `MarketDataRecord`, `PriceBar`, `FeatureSet`, `BacktestResult`, and `ValidationReport`; it also contains replay/governance code and legacy trading modules. D0 reviewed their existence and names only as migration evidence. Their local working-tree state is owned by other agents and was not changed. No local replay was run. Therefore every proposed reuse is `ADAPT_PENDING_INTERFACE_AUDIT`, not a verified 0017 runtime.

## Scope scans and negative findings

- The local inventory includes data formats and modules that may relate to order-book, aggregate or legacy flow concepts. They are explicitly excluded from the 0017 BAR_ONLY input set.
- The coordination repository exposes existing 0017 blueprints, but no deterministic breach/reclaim labeler, no results dataset, no market-validity claim and no completed A-share backtest.
- No broker credential, account, order, live feed or service lifecycle was accessed.

## Reproducibility conclusion

The D0 package is public-safe and reproducible as a **planning artifact**. It is not independently reproducible as a historical research run until an authorized manifest declares a source, license, field semantics, corporate-action policy, calendar, timezone and availability model. This is recorded as `U-DATA`, `U-RULES` and `U-EXTERNAL` rather than silently filled with defaults.
