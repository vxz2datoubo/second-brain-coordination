# R152 — Idle Signal Auto-Release Apply Transaction

Issue: #463

Base main at engineering start: `9ba2fa2346fcb813782a840a781de1ad7338663a`

## Purpose

R151 deliberately stops at `IdleSignalAutoReleaseAuthorization/v1` plus a logical side-effect plan. R152 makes the handoff to GitHub / Control Tower mechanically safe without creating a second task, route, claim, worker, Signal, R145, R149, R150 or R151 authority.

## Fresh architecture reconciliation

R152 reuses canonical R151 by replaying `evaluate_idle_signal_startup(...)` at apply time. A caller cannot attest current priority completeness or present a stale authorization as current truth.

A further canonical constraint was discovered during implementation: R144 requires every ACTIVE or RESERVED GPT worker slot to carry complete Issue / PR / branch / provenance binding, and Work Claim identity must exactly match the slot. Therefore R151's five logical side-effect capabilities cannot safely be serialized as five immediate canonical writes before a Draft implementation PR exists.

R152 preserves the R151 logical plan but materializes it in two governed stages:

1. **NON_EXECUTABLE_BOOTSTRAP**
   - fresh replay R151;
   - deterministic task / route / worker / branch identity from the R151 authorization digest;
   - create the implementation Issue;
   - create the deterministic branch and an **empty bootstrap commit only**;
   - create a Draft implementation PR;
   - no file mutation, no Route / Work Claim / worker-slot canonical write, no execution authority.

2. **ACTIVATION_GATE_CANDIDATE**
   - fresh replay R151 again against exact current main;
   - require exact bootstrap Issue / PR / branch / bootstrap-head evidence;
   - require original proposal surface == requested apply surface;
   - require target lane is presently closed and its canonical reopen rule permits the release class;
   - require no competing ACTIVE / RESERVED Work Claim or GPT worker slot;
   - construct route + Work Claim + worker-slot payloads with exact task / epoch / Issue / PR / branch / surface identity;
   - require one atomic control-plane commit in a **separate activation-gate PR**;
   - activation gate requires independent exact-head review and expected-head merge;
   - executable engineering becomes eligible only after that gate is canonical.

This does not weaken R144 to make automation easier.

## Post-apply verification

`IdleSignalAppliedState/v1` must prove the accepted activation-gate head, canonical merge, Issue / implementation PR / branch and exact Route / Claim / worker-slot payloads. The derived `IdleSignalApplyReceipt/v1` is evidence-only and grants no execution or merge authority.

## Hard locks

- `NO_SECOND_TASK_AUTHORITY`
- `NO_SECOND_ROUTE_AUTHORITY`
- `NO_SECOND_WORK_CLAIM_AUTHORITY`
- `NO_SECOND_WORKER_SLOT_AUTHORITY`
- `NO_SECOND_SIGNAL_STORE`
- `NO_SECOND_R145_R149_R150_R151`
- `NO_CALLER_PRIORITY_COMPLETENESS`
- `NO_STALE_R151_AUTHORIZATION`
- `NO_SURFACE_DOMAIN_INTERFACE_AUTHORITY_EXPANSION`
- `NO_PARTIAL_CONTROL_PLANE_APPLY`
- `NO_ACTIVE_SLOT_WITHOUT_PR_BINDING`
- `NO_INVALID_LANE_REOPEN`
- `NO_W3_WRITE`
- `NO_SIGNAL_TOWER_RUNTIME_WRITE`
- `NO_TRADE`
- `NO_ACCOUNT_ORDER_FUND`
- `NO_SECRET_PERMISSION_VISIBILITY_EXPANSION`
- `NO_PRODUCTION_DEPLOY`
- `NO_DESTRUCTIVE_HISTORY_REWRITE`
- `NO_SELF_REVIEW`
- `NO_SELF_MERGE`

## Implementation PR scope

This R152 implementation PR itself may modify only:

1. `coordination/CONTROL-TOWER/idle_signal_apply.py`
2. `coordination/CONTROL-TOWER/tests/test_idle_signal_apply.py`
3. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R152/PROJECT-PLAN.md`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R152/IDLE-SIGNAL-APPLY-CONTRACT.schema.json`
5. `.github/workflows/program-control-tower-r152-idle-signal-apply.yml`

It MUST NOT modify any `coordination/ACTIVE-*`, `coordination/ROUTES/**`, `LANE-WORK-CLAIMS.yaml`, W3, Signal Tower runtime, trading or production authority surface.

## Stop gate

Exact-head Python 3.11 + 3.13 CI, retained R151/R150/R149, full Control Tower suite, changed-path allowlist, authority-boundary checks and `git diff --check` must pass before a new `REVIEW_REQUEST/v1` is appended to #453.

No self-review. No merge before independent ACCEPT.

Completion signal:

`R152_IDLE_SIGNAL_AUTO_RELEASE_APPLY_TRANSACTION_READY_FOR_INDEPENDENT_REVIEW`
