# Program Control Tower Foundation

This directory is the executable, fail-closed implementation of the cross-program Control Tower declared by Issue #310.

## Authority boundary

The Control Tower is **not** a task router, market authority, W3 knowledge store, W7 risk veto, W12 probability authority, trading engine, or AI-film canonical source. It only reads canonical sources and produces reconciliation findings, collision classifications, route-freshness witnesses, and a derived human projection.

Source precedence remains:

1. current explicit user direction;
2. latest per-agent `ACTIVE-*.yaml` route on remote `main`;
3. project/program canonical authority;
4. `coordination/ACTIVE-PROGRAM-LANES.yaml` for lane relationships only;
5. derived human views;
6. historical aggregate views.

## Commands

From this directory:

```bash
python run_all_tests.py
python run_control_tower.py check --repo-root ../..
python run_control_tower.py projection --repo-root ../..
python run_control_tower.py witness --repo-root ../.. --agent CODEX
python run_control_tower.py verify-witness --repo-root ../.. --agent CODEX --witness-file witness.json
```

`check` fails closed when canonical route projection, user hold, WIP/resource boundaries, or registry structure is inconsistent. A user hold is not an implementation failure: it returns `HOLD_BY_USER` while the structural foundation can still be `PASS`.

## Two separate gates

- **Foundation Ready**: scanner/reconciler code, O0-O4 classifier, WIP checks, commit-time route witness, deterministic projection and CI are validated.
- **Lane Release**: only after Foundation Ready, GPT performs a current three-lane dry-run. Harness and A-share remediation remain paused until that explicit gate is changed.

Passing CI never auto-starts Lane A or Lane B.

## Projection rule

`coordination/PROGRAM-CONTROL-TOWER.md` contains a machine-generated block delimited by `CONTROL_TOWER_AUTOGEN`. CI requires that block to equal the state derived from canonical sources. The remaining prose is explanatory only and cannot authorize work.

## Runtime dependency

The implementation uses PyYAML only as a test/runtime parser. The CI workflow pins the test-only parser version. No network access, private data, account access, trading action, scheduler activation, or production deployment is performed.