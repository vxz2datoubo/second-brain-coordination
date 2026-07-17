# Current Architecture Map

## Reused Mother-System Core

- `brain_core/contracts.py`
  - Implemented: `SourceRecord`, `EvidenceItem`, `KnowledgeAtom`, `MarketDataRecord`, `PriceBar`, `FeatureSet`, `OrderBookSnapshot`, `TradePrint`, `SignalRecord`, `ValidationReport`, `SkillRegistryEntry`, `ModuleStatusRecord`, `BulletinStateRecord`, `SelfEvolutionLog`.
  - Gap: no explicit realtime event contracts for `RawMarketPayload`, `MarketSnapshotEvent`, `VendorFundFlowSnapshot`, `DataQualityEvent`, `SourceCapability`, `MarketPhase`, or `StalenessState`.

- `brain_core/foundation_data_governance.py`
  - Implemented: raw / normalized / features / signals / reports / runtime_logs layer policies.
  - Implemented: interface-style `TradeEvent`, `OrderEvent`, `BookSnapshot`, `AuctionSnapshot`, `CapabilityDescriptor`, adapter health and reliability profiles.
  - Existing adapter catalog: `HistoricalTradeReplayAdapter`, `TdxMcpSnapshotAdapter`, `MockMboAdapter`, `MockAuctionAdapter`.
  - Gap: current Tdx adapter is capability descriptor and governance surface, not an actual unified realtime collector.

- `brain_core/trading_domain.py`
  - Implemented: research replay, A-share proxy guard, TDX quote sample writeback, Tencent qt sample writeback, WorkBuddy context sample writeback, WeStock/Tushare historical baseline lanes, ResearchQueue governance.
  - Gap: realtime data is still accepted mainly as injected samples or reports, not as append-only raw events with local sequence, raw hash, source version, entitlement, staleness, and failover state.

- `apps/cli/brainctl.py` and `server.py`
  - Implemented: thin CLI/API for trading replay and A-share sample snapshot reporting.
  - Gap: no endpoint/CLI for a governed realtime event collector or source health router.

## Existing Data Routes

- `mcp/tdx_live_bridge.py`
  - Official TDX MCP stdio bridge.
  - Tools: `tdx_realtime`, `tdx_kline`, `tdx_lookup`, `tdx_news`, `tdx_notice`, `tdx_screener`.
  - Uses environment/local credential lookup. No raw payload persistence layer.

- `daytrade_system/live/tdx_mcp_client.py`
  - HTTP JSON-RPC client for TDX MCP.
  - Methods: quotes, kline, news, notice, lookup, macro, screener.
  - Provides throttling but no governed raw/normalized event schema.

- `daytrade_system/medallion/tdx_connector.py`
  - Historical local `vipdoc` fallback plus unfinished MCP branch.
  - Reads `.day` and `.lc5` style files for day/5m bars.
  - Risk: `_offline_quote` constructs pseudo realtime quote from historical/minute files; must be marked `HISTORICAL_BAR` or `offline_proxy`, never realtime L2.

- `mcp/tdx_bridge.py`
  - Local binary historical bridge for realtime-like latest bar and kline.
  - Should feed `BarEvent` / `PriceBar`, not L2/tick signals.

## Existing Tests

- `tests/test_v01_trading_domain.py` is broad and covers replay, proxy guard, sample snapshot writeback, true-money-flow readiness, Tencent/WeStock sample routes, and governance writebacks.
- Gap: no dedicated tests for realtime event schemas, dedup keys, staleness, capability gating, L2 aggregate semantics, callback debounce, or cross-source conflict handling.

## Current Weakest Point

The repository already has governance records and sample snapshot writeback, but it lacks a unified realtime event layer that preserves raw vendor semantics while supporting normalized downstream features. Without that layer, new TdxQuant/TQ-Local/WorkBuddy outputs will keep landing as ad hoc samples instead of governed market events.

