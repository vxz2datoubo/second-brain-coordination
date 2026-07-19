# Implementation Milestones

## Phase 0: Post-0008 Evidence Intake

Goal: ingest WorkBuddy upgrade A/B results as evidence, not code assumptions.

Tasks:

- Read 0008 post-upgrade artifacts.
- Update source capability matrix.
- Create preservation map for v1.0.4 vs upgraded methods.
- Decide which gates are open.

Acceptance:

- Capability decisions cite raw evidence.
- No unverified field is promoted.

## Phase 1: Event Contracts

Goal: add realtime event contracts and tests.

Scope:

- `RawMarketPayload`
- `MarketSnapshotEvent`
- `VendorFundFlowSnapshot`
- `BarEvent`
- `DataQualityEvent`
- `SourceCapability`
- `MarketPhase`
- `StalenessState`

Acceptance:

- Unit tests validate required fields, local time vs source time, raw hash, capability labels, and status enums.

## Phase 2: Raw Writer And Normalizers

Goal: implement append-only raw persistence and source-specific normalization.

Scope:

- TdxQuant snapshot/get_more_info normalizer.
- TDX MCP snapshot normalizer.
- WeStock historical/context normalizer.
- vipdoc bar normalizer.

Acceptance:

- Same raw payload yields deterministic hash and normalized output.
- Raw payloads are not tracked by Git.

## Phase 3: Callback-Driven Collector

Goal: implement `subscribe_hq -> active read` collector when WorkBuddy confirms safe route.

Scope:

- debounce
- rate limit
- local sequence
- staleness
- polling backstop
- safe method whitelist

Acceptance:

- Simulated callback stream produces snapshot reads without duplicate floods.
- Callback payload alone does not produce tick events.

## Phase 4: Health And Failover

Goal: route selection and degradation.

Scope:

- source health
- duplicate/stale/anomaly events
- cross-source comparison
- fallback to MCP/WeStock/vipdoc

Acceptance:

- Failed primary route degrades without breaking replay.
- Unsupported strategies return blocked/no-signal.

## Phase 5: Feature And Signal Integration

Goal: feed governed features to ResearchQueue.

Scope:

- snapshot spread/imbalance
- L2 aggregate deltas
- source conflict features
- A-share session features

Acceptance:

- Raw L2-only indicators stay blocked unless capabilities are verified.
- Mother-system writeback updates SkillRegistry, ModuleStatus, bulletin, and SelfEvolutionLog.

