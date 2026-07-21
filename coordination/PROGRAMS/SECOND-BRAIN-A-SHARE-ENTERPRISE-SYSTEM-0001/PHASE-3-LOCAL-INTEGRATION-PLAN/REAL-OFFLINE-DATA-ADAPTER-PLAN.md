# Real Offline Data Adapter Plan

## Scope and safe source classes

This plan covers local TDX `vipdoc` bars, user-provided TQ exports, and CSV/JSON/JSONL datasets. It does not call TdxQuant, TDX MCP, broker APIs, or realtime sources.

| Route | Initial class | Required evidence before replay | Default outcome |
| --- | --- | --- | --- |
| `vipdoc` `.day` / minute files | `legacy_unknown` | file-format parser evidence, symbol/timezone/session interpretation, corporate-action policy | offline bar candidate |
| TQ export | `payload_sample_only` | export manifest, tool/version, field table, entitlement and timestamp semantics | provider-specific offline candidate |
| CSV / JSON / JSONL | `legacy_unknown` | source ID, schema, raw hash, time semantics, availability, and sample validation | manifest-gated candidate |
| P2 synthetic fixture | `historical_verified` only for its synthetic contract | deterministic fixture and test hash | regression baseline, not market proof |

## Pipeline

1. Inventory path and generate a non-secret source manifest.
2. Copy a bounded approved sample into an isolated research fixture area; retain original immutable reference and hash.
3. Parse raw records without dropping vendor-specific fields.
4. Normalize only documented fields to `MarketDataRecord` / `PriceBar`; retain raw payload reference.
5. Gate on A-share session calendar, T+1, suspensions, daily limits, corporate actions, and point-in-time availability. A missing rule blocks promotion.
6. Snapshot dataset and run deterministic replay tests. Emit abstention and quality reports.

## No-data-loss and no-overclaim rules

- Duplicate keys are source-specific: provider symbol, source time when known, provider sequence when known, raw hash, and local receive/ingest sequence. None alone is universal.
- Zero, blank, missing, permission-denied, and parser error receive separate quality codes.
- L1 snapshots, L2 aggregates, and historical bars have distinct capability labels.
- No public repository upload of proprietary raw data, database files, JSONL runtime logs, account-related files, or data with unknown license.

## Acceptance probe

An adapter can move from `Interface` to `Experimental` only when a small real offline sample produces: manifest, stable parser, raw-to-normalized mapping, deterministic rerun, lineage hash, quality report, and no prohibited capability claim.
