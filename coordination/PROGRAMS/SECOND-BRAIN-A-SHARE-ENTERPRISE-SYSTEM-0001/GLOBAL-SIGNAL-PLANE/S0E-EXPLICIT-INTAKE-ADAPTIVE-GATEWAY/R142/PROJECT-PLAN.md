# R142 Retrospective Signal Intake Bridge — Project Plan

- task_id: `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE`
- route_epoch: `142`
- issue: `#393`
- mode: `project_plan`
- implementation_branch: `codex/r142-retrospective-signal-intake-bridge`
- executor_role: `GPT_ENGINEERING_WORKER`
- model_id: `GPT-5.6 Sol`
- plan_status: `M0_COMMITTED_BEFORE_IMPLEMENTATION`
- fresh_canonical_main: `81566f47721f07519f2617ab8901147adf437789`
- fresh_reconcile_basis: `2026-08-18 canonical GitHub connector reads`
- f05_current_main_rebind: `8780d457997914632507eed03e54a1c685444aba`
- f05_independent_review: `4962938733`
- f05_issue_checkpoint: `5330537475`
- f05_status: `IN_PROGRESS_PENDING_FRESH_M4_AND_EXACT_HEAD_CI`

> The original `fresh_canonical_main` above is preserved as the truthful M0 plan-time fact. F05 does not rewrite that history; the current acceptance binding is tracked separately by `f05_current_main_rebind` and the current R142 package/evidence/status artifacts.

## 1. M0 fresh reconciliation result

Execution may proceed because the current canonical control plane is internally consistent for the GPT executor substitution:

- Issue `#393` remains open and bound to the same R142 mission/epoch.
- Issue comment `5323711043` is the current GPT executor-substitution handoff and records user start.
- `coordination/ACTIVE-CODEX-TASK.yaml` records historical Codex as `PAUSED_EXECUTOR_SUBSTITUTED`, `execution_allowed=false`, with continuation owned by the GPT substitution route.
- `coordination/ACTIVE-PROGRAM-LANES.yaml`, `coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml`, and `coordination/PROGRAM-CONTROL-TOWER.md` agree that Lane A is reserved for the same R142 write surfaces and that the GPT Engineering Worker may begin only after fresh reconciliation and this M0 plan commit.
- `coordination/ROUTES/GPT-ENGINEERING-WORKER-R142-EXECUTOR-SUBSTITUTION.yaml` grants the replacement execution route without changing the historical `codex/` branch name or agent enum.
- The original R142 route and task brief are retained as historical/task contracts; their historical Codex execution field does not override the later canonical ACTIVE/substitution binding.
- No R142 implementation branch or implementation PR existed at fresh reconcile; this branch was created from exact canonical main.
- Open R60 PR `#304` changes only the R60 program root and `.github/workflows/r60-retrieval-adversarial-benchmark.yml`; no R142 allowed write path overlaps.
- Same-canonical-object writer max remains 1, local-heavy stage max remains 1, and nested parallelism remains forbidden.

If canonical main later advances, execution must re-read main and continue only when the new head is a non-conflicting descendant. Conflicting control-plane or write-surface drift is a stop condition.

## 2. Existing authorities to reuse, not duplicate

R142 is a bounded last-mile extension of existing accepted Signal Plane machinery.

### R136 S0E

Reuse `SignalIntakeGateway` from `src/global_signal_gateway/gateway.py` for the durable admission boundary. Existing R136 behavior already:

- validates public-safe intake envelopes;
- derives durable-vs-ephemeral routing;
- creates immutable `SignalEvent` records;
- admits only through its supplied ledger;
- preserves omission as a no-op;
- does not create a Task or Work Claim.

### S0C

Reuse read-only S0C source `global_signal_plane.DurableSignalLedger` and its SQLite append-only persistence. Existing ledger behavior already provides:

- durable uniqueness for `(event_source,event_id)` and `idempotency_key`;
- collision fail-closed behavior;
- input revision;
- deterministic projection rebuilding and checksum;
- replay/read-back from admitted history;
- no W3/domain/execution-authority mutation.

