# Enterprise Data and Event Flow

## Canonical flow

```text
source artifact + entitlement + source capability
  -> RawMarketPayload / RawObservation (append-only)
  -> lineage, temporal and DataQualityEvent
  -> normalized MarketDataRecord / BarEvent / event envelope
  -> versioned FeatureSet and indicator/theory definitions
  -> hypothesis/strategy/agent scenario candidates
  -> replay + cost + A-share rule + OOS validation
  -> ValidationReport and RiskCheckResult
  -> ForecastRecord / DecisionRecord / TradeJournal (research-only)
  -> KnowledgeAtom / EvidenceItem / SelfEvolutionLog / EngineeringLearning review
```

## Time rule

Every temporal object carries, when applicable: event_time, vendor/source time, observed_at, receive_time, entered_system_at, available_at, local sequence, source sequence and timezone. Local receive time must never be relabelled as exchange time. Historical consumers must enforce `available_at <= as_of`.

## Knowledge flow

```text
user/local source -> QCLAW offline candidate packet -> quarantine/review -> approved private-Git authority
 -> rebuildable indexes/projection -> read-only context bundle -> agents/research consumers
```

QCLAW is an offline digester, not a runtime dependency. Candidate packets do not overwrite established knowledge. Conflicts become explicit relations and review tasks.

## Failure flow

Adapter error, entitlement ambiguity, missing field, stale feed, schema drift, replay leakage, negative OOS result or risk breach creates a quality/risk/validation event. The consumer receives a capability-constrained abstention; the event feeds SelfEvolutionLog and the engineering-learning loop. No automatic order path exists.
