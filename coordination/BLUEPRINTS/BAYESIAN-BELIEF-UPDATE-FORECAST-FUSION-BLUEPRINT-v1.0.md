# Bayesian Belief Update & Forecast Fusion Blueprint v1.0

## Status

- Skill: `BAYESIAN-BELIEF-UPDATE-FORECAST-FUSION-SKILL-0012B`
- Parent: Issue #63
- Execution issue: #519
- Lifecycle: `BELIEVE`
- Priority: `P0`
- Boundary: `RESEARCH_ONLY / NO_TRADE`
- First slice: architecture / contract / evaluation only

## Architecture decision

DS-02 is the A-share system's **belief transformation layer**, not a second signal system and not a trading authority.

```text
W2 market/PIT ───────┐
W5 event/evidence ───┤
W13 participant flow ┤
quant/technical skills├─> EvidencePacket
multi-agent forecasts ┤        │
fundamental/valuation ┘        v
                         DependenceMap
                              │
                              v
Prior Registry ────────> Bayesian Update
                              │
DS-11 regime ────────────────┤
                              v
                     Posterior Predictive
                              │
                              v
                     Calibration/Diagnostics
                              │
                              v
                         BeliefPacket/v1
                    ┌─────────┼─────────┐
                    v         v         v
                   W7        W10       W11/#62
                  Risk    Decision    Allocation
```

Hard forbidden path:

```text
BeliefPacket -> live order
```

## Why this is required

The system already has many evidence-producing skills. Without a common belief layer, five failure modes recur:

1. scores are mislabeled as probabilities;
2. shared evidence is double counted;
3. historical hit rates are treated as timeless likelihoods;
4. regime/rule changes silently invalidate relationships;
5. probability values lose target, time, version and provenance context.

DS-02 resolves those failures by standardizing the probability object and its lifecycle.

## Core epistemology

A Bayesian update is only valid relative to explicit assumptions. The engine must preserve:

- what was believed before evidence (`Prior`);
- what evidence arrived and when;
- how probable that evidence is under competing hypotheses (`Likelihood`);
- how evidence sources depend on one another;
- the updated belief (`Posterior`);
- what future observations the model predicts (`Posterior Predictive`);
- what remains unknown (`UNKNOWNMass`);
- which market/rule regime the relationship is valid under.

The system must never treat mathematical posterior computation as proof that the model is economically correct.

## Forecast target ontology

A probability is invalid unless its event is frozen.

Minimum target identity:

```text
target_id
target_definition_version
universe/security scope
forecast horizon
threshold
benchmark
as_of_time
knowledge_cutoff
market_rule_version
```

Initial A-share horizons are fixed for comparability:

`INTRADAY, 1D, 3D, 5D, 10D, 20D, 60D`.

Each horizon is a different target. A display phrase such as “up probability” is not a target contract.

## Prior design

Prior types:

1. empirical base rate;
2. hierarchical market/industry/theme/security prior;
3. weakly informative prior;
4. regime-conditioned prior;
5. provenance-bound expert prior.

Every prior is immutable/versioned. A later prior may supersede an older prior, but must not overwrite history.

Small-sample A-share signals should default toward hierarchical shrinkage instead of extreme local estimates.

## Evidence adapter boundary

Evidence-producing skills retain their authority. DS-02 receives references plus normalized evidence metadata.

Each evidence item must preserve:

- source and source grade;
- source family;
- independence group;
- feature definition/version;
- value/unit/polarity;
- likelihood model/version;
- valid time;
- point-in-time snapshot digest.

No reliable likelihood means `UNKNOWN/ABSTAIN`.

## Dependence graph

Naive Bayes multiplication is forbidden when independence is unsupported.

Dependence must account for:

- copied/derived media;
- multiple agents consuming the same feed;
- multiple indicators derived from the same raw observations;
- models sharing training data;
- models sharing architecture/features;
- common upstream event or market-state causes.

A source count is not an independence count.

## Regime and change point

DS-02 consumes DS-11 regime outputs rather than creating another regime authority.

Beliefs may be conditioned on market, volatility, liquidity and policy regimes. A material change point, market-rule change, feature-semantic change or calibration drift can mark a likelihood model `REVALIDATION_REQUIRED`.

Historical evidence from incompatible rule regimes must not be silently pooled.

## Posterior predictive first

The user-facing and downstream object should not collapse uncertainty to one number. At minimum preserve expected value, median, p05/p25/p50/p75/p95, probability positive, probability below a defined loss threshold and a predictive-distribution reference.

