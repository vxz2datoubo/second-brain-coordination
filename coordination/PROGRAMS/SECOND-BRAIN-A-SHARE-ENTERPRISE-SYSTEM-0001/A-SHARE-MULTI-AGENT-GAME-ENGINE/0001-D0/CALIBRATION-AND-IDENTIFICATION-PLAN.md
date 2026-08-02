# Calibration and Identification Plan

## Identification boundary

An observed trace can be compatible with several participant hypotheses. This engine distinguishes: (a) descriptive association, (b) a simulated feasible or best-response candidate, and (c) causal attribution. Only (a) can be measured directly when a permitted source supports it; (b) is model output; (c) remains UNKNOWN unless an independently identified design supports it. None is evidence of legal identity.

## Preregistration requirements

Before any empirical study, freeze: rule and security-status versions; source manifests and licenses; `available_at` cutoff; target variable and unit; hypothesis family and priors; action feasibility; cost/slippage/capacity model; baseline families; temporal split; parameter/variant budget; scoring rule; abstention policy; and rejection/promotion thresholds. A changed item creates a new experiment ID rather than retroactively editing results.

## Temporal design

| Layer | Purpose | Required control |
| --- | --- | --- |
| Development window | Build deterministic transforms and baselines. | No peeking into validation/lockbox. |
| Validation window | Select among registered variants. | Chronological; purge/embargo only if overlapping labels justify it. |
| Lockbox | One final estimate of generalization. | No tuning after access without invalidating the run. |
| Walk-forward folds | Regime and time stability. | Fixed fold calendar, point-in-time availability and cost assumptions. |

Purge/embargo are `NOT_APPLICABLE` until a label horizon and overlap structure are formally defined; applying them ritualistically is not a control.

## Calibration and coverage

For numeric probabilities, record Brier score, log loss, reliability bins, sharpness and sample count. For set-valued or abstaining outputs, record coverage, abstention rate, conditional error after abstention, and UNKNOWN rate. A lower error obtained by hiding hard cases is a failure unless coverage is reported against a predeclared minimum.

## Competing explanations and failure tests

Every mechanism comparison includes: placebo windows, negative controls, shuffled or alternative labels where valid, alternative priors, regime strata, sensitivity to costs/capacity, and a no-signal baseline. Report failures, low coverage, instability and non-identification. A result fails promotion if it depends on future availability, unversioned rules/status, a single regime, unregistered variant expansion, or a confidence claim unsupported by calibration.

## Promotion rule

Only a separate GPT-routed phase can promote a *research capability*. No calibration result promotes identity attribution, profitability, production execution or a candidate source claim. All negative experiments remain in the evidence ledger.
