# Counterfactual Engine Plan

Status: `Future Roadmap`. A counterfactual is a registered alternative transition under explicit synthetic or admitted assumptions; it is not a claim about what a real actor would have done.

## Required record

Every future counterfactual records a factual-state reference, intervention, unchanged variables, rule/status snapshot, information-set cutoff, alternative participant hypotheses, matching assumptions, output unit, uncertainty method, placebo/negative control, invalidation condition and forbidden downstream use.

## Minimal tests

* Change no causal input: result must be identical.
* Change an unavailable variable: run must abstain or fail closed.
* Replace an identity hypothesis with a competing hypothesis: both outputs must remain observable.
* Change a rule snapshot: feasibility must change only where the snapshot authorizes it.
* Use a placebo intervention: apparent effect is reported as a warning, not evidence.

Empirical causal claims require the D2-D3 admission and identification gates. D0 creates no counterfactual runtime.
