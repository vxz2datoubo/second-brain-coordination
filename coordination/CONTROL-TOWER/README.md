# Program Control Tower Foundation

This directory contains the executable, fail-closed Program Control Tower declared by Issue #310.

## Authority boundary

The Control Tower is not a task router, domain truth store, trading engine, W3 authority or AI-film/world-model canonical source. It reconciles canonical routes, worker slots, work claims, overlap/WIP state, authorization witnesses and derived human projections.

Source precedence remains: current explicit user direction → current per-agent canonical route → project/program canonical authority → lane relationship registry → derived views → historical views.

## Core files

- `LANE-WORK-CLAIMS.yaml`: machine-readable current work surfaces.
- `RELEASE-GATE.yaml`: release-level governance.
- `control_tower.py`: reconciliation, WIP/staleness and O0-O4 classification.
- `worker_slots.py`: GPT Engineering Worker multi-slot authority validation.
- `lane_claims.py`: exact route/claim binding and closed/proposal isolation.
- `path_action_constraints.py`: exact-path action semantics and optional governed transition-lineage enforcement.
- `authorization_witness.py`: freshness binding for route, worker, claim and release policy.
- `PROGRAM-CONTROL-TOWER.md`: derived human projection, never execution authority.

## GPT Engineering Worker slots

`GPT_ENGINEERING_WORKER` is one agent ontology with multiple bounded `worker_slot_id` leases. Window labels such as 编程1/编程2 are provenance, not separate agent species. Active slots must exact-bind model/task/epoch/Issue/PR/branch, status, execution flag, paths, interfaces, domains, authority claims, provenance and reviewer separation. Duplicate, colliding, over-capacity, impersonating, self-reviewing or structurally malformed leases fail closed.

## Exact-path action constraints

`write_paths` continue to describe mutable surfaces for collision/WIP purposes. When one path requires narrower semantics than generic write, Worker, Work Claim and Route must declare the same exact contract:

```yaml
path_action_constraints:
  - path: path/to/exact/file
    allowed_actions: ["DELETE"]
    transition_baseline_sha: 0123456789abcdef0123456789abcdef01234567
    required_final_state: "ABSENT"
```

The Route mirrors this under `write_scope.exact_action_constraints`. The validator requires all three sources to agree on execution identity, write surface, allowed actions, transition baseline and final state. Constrained paths cannot be wildcards and cannot sit beneath a broader write pattern that bypasses their action restriction.

For PR checks, `git diff --name-status -M` is mapped to `CREATE`, `MODIFY` and `DELETE`; rename/copy/unknown actions fail closed unless separately modeled. Transition mode additionally requires the baseline commit to exist and remain an ancestor, the baseline path to exist, and the required final state to hold. A baseline-present → final-ABSENT delete-only cleanup must be exactly one net `DELETE`. Missing/stale baselines return structured failure, never fallback authority or an unhandled exception.

## Work Claim and witness rules

`ACTIVE_IMPLEMENTATION` requires a matching executable route and explicit work surface. `HELD_PROPOSAL_ONLY` is isolated proposal work only. `CLOSED_NO_ACTIVE_IMPLEMENTATION` carries no execution lease. Reopening or changing levels is a new authorization event. No Work Claim means no durable runtime write.

The authorization witness binds route, raw worker authority, Work Claim, lane state, release/hold policy, WIP/resource policy, overlap declarations and Release Gate state. Material changes invalidate old witness material.

## Commands

```bash
python run_all_tests.py
python run_control_tower.py check --repo-root ../..
python run_lane_claims.py --repo-root ../..
python run_control_tower.py projection --repo-root ../..
python run_claim_projection.py check --repo-root ../..
python run_authorization_witness.py create --repo-root ../.. --lane LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP > witness.json
python run_authorization_witness.py verify --repo-root ../.. --lane LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP --witness-file witness.json
```

Passing CI never auto-starts work or grants a higher release level. The Control Tower layer performs no trading/account action, private-data publication, production deployment or automatic task release.
