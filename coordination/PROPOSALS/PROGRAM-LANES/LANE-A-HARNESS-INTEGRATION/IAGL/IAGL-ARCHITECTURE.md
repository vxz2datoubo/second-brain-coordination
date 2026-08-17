# IAGL — Interruptible Autonomous Governance Loop

Status: `ARCHITECTURE_STAGE_A / PLANNING_ONLY / NOT_EXECUTABLE`

Owner: USER  
Architecture owner: GPT  
Issue: #386  
Canonical predecessor closure: R140 / main `bd7e49f5d596b63efa158b622b6116229df644b7`

## 1. Mission

IAGL turns the current stop-and-wait engineering loop into a bounded, interruptible, resumable governance loop.

Core behavior:

```text
GitHub / CI / user event
        +
periodic watchdog reconciliation
        ↓
Global Reconciliation
        ↓
Priority Router
  P0 user / high-risk gate
  P1 exact-head review
  P2 active blocker
  P3 bounded improvement slice
  P4 open research candidate
        ↓
atomic work slice
        ↓
safepoint checkpoint
        ↓
interrupt? ── yes → review / gate work → reconcile → resume
     │
     no
     ↓
evaluate → learn → next slice
```

The system MUST NOT depend on one ChatGPT conversation remaining alive or sleeping for a fixed duration. Time belongs to a scheduler/trigger layer, cognition belongs to GPT, and resumability belongs to durable working-state contracts.

## 2. First principles

1. `Scheduler owns time; GPT owns cognition; state store owns resumability.`
2. `Event-driven first; periodic reconciliation second.`
3. Signal is not a task and never grants execution authority.
4. Control Tower owns authorization, claim, WIP, lease and merge gates.
5. Harness owns runtime/orchestration mechanics, not knowledge truth.
6. W3 remains the sole knowledge/memory authority.
7. Reviewer and executor must be separable identities/roles.
8. Cognitive autonomy may be high while action authority remains bounded.
9. No claimed completion without evidence-bound receipts.
10. Continuous improvement must have value/stop gates; there is no permission for infinite research.

## 3. System placement

```text
USER
  │ goals / approvals / stop / resume
  ▼
CONTROL TOWER
  │ task release / claims / leases / merge gates
  ▼
HARNESS / IAGL SUPERVISOR
  │ deterministic orchestration only
  ├─ Event Inbox
  ├─ Priority Router
  ├─ Checkpoint Store
  ├─ Budget / Lease / Fencing
  └─ Reconciliation
        │
        ├─ GPT Independent Reviewer
        ├─ GPT Research Worker
        ├─ GPT Architecture Worker
        ├─ GPT Evaluation / Adversarial Worker
        └─ GPT Adjudicator

SIGNAL TOWER → signals/gaps/opportunities → Improvement Queue
W3 → knowledge/memory authority; IAGL may read bounded context but never becomes a second W3
CODEX / QCLAW / WORKBUDDY → bounded execution under Control Tower release
```

## 4. What IAGL owns

IAGL owns only governance-loop working state and orchestration decisions:

- event normalization and dedupe;
- priority selection;
- safe-point preemption;
- checkpoint/resume state;
- bounded research/improvement slice selection;
- watchdog reconciliation;
- budget and starvation/fairness controls;
- worker-role routing;
- review-pending detection;
- trace/receipt references.

IAGL does NOT own:

- canonical knowledge or user memory;
- domain truth;
- market-data truth;
- AI Film maturity or lesson authority;
- Signal Tower truth;
- Control Tower authorization;
- production credentials;
- merge authority;
- trading/orders/funds.

## 5. Trigger model

Primary triggers are event-driven:

- new PR/head;
- exact-head CI completion;
- review request / changes requested / acceptance;
- task/claim/lease status change;
- user stop/resume/governance command;
- high-materiality Signal Tower event.

Fallback trigger is watchdog reconciliation. Initial target cadence for an external scheduler is 20 minutes, but cadence is NOT a semantic guarantee and may later be lowered if cost, rate limit and noise controls pass.

A watchdog tick MUST reconcile before acting. It MUST NOT assume that the state observed in a previous tick is still current.

## 6. Priority semantics

Priority is strict but not starvation-blind:

- P0: user command, secrets/permission/production/trading/destructive gate.
- P1: Codex/agent exact-head review or review remediation completion.
- P2: active formal blocker/security regression/reconciliation drift.
- P3: selected improvement mission.
- P4: open research candidate.

A lower-priority item may continue only until the next declared safepoint after a higher-priority event is observed.

## 7. Cooperative preemption

Hard process killing is forbidden as a normal scheduling primitive.

Preemption sequence:

1. finish current atomic operation;
2. emit checkpoint with evidence refs and next exact action;
3. mark mission `PAUSED_FOR_HIGHER_PRIORITY`;
4. release or explicitly retain lease according to contract;
5. execute higher-priority work;
6. fresh global reconciliation;
7. validate resume preconditions;
8. resume from checkpoint or invalidate/replan.

If the current operation cannot reach a safe point within budget, it must fail closed rather than hide a partially applied state.

## 8. Continuous Improvement Queue

The queue is fed by normalized signals, not free-form curiosity.

Allowed sources:

- unresolved UNKNOWN;
- architecture debt;
- evidence/test/security/performance gaps;
- review findings;
- real generation / market / engineering feedback;
- stale methods needing revalidation;
- user-declared goals;
- verified new official platform capability;
- regression and false-green lessons.

