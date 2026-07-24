# Validation and Anti-overfit Plan

Every future experiment requires a registered research question, target, point-in-time data boundary, holdout policy, baseline, parameter budget, cost/slippage/capacity assumptions and promotion rule. Use chronological walk-forward splits, purge and embargo where overlapping labels justify them, a final lockbox, regime-stratified reporting and repeated seeded runs for stochastic methods.

Record the number of hypotheses and model variants. Apply appropriate multiple-testing diagnostics such as false-discovery control, probability of backtest overfitting or deflated Sharpe only when their assumptions are met; otherwise mark them `NOT_APPLICABLE` with rationale. Report failures, no-trade outcomes, low coverage and sensitivity. A favorable simulated result is insufficient without calibration and out-of-sample evidence.
