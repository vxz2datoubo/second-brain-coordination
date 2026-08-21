# Program Control Tower Foundation

This directory contains the executable, fail-closed Program Control Tower declared by Issue #310.

## Authority boundary

The Control Tower is not a task router, domain truth store, trading engine, W3 authority or AI-film/world-model canonical source. It reconciles canonical routes, worker slots, work claims, overlap/WIP state, authorization witnesses and derived human projections.

Source precedence remains: current explicit user direction → current per-agent canonical route → project/program canonical authority → lane relationship registry → derived views → historical views.

## Core files

- `LANE-WORK-CLAIMS.yaml`: current work surfaces.
- `RELEASE-GATE.yaml`: release governance.
- `control_tower.py`: reconciliation, WIP/staleness and O0-O4 classification.
- `worker_slots.py`: GPT Engineering Worker slot validation.
- `lane_claims.py`: route/claim binding and closed/proposal isolation.
- `path_action_constraints.py`: exact-path action semantics plus optional transition-lineage enforcement.
- `authorization_witness.py`: freshness binding across route, worker, claim and release policy.
- `PROGRAM-CONTROL-TOWER.md`: derived human projection only.

## Exact-path action constraints

Ordinary `write_paths` remain collision/write surfaces. A narrower authority must be repeated identically by Worker, Work Claim and Route:

```yaml
path_action_constraints:
  - path: path/to/exact/file
    allowed_actions: ["DELETE"]
    transition_baseline_sha: 0123456789abcdef0123456789abcdef01234567
    required_final_state: "ABSENT"
```

The Route mirrors the entry under `write_scope.exact_action_constraints`. The validator requires exact agreement on execution identity, write surface, actions, baseline and final state. Wildcard constrained paths and broader write patterns covering a constrained exact path fail closed.

PR actions come from `git diff --name-status -M`: CREATE/MODIFY/DELETE are explicit; rename/copy/unknown actions fail closed unless separately governed. Transition mode additionally requires the baseline commit to exist and remain an ancestor, the baseline path to exist, the required final state to hold, and a baseline-present→final-ABSENT cleanup to produce exactly one net DELETE. Missing/stale baselines yield structured failure rather than exception or fallback authority.

## Worker, claim and witness rules

`GPT_ENGINEERING_WORKER` is one agent ontology with bounded worker-slot leases. Active slots exact-bind model/task/epoch/Issue/PR/branch and their work surface. Duplicate/colliding/over-capacity/impersonating/self-reviewing or malformed leases fail closed. Every active/reserved slot must be owned by exactly one matching Work Claim.

`ACTIVE_IMPLEMENTATION` requires an executable route and explicit work surface. `HELD_PROPOSAL_ONLY` is isolated proposal work only. `CLOSED_NO_ACTIVE_IMPLEMENTATION` carries no lease. Reopening or changing release level is a new authorization event. No Work Claim means no durable runtime write.

Authorization witnesses bind raw worker authority, route, claim, lane/release policy, WIP and overlap state; material changes invalidate old witness material.

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

Passing CI never starts work or grants a higher release level. This layer performs no trading/account action, private-data publication, production deployment or automatic task release.
