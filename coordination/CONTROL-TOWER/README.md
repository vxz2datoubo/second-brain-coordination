# Program Control Tower Foundation

This directory is the executable, fail-closed implementation of the cross-program Control Tower declared by Issue #310.

## Authority boundary

The Control Tower is **not** a task router, market authority, W3 knowledge store, W7 risk veto, W12 probability authority, trading engine, or AI-film canonical source. It reads canonical sources and produces reconciliation findings, collision classifications, work-claim validation, authorization witnesses, and derived human projections.

Source precedence remains:

1. current explicit user direction;
2. latest per-agent `ACTIVE-*.yaml` route on remote `main`;
3. project/program canonical authority;
4. `coordination/ACTIVE-PROGRAM-LANES.yaml` for lane relationships only;
5. derived human views;
6. historical aggregate views.

## Core files

- `LANE-WORK-CLAIMS.yaml`: the current machine-readable work surface for each Program Lane.
- `RELEASE-GATE.yaml`: separates Foundation Ready, proposal-only lane release and implementation release.
- `control_tower.py`: desired/observed reconciliation, stale-view/WIP checks and O0-O4 classifier.
- `worker_slots.py`: canonical `GPT_ENGINEERING_WORKER` multi-slot/lease registry validation (see below).
- `lane_claims.py`: exact route binding, proposal-only isolation and closed-lane no-lease validation.
- `authorization_witness.py`: fingerprints route + worker slots + work claim + hold/WIP/overlap/release policy so stale authorization cannot be silently reused.
- `PROGRAM-CONTROL-TOWER.md`: human projection only; its generated blocks are checked by CI.

## GPT Engineering Worker slots

`GPT_ENGINEERING_WORKER` is a first-class execution identity backed by `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`, which holds a `worker_slots` list. There is exactly one agent ontology (`GPT_ENGINEERING_WORKER`); 编程1/编程2 are `worker_slot_id` provenance labels, not separate agent species.

Each active slot must bind: `worker_slot_id`, `executor_role`, `model_id`, `task_id`, `route_epoch`, `issue`, `pr`, `branch`, `status`, `execution_allowed`, write/read paths, interfaces, domains, authority claims, resource class, provenance, reviewer role/separation, activation and closure state.

Fail-closed rules: duplicate slot id (silent overwrite / double booking) fails; a released/closed slot with an execution lease fails; two active slots colliding on the same mutable surface or authority (O3/O4) fail; active executable slots beyond `gpt_engineering_worker_active_slots_max` fail; a slot declaring a non-GPT agent identity (CODEX impersonation) fails; `reviewer_role == executor_role` (self-review) fails. A Work Claim bound to `GPT_ENGINEERING_WORKER` must also bind the exact `worker_slot_id`.

## Commands

From this directory:

```bash
python run_all_tests.py
python run_control_tower.py check --repo-root ../..
python run_lane_claims.py --repo-root ../..
python run_control_tower.py projection --repo-root ../..
python run_claim_projection.py check --repo-root ../..
python run_authorization_witness.py create --repo-root ../.. --lane LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP > witness.json
python run_authorization_witness.py verify --repo-root ../.. --lane LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP --witness-file witness.json
```

`check` fails closed when canonical route projection, user hold, WIP/resource boundaries, or registry structure is inconsistent. A user hold is not an implementation failure: it returns `HOLD_BY_USER` while the structural foundation can still be `PASS`.

## Work Claim rule

A Program Lane cannot gain durable runtime-write permission merely because a chat window, issue, dashboard, or model says it is working.

- `ACTIVE_IMPLEMENTATION` requires an exact current Agent route binding and explicit write paths/interfaces/authority surface.
- `HELD_PROPOSAL_ONLY` reserves no Agent route and may write only inside the lane's isolated proposal root.
- `CLOSED_NO_ACTIVE_IMPLEMENTATION` represents a completed lane stage with **no current execution lease**. It requires:
  - `execution_agent: null`;
  - no route binding;
  - no current read/write/interface/domain/authority work surface;
  - a durable `closure_receipt` preserving the completed evidence.
- Moving from proposal-only to implementation requires a new Work Claim and a fresh O0-O4 scan.
- Reopening a closed lane is also a **new authorization event**: create a new per-agent route, replace the closed claim with a bounded `ACTIVE_IMPLEMENTATION` claim, rescan O0-O4/WIP and create a fresh witness.
- No Work Claim means no durable runtime write.

`CLOSED_NO_ACTIVE_IMPLEMENTATION` exists so the Control Tower can represent normal completion truthfully. A completed implementation must not remain `ACTIVE_IMPLEMENTATION`, and a completed lane must not be disguised as `HELD_PROPOSAL_ONLY` merely to satisfy the validator.

## Durable authorization witness

A route check only protects task identity. The full authorization witness additionally binds:

- current route fingerprint;
- current Work Claim;
- current Program Lane state;
- user release/hold policy;
- WIP/resource policy;
- relevant cross-lane overlap declarations;
- current Release Gate state.

For a closed claim, the witness may still fingerprint the lane/claim/governance state for freshness, but `execution_agent` and route fingerprint are null and the witness grants **no execution authority**.

Create the witness after preflight. Verify it again immediately before a durable write/commit. Any material change invalidates the old witness and requires a fresh preflight.

## Separate release levels

- **Foundation Ready**: scanner/reconciler, O0-O4 classifier, Work Claims, WIP checks, authorization witness, deterministic projections and exact-head CI are validated.
- **Proposal-only lane release**: GPT may allow a lane to research/design and write only in its isolated proposal root. No shared runtime implementation is authorized.
- **Implementation lane release**: requires a separate executable Agent route plus a fresh `ACTIVE_IMPLEMENTATION` Work Claim and collision scan.
- **Closed lane**: carries no execution lease; reopening is never implied by passing CI or by another lane starting proposal work.

Passing CI never auto-starts a held lane and never auto-grants implementation permission.

## Projection rule

`coordination/PROGRAM-CONTROL-TOWER.md` contains two generated regions:

- `CONTROL_TOWER_AUTOGEN`: current routes, lane state and release hold;
- `CONTROL_TOWER_CLAIMS_AUTOGEN`: current work surfaces and pairwise claim collisions.

CI requires both regions to equal state derived from canonical sources. The remaining prose is explanatory only and cannot authorize work.

## Current closure example

After Second Brain P2.4B/Foundation Closure:

- R132 is retained in `ACTIVE-CODEX-TASK.yaml` as a non-executable `DONE` tombstone;
- Lane C uses `CLOSED_NO_ACTIVE_IMPLEMENTATION` and keeps a closure receipt;
- Lane A may be active at the strategic/program level while its current Work Claim is still `HELD_PROPOSAL_ONLY`, meaning architecture proposal work is allowed but implementation remains held;
- Lane B may remain user-held independently.

This distinction prevents three common false states:

1. completed work still looking executable;
2. a completed lane pretending to be a proposal lane;
3. proposal activity being mistaken for runtime implementation permission.

## Runtime dependency

The implementation uses PyYAML only as a test/runtime parser. CI pins `PyYAML==6.0.2`. No network access, private data, account access, trading action, scheduler activation, production deployment, or automatic agent activation is performed.
