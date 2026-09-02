# First Three P0 Vertical Slices

## Decision

The Gap Compiler is D1 meta-infrastructure and does not consume a child-slice slot. The first three child slices are:

1. `DS-01 DECISION-FRAMING-INFLUENCE-DIAGRAM-SKILL-0012A`
2. `DS-02 BAYESIAN-BELIEF-UPDATE-FORECAST-FUSION-SKILL-0012B`
3. `DS-10 RESEARCH-MULTIPLE-TESTING-OVERFITTING-AUDIT-SKILL-0012J`

## Why This Order

- DS-01 prevents a precise answer to the wrong decision problem and freezes goals, alternatives, constraints, observability and causal boundaries.
- DS-02 prevents uncalibrated scores, correlated sources and fixed-weight votes from masquerading as probabilities.
- DS-10 prevents repeated strategy search, selective reporting and backtest overfitting from promoting false discoveries.
- Together they establish framing, belief integrity and research truth before allocation, execution or adaptive experimentation.

## Minimum Contracts

### DS-01 `DecisionFrame`

Inputs: task context, decision horizon, alternatives, constraints, evidence references, `RuleSnapshotRef` and observability order.

Outputs: objectives, admissible actions, uncertainty nodes, information nodes, causal/correlation labels, decision sequence, abstention conditions and unresolved assumptions.

Non-goals: world-model replacement, user utility selection, risk approval or order creation.

### DS-02 Shared `ProbabilityEstimate`

Inputs: prior/base rate, evidence likelihood claims, source lineage, correlation group, data availability time and calibration history.

Outputs: the single canonical `ProbabilityEstimate` with posterior/distribution, unknown mass, contribution ledger, excluded duplicate evidence, dependence clusters, Brier/log-loss calibration state, abstention and invalidation conditions. W10 stores only the estimate reference and ex-ante hash; W11 is a read-only consumer.

Non-goals: actor identity certainty, fixed-weight sigmoid as probability, a second PEOS/personal probability object, portfolio sizing or trade recommendation.

### DS-10 `ResearchAuditReport`

Inputs: immutable experiment family ledger, tried variants including failures, train/OOS/walk-forward results, selection process and cost assumptions.

Outputs: multiplicity method and applicability, Romano-Wolf/SPA/PBO/DSR or justified alternatives, leakage findings, selection-bias assessment, promotion block and next evidence.

Non-goals: replacing W7 hard validation, guaranteeing market validity or authorizing production.

## Deferred

- DS-03 and DS-04 follow these three because information value and robust choice depend on a valid frame and belief model.
- Wyckoff becomes the first domain hypothesis slice only after DS-02/DS-10 and raw-data capability gates. Spring/Test/SOS/Effort-Result/LPS must be one evidence-sharing hypothesis graph, not independent votes.
