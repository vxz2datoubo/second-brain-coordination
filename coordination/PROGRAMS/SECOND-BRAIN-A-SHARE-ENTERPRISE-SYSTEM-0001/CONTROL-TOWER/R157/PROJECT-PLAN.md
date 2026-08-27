# R157 — Idle Opportunity Ranking Calibration & Counterfactual Evaluation Harness

Issue: #473

Base canonical main: `2f85f6029de4acb0df428024ab259436023224f1`

## Why this exists

R154 introduced trusted mechanical rank features, R155 added bounded explicit user-value evidence, and R156 activated the canonical P3/P4 distinction. The remaining gap is not another input feature. It is confidence that the retained R151 ranking policy behaves coherently across boundary and counterfactual cases before anyone tunes its weights.

R157 therefore builds a wind-tunnel around the existing policy instead of changing the engine.

## Subject under test

The sole ranking subject is the retained R151 function:

`coordination/CONTROL-TOWER/idle_signal_scheduler.py#_rank_key`

At the R157 base it orders by:

1. canonical priority order (`P3` before `P4`);
2. descending composite score;
3. descending capped age;
4. lexical `opportunity_id`.

R157 does **not** copy that formula into a second production ranker. The evaluator imports and observes `_rank_key` directly. Any future R151 change will therefore be measured by the same harness rather than silently leaving a stale duplicate formula behind.

## Evaluation families

The canonical scenario corpus exercises:

- trusted user-value monotonicity;
- materiality monotonicity;
- dependency-readiness-score monotonicity;
- estimated-cost monotonicity;
- age monotonicity before the retained 20-cycle cap;
- exact age-cap plateau behavior after cycle 20;
- P3 dominance over P4 even under deliberately extreme scalar-score contrast;
- deterministic lexical tie-breaking;
- permutation invariance of the selected minimum rank key;
- report digest repeatability.

Scenario expectations are mechanical. The corpus cannot supply an `expected=PASS` escape hatch, redirect the subject to a caller ranker, inject weights, or alter the ranking policy.

## Output

`RankingCalibrationReport/v1` is rebuildable diagnostic evidence containing:

- exact subject reference;
- scenario-corpus digest;
- per-scenario observed rank keys/winners;
- pass/fail totals;
- report digest;
- explicit all-false authority flags except `evaluation_only=true`.

A report does not become Signal truth, ranking authority, a Task, or a release decision.

## Authority boundary

R157 MUST NOT:

- modify R151 `_rank_key` or any scheduler/release code;
- tune or replace R154/R155/R156 weights/evidence;
- select or release an opportunity;
- create Issue/Route/Claim/worker slot from evaluation output;
- mutate S0C or owner-domain truth;
- grant execution/domain/W3/merge authority;
- touch trading, order, fund, account, credential, permission or deployment surfaces;
- use free text, sentiment, embeddings, model judgment, private context or inferred user preference as ranking evidence.

## Exact implementation scope

Six additive files only:

1. `.github/workflows/program-control-tower-r157-ranking-calibration.yml`
2. `coordination/CONTROL-TOWER/evals/r157_ranking_calibration.py`
3. `coordination/CONTROL-TOWER/tests/test_r157_ranking_calibration.py`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R157/PROJECT-PLAN.md`
5. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R157/RANKING-CALIBRATION-REPORT.schema.json`
6. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R157/RANKING-CALIBRATION-SCENARIOS.json`

No existing file modification is authorized in R157/v1.

## Validation plan

- Python 3.11 and 3.13;
- compile evaluator/tests;
- JSON syntax validation for schema and scenario corpus;
- R157 adversarial/counterfactual tests;
- retained R156/R155/R154/R153/R152/R151/R150/R149 regressions;
- full Control Tower suite;
- exact six-additive-file diff gate;
- AST/static evaluation-only boundary gate;
- `git diff --check` and unfinished-marker gate.

## Stop gate

Draft PR only until exact-head CI is green and an independent reviewer settles the exact `(pr, head)` ticket through Review Queue #453.

No self-review. No merge before governed ACCEPT.

Completion signal:

`R157_RANKING_CALIBRATION_COUNTERFACTUAL_HARNESS_READY_FOR_INDEPENDENT_REVIEW`