R142 MUST NOT create a second Signal ledger/store/backlog or modify S0C source. If implementation evidence proves an S0C source change is required, stop and request independent GPT scope expansion.

## 3. Minimal architecture selected

Implement one bounded module under the existing S0E package, provisionally `retrospective_intake.py`, with no daemon or background service.

```text
SignalImportPackage/v1
        |
        v
parse + public-safety + deterministic canonicalization/digest
        |
        v
CurrentCanonicalSnapshot/v1 (explicit, evidence-bound input)
        |
        v
RetrospectiveReconciler
        |
        +--> non-admitting disposition + evidence
        |
        `--> NEW_DURABLE_SIGNAL only
                  |
                  v
          existing SignalIntakeGateway
                  |
                  v
          existing S0C DurableSignalLedger
                  |
                  v
 durable receipt + deterministic read-back/replay checksum
```

A GitHub-staged import document/package is transport/replay input only. It never becomes effective Signal truth by existing in Git. Effective truth changes only after S0C admission succeeds.

## 4. M1 — SignalImportPackage/v1

Build a machine-checkable package and candidate validator with:

- batch identity and per-candidate identity;
- `candidate_id`, source window/message/project/time refs;
- public-safe summary/original intent ref;
- signal kind, epistemic state, desired effect, problem, success condition;
- expected problems, risks, assumptions, unknowns, dependencies;
- evidence/counterevidence refs;
- primary/related domains and privacy scope;
- historical status and candidate relations;
- model/tool/version/work-item refs;
- explicit `UNKNOWN` instead of fabrication;
- deterministic JSON canonicalization and SHA-256 digest;
- batch retry idempotency and same-id/different-body collision rejection.

Raw private conversation body and secret-like material fail closed before reconciliation or admission.

## 5. M2 — current-canonical reconciler

The reconciler accepts an explicit `CurrentCanonicalSnapshot/v1` assembled from fresh authoritative observations. It MUST NOT infer current truth from the historical package itself.

Supported dispositions:

- `NEW_DURABLE_SIGNAL`
- `ALREADY_CANONICAL`
- `ALREADY_SATISFIED`
- `DUPLICATE`
- `EXTENDS`
- `REINFORCES`
- `CONTRADICTS`
- `SUPERSEDED`
- `DOMAIN_CANONICAL_ONLY`
- `NEEDS_REVALIDATION`
- `REJECT_PRIVATE_OR_UNSAFE`
- `INSUFFICIENT_PROVENANCE`

Decision inputs must preserve exact refs for current/open and historical/closed Signals, current Tasks/Missions, Issues/PR/reviews, accepted R136-R141 capability refs, domain canonical refs, dependencies, conflicts, supersession, and desired-effect satisfaction.

Fail-closed rules:

- historical `NEW` never forces current `NEW_DURABLE_SIGNAL`;
- no newest-wins rule;
- no text-similarity-only auto-admission;
- no closed-task resurrection merely because a historical task is closed;
- omission is not revocation;
- contradictions are retained rather than silently overwritten;
- a stale canonical snapshot blocks admission;
- ambiguous evidence becomes `NEEDS_REVALIDATION` or `INSUFFICIENT_PROVENANCE` rather than optimistic admission.

## 6. M3 — one-shot durable bridge

Implement an on-demand call that consumes one validated package plus one fresh snapshot and a supplied existing S0C ledger instance/path. For each candidate:

1. validate and digest;
2. reconcile against current evidence;
3. admit only `NEW_DURABLE_SIGNAL` through the existing `SignalIntakeGateway`;
4. require an S0C `ADMITTED` or idempotent durable receipt before claiming persistence;
5. read the accepted event back from S0C history;
6. rebuild/read current projection;
7. record deterministic replay checksum/identity;
8. produce a public-safe R142 receipt.

`write_status=PERSISTED` is allowed only when durable append/identity plus read-back are proven. Every other case is `NOT_PERSISTED`.

No admission may create a Task, Work Claim, route, Mission authorization, W3 write, domain write, production action, or trading action.

## 7. M4 — adversarial and retrospective evidence

Create tests for every Issue #393 adversarial requirement, including:

1. old `NEW` but current already satisfied;
2. true new;
3. duplicate retry;
4. same ID/different body collision;
5. superseded historical requirement;
6. contradictory historical lessons;
7. domain-only knowledge;
8. private/raw rejection;
9. missing provenance;
10. omission != revocation;
11. Signal != Task;
12. stale canonical snapshot;
13. closed task but desired effect unmet;
14. current task dependency;
15. stable replay checksum;
16. transport cannot mutate effective truth;
17. old-window `NEW` overridden;
18. no durable receipt => `NOT_PERSISTED`;
19. cross-window duplicate;
20. real retrospective package case.

### Real historical source status at M0

A real 2026-08-15 historical `UNIFIED_SIGNAL_TOWER_REQUIREMENTS_HANDOFF` source is available to this GPT window via File Library and can be treated only as historical source evidence. However, fresh searches have NOT located the previously mentioned governed package that explicitly enumerates the approximately 45 candidates / approximately 24 historical `NEW` labels.

Therefore current status is:

`REAL_RETROSPECTIVE_SOURCE_HANDOFF_AVAILABLE / GOVERNED_45_CANDIDATE_PACKAGE_UNAVAILABLE`

R142 will not fabricate a 45-candidate fixture and will not relabel a synthetic corpus as the real case. The implementation and synthetic/adversarial suite may complete, but M4 real-case completion must remain `REAL_RETROSPECTIVE_SOURCE_UNAVAILABLE` unless a public-safe enumerated source package is actually recovered before handoff.

## 8. M5 — exact-head CI and safety

Add only `.github/workflows/global-signal-plane-r142-retrospective-intake.yml` and run R142-owned validation on Python 3.11 and 3.13.

Required CI evidence:

- `git rev-parse HEAD`;
- PR head SHA;
- base SHA;
- merge-ref SHA where GitHub exposes it;
- Python version;
- exact commands and results;
- R142 tests plus relevant bounded S0E/S0C regression tests;
- changed-path allowlist;
- public-safety/secret/private-body scan;
- placeholder/TODO/shadow-implementation scan for R142 code;
- `git diff --check`;
- task-owned process/resource cleanup;
- no nested process pools and no daemon.

The workflow must not treat adjacent Signal Plane CI as proof of R142.

## 9. M6 — evidence handoff

Before requesting independent review, capture:

- canonical main used and any non-conflicting descendant reconciliation;
- M0 plan commit and implementation commits;
- Draft PR and exact tested head;
- changed-file inventory + allowlist proof;
- parser/validator/digest evidence;
- reconciler disposition matrix;
- durable S0C receipt/read-back/replay/idempotency evidence;
- stale/private/Signal!=Task fail-closed evidence;
- real-source provenance and honest availability/count status;
- Python 3.11/3.13 run/job IDs and exact refs;
- public safety, workspace/process cleanup, rollback;
- all `UNKNOWN` / `NEEDS_REVALIDATION` items;
- `executor_role=GPT_ENGINEERING_WORKER`;
- `model_id=GPT-5.6 Sol`;
- actual tool provenance.

Then emit exactly the project completion signal and stop for an independent GPT exact-head review. Do not self-review, self-merge, or convert missing real-E2E evidence into success wording.

## 10. Write-scope and rollback

Only these write surfaces are authorized:

1. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/src/global_signal_gateway`
2. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/tests`
3. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/R142`
4. `.github/workflows/global-signal-plane-r142-retrospective-intake.yml`

Rollback is branch/PR-level reversal of R142-only commits. No reset, rebase, force-push, destructive history rewrite, global process kill, S0C source edit, or unrelated branch mutation is authorized.
