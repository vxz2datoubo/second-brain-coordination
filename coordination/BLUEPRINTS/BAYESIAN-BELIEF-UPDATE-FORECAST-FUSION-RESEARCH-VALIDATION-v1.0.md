# DS-02 Bayesian Belief Update & Forecast Fusion Research Validation v1.0

## Scope

This artifact records what external theory can justify, what it cannot justify, and what must still be validated in the A-share system.

Boundary: `RESEARCH_ONLY / NO_TRADE`.

## Evidence hierarchy

Preferred evidence order:

1. primary mathematical/statistical papers and books;
2. official project documentation for inference diagnostics/workflows;
3. exchange/regulator rules for A-share constraints;
4. peer-reviewed finance/econometrics literature;
5. institutional methods/case studies with reproducible assumptions;
6. secondary explainers only as navigation aids.

No external source becomes internal authority merely by citation.

## Research map

### Bayes / Bayesian decision theory

**Supported:** prior + likelihood define a posterior under an explicit probabilistic model; sequential learning can be represented coherently under model assumptions.

**Not supported:** that any chosen prior/likelihood is economically correct, or that Bayesian inference automatically produces profitable trading signals.

**Engineering consequence:** model assumptions, prior version and likelihood version are first-class fields.

**Validation:** analytic fixtures + simulation + OOS calibration.

### Proper scoring rules

Core families: Brier score and logarithmic score.

**Supported:** probabilistic forecasts should be evaluated as probabilities, not only by classification accuracy; proper scoring discourages strategic distortion of reported probabilities under their assumptions.

**Not supported:** a good score alone proves economic usefulness or causal validity.

**Engineering consequence:** calibration metrics are mandatory before downstream sizing.

### Prior predictive and posterior predictive checking

Modern Bayesian workflows represented by PyMC/Stan ecosystems emphasize checking what a model implies before and after conditioning on observations.

**Supported:** predictive checks can expose implausible priors and model-data mismatch.

**Not supported:** passing a predictive check proves the model is uniquely correct.

**Engineering consequence:** prior/posterior predictive status belongs in BeliefPacket diagnostics.

### MCMC diagnostics

Stan-style diagnostics include R-hat, effective sample size and divergent-transition analysis.

**Supported:** these diagnose important computational pathologies in sampling-based inference.

**Not supported:** computational convergence proves model adequacy or financial validity.

**Engineering consequence:** sampling paths fail closed on material diagnostic failure; analytic/approximate paths record their own diagnostics instead of fake MCMC fields.

### Simulation-Based Calibration

SBC tests inference algorithms by simulating parameters/data from the model and checking posterior rank behavior.

**Supported:** strong tool for detecting implementation/inference calibration defects when simulation and inference model assumptions match.

**Not supported:** proves real markets follow the simulated model.

**Engineering consequence:** V3 uses known synthetic worlds before A-share backtests.

### PSIS-LOO / Pareto-k

**Supported:** approximate leave-one-out diagnostics and Pareto-k can identify influential/problematic observations and approximation instability under their conditions.

**Not supported:** replaces final time-ordered out-of-sample validation in non-stationary markets.

**Engineering consequence:** use as model diagnostic/comparison evidence, never as the sole financial validation gate.

### Hierarchical Bayesian modeling

**Supported:** partial pooling can stabilize estimates across related groups and express uncertainty in sparse groups.

**Not supported:** market/industry/theme/security hierarchy is automatically exchangeable.

**A-share transfer risk:** industries, themes and policy-sensitive securities may have structural heterogeneity.

**Engineering consequence:** hierarchy/exchangeability assumptions must be versioned and attacked with leave-group/regime tests.

### State-space / Kalman filtering

**Supported:** latent dynamic states can be estimated recursively under explicit transition/observation models; Kalman filtering is exact for standard linear-Gaussian assumptions.

**Not supported:** financial state dynamics are generally linear-Gaussian.

**Engineering consequence:** Kalman is one model family, not the universal regime engine.

### Particle filtering

**Supported:** sequential Monte Carlo can represent nonlinear/non-Gaussian state-space inference.

**Not supported:** particle filters remove model risk or degeneracy problems.

**Engineering consequence:** only later implementation if simpler models fail materially; track particle degeneracy/ESS and computational cost.

### Hamilton-style regime switching

**Supported:** discrete latent regimes can model parameter changes and persistent state transitions.

**Not supported:** every statistical regime has a unique economic meaning or stable future transition matrix.

**Engineering consequence:** DS-02 consumes DS-11 regime posterior; economic labels remain hypotheses unless separately evidenced.

### Bayesian Online Changepoint Detection

Adams & MacKay's BOCPD framework tracks a posterior over run length and supports online structural-change detection under a specified predictive model/hazard.

**Supported:** explicit probabilistic detection of potential structural breaks.

**Not supported:** every detected break identifies its economic cause.

**Engineering consequence:** changepoint probability can trigger likelihood revalidation, not automatic trading direction.

### Forecast combination / stacking

**Supported:** multiple predictive models can be combined, and predictive performance can inform ensemble weights.

**Not supported:** combining many correlated models necessarily adds information.

