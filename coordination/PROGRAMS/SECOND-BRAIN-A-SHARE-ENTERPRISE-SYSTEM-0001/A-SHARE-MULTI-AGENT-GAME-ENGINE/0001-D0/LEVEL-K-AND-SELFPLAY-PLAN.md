# Level-k and Self-play Plan

Status: `Experimental / Future Roadmap`.

Level-k reasoning may be evaluated only after the synthetic rule-based baseline has deterministic state transitions, feasibility checks, abstention behavior and counterfactual tests. Self-play or MARL additionally requires a stable reward definition, computational budget, reproducibility seed policy, held-out regimes, adversarial tests, comparison with simple baselines and explicit analysis of reward hacking and distribution shift.

Promotion gates: synthetic contract pass -> independent rules review -> authorized point-in-time replay -> out-of-sample and calibration pass -> shadow-only research evaluation. At no gate can model behavior be treated as evidence of real-market intent or be connected to trading execution.
