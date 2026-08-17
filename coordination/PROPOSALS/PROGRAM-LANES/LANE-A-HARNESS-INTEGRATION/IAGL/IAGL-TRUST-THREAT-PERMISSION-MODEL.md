# IAGL Trust, Threat and Permission Model

Status: `STAGE_A_ARCHITECTURE / NO_SECRET / NO_PRODUCTION`

## 1. Trust boundaries

### User
Owns high-risk approval, funds, real trading, credentials/permissions, destructive operations and major authority changes.

### Control Tower
Owns task release, claims, WIP, leases/fencing, write allowlists and merge gates.

### IAGL Supervisor
May schedule and route bounded work but has no independent authority to widen scope.

### GPT cognition workers
May research, reason, audit, design and propose. Their outputs are claims until evidence-bound and accepted by the relevant authority.

### Codex / execution agents
May implement only inside a released Task/route/claim/allowlist. They cannot self-grant merge or domain authority.

### Signal Tower
Provides signals/gaps/opportunities; signals never authorize writes.

### W3 / domain repositories
Remain canonical truth owners for their respective knowledge/domain state.

## 2. Permission tiers

### Tier C0 — cognition/read
Allowed by default in architecture/research work:
- public web research;
- official docs/papers;
- GitHub read;
- canonical-state inspection;
- architecture/eval/threat design;
- synthetic tests;
- candidate mission design.

### Tier C1 — coordination write
Allowed only inside an explicitly scoped GPT architecture/governance branch or released agent task:
- proposal docs;
- task briefs;
- review comments;
- receipts;
- synthetic fixtures.

### Tier C2 — bounded implementation write
Requires Control Tower release, exact allowlist and lease:
- code changes on task branch;
- tests/workflows scoped to mission;
- draft PR.

### Tier C3 — sensitive operational
Requires explicit user approval and separate gate:
- new API secret;
- GitHub permission expansion;
- service/daemon/production scheduler;
- private-data access expansion;
- domain canonical writer;
- deployment/production automation.

### Tier C4 — irreversible/financial
Always user-gated:
- real orders/funds/accounts;
- destructive history rewrite;
- force push/rebase/reset as governance action;
- repository visibility/ownership changes;
- destructive deletion of canonical data.

IAGL Stage A is limited to C0-C1.

## 3. Reviewer/executor separation

Threat: an executor reports SUCCESS and the same effective identity converts that report into acceptance.

Controls:
- executor evidence is untrusted until independently re-observed;
- reviewer binds to exact head and independently reads diff/CI/control plane;
- provider-issued evidence and caller-authored structure must be distinguishable;
- no self-signed completion receipt can substitute for external observation;
- review disposition is separate from merge authority.

Residual limitation:
- same-process seals are API trust boundaries, not cryptographic isolation from hostile code already inside the process.

## 4. Threat catalog

### T01 Duplicate event execution
A webhook/watchdog/retry causes the same semantic event to run twice.

Controls: idempotency key, target-state binding, lease/fencing, append-only event history.

### T02 Stale-head review
Review starts on head A while PR moves to head B.

Controls: exact-head anchor, final head recheck, invalidate review on drift.

### T03 CI-green false acceptance
Tests pass but diff, scope, receipt or authority is wrong.

Controls: independent diff/receipt/authority audit; CI is necessary evidence only.

### T04 Caller-authored authority
A worker supplies favorable metadata and receives trusted evidence.

Controls: mechanism-bound provider projection; untrusted structural preview is explicitly UNVERIFIED.

### T05 False negative by incomplete retrieval
No candidate is passed and system concludes UNSUPPORTED.

Controls: absence of input is not authority-resolution completeness evidence; fail closed unless a future completeness proof exists.

### T06 Infinite improvement loop
No high-priority work exists, so the system keeps browsing/researching forever.

Controls: Improvement Slice contract, VOI stop gate, budget, expected artifact, no-value streak detection.

### T07 Priority starvation
Repeated P1 reviews prevent useful P3 progress forever or P4 never runs.

Controls: aging metrics and fairness reporting, but P0/P1 safety priority cannot be bypassed.

### T08 Unsafe preemption
Worker is killed during a partial write or transaction.