**Engineering consequence:** DependenceMap precedes ForecastPool; model count is not evidence count.

### Black-Litterman

**Supported:** a downstream framework for combining equilibrium-like portfolio priors with investor views and confidence under explicit assumptions.

**Not supported:** an alpha generator or a substitute for probability calibration.

**Engineering consequence:** belongs downstream in belief-to-portfolio/DS-07, not inside DS-02 authority.

## A-share-specific research claims

### Point-in-time data

Historical research must preserve when information became available to the market, including revisions/corrections. `published_at`, `available_at` and `market_effective_at` are distinct when evidence supports the distinction.

### Rule regimes

Exchange and regulator rules are versioned facts. Historical likelihoods must bind the effective rule version. Material changes in price limits, sessions, ST rules, listing/relisting regimes or other market mechanics can invalidate pooled historical estimates.

### T+1

T+1 affects downstream payoff/execution feasibility and label design. A probability model must not assume an intraday stop-loss exit that the underlying inventory cannot legally execute.

### Price limits / suspension / queueing

Observed returns are censored/affected by market mechanics. Economic validation must distinguish predictive correctness from executable realization.

## Required source registry for implementation phase

Before claiming `RESEARCH_VALIDATED`, implementation evidence must pin fresh references/versions for:

- Bayesian workflow documentation from PyMC and/or Stan;
- Stan convergence/diagnostic guidance;
- ArviZ/PSIS-LOO diagnostics where used;
- SBC primary literature;
- Adams & MacKay BOCPD;
- Hamilton regime-switching primary literature;
- proper-scoring primary literature;
- hierarchical modeling references;
- state-space/Kalman and SMC references if implemented;
- current SSE, SZSE, BSE and CSRC rule sources relevant to tested instruments/periods.

Each source entry must record:

```text
source_id
source_type
source_version_or_date
claim_supported
claim_not_supported
assumptions
A-share transfer risk
implementation consequence
validation consequence
confidence/source grade
```

## Baseline and ablation matrix

A-share validation must compare:

| Baseline | Description | Purpose |
|---|---|---|
| B0 | historical base rate | prove model beats no-feature probability |
| B1 | simple logistic/frequentist baseline | test whether Bayesian complexity adds value |
| B2 | current rule/skill baseline | preserve current-system comparison |
| B3 | current ensemble | compare against existing fusion |
| B4 | B3 + DS-02 | measure DS-02 incremental value |

Ablations:

- remove dependence correction;
- remove regime conditioning;
- remove hierarchical shrinkage;
- remove UNKNOWN/abstention;
- replace posterior predictive with point estimate;
- use stale versus current rule version only as an adversarial negative control.

## Metrics

### Probability quality
- Brier score
- log score/log loss
- reliability/calibration curve
- calibration slope/intercept

### Discrimination
- ROC-AUC where meaningful
- PR-AUC for imbalanced targets

### Distribution quality
- predictive interval coverage
- CRPS where appropriate
- tail-threshold calibration

### Economic increment
- after-cost return of a separately governed decision policy
- drawdown
- expected shortfall/CVaR
- turnover
- implementation shortfall
- capacity/liquidity sensitivity

These economic metrics belong to downstream evaluation and cannot grant DS-02 order authority.

### Robustness
- regime stability
- prior sensitivity
- dependence sensitivity
- change-point response
- parameter drift
- rule-version sensitivity

### Abstention
- UNKNOWN rate
- useful abstention rate
- bad-confidence rate
- false precision rate

## Adversarial validation matrix

1. **Copied source attack**: 10 copies of one event must not create 10 independent updates.
2. **Shared-feed agent attack**: multi-agent consensus from one feed must remain dependence-aware.
3. **LLM confidence attack**: natural-language confidence cannot mint a calibrated probability.
4. **Sparse sample attack**: 4 successes in 5 observations must not create unjustified certainty.
5. **Rule change attack**: old likelihood under incompatible market rules must be rejected/revalidated.
6. **PIT revision attack**: revised financial data cannot appear before its historical availability.
7. **Target alias attack**: same display label with different mathematical definition must fail version identity.
8. **Numeric round-trip attack**: UI rounding cannot alter canonical posterior on reload.
9. **Evidence retraction attack**: denied/retracted evidence creates an auditable recomputation.
10. **Novel-event attack**: unsupported likelihood produces UNKNOWNMass/ABSTAIN.
11. **High-probability bad-payoff attack**: DS-02 emits belief only and cannot bypass downstream utility/risk.
12. **Regime-label attack**: statistical regime output cannot be asserted as a certain economic cause.

## Acceptance criteria for RESEARCH_VALIDATED

All must hold:

- source registry pinned and fresh;
- no major theory represented beyond what sources support;
- A-share transfer limitations explicit;
- all P0 subskills mapped to existing authorities;
- no duplicate runtime/authority introduced;
- validation ladder has executable test definitions;
- numeric integrity and PIT rules machine-readable;
- UNKNOWN/ABSTAIN preserved;
- exact-head independent review accepts the artifacts.

Only then may maturity advance from `CANDIDATE_SKILL_REGISTERED` to `RESEARCH_VALIDATED`.
