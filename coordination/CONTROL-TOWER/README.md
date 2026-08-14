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
- `RELEASE-GATE.yaml`: separates Foundation Ready from lane release.
- `control_tower.py`: desired/observed reconciliation, stale-view/WIP checks and O0-O4 classifier.
- `lane_claims.py`: exact route binding and proposal-only work-surface validation.
- `authorization_witness.py`: fingerprints route + work claim + hold/WIP/overlap/release policy so stale authorization cannot be silently reused.
- `PROGRAM-CONTROL-TOWER.md`: human projection only; its two generated blocks are checked by CI.

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
- Moving from proposal-only to implementation requires a new Work Claim and a fresh O0-O4 scan.
- No Work Claim means no durable runtime write.

This is how Lane A Harness and Lane B A-share can later work in parallel without being allowed to modify Lane C's changing runtime by accident.

## Durable authorization witness

A route check only protects task identity. The full authorization witness additionally binds:

- current route fingerprint;
- current Work Claim;
- current Program Lane state;
- user release/hold policy;
- WIP/resource policy;
- relevant cross-lane overlap declarations;
- current Release Gate state.

Create the witness after preflight. Verify it again immediately before a durable write/commit. Any material change invalidates the old witness and requires a fresh preflight.

## Two separate release levels

- **Foundation Ready**: scanner/reconciler, O0-O4 classifier, Work Claims, WIP checks, authorization witness, deterministic projections and exact-head CI are validated.
- **Proposal-only lane release**: GPT may allow Lane A/B to research/design and write only in their isolated proposal roots. No shared runtime implementation is authorized.
- **Implementation lane release**: requires a separate executable Agent route plus a fresh implementation Work Claim and collision scan.

Passing CI never auto-starts Lane A or Lane B and never auto-grants implementation permission.

## Projection rule

`coordination/PROGRAM-CONTROL-TOWER.md` contains two generated regions:

- `CONTROL_TOWER_AUTOGEN`: current routes, lane state and release hold;
- `CONTROL_TOWER_CLAIMS_AUTOGEN`: current work surfaces and pairwise claim collisions.

CI requires both regions to equal state derived from canonical sources. The remaining prose is explanatory only and cannot authorize work.

## Runtime dependency

The implementation uses PyYAML only as a test/runtime parser. CI pins `PyYAML==6.0.2`. No network access, private data, account access, trading action, scheduler activation, production deployment, or automatic agent activation is performed.