# Enterprise Target Architecture

- agent_id: CODEX
- status: PROPOSED_FROM_PHASE0
- boundary: research_only / NO_TRADE

## Architectural thesis

The system is a governed research platform, not a single service and not an automated trading engine. Its control loop is:

```text
raw facts and source artifacts
  -> temporal/provenance/quality envelopes
  -> normalized market, event, knowledge and experiment records
  -> features, hypotheses, scenarios and evidence-aware assessments
  -> replay, validation, risk and abstention gates
  -> human decision support only
  -> journals, failures and engineering learning
```

The Second Brain supplies authority, evidence, memory, conflict handling and retrieval. The A-share platform supplies market rules, data/replay, research and validation. The control plane supplies task ownership, approvals, run traces and audit. They share contracts, not hidden mutable state.

## Planes

1. **Authority plane**: protected L0 blueprints; future private Git knowledge and approved research records; explicit version and conflict history.
2. **Fact plane**: immutable/append-only raw market and event artifacts with source, entitlement, observed, received and available times.
3. **Research plane**: normalized data, features, indicator/theory/strategy definitions, experiments, replay, validation and risk records.
4. **Knowledge plane**: candidate packets, atoms, relations, structures, skills, retrieval indexes, unknowns and review tasks.
5. **Decision-support plane**: evidence bundles, scenarios, forecasts, abstentions, DecisionRecord and TradeJournal. It has no broker execution authority.
6. **Operations plane**: adapters, capability negotiation, health, audit, rollout, task routing and engineering-learning feedback.

## Mandatory separations

- raw fact vs normalized interpretation;
- source reliability vs evidence quality vs analytic confidence vs probability vs model calibration;
- event time vs observation time vs receive time vs available time;
- candidate knowledge vs approved authoritative knowledge;
- research-only recommendation vs real trading execution;
- runtime endpoint availability vs authority role;
- public coordination artifacts vs protected blueprint/private knowledge/raw licensed data.

## Integration rules

Every cross-context message carries stable ID, schema version, producer, run_id, trace_id, source/lineage references, time semantics, quality status, and a reversible state transition. Consumers must preserve vendor semantics and capability limits. A missing capability produces an abstention or degraded result; it never creates synthetic order flow, tick, or causal evidence.

## Maturity rule

A component moves from Interface/Mock/Experimental to governed research capability only after: machine-readable contract, traceable source, deterministic test, failure/rollback behavior, owner, source-of-record decision, and acceptance gate. Production or real-trade maturity is outside this program and requires separate user approval.
