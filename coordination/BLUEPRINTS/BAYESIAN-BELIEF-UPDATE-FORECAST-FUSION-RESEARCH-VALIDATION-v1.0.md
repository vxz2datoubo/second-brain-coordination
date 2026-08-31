# DS-02 Research Validation v1.0

## Evidence policy

Research evidence informs design constraints. It does **not** prove this system is calibrated, profitable, transferable to A-shares, or suitable for live trading. Each source in the machine registry records both supported and unsupported claims.

## Bayesian workflow evidence

### Prior and posterior predictive checks

Current PyMC documentation treats prior predictive checks as a way to inspect the implications of priors before conditioning on observed data, and posterior predictive checks as a way to compare data generated under posterior draws with observed structure.

**Engineering consequence:** sampler convergence is not model adequacy; predictive checks remain separate gates.

### MCMC diagnostics

Stan diagnostic guidance treats R-hat, effective sample size, divergences, tree-depth warnings and Monte Carlo error as evidence about computational reliability.

**Engineering consequence:** future sampling paths may abstain. A successful function return is not trustworthy inference by itself.

### PSIS-LOO

ArviZ documents PSIS-LOO as an estimate of expected pointwise predictive performance and exposes Pareto-k diagnostics.

**Engineering consequence:** model comparison may consume PSIS-LOO only with diagnostic provenance; it is never trading-action authority.

### Simulation-based calibration

SBC tests whether an inference implementation recovers calibrated posterior ranks in synthetic data drawn from the assumed generative model.

**Engineering consequence:** passing SBC tests inference under the simulator, not realism of the market model.

## Proper scoring and calibration

Proper scoring rules such as logarithmic score and Brier score provide principled evaluation of probabilistic forecasts. Evaluation must retain the complete forecast/outcome ledger, including failed trials and abstentions. Accuracy alone is insufficient.

## Dependence and forecast combination

Different labels do not imply independent information. Agents or models sharing data, feature engineering, training corpora or upstream evidence cannot be multiplied as independent measurements unless a validated dependence model permits it.

**Engineering consequence:** ancestry and `independence_group_id` are admission inputs. Unresolved dependence increases uncertainty rather than confidence.

## Regime/change evidence

Bayesian changepoint methods motivate explicit validity windows and structural-break handling, but DS-11 remains regime authority. DS-02 consumes regime/changepoint state and may return `REVALIDATION_REQUIRED`.

## 2026 A-share rule evidence

Fresh official exchange publications provide a real structural-break case:

- SSE published its 2026 trading rules on 2026-04-24, effective 2026-07-06, superseding the 2023 revision and separately treating deferred provisions.
- SZSE published its 2026 trading rules on 2026-04-24, effective 2026-07-06, superseding the 2023 revision.
- BSE published revised rules on 2026-04-24 with general effect from 2026-07-06 while explicitly deferring specified clauses to later notice.

**Engineering consequence:** `market_rule_version` alone is insufficient where clause activation can be deferred. Beliefs also bind a clause-state version.

These rule sources do **not** prove predictive alpha, likelihood transfer, execution performance, or economic value.

## Validation ladder

| Gate | Question | Minimum evidence | Fail-closed state |
| --- | --- | --- | --- |
| V0 | Is closed-form math correct? | Beta-Binomial + Normal-Normal oracles | INVALID_MODEL |
| V1 | Are metamorphic properties preserved? | sequential/batch where valid, retraction, serialization | INVALID_MODEL |
| V2 | Is evidence point-in-time? | timestamp/revision fixtures | PIT_VIOLATION |
| V3 | Is inference calibrated under assumed simulator? | SBC | INFERENCE_INVALID |
| V4 | Is numerical inference reliable? | R-hat/ESS/divergence/MC-error gates | ABSTAIN |
| V5 | Can the model generate material observed structure? | prior/posterior predictive checks | MODEL_MISFIT |
| V6 | Are forecasts calibrated OOS? | Brier/log score/reliability | UNCALIBRATED |
| V7 | Does DS-02 add A-share economic information? | purged walk-forward + embargo + lockbox + costs | NO_INCREMENT |
| V8 | Is discovery robust to multiplicity? | DS-10 audit | OVERFIT_RISK |
| V9 | Does shadow behavior remain stable? | drift/abstention/reproducibility ledger | REVALIDATION_REQUIRED |

## Explicit non-claims

This contract does not claim:

1. Bayesian methods dominate frequentist methods in A-share forecasting.
2. A posterior probability is automatically calibrated.
3. Calibration implies positive expected value.
4. Positive expected value implies a position should be taken.
5. MCMC convergence proves model adequacy.
6. PSIS-LOO proves future market performance.
7. Official exchange rules imply an edge.
8. Mathematically valid composition proves conditional independence.
9. Larger models beat simple base-rate or regularized-logistic baselines.
10. Anything in this slice authorizes runtime, capital, orders, or trades.

## Future A-share comparison baseline

Phase 3 must compare at least:

- B0 empirical base rate;
- B1 simple regularized logistic/frequentist baseline;
- B2 pre-DS-02 rule/skill baseline;
- B3 existing ensemble;
- B4 existing ensemble + DS-02.

Evaluation is horizon-specific and split by market/rule/regime eras. Claimed improvements must survive realistic costs and DS-10 multiple-testing controls.
