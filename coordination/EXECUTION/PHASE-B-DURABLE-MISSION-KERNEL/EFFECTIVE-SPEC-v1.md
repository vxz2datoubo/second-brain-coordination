# R188 Phase B Durable Mission Kernel — Effective Spec (B0)

**task_id:** `WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL`
**route_epoch:** 188
**execution_mode:** `SYNTHETIC_AND_DISPOSABLE_FIXTURE_ONLY`
**model_profile:** `DEEP_ENGINEERING` (resolved fresh to Deepseek-V4-Pro)
**project:** `SECOND_BRAIN`
**repository:** `vxz2datoubo/second-brain-coordination`

## 1. Objective

Implement and verify a **Windows-local resumable Durable Mission Kernel** that
*extends* the existing Unified Execution Fabric rather than creating a second
control plane. It preserves long-horizon progress across bounded episodes,
context rollover and worker failure using durable transactional state,
checkpoints, explicit effect reconciliation and machine-verifiable provenance.

## 2. Target architecture

```
SECOND_BRAIN_CONTROL_PLANE -> DURABLE_MISSION_KERNEL -> WORKBUDDY HEADLESS/SDK EPISODES
        -> DETERMINISTIC VERIFIERS -> INDEPENDENT REVIEWER -> INDEPENDENT CANONICALIZER
```

The kernel is a **bounded executor slot**, NOT a new control plane. It reuses the
canonical executor-pool architecture and the typed numeric ledger (`reuse_not_replace`).

## 3. State machine (frozen by `tools/durable_mission_kernel/schemas.py`)

```
CREATED -> PLANNING -> READY -> EPISODE_RUNNING -> CHECKPOINTED -> VERIFYING
   -> REVIEW_READY -> REVIEWING -> CANONICALIZATION_READY -> CANONICALIZING -> COMPLETE
```

Wait/terminal states: `PAUSED_OWNER_GATE`, `PAUSED_DEPENDENCY`, `BLOCKED`,
`FAILED_CIRCUIT_BREAKER`, `CANCELLED`. Every transition is explicit and machine-validated
by a pure deterministic reducer (`reducers.reduce_state`).

## 4. Role contracts (independence)

`AUTHOR != REVIEWER != CANONICALIZER` (hard invariant, enforced by `protocols.py`).

- no self-review (`assert_no_self_review`);
- no self-merge (`assert_no_self_merge`);
- canonicalizer READY requires **actual** merge-capability evidence, not a read-only gate.

## 5. Exact write surfaces (frozen)

Authorized (WorkBuddy exclusive):
- `tools/durable_mission_kernel/**`
- `tests/durable_mission_kernel/**`
- `tests/test_unified_execution_durable_mission_kernel.py`
- `coordination/EXECUTION/PHASE-B-DURABLE-MISSION-KERNEL/**`
- `coordination/EXECUTION/WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL/**`

Protected (never mutated): `coordination/GOVERNANCE/**`,
`coordination/ACTIVE-WORKBUDDY-TASK.yaml`, `ACTIVE-TASK-INDEX-REGISTRY.json`,
`.github/workflows/unified-execution-fabric.yml`, all R175/R184 surfaces.

## 6. Module map

| B-item | Module | Responsibility |
|---|---|---|
| B0 | `schemas.py` | states, roles, result classes, event types, write surfaces |
| B1 | `canonical.py` | RFC8785/JCS canonical bytes + SHA-256 hash chain |
| B1 | `reducers.py` | pure deterministic state reducers |
| B1 | `verifier.py` | independent hash-chain verifier |
| B2 | `ledger.py` | single-controller SQLite ledger + checkpoint/replay + backup |
| B3 | `effects.py` | effect outbox + idempotency + budget envelope |
| B3 | `lease.py` | runtime lease + fencing + stale-worker replacement |
| B4 | `containment.py` | Windows Job Object hard containment + orphan reaper |
| B5 | `headless.py` | headless adapter + runtime/model attestation + rollover |
| B6 | `protocols.py` | reviewer/canonicalizer independence + no-self-merge |
| B7 | `endurance.py` | synthetic endurance canary + failure injection |

## 7. CI oracle

`tests/test_unified_execution_durable_mission_kernel.py` — discovered by the exact-head
CI (`python -m unittest discover -s tests -p 'test_unified_execution*.py'`). It aggregates
the kernel unit suite via `load_tests` and re-asserts the highest-value invariants
(golden hash vectors, chain integrity, reducer determinism, independence, write surfaces,
endurance canary).

## 8. Hard boundaries (frozen)

`NO_R184_OR_LOCAL_BRIDGE_ACTIVATION`, `NO_REAL_CAPTURE`, `NO_OPERATIONAL_W3_WRITE`,
`NO_PROGRAM_S2_START`, `NO_PRODUCTION_DEPLOYMENT_OR_BACKGROUND_SERVICE_ACTIVATION`,
`NO_TRADING_FUNDS_ORDERS`, `NO_SECRET_TOKEN_COOKIE_PLAINTEXT_PERSISTENCE`,
`NO_DIRECT_MAIN_WRITE`, `NO_SELF_REVIEW`, `NO_SELF_MERGE`, `NO_R175_MUTATION`,
`NO_R184_MUTATION`, `NO_FORCE_PUSH_REBASE_RESET_AMEND_HISTORY_REWRITE`,
`NO_BROAD_COORDINATION_OR_UNRELATED_WILDCARD_AUTHORITY`,
`NO_SILENT_DOWNGRADE_FROM_JOB_OBJECT_HARD_CONTAINMENT_TO_BARE_PROCESS_EXECUTION`.