Every Improvement Slice requires:

- `slice_id`;
- source signal(s);
- problem signature;
- bounded goal;
- evidence target;
- allowed tools/data;
- risk class;
- time/compute budget;
- expected artifact;
- falsifier / stop condition;
- writeback destination or `NO_WRITEBACK`.

`browse indefinitely` and `improve system generally` are invalid slice definitions.

## 9. Research and method routing

IAGL consumes, but does not recreate, the frozen Method Discovery / Effective Challenge architecture.

Typical internal route:

`ProblemSignature → Method/Failure/Case Retrieval → Method Selection → VOI → Evidence Acquisition → Execution → Challenge → Evaluation → Method Credit`

The router is allowed to choose zero methods and emit `ABSTAIN / NO_SUITABLE_METHOD`.

High-materiality architecture, finance, permission, production and false-green claims require challenge/audit before promotion or irreversible action.

## 10. Checkpoint semantics

A checkpoint is working state, not knowledge truth.

It must contain only enough state to resume safely:

- mission/slice identity;
- exact control-plane snapshot refs;
- hypotheses/current findings with confidence class;
- evidence refs/digests;
- completed atomic steps;
- open unknowns;
- next exact action;
- current budget usage;
- lease/fencing data;
- interrupt reason;
- resume preconditions.

It must not copy raw private canonical bodies into public coordination storage.

## 11. Event and state freshness

Before any review, resume, task release or material write:

- refresh canonical main;
- refresh target PR/head/base/state;
- refresh exact-head CI;
- refresh route/claim/lane/lease;
- refresh user/approval/revocation state;
- reject stale event payloads;
- reject duplicate idempotency keys;
- reject head drift during review.

Old event payloads are hints, never final authority.

## 12. Reviewer semantics

Independent Reviewer must verify at least:

- exact head;
- changed-file scope;
- diff/patch substance;
- required CI/jobs/artifacts;
- control-plane/receipt consistency;
- authority and permission boundaries;
- adversarial regressions;
- unresolved UNKNOWNs;
- false-green routes;
- whether report claims exceed evidence.

A successful CI run does not equal acceptance.

## 13. Resource governance

Initial Stage A defaults:

- one active local heavy stage;
- no nested pools;
- single-worker default for local tests;
- no global `kill python` / global Docker kill;
- bounded network/tool calls;
- explicit cost budget;
- explicit timeout;
- task-owned cleanup only;
- preserve dirty/untrusted workspace evidence;
- use isolated worktree/branch for implementation.

## 14. Governance modes

IAGL must distinguish runtime governance mode from prompt prose.

Minimum modes:

- `USER_CONTROLLED`: automatic execution/claiming disabled; checkpoint state retained.
- `AUTONOMOUS_LOW_MEDIUM`: bounded low/medium-risk engineering/research may run; high-risk gates still require user.
- `PAUSED`: no new execution; reconciliation may read-only report.
- `EMERGENCY_STOP`: cancel future dispatch; preserve evidence; no destructive cleanup.

A sentence such as “manual governance mode” in a prompt MUST NOT be treated as proof that a local automation is actually disabled.

## 15. Stage A scope

Stage A is architecture + synthetic verification only.

Allowed:

- deterministic supervisor/state machine design;
- synthetic event queue;
- checkpoint/resume replay;
- mock review preemption;
- duplicate/stale-head/lease-collision tests;
- budget/starvation/fairness tests;
- crash/restart recovery tests;
- public-safe fixtures.

Forbidden in Stage A:

- OpenAI API key activation;
- GitHub secret/permission expansion;
- production scheduler;
- autonomous merge;
- domain canonical write;
- private conversation/media ingestion;
- trading/accounts/orders/funds;
- destructive history operations.

## 16. Stage B concept

Stage B may introduce a real external scheduler and GPT API reviewer only after a separate gate proves:

- secret storage design;
- least-privilege GitHub App/token scopes;
- cost/rate-limit controls;
- independent reviewer identity;
- replay/idempotency/fencing;
- kill switch and rollback;
- audit retention;
- user approval for secrets and permission expansion.

## 17. Acceptance stories

1. GPT is researching when Codex pushes a new head; research checkpoints, review runs, then research resumes.
2. Same PR pushes three heads rapidly; old-head reviews cannot approve the newest head.
3. CI reports green but diff/receipt disagree; reviewer blocks.
4. Improvement research produces no new evidence for repeated slices; VOI gate stops or reprioritizes.
5. Worker crashes after checkpoint; restart resumes only after fresh reconciliation.
6. User switches to user-controlled mode; automatic claims stop without losing checkpoint.
7. User later restores autonomous mode; system reconciles before resuming.
8. A candidate action needs secret/permission/production/trading authority; user gate preempts all lower work.
9. Two workers attempt same slice; fencing allows only one current lease.
10. New research contradicts canonical knowledge; it becomes a candidate/conflict, never silent overwrite.

## 18. Completion gate for architecture phase

Architecture freeze is complete only when the companion runtime contract, threat/permission model, eval/unknown registry, reuse/stage-B gate and Skill Manifest are merged and consistent.

After that, a new executable Codex task may be prepared only through fresh Global Reconciliation and a new Task ID / epoch / Work Claim / exact allowlist.
