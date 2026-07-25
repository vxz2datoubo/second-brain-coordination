# Validation and Anti-overfit Plan

## Experiment ledger

Each future experiment has an immutable ID, research question, input manifest hash, rule/status versions, target and horizon, code/version hash, seed list, candidate family, baseline family, parameter count, rejected variants, split specification, outputs, and owner. Failed, cancelled, abstaining and no-trade outcomes are first-class records.

## Baselines and regimes

Baseline families must include at least: a feasibility-only abstaining baseline, a simple prior/base-rate baseline, and a no-signal/shuffled comparator where valid. Results are stratified by predeclared market phase, volatility/liquidity proxy, limit/halt state, rule regime and data-capability level. A model cannot claim robustness by averaging away an undefined or unavailable regime.

## Variant and multiple-testing control

The plan records all attempted hypotheses, hyperparameter combinations, feature/label definitions and stopping decisions. False-discovery controls, PBO and deflated-Sharpe-like diagnostics may be used only when their mathematical assumptions and inputs are documented. Otherwise their status is `NOT_APPLICABLE`, not a decorative score. Exploratory runs are labeled exploratory and cannot use confirmatory thresholds.

## Rejection gates

Reject or freeze a candidate when any of the following holds: point-in-time breach; missing effective rule/status snapshot; unlicensed source; undefined cost/impact unit; lower coverage hidden by abstention; materially worse calibration than baseline; instability across registered folds/seeds; sensitivity only to one regime; variant-budget breach; or an unreplicated result. Promotion requires all gates plus independent review, never merely a positive simulated utility.

## Evidence required from future validation

Every report must state units, horizons, sample counts, missingness, abstention, costs, confidence intervals or uncertainty method where applicable, counterexamples, limitations and forbidden use. It must say explicitly that participant identity remains latent and that outputs are not order instructions.
