# Opponent Modeling Plan

Status: `Future Roadmap`. Opponent modeling begins as a comparison of latent policy hypotheses, never a classifier of real market participants.

## Model progression and gates

| Level | Permitted object | Required evidence | Prohibited conclusion |
| --- | --- | --- | --- |
| D1 | Two synthetic fixed policies and explicit alternatives. | Fixture/invariant pass only. | Market realism or participant identity. |
| D3 | Calibrated likelihood comparison against approved point-in-time replay. | Admission, temporal split, baseline and calibration report. | Causal attribution or tradable edge. |
| D4 | Registered Bayesian posterior or bounded Level-k candidate. | D3 promotion, priors, sensitivity and abstention evidence. | Private inventory/information inference. |
| D5 | Synthetic self-play stress test. | Seed/compute budget and independent review. | Market prediction. |

## Posterior discipline

`HiddenTypePosterior` stores candidate types, prior source, likelihood inputs, correlated-evidence handling, counterevidence, normalization method, calibration status and abstention. A posterior must become `UNKNOWN` when its required observation capability or rule/status context is absent. Equal likelihood under multiple hypotheses is a result, not a failure to be hidden.

## Evaluation

Compare against feasibility-only and base-rate baselines. Report calibration, coverage, abstention, regime sensitivity, prior sensitivity, counterfactual performance and failure cases. A numerical posterior is `candidate_only` until independently calibrated. No result feeds an order, target position or market-fact record.
