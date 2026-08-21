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

- `LANE-WORK-CLAIMS.yaml`: current machine-readable work surface for each Program Lane.
- `RELEASE-GATE.yaml`: separates foundation, proposal-only release and implementation release.
- `control_tower.py`: desired/observed reconciliation, stale-view/WIP checks and O0-O4 classification.
- `worker_slots.py`: canonical `GPT_ENGINEERING_WORKER` multi-slot/lease registry validation.
- `lane_claims.py`: exact route binding, proposal-only isolation and closed-lane no-lease validation.
- `path_action_constraints.py`: reconciles exact-path action restrictions across Worker / Work Claim / Route, validates Git diff actions, and optionally enforces a governed baseline/final-state transition.
- `authorization_witness.py`: binds route, worker authority, Work Claim and release policy so stale authorization cannot be silently reused.
- `PROGRAM-CONTROL-TOWER.md`: human projection only; generated blocks are checked by CI.

## GPT Engineering Worker slots

`GPT_ENGINEERING_WORKER` is a first-class execution identity backed by `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`. 编程1/编程2 are worker-slot provenance labels, not separate agent species.

Each active slot binds its worker id, agent/executor role, model, task/epoch/Issue/PR/branch, status, execution flag, paths, interfaces, domains, authority claims, resource class, provenance and reviewer separation. Duplicate/double-booked slots, released slots retaining a lease, O3/O4 mutable-surface collisions, capacity overflow, impersonation or self-review fail closed. Every ACTIVE/RESERVED GPT worker slot must be owned by exactly one matching Work Claim.

Worker registry identity remains schema-version strict. `execution_allowed` must be a real YAML boolean, malformed identity material is not inferred, and raw worker authority participates in authorization freshness.

## Exact-path action constraints

Ordinary `write_paths` describe collision/write surfaces. When an authority must be narrower than generic write, Worker, Work Claim and Route must repeat one exact action contract:

```yaml
path_action_constraints:
  - path: path/to/exact/file
    allowed_actions: ["DELETE"]
    transition_baseline_sha: 0123456789abcdef0123456789abcdef01234567
    required_final_state: "ABSENT"
```

The Route stores the same entry under `write_scope.exact_action_constraints`. The action validator requires all three sources to agree on execution identity, write surface, allowed actions, baseline and final state. Wildcard constrained paths are forbidden, and a broader write pattern may not cover a constrained exact path.

`git diff --name-status -M` is mapped to `CREATE`, `MODIFY` and `DELETE`; rename/copy/unknown operations fail closed unless a later reviewed contract explicitly models them. With transition mode enabled, the baseline commit must exist and remain an ancestor, the baseline path must exist, the required final state must hold, and a baseline-present→final-ABSENT delete-only cleanup must be exactly one net `DELETE`. Missing/stale baselines return structured failures rather than exceptions or fallback authority.

## Corrective maintenance/adoption authority

R144's `R144-GPT-MAINTENANCE-ADOPTION.yaml` is a separate exceptional corrective-maintenance provenance artifact, not a runtime slot and not a replacement for route/claim execution authority. It remains fail-closed and participates in witness freshness.

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

## Work Claim rule

- `ACTIVE_IMPLEMENTATION` requires an exact executable route and explicit work surface.
- `HELD_PROPOSAL_ONLY` grants only isolated proposal-root work.
- `CLOSED_NO_ACTIVE_IMPLEMENTATION` carries no execution lease and requires durable closure evidence.
- Reopening or moving from proposal to implementation is a new authorization event with fresh claim/collision/witness checks.
- No Work Claim means no durable runtime write.

## Durable authorization witness

The witness binds route, strict raw GPT worker authority, current Work Claim, Program Lane state, hold/release policy, WIP/resource policy, overlap declarations and Release Gate state. Material changes invalidate old witness material. Invalid worker authority fails closed.

## Separate release levels

Passing CI never starts work by itself. Foundation readiness, proposal-only release, active implementation release and closed-lane state remain separate governance levels.

## Projection rule

`PROGRAM-CONTROL-TOWER.md` contains generated Control Tower and Work Claim regions. CI requires them to match canonical sources; prose outside those regions cannot authorize work.

## Runtime dependency

PyYAML is used as a pinned parser in CI. This Control Tower layer performs no trading/account action, private-data publication, scheduler activation, production deployment or automatic task release.
