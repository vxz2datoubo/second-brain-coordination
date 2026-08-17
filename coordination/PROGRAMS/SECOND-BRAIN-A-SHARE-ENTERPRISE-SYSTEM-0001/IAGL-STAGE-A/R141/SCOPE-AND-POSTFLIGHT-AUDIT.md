# R141 Scope and Postflight Audit

- agent_id: `CODEX`
- task: `CODEX-IAGL-R141-STAGE-A-SYNTHETIC-SUPERVISOR`
- issue: `#389`
- branch: `codex/r141-iagl-stage-a-synthetic-supervisor`

## Scope result

Only the four route-authorized surfaces are changed: the Stage-A source,
tests, R141 evidence directory, and the exact-head workflow. The supervisor
uses only Python standard library facilities and synthetic fixtures. It opens
no network connection, starts no subprocess/server/pool, and has no domain or
W3 write mechanism.

## Residuals and rollback

The test suite creates and removes task-owned temporary SQLite resources.
There are no task-owned long-running processes. Rollback is to leave this
unmerged branch unmerged; no shared history or workspace needs rewriting.

## R3 local postflight

- Canonical E001--E018 plus eight supporting/adversarial regressions: PASS
  (26 tests, Python 3.13).
- Retained Phase-3 local-adapter regressions: PASS (98 tests, Python 3.13).
- Retained Phase-3 integrated offline-memory regressions: PASS (291 tests,
  Python 3.13); its public safety scan passed 108 files with zero issues.
- R141 YAML, R141 public-safety import boundary, allowlist scope audit,
  reserved-marker scan, and `git diff --check`: PASS.
- Python 3.11 is not installed locally; the exact-head R141 workflow is the
  required dual-version final evidence after normal push.
- Existing untracked `src/__pycache__/` and `tests/__pycache__/` are a narrow
  passive residual under the recorded waiver. They are not staged, committed,
  or delivered and were not broadly cleaned.

## Truthfulness boundary

Passing expected-mechanism tests does not establish external scheduler
operation, production readiness, domain authority, outcome quality, or GPT
acceptance. Those remain locked or unknown as listed in `UNKNOWN-REGISTRY.yaml`.

## R3 B01R/B03R/B04R/B08 remediation truth

The test matrix now preserves the frozen IAGL-E001 through IAGL-E018 meanings.
The synthetic mechanism enforces canonical transitions, current reconciliation
identity, governance/P0 checks, active lease/fencing, event-derived preemption,
and pre-execution budget reservation. These remain synthetic mechanism proofs,
not an authorization for an external scheduler or any production capability.

R3 adds an event-derived `ReviewWorkIdentity`, bound to the current exact head
and reconciliation generation. Stale P1 event heads become trace-only, so they
cannot re-open a review. It also enforces that a real fence for slice X cannot
authorize plan, safepoint, checkpoint, or resume of slice Y. An empty caller
candidate/retrieval input remains `UNKNOWN/INCOMPLETE`; only an explicit,
reconciliation-bound synthetic complete-empty observation reaches bounded idle.

`ImprovementSlice` and `Checkpoint` now validate the frozen Stage-A fields in
public-safe forms before use or persistence: source/evidence references,
material goal, risk, stop/falsifier, writeback, budget/lease/fence, privacy,
and resume preconditions. This is still no live authority provider or canonical
write capability.
