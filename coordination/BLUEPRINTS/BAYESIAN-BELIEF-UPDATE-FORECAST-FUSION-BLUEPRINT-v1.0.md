# DS-02 Bayesian Belief Update & Forecast Fusion Blueprint v1.0

## Status

`RESEARCH_ONLY / NO_TRADE / CONTRACT_AND_EVAL_ONLY`

Source: Issue #522. Effective snapshot: `SECOND-BRAIN-DS02-CLEAN-SUCCESSOR-ISSUE522-SNAPSHOT-001` (`issuecomment-5473031902`). Canonical base: `1a514fe839b1c47a14d7fad4a96e8c9fd2365338`.

This is a BELIEVE-layer contract. It does not authorize runtime, backtest, capital allocation, brokerage, order creation, or live trading.

## First principles

The unit of truth is not model confidence. A belief is meaningful only when bound to a target, horizon, knowledge cutoff, point-in-time evidence, prior version, likelihood assumptions, dependence structure, rule regime and numerical policy.

`posterior ∝ likelihood × prior`

For compatible binary evidence, numerically stable composition may use:

`logit(posterior) = logit(prior) + Σ log(BF_i)`

This algebra is not permission to sum correlated evidence. Evidence enters only after dependence and provenance admission.

## Authority topology

```text
W2 market/replay ─┐
W5 event/evidence ├──> DS-02 BELIEVE ──> W7 risk
W13 participants ─┤                    ├─> W10 DecisionEpisode
DS-11 regime ─────┤                    ├─> W11 allocation
#457 epistemic ───┘                    └─> #62 Kelly/EV

DS-02 ─X─> BROKER
DS-02 ─X─> LIVE_ORDER
DS-02 ─X─> ACCOUNT_FUNDS
```

DS-02 derives a belief. It cannot rewrite upstream canonical evidence, mint a regime, choose an action, size capital, or execute.

## Forecast identity

A probability without target and horizon is invalid. Minimum identity:

- `target_id`
- `target_definition_version`
- `symbol_or_universe`
- `forecast_horizon`
- `as_of_time`
- `knowledge_cutoff`
- `market_rule_version`
- `market_rule_clause_state_version`

Clause-state version is distinct because an exchange may publish a rule while deferring activation of specified clauses.

## Prior discipline

Every prior is immutable by ID/version and records family/parameters, training window, universe, regime scope, evidence digest, effective-from time and invalidation conditions. A prior tuned after seeing the target outcome cannot be relabeled ex-ante.

## Evidence admission and dependence

Every evidence item carries temporal provenance and semantic provenance. Admission requires:

1. `available_at <= decision_time`;
2. explicit source and feature versions;
3. reposted claims share ancestry and cannot create independent Bayes factors;
4. agents sharing data/features/training lineage are not presumed independent;
5. raw LLM confidence is metadata unless separately calibrated;
6. revised data cannot replace historical PIT data without revision lineage.

## Reference update families

V1 contract admits three analytic sanity families:

- Beta-Binomial;
- Normal-Normal with known observation variance;
- log-odds/log-Bayes-factor composition.

More complex hierarchical logistic, MCMC, state-space and particle paths remain future candidates and must satisfy diagnostics before producing accepted beliefs.

### Retraction

The ledger is append-only. Retraction appends an invalidation and recomputes from surviving admitted evidence. Under additive log-Bayes-factor assumptions, removing a factor must reproduce a fresh recomputation without that factor.

## Posterior predictive, not scalar-only probability

Predictive output must preserve expected value, p05/p25/p50/p75/p95, probability positive, probability below configured loss threshold, distribution reference, and UNKNOWN mass. Downstream layers decide whether to act. DS-02 never emits BUY/SELL authority.

## Diagnostics and abstention

Future sampling paths surface R-hat, ESS, divergences, prior/posterior predictive checks, calibration status and PSIS-LOO/Pareto-k where applicable. `UNKNOWN`, `ABSTAIN`, and `REVALIDATION_REQUIRED` are first-class states.

## A-share structural breaks

SSE, SZSE and BSE changed core trading rules in 2026. Historical likelihoods are not silently pooled across incompatible rule eras. A mismatch in price limits, auctions, after-hours mechanisms, board/security type, or clause activation must be explicitly bridged or produce `REVALIDATION_REQUIRED`.

## Validation path

1. Analytic oracles.
2. Metamorphic properties and retraction.
3. Point-in-time/revision fixtures.
4. Simulation-based calibration.
5. Inference diagnostics.
6. Prior/posterior predictive checks.
7. Proper-score calibration.
8. Purged/embargoed A-share OOS increment versus simpler baselines.
9. DS-10 research-overfitting audit.
10. Shadow-only validation.

Mathematical correctness is necessary but never sufficient evidence of A-share alpha.

## Stop condition

This slice stops before runtime. Phase 2 requires independent acceptance, canonical merge, fresh main, a new pre-write Phase 2 snapshot, and a valid execution slot. Phase 3 A-share OOS remains separately governed. Live trading remains prohibited.
