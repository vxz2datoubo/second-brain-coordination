# R141 Scope and Postflight Audit

- task: `CODEX-IAGL-R141-STAGE-A-SYNTHETIC-SUPERVISOR`
- issue: `#389`
- branch: `codex/r141-iagl-stage-a-synthetic-supervisor`
- mode: `project_plan`
- historical initial executor: `CODEX`
- current remediation executor: `GPT_ENGINEERING_WORKER`
- current model: `GPT-5.6 Sol`
- final acceptance owner: independent GPT Reviewer, not this executor

## B19 single-runtime boundary

The Stage-A runtime is collapsed back to one canonical module:
`src/iagl_synthetic_supervisor.py`. The previous
`iagl_synthetic_supervisor_core.py` alternate Supervisor/Store implementation is
removed. CI statically requires one `SyntheticSupervisor`, one
`WorkingStateStore`, no core file/reference, and the runtime constructor rejects
an incompatible store type. This is a mechanical boundary, not an `internal`
naming convention.

## B20 authoritative P2 without transport history

Fresh reconciliation materializes authoritative `active_p2_classes` and
`active_p2_event_keys` into reconciliation-derived P2 working state when no
matching event row exists. The derived blocker is lower-work blocking and can
reach `RESOLVED_TRACE` only through authoritative-complete observation plus an
explicit exact resolution.

## B21 renewed P0 recurrence

A later identical semantic high-risk occurrence reopens a historical
`P0_DISPOSITION_TRACE` as unadjudicated P0. The previous decision record remains
append-only history and its old decision reference cannot clear the renewed
occurrence. A new current reconciliation-bound disposition is required.

## Scope and truthfulness

No network, subprocess, daemon, scheduler, secret, permission, production,
domain/W3, trading/funds, destructive-history, self-review, or merge authority is
introduced. The expected exact-head deterministic layout is 43 prior tests, 7
B16/B17 tests, and 4 B19-B21 tests. Final PASS/count and CI run IDs are bound
externally after the final commit exists.

UNKNOWN/LOCKED/future-governed dependencies remain open. Synthetic PASS is not
Stage-B or production readiness.
