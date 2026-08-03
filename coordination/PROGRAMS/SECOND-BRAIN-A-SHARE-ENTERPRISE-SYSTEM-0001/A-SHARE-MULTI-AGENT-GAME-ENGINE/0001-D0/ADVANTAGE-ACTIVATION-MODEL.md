# Dynamic Advantage Activation Model

An advantage is a conditional candidate mechanism, not a stable label or proof of a participant's presence. `ActiveAdvantages` and `ExposedWeaknesses` are generated only when their preconditions, evidence scope and counterevidence are explicit.

## Record contract

Each activation record contains: family/subtype hypothesis; market-state and information-set references; activation preconditions; observable proxies; confounders; capability limits; alternative hypotheses; expected effect horizon/unit or `UNKNOWN`; deactivation triggers; weakness amplification condition; evidence and counterevidence; confidence/calibration status; and forbidden downstream use.

## Dynamic rules

* Unknown rule/status, unavailable capability or contradictory evidence produces `inactive_or_unknown`, not a favorable activation.
* A proxy is not a private information advantage. Aggregate L2 fields remain aggregate observations.
* The same observation can activate different candidate mechanisms for different families; the output retains all supported alternatives.
* Every activation must specify a counterfactual test or `NOT_TESTABLE_WITH_CURRENT_CAPABILITY`.

This model has no direct signal, sizing or order authority.