A high probability of a small gain can coexist with poor expected utility. DS-02 therefore never issues BUY/SELL authority.

## UNKNOWN mass

For novel policies, new securities, rule changes, black swans or unsupported mechanisms, forcing all mass into known scenarios creates false precision.

The contract therefore permits explicit `UNKNOWNMass` and abstention. Unknown is a valid epistemic result, not an error to hide.

## Numerical integrity

### Canonical numeric rules

- internal probability: float64;
- persisted probability: canonical precision policy, initial contract 12 decimal places;
- money: integer smallest currency unit where possible;
- shares: integer;
- prices: exchange-tick quantized;
- timestamps: timezone explicit;
- long probability products: log-space preferred;
- canonical serialization and digest required;
- UI rounding is never canonical truth.

### Semantic drift controls

Every numeric feature binds:

```text
feature_definition_id/version
label_definition_id/version
unit
polarity
adjustment policy/version
calendar/version
available_at semantics
rounding policy/version
```

Changing `close[t+5]/close[t]-1` into `close[t+5]/open[t+1]-1` requires a new label definition. It cannot silently keep the same ID.

## A-share adaptation

Every belief binds a versioned rule snapshot. Required rule families include exchange/board/security type, T+1 inventory implications, price-limit regimes, suspensions/resumptions, IPO/relisting/no-limit periods, ST/delisting states, declaration quantities, tick sizes and trading sessions.

The belief layer does not simulate execution itself, but downstream economic validation must include commissions, taxes/fees where applicable, slippage, impact, queueing, partial fills and liquidity.

## Validation architecture

### V0 Closed-form truth

Beta-Binomial and Normal-Normal fixtures prove the update implementation against analytic solutions.

### V1 Metamorphic

Test sequential/batch equivalence where mathematically valid, dependence dedupe, evidence retraction, serialization round-trip and semantic-version rejection.

### V2 Point-in-time

No feature can be consumed before `available_at`. Revised fundamentals and corrected events require revision lineage.

### V3 Simulation-based calibration

Generate synthetic worlds with known parameters and verify posterior recovery/rank behavior.

### V4 Inference diagnostics

Sampling paths record R-hat, bulk/tail ESS, divergences and convergence failures. “Sampler finished” is not acceptance.

### V5 Prior/posterior predictive checks

A converged sampler can still represent a bad model. Predictive checks attack model adequacy.

### V6 Forecast calibration

Track Brier score, log score, reliability, calibration slope/intercept and useful abstention. Discrimination metrics are secondary and cannot substitute calibration.

### V7 A-share OOS increment

Use purged walk-forward, embargo and final lockbox. Compare:

- B0 historical base rate;
- B1 simple logistic/frequentist baseline;
- B2 current rule/skill baseline;
- B3 current ensemble;
- B4 B3 + DS-02.

The question is whether B4 adds out-of-sample value, not whether Bayes' theorem is true.

### V8 Research overfitting

Route experiment families to DS-10 for multiple-testing controls and failed-trial preservation.

### V9 Shadow validation

No live orders. Measure calibration drift, abstention quality, regime decay, latency, reproducibility and economic increment.

## Cross-skill coordination

### W5

Owns event/claim/evidence truth. DS-02 consumes point-in-time evidence and expectation snapshots.

### W2

Owns market data and replay. DS-02 must not create its own historical market store.

### W13

Provides participant/capital-flow evidence with vendor semantics preserved. DS-02 cannot upgrade behavioral proxies into actor identity truth.

### Multi-agent game engine

Agent forecasts are forecast candidates. Their common inputs and model dependencies must be mapped before fusion.

### DS-10

Owns research multiple-testing/overfitting audit.

### DS-11

Owns regime/change/decay semantics.

### W7

Consumes uncertainty for risk controls and retains independent hard-risk authority.

### W10

Freezes the decision-time belief/evidence state in DecisionEpisode.

### W11 / Issue #62

Consumes calibrated posterior distributions for allocation research. Kelly cannot repair bad probability inputs.

### Issue #457

Owns user epistemic projection. DS-02 explanations adapt to the existing cognitive-band interface without creating a second user model.

## Governance

Maturity may not skip stages:

```text
CANDIDATE_SKILL_REGISTERED
-> RESEARCH_VALIDATED
-> CONTRACTED
-> IMPLEMENTED
-> A_SHARE_BACKTESTED
-> SHADOW_VALIDATED
-> VALIDATED_RESEARCH_CAPABILITY
```

First slice stops at architecture/contract/evaluation evidence and independent review. Runtime implementation and any trading path require later governed authorization.
