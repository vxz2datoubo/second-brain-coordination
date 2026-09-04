# R579 WorkBuddy Multi-slot Overlap Reconciliation

## Fresh baseline

- canonical main observed at branch creation: `b373fbf66c4b9be5c96cd75ed4951b866c1e5d05`
- R579 Issue: #579
- R579 Draft PR: #580
- independent review anchor: #581
- WorkBuddy current legacy projection: `coordination/ACTIVE-WORKBUDDY-TASK.yaml`
- current WorkBuddy task: `WORKBUDDY-R175-ORDERED-BATCH`, route epoch `175`

## Active Control Tower work checked

### R6 lifecycle foundation

Issue #565 / PR #568 current exact head:

`8ecdf4ba6909873096b6360055c7632c3b892fc0`

R6 changed files are exactly:

1. `coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R6.yaml`
2. `coordination/CONTROL-TOWER/worker_lifecycle.py`
3. `coordination/CONTROL-TOWER/tests/test_worker_lifecycle.py`

R579 does not modify those files.

### Post-R6 R7 planning

Issue #572 is still pre-activation planning. Its future atomic migration surface is primarily:

- `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`
- `coordination/ACTIVE-PROGRAM-LANES.yaml`
- optional task-local migration receipt/tests

R579 intentionally does not modify either GPT projection file in the current implementation slice.

## R579 additive implementation surface

Current intended/implemented surface:

- `coordination/ACTIVE-WORKBUDDY-TASKS.yaml` new plural WorkBuddy registry
- `coordination/CONTROL-TOWER/workbuddy_slots.py` new WorkBuddy slot validator/collision resolver
- `coordination/CONTROL-TOWER/run_workbuddy_slots.py` validation entrypoint
- `coordination/CONTROL-TOWER/tests/test_workbuddy_slots.py` focused adversarial tests
- `coordination/WORKBUDDY-TASK-ROUTER.md` migrate routing semantics to plural registry with singular compatibility projection
- `.github/workflows/workbuddy-multislot.yml` exact-head CI
- task-local R579 evidence files only

The existing `coordination/ACTIVE-WORKBUDDY-TASK.yaml` is not modified in this slice. It remains the R175 compatibility projection.

## R175 preservation check

The new plural registry seeds one primary slot from the current R175 task without changing:

- task id
- route epoch
- active Issue
- implementation branch
- READY/execution state
- Work Claim
- Task Lease
- Executor Reservation
- canonical route
- authorized write paths
- completion signal

R175 continues to forbid credential, real-data, deployment, trade, review and merge authority.

## Collision model

R579 adds fail-closed checks for:

- write/write and write/read path overlap, including `/**` scope normalization;
- mutable interface/domain authority overlap;
- authority-claim overlap;
- exclusive local-resource overlap;
- mutable runtime/service/config overlap;
- credential-surface overlap;
- unapproved real-data surface sharing;
- duplicate task occupying multiple active slots;
- registry capacity overflow;
- route/claim/lease/reservation identity drift;
- legacy singular projection disagreement;
- any attempt for the WorkBuddy registry itself to grant order/trade authority.

## Immediate intended parallel case

The required acceptance example is:

- Slot A: existing interactive-film R175 task
- Slot B: future A-share Issue #553 local TdxQuant capability witness

The pair is eligible only when Slot B has its own route/claim/lease/reservation and a fresh resource collision scan proves disjoint mutable surfaces. Merely adding the registry does not release Slot B.

## Overlap disposition

`R6_FILE_OVERLAP = O0`

`R7_CURRENT_ACTIVE_WRITER_OVERLAP = NONE_OBSERVED` because #572 remains planning-only and no R7 implementation branch/write authority is active at this reconciliation point.

`R579_SHARED_GOVERNANCE_SEMANTIC_DEPENDENCY = YES` because all slices share the broader Control Tower architecture, but R579 uses a separate additive WorkBuddy seam and does not mutate the current R6 lifecycle resolver or GPT lifecycle projections.

## Gate

Substantive R579 implementation may proceed on its isolated Draft PR, but canonicalization still requires:

1. exact-head CI;
2. independent exact-head review through #581;
3. confirmation that any later R6/R7 head movement has not introduced a new file/authority collision;
4. no self-review and no self-merge.
