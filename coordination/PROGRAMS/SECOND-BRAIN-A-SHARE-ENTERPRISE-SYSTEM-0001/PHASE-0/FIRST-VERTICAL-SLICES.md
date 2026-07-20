# First Vertical Slices

## Candidate A - governed offline A-share replay (selected)

**Path:** a locally permitted historical/sample dataset -> raw manifest -> MarketDataRecord/PriceBar -> FeatureSet -> one existing research-only candidate -> replay with T+1/session/cost constraints -> BacktestResult/ValidationReport -> ForecastRecord/DecisionRecord/TradeJournal -> learning record.

**Why selected:** it reuses verified local contracts and tests, gives the enterprise architecture a concrete backbone, does not depend on real-time entitlement, cloud provisioning, QCLAW completion or a new service, and remains fully NO_TRADE.

**Not a claim:** it does not validate alpha, raw L2, order flow, agent identity or production readiness.

**Preconditions:** clean Codex branch/worktree; explicit sample license/lineage; data-manifest fixture; A-share market-rule source; deterministic seed/config; no writes to shared runtime stores.

**Acceptance:** same input/config produces same normalized rows and result manifest; `available_at` discipline; T+1 and session gates are tested; costs/slippage assumptions are explicit; OOS result is separated; strategy remains Experimental or NO_TRADE; journal and learning event have rollback pointers.

## Candidate B - QCLAW candidate-package to authority boundary

**Path:** approved dummy/candidate local packet -> schema validation -> quarantine/duplicate/conflict decision -> authority manifest proposal -> read-only retrieval fixture.

**Why not first:** WorkBuddy Issue #32 is still pending and no private authority repository may be created in Phase 0.

**Gate:** start only after #32 returns verified local entry/output/permission evidence and user approves the relevant storage scope.

## Candidate C - TEIF event/assessment contract compatibility

**Path:** fixture source artifact -> temporal event envelope -> available_at as-of query -> assessment with counterevidence -> abstention -> read-only Second Brain link.

**Why not first:** PR #8 remains Draft and its schemas have not yet undergone the requested local compatibility/time-leakage audit.

## Rejected anti-slices

- “Connect every source and model”: unbounded, cannot be tested.
- “Build MARL first”: upstream data/model validity absent.
- “Make the 8766 service authoritative”: confuses runtime observation with governance.
- “Enable paper/live execution”: outside Phase 0 and not required for research validation.
