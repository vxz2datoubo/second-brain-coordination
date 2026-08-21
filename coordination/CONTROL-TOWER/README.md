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
- `path_action_constraints.py`: reconciles exact-path action restrictions across Worker / Work Claim / Route, validates Git diff actions, and can enforce a governed baseline/final-state transition proof.
- `authorization_witness.py`: fingerprints route + strict worker authority material + work claim + hold/WIP/overlap/release policy so stale authorization cannot be silently reused.
- `PROGRAM-CONTROL-TOWER.md`: human projection only; its generated blocks are checked by CI.

## GPT Engineering Worker slots

`GPT_ENGINEERING_WORKER` is a first-class execution identity backed by `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`, which holds a `worker_slots` list. There is exactly one agent ontology (`GPT_ENGINEERING_WORKER`); 编程1/编程2 are `worker_slot_id` provenance labels, not separate agent species.

Each active slot must bind: `worker_slot_id`, `agent_type`, `executor_role`, `model_id`, `task_id`, `route_epoch`, `issue`, `pr`, `branch`, `status`, `execution_allowed`, write/read paths, interfaces, domains, authority claims, resource class, provenance, reviewer role/separation, activation and closure state.

Fail-closed rules: duplicate slot id (silent overwrite / double booking) fails; a released/closed slot with an execution lease fails; two active slots colliding on the same mutable surface or authority (O3/O4) fail; active executable slots beyond `gpt_engineering_worker_active_slots_max` fail; a slot declaring a non-GPT agent identity (CODEX impersonation) fails; `reviewer_role == executor_role` (self-review) fails. A Work Claim bound to `GPT_ENGINEERING_WORKER` must also bind the exact `worker_slot_id`, and every ACTIVE/RESERVED slot must be owned by exactly one matching Work Claim.

R144 R3 makes the execution-identity schema type-strict. Once the Program capacity policy enables GPT worker slots, removing the canonical registry is an ERROR and means no GPT worker execution. `execution_allowed` must be an actual YAML boolean: values such as `"false"`, `"0"`, numbers, containers or omitted authority material never become an executable lease by coercion. `agent_type` and `executor_role` are explicit authority fields and are not inferred/defaulted for a malformed slot. Raw `worker_slots` material, including invalid entries, participates in authorization freshness. If canonical worker authority is structurally invalid, `authorization_witness.py` refuses to mint or refresh a green witness instead of filtering the defect away.

## Exact-path action constraints

A path listed in `write_paths` normally means the active authority may mutate that surface subject to the rest of the Control Tower contract. When authority is intentionally narrower than generic write, the same exact constraint must be declared by the Worker slot, its Work Claim and the bound Route.

```yaml
path_action_constraints:
  - path: path/to/exact/file
    allowed_actions: ["DELETE"]
    transition_baseline_sha: 0123456789abcdef0123456789abcdef01234567
    required_final_state: "ABSENT"
```

The Route carries the same entry under `write_scope.exact_action_constraints`. The validator requires Worker / Work Claim / Route execution identity, write surface, allowed actions, baseline and final state to agree exactly. Constrained paths must be exact, and no broader write pattern may cover a constrained exact path.

For PR enforcement, `git diff --name-status -M` maps operations to `CREATE`, `MODIFY` or `DELETE`; rename/copy/unknown operations fail closed unless a future reviewed contract explicitly models them. With transition mode enabled, the baseline commit must exist and remain an ancestor, the baseline path must exist, the required final state must hold, and a baseline-present→final-ABSENT DELETE-only cleanup must resolve as exactly one net DELETE. Unavailable/stale baselines produce structured failures rather than exceptions or fallback authority.

## Corrective maintenance/adoption authority

R144 uses `R144-GPT-MAINTENANCE-ADOPTION.yaml` only for the exceptional bounded repair of the existing Draft PR after independent review. This artifact is **not** a `GPT_ENGINEERING_WORKER` runtime slot and is **not** a replacement for an executable Agent route or Work Claim. It records the user's explicit branch-maintenance instruction, the exact candidate input head/review that triggered repair, truthful executor provenance, and an allow-list of governance files that may be corrected.

The maintenance/adoption contract is mechanically fail-closed: `execution_allowed`, runtime write, trade, merge, acceptance, self-review and retroactive WorkBuddy authorization must all remain false; same-PR continuity, fresh exact-head CI and a separate independent review must remain true. Any mutation of this authority participates in the worker-registry authorization witness and therefore invalidates previously minted authorization material. It gives GPT architecture-owner corrective-maintenance provenance without pretending that WorkBuddy was authorized at R1 or that GPT acquired CODEX/runtime execution identity.

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

`check` fails closed when canonical route projection, user hold, WIP/resource boundaries, worker authority/registry structure, or maintenance/adoption guard is inconsistent. A user hold is not an implementation failure: it returns `HOLD_BY_USER` while the structural foundation can still be `PASS`.

## Work Claim rule

A Program Lane cannot gain durable runtime-write permission merely because a chat window, issue, dashboard, or model says it is working.

- `ACTIVE_IMPLEMENTATION` requires an exact current Agent route binding and explicit write paths/interfaces/authority surface.
- `HELD_PROPOSAL_ONLY` reserves no Agent route and may write only inside the lane's isolated proposal root.
- `CLOSED_NO_ACTIVE_IMPLEMENTATION` represents a completed lane stage with **no current execution lease**. It requires `execution_agent: null`, no route binding, no current work surface, and a durable closure receipt.
- Moving from proposal-only to implementation or reopening a closed lane requires a new authorization event, fresh Work Claim, O0-O4/WIP scan and witness.
- No Work Claim means no durable runtime write.

## Durable authorization witness

A route check only protects task identity. The full authorization witness additionally binds current route, strict raw GPT worker authority, current Work Claim, Program Lane state, release/hold policy, WIP/resource policy, overlap declarations and Release Gate state. Any material change invalidates the old witness and requires a fresh preflight. Invalid worker authority fails closed rather than returning a false-green fresh witness.

## Separate release levels

- **Foundation Ready**: scanner/reconciler, O0-O4 classifier, Work Claims, WIP checks, authorization witness, deterministic projections and exact-head CI are validated.
- **Proposal-only lane release**: GPT may allow isolated proposal-root work only.
- **Implementation lane release**: requires a separate executable Agent route plus a fresh `ACTIVE_IMPLEMENTATION` Work Claim and collision scan.
- **Closed lane**: carries no execution lease; reopening is never implied by passing CI.

Passing CI never auto-starts a held lane and never auto-grants implementation permission.

## Projection rule

`coordination/PROGRAM-CONTROL-TOWER.md` contains `CONTROL_TOWER_AUTOGEN` and `CONTROL_TOWER_CLAIMS_AUTOGEN` generated regions. CI requires both to match canonical sources. Remaining prose is explanatory only and cannot authorize work.

## Runtime dependency

The implementation uses PyYAML only as a test/runtime parser. CI pins `PyYAML==6.0.2`. No network access, private data, account access, trading action, scheduler activation, production deployment, or automatic agent activation is performed.
