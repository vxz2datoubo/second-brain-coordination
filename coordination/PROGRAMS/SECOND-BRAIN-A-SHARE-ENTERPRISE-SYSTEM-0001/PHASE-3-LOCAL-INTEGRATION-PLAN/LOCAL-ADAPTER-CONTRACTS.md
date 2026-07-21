# Local Adapter Contracts

`agent_id: CODEX`  
`task_id: A-SHARE-LOCAL-MOTHER-SYSTEM-ADAPTER-PLAN-0003`  
`scope: design only; research_only / NO_TRADE`

## Common envelope

Every adapter output must expose `object_id`, `authority_id`, `source_manifest_id`, `schema_version`, `lineage`, `quality`, `capability`, `available_at`, `receive_time_local`, and `trace_id`. `receive_time_local` is never relabeled as exchange/provider time. Missing semantics remain `UNKNOWN`, not inferred.

## Interfaces

| Interface | Input | Output | Hard boundary |
| --- | --- | --- | --- |
| `OfflineDatasetAdapter` | approved local file reference plus manifest | `RawMarketPayload` or `MarketDataRecord` projection | Read/copy only; preserves provider fields and raw hash. |
| `LocalReadAdapter` | narrow allow-listed local module/service contract | typed read projection | No broad filesystem/database write or service control. |
| `KnowledgeGatewayAdapter` | authorized query plus access policy | `KnowledgeQuery`, `ContextBundle`, evidence references | Full authorized semantics allowed; credential values never leave local-only storage. |
| `LearningPacketAdapter` | candidate learning object | P1-compatible candidate packet | Cannot overwrite approved authority. |
| `CapabilityProbeAdapter` | read-only probe specification | signed evidence envelope and capability delta | No account/order/broker method or undocumented field invention. |

## Required result states

`VERIFIED`, `PARTIALLY_VERIFIED`, `PAYLOAD_SAMPLE_ONLY`, `LEGACY_UNKNOWN`, `REJECTED`, and `BLOCKED_BY_POLICY` are distinct. A returned zero is not equivalent to absent, permission-denied, malformed, or provider error.

## Market-data invariants

- A source manifest declares provider, export/tool version when known, market, symbol format, timezone, field semantics, corporate-action treatment, entitlement, raw hash, and source classification.
- A bar is eligible for replay only after point-in-time availability, calendar/session, suspension, corporate-action, and daily-limit policies are declared or explicitly abstained.
- L2 aggregate fields are aggregates. They cannot become raw trade, order, queue, cancel-event, or auction trajectory records without direct evidence.
- All adapters default to research output and `NO_TRADE`.

## Compatibility with P1/P2

Local contracts adapt P1 exchange envelopes and may reuse P2 deterministic test patterns. They do not make P2 synthetic data, legacy local state, or a service route the system of record.