Controls: cooperative safepoints, atomic operations, checkpoint, no global process kill.

### T09 Resume under drift
Checkpoint resumes after main/domain/route/permission changed.

Controls: resume validation and fresh Global Reconciliation; invalid checkpoint is replanned, not blindly continued.

### T10 Second knowledge authority
Checkpoint, queue or session begins storing canonical knowledge and drifts from W3/domain truth.

Controls: refs/digests only where possible; explicit working-state classification; no canonical promotion from checkpoint.

### T11 Secret leakage
API keys/tokens/private bodies enter GitHub, prompts, logs or traces.

Controls: Stage A no secrets; Stage B secret gate; redaction; explicit forbidden fields; least privilege.

### T12 Permission creep
A convenient automation token accumulates contents write, actions admin, merge and secret scopes.

Controls: role-separated credentials; reviewer read/comment credential vs implementation credential; no merge credential by default.

### T13 Arbitrary command injection
GitHub prose or model output is executed as shell.

Controls: structured dispatch contracts; allowlisted actions; no eval/cmd of arbitrary comments.

### T14 Malicious or compromised provider
Provider returns fabricated current state.

Controls: first-party source preference, exact revision/response identity, cross-checks where material, provider trust class, independent audit.

### T15 Partial GitHub observation
Pagination/rate limit/API error yields incomplete state but is treated as complete.

Controls: fail closed on partial pagination, rate limits and ambiguous errors.

### T16 Governance-mode fiction
Prompt says USER_CONTROLLED but local automation is still running.

Controls: governance mode requires observed control state; prose is not proof.

### T17 Duplicate worker collision
Two workers claim same improvement slice or mutable path.

Controls: Control Tower lease, fencing token, same-object writer max 1.

### T18 Cost runaway
Frequent events or recursive research consumes excessive API/compute budget.

Controls: per-slice budget, daily/mission budget, max retries, dedupe, no nested agent fan-out without explicit budget.

### T19 Model self-confirmation
Research worker and reviewer converge because they share assumptions/context.

Controls: independent evidence auditor, competing hypotheses, targeted contrary evidence, adjudication, no model self-score as truth.

### T20 Domain authority laundering
A general GPT conclusion silently becomes AI Film/A-share/W3 formal truth.

Controls: domain-owned promotion only; candidate-first lifecycle; writeback gate and provenance.

### T21 Destructive recovery
A stale/untrusted workspace triggers reset/clean/force push.

Controls: preserve evidence; fresh clone/worktree; no history rewrite recovery.

### T22 Local resource storm
Agent spawns dozens of Python processes or nested pools.

Controls: single worker default, one local heavy stage, bounded subprocesses, task-owned cleanup, no global kill.

## 5. Hard gates

The following always stop autonomous progression and require user approval or a separate explicit authority gate:

- secrets/credentials/API keys;
- GitHub permission expansion;
- production daemon/scheduler deployment;
- domain canonical write authority;
- W3 formal truth write expansion;
- repository visibility/security-setting changes;
- real trading/accounts/orders/funds;
- destructive history rewrite;
- broad deletion/migration of canonical data;
- autonomous merge authority.

## 6. Stage B credential separation candidate

If Stage B is later approved, use at least two logical credentials:

1. Reviewer credential: repository read, Actions read, PR/Issue comment/review only.
2. Engineering credential: bounded branch contents write and draft PR only after released task.

Neither should have secret administration, repository administration, branch-protection bypass or autonomous merge by default.

## 7. Evidence classes

- `OBSERVED_FIRST_PARTY`: direct GitHub/API/domain exact read.
- `PROVIDER_BOUND`: verified provider-issued evidence bundle.
- `EXECUTOR_REPORTED`: agent self-report, never sufficient alone for acceptance.
- `MODEL_INFERENCE`: explicit inference, never authority fact.
- `UNKNOWN`: evidence unavailable/incomplete/conflicted.

Material decisions must state which class supports each key claim.

## 8. Failure behavior

When trust or permission cannot be established:

- stop material write;
- preserve checkpoint/evidence;
- emit `UNKNOWN / BLOCKED / NEEDS_USER_GATE`;
- never upgrade confidence because the model can imagine a likely answer;
- never widen permissions automatically.
