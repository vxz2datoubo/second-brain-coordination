# IAGL Existing-System Reuse and Stage-B Gate

Status: `STAGE_A_ARCHITECTURE / NO_RUNTIME_RELEASE`

## 1. Reuse decisions

### Global Signal Tower R136-R140
Decision: `REUSE_AS_AUTHORITY_CONSUMER / DO_NOT_REBUILD`

Use for:
- signal intake;
- system awareness;
- verified observation/execution evidence;
- domain learning handoff;
- read-only domain learning recall.

IAGL may consume signals and receipts but must not create a second Signal Tower.

### Control Tower
Decision: `REUSE_AS_AUTHORIZATION_AUTHORITY`

Use for:
- task release;
- claims;
- lanes;
- WIP;
- lease/fencing;
- write allowlists;
- merge gates.

IAGL cannot authorize itself.

### Harness
Decision: `EXTEND_ORCHESTRATION_SEAM / NO_AUTHORITY_EXPANSION`

IAGL runtime belongs near Harness orchestration, but Harness remains runtime/orchestration only. It must not become W3, Signal Tower, domain truth or trading authority.

### W3 / Second Brain cognitive authority
Decision: `REUSE_READ_AND_CANDIDATE_WRITE_PATHS_ONLY_WHEN_SEPARATELY_AUTHORIZED`

Checkpoint and queue data are working state. Stable learned knowledge must flow through existing W3/domain lifecycle rather than becoming an IAGL database of truth.

### Issue #7 Codex dispatch / local automation lessons
Decision: `SELECTIVE_REUSE`

Reuse:
- structured dispatch;
- idempotency;
- workspace allowlist;
- no arbitrary shell from GitHub prose;
- pause/resume control requirement;
- persistent-thread concept only where runtime supports it.

Do not assume:
- GitHub comments automatically wake a visible Codex App conversation;
- prompt text disables local automation;
- current 10-minute local cadence is a remote canonical fact unless observed.

### Issue #4 Agent telemetry
Decision: `REUSE`

IAGL should write execution difficulty, resource cost, failed attempts, unexpected findings and opportunities into the existing feedback system rather than inventing a second telemetry schema.

### Issue #312 Method Discovery / Effective Challenge
Decision: `REUSE_AS_COGNITIVE_ROUTER`

IAGL improvement work consumes ProblemSignature, MethodMemory, SkillManifest, Effective Challenge and VOI logic. No second method registry.

### Issue #282 cognitive loop
Decision: `REUSE_AS_LEARNING/RECALL_SEAM`

IAGL can trigger bounded recall and candidate learning, but long-term knowledge remains W3/domain-owned.

### ChatGPT Scheduled Tasks
Decision: `LIMITED_FALLBACK / NOT_PRIMARY_IAGL_SCHEDULER`

Current product-level scheduling limits do not satisfy the desired 20-minute/event-driven loop. Do not build semantic guarantees around it.

### GitHub Actions / workflow events
Decision: `CANDIDATE_TRIGGER_LAYER`

Good fit for event and periodic triggers, but Stage A must not deploy a production watcher or new secret scope. Stage B should compare hosted workflow vs local dispatcher/self-hosted runtime.

### OpenAI Agents SDK / API runtime
Decision: `STAGE_B_CANDIDATE`

Potential fit for worker roles, sessions, handoffs, traces and resumability. Stage B must re-verify current official capabilities and cost/security constraints before implementation.

### Temporal or equivalent durable workflow engine
Decision: `DEFER / ONLY_IF_SIMPLE_SUPERVISOR_INSUFFICIENT`

Do not add durable-workflow infrastructure before Stage A proves a simpler state machine cannot satisfy recovery/fencing requirements.

## 2. Anti-duplication rules

IAGL implementation is rejected if it introduces any of the following:

- second canonical memory/knowledge store;
- second Signal Tower;
- second task/claim authority;
- second domain maturity authority;
- generic cross-repo writer;
- parallel skill registry;
- separate independent history rewrite/recovery controller;
- duplicate final lesson truth.

## 3. Stage A to Stage B gate

Stage B means connecting a real scheduler/event trigger to a real GPT API reviewer/improvement worker. It is NOT automatically authorized by Stage A acceptance.

Required before Stage B release:

1. Stage A architecture and synthetic tests accepted.
2. Fresh official verification of OpenAI API/runtime capabilities.
3. Fresh GitHub trigger/permission design verification.
4. Explicit user approval for any new secret/API billing/permission scope.
5. Least-privilege credential design.
6. Cost/rate-limit/retry budget.
7. External kill switch and pause semantics.
8. Event dedupe/idempotency/fencing proof.
9. Checkpoint/resume crash proof.
10. Reviewer/executor separation proof.
11. Public/private data classification and redaction.
12. Logging/audit retention and secret scrubbing.
13. No merge authority unless separately approved.
14. No production/domain write/trading expansion.

## 4. Candidate Stage B topology

```text
GitHub PR / CI event ─┐
                      ├─ Trigger Adapter ──> IAGL Supervisor
20m watchdog ─────────┘                       │
                                              ├─ exact-state reconciliation
                                              ├─ GPT Reviewer
                                              └─ GPT Improvement Worker

Control Tower <──── task/claim/lease/permission gates
W3 / Domain <────── read or separately governed candidate write
Codex <──────────── bounded execution task only
```

## 5. Credential model candidate

### Reviewer token
Minimum intended scope:
- repository contents read;
- Actions read;
- PR read + review/comment;
- Issue read + comment.

No contents write, secret admin, repo admin, branch protection bypass or merge by default.

### Engineering token
Only if a released implementation task needs it:
- bounded branch contents write;
- draft PR creation/update.

No secret admin, repo admin, branch-protection bypass or merge by default.

Credentials must be stored in approved secret/credential storage, never committed, never printed in logs, never copied into W3 or checkpoints.

## 6. Cost-control gate

Stage B needs explicit limits for:

- daily spend;
- per-review spend;
- per-improvement-slice spend;
- max tool/network calls;
- max retries;
- max simultaneous workers;
- no-value streak;
- watchdog frequency.

Cost exhaustion must stop or degrade gracefully, not silently switch to weaker evidence standards.

## 7. Deployment progression

### B0 Shadow
Observe events and produce proposed actions only. No Codex dispatch.

### B1 Review-only
Automatically start independent GPT review after eligible exact-head CI. May post review/comment only.

### B2 Improvement shadow
When no P0-P2 work exists, run bounded improvement slices but write results only to candidate/proposal surfaces.

### B3 Bounded dispatch
May create structured low/medium-risk Codex tasks after Control Tower release. No merge.

### B4 Production consideration
Only after sustained false-accept/false-block/cost/recovery evidence and separate user approval.

## 8. Rollback

Any Stage B rollout must support:

- disable trigger adapter;
- preserve event/checkpoint audit state;
- invalidate outstanding leases;
- stop future automatic dispatch;
- leave repositories/history intact;
- revert only task-owned implementation changes;
- return to USER_CONTROLLED mode.

## 9. Current decision

`PROCEED_STAGE_A_ARCHITECTURE_AND_SYNTHETIC_IMPLEMENTATION_DESIGN`

`DO_NOT_ENABLE_SECRET / API BILLING / PRODUCTION TRIGGER / AUTONOMOUS MERGE / DOMAIN WRITE / TRADING`
