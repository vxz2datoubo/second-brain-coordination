# Game Formulation

## Scope

The future engine is a research-only partially observable stochastic game. A participant family is a latent hypothesis, not an observed account class. The numerical layer must remain separate from narrative explanation and the second brain stores provenance, alternatives, uncertainty and failures.

## State and transition

At time `t`, `MarketState`, `AgentState`, `InventoryState` and `InformationSet` are versioned and bound to `RuleSnapshotRef`. The transition consumes only capabilities declared by governance. Unknown, late, stale, aggregate-only or non-point-in-time inputs reduce feasible actions and confidence rather than being silently filled.

## Candidate utility

`U(a)` is decomposed into expected mark-to-market outcome, fill probability, market impact, transaction and financing cost, inventory/rule risk, adverse selection, opponent response and evidence mismatch risk. Each component has a source, horizon, assumptions and failure condition. D0 specifies no coefficients and makes no payoff or performance claim.

## Required action classifications

1. `FeasibleActions`: legal, inventory-, time-, price-limit-, suspension- and capability-compatible candidate actions.
2. `RationalCandidateActions`: feasible actions that fit a hypothesis objective under stated beliefs.
3. `BestResponseCandidates`: rational actions conditioned on explicit opponent hypotheses.
4. `MostConsistentAction`: the hypothesis action best aligned with the present evidence bundle, never a fact.
5. `RobustAction`: an action hypothesis that remains non-dominated under declared counter-scenarios.
6. `InvalidOrBlockedActions`: actions excluded by rule, inventory, data, capacity or uncertainty gates.

Every classification must carry supporting and opposing evidence, posterior uncertainty, alternative explanations, rule snapshot, assumptions, confounders and invalidation conditions. No class can emit an order, position or performance assertion.
