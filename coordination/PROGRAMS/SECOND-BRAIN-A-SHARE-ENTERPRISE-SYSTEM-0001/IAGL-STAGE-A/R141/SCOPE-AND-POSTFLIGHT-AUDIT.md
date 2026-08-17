# R141 Scope and Postflight Audit

- task: `CODEX-IAGL-R141-STAGE-A-SYNTHETIC-SUPERVISOR`
- issue: `#389`
- branch: `codex/r141-iagl-stage-a-synthetic-supervisor`
- mode: `project_plan`
- historical initial executor: `CODEX`
- current remediation executor: `GPT_ENGINEERING_WORKER`
- current model: `GPT-5.6 Sol`
- final acceptance owner: independent GPT Reviewer, not this executor

## Scope

Authorized surfaces remain limited to the Stage-A source, tests, R141 evidence
directory, and the existing R141 workflow. B16-B18 do not add any network,
subprocess, daemon, scheduler, secret, permission, production, W3/domain,
trading/funds, or merge capability.

B16 adds only local lifecycle bookkeeping around an already-governed P2 semantic
blocker. B17 adds only deterministic SQLite starvation counters/visibility and a
bounded ranking rule. The P4 promotion ceiling is P3; P3 never becomes P2, and
fairness is evaluated only after P0/P1/P2 gates.

The public import/runtime entry remains `iagl_synthetic_supervisor.py`. The
previously reviewed B13-B15 runtime blob is retained byte-for-byte as the
internal `iagl_synthetic_supervisor_core.py`; the public entrypoint extends it
with B16/B17 only. This is an internal extraction for auditability, not a second
active supervisor entrypoint.

## Current local validation

- Canonical `IAGL-E001..E018`: retained.
- Additional stale-event guard: retained.
- Remediation regressions through B17: 23.
- Supporting contracts: 8.
- Total deterministic suite: **50 tests**, **50/50 PASS twice** on Python 3.13.5.
- `py_compile`: PASS.
- forbidden-import/public-safety AST scan: PASS.
- reserved-marker scan: PASS.
- no R141/test-owned long-running process observed.

The exact final commit SHA and its CI run IDs are intentionally not embedded in
this in-branch file. They are self-referential facts that only exist after this
evidence package is committed. They must be bound externally to the resulting
exact head on PR #391 / Issue #389.

## B16 lifecycle truth

A P2 event can now move from `PENDING` to `RESOLVED_TRACE`, then return to
`PENDING/P2` when a later fresh reconciliation positively reports the same
semantic blocker active again. The prior resolution record is not deleted and
the lifecycle history records both `RESOLVED` and `REACTIVATED`.

## B17 fairness truth

The Stage-A fairness mechanism persists a bounded starvation counter per
`slice_id`. Aged items are inspectable with a deterministic reason. Any priority
effect requires all three frozen conditions: `AGING`, `MATERIALITY`, and
`FRESH_RECONCILIATION`.

- P4 may be promoted only to an effective P3.
- P3 aging affects only P3 within-class ordering.
- P0 and P1 are processed before fairness.
- P2 blocker safety is processed before fairness and is never weakened.

The Stage-A threshold is a deterministic fixture policy, not a production
calibration. Production fairness calibration remains UNKNOWN.

## B18 provenance / UNKNOWN truth

Historical CODEX R3 provenance remains historical. The current B16-B18
remediation is attributed to `GPT_ENGINEERING_WORKER / GPT-5.6 Sol`. Synthetic
PASS does not close live scheduler, live reconciliation provider, privacy,
authority, production outcome, domain/W3, trading, or merge UNKNOWNs.

## Rollback and residuals

Rollback remains: do not merge this Draft PR. No shared history rewrite is
needed. Only task-owned temporary test resources / pycache are eligible for
cleanup; no global Python/Docker kill is used.
