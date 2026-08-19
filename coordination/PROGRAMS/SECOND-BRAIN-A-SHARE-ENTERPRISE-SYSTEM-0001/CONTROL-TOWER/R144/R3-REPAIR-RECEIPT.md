# R144 R3 Corrective Repair Receipt

This is an **implementation/modifier receipt**, not an independent acceptance review and not merge authority.

## Input gate

- Issue: `#406`
- Draft PR: `#408`
- branch: `codex/r144-control-tower-gpt-worker-first-class`
- R2 reviewed exact head: `4446dfcba09d8983aa8a17f855a4f2a813fd0615`
- R2 independent Review: `4973934171`
- R2 disposition: `CHANGES_REQUIRED_R3_AUTHORITY_AND_FAIL_CLOSED_SCHEMA_WITNESS / KEEP_DRAFT / NO_MERGE / R143_REMAINS_FROZEN`
- R3 modifier: `GPT_ARCHITECTURE_OWNER`
- authority source for this corrective maintenance: `coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION.yaml`

## Provenance truth retained

- R1 actual implementation executor: `WORKBUDDY`.
- R1 WorkBuddy was not canonically released for R144; R1 remains candidate implementation provenance only.
- R3 does not create retroactive WorkBuddy authorization.
- R3 does not impersonate CODEX.
- R3 bounded maintenance/adoption authority is not a `GPT_ENGINEERING_WORKER` runtime lease.
- Git author/committer metadata is repository provenance and is not execution authority.

## Blocking finding closure map

### B01 — governed modifier/adoption authority

Added machine-readable `R144-GPT-MAINTENANCE-ADOPTION.yaml`, mechanically validated by `worker_slots.py` and included in authorization witness material. It binds Issue/PR/branch/review/candidate-input-head and an explicit write allow-list. Runtime execution, trade, merge, acceptance, self-review and retroactive executor authority are all hard false; same-PR continuity, fresh exact-head CI and separate independent review are hard true.

### B02 — missing canonical GPT worker registry

Once GPT-worker capacity policy is enabled, absence of `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml` emits `WORKER_REGISTRY_MISSING` and the worker authority structural check fails. Missing canonical authority cannot degrade to an empty valid registry.

### B03 — strict authority schema

`execution_allowed` is accepted only as an actual YAML boolean and is never normalized through `bool(...)`. Malformed values such as `"false"` / `"0"` normalize safely non-executable and also emit an explicit schema ERROR. `agent_type` and `executor_role` are no longer defaulted to GPT identity when omitted. Path/domain/authority list shapes, provenance mapping and route scalar shapes are also checked fail-closed.

### B04 — malformed registry cannot retain a fresh witness

The authorization witness now binds strict raw registry material including raw `worker_slots`, bounded maintenance/adoption authority and worker structural status. Witness creation refuses invalid worker authority. Witness verification converts invalid current authority into `fresh=false / AUTHORIZATION_MATERIAL_INVALID` instead of returning a false-green match.

Regression coverage includes:

- required registry missing => FAIL;
- `execution_allowed: "false"` and `"0"` => FAIL / no executable slot;
- missing explicit agent identity => FAIL;
- create witness -> inject malformed slot scalar -> verify => `fresh=false`;
- create witness -> change execution_allowed to string => `fresh=false`;
- maintenance/adoption authority mutation => stale witness;
- maintenance/adoption cannot gain merge authority.

## Retained R2 protections

R2 reverse slot-to-claim cardinality, exact identity/surface/resource binding, RESERVED non-executable semantics, nested same-task guard, parallel-policy drift checks, collision/capacity checks, reviewer separation, deterministic projections and CODEX/QCLAW/WORKBUDDY compatibility remain in place.

## Gate

- PR #408 remains Draft/Open/Unmerged.
- `KEEP_DRAFT`.
- `NO_MERGE` / `NO_SELF_MERGE`.
- `NO_SELF_REVIEW`.
- R143 / PR #405 remains frozen.
- Final exact head and fresh merge-ref/CI must be reported in the R3 handoff after this receipt lands.
- Required next authority: **separate GPT independent exact-head review**.

Completion signal after final-head CI:

`R144_R3_GPT_CORRECTIVE_PATCH_READY_FOR_INDEPENDENT_REVIEW`
