# Independent Review and Pipeline Liveness Protocol v2

Status: GOVERNANCE_PROTOCOL / READ_ONLY_AUDIT_EXTENSION / NO_REMEDIATION_AUTHORITY / NO_MERGE_AUTHORITY / NO_RELEASE_AUTHORITY

Canonical bootstrap directory: Issue #481.

## Purpose
A human shorthand `验算...` must never equate an empty exact-head review queue with a healthy or idle project. Every invocation has two serial phases:

1. Independent exact-head review of pending canonical queue tickets.
2. Read-only pipeline-liveness audit when no pending ticket remains, or after the bounded review batch completes.

The liveness phase does not grant the reviewer any engineering, remediation, merge, canonicalization, release, task-authority, runtime-authority, or domain-write capability.

## Required state machine

ENGINEERING_ACTIVE -> WAITING_INDEPENDENT_REVIEW -> INDEPENDENT_ACCEPT -> WAITING_CANONICALIZATION -> CANONICAL -> WAITING_CONTROL_TOWER_RELEASE -> RELEASED -> ENGINEERING_ACTIVE

`CHANGES_REQUIRED` returns to bounded Engineering remediation on the same line. A new exact head requires a new REVIEW_REQUEST/v1.

## Phase A: exact-head review

Fresh-read the selected canonical queue, compute pending `(repository, pr, exact_head)` tickets, and independently review them under the repository's existing protocol. Never re-review an exact head that already has a matching terminal REVIEW_RESULT/v1 unless the prior result is proven invalid/stale by fresh evidence.

## Phase B: pipeline-liveness audit

When no pending ticket remains, or after completing the bounded review batch, classify the project using fresh GitHub evidence. Minimum classes:

- ACCEPTED_NOT_CANONICALIZED: exact head has matching ACCEPT but the PR/head is not yet governed into canonical main.
- CANONICALIZED_NOT_RELEASED: prerequisite is canonical but the next Control Tower task remains blocked/unreleased.
- RELEASED_NOT_IMPLEMENTED: task is explicitly released but no corresponding engineering PR/exact-head candidate exists.
- IMPLEMENTED_NOT_QUEUED: formal PR/exact head exists and appears at its review stop gate, but no matching REVIEW_REQUEST/v1 exists. Do not invent a ticket; report routing defect only.
- REMEDIATION_NOT_REQUEUED: prior CHANGES_REQUIRED appears remediated on a new exact head but no new request exists. Do not review without the canonical request.
- STALE_REVIEW_REQUEST: queued exact head no longer equals current PR head.
- CI_OR_PROVENANCE_BLOCKED: review/canonicalization cannot proceed because required exact-head CI/provenance is missing or failing.
- NORMAL_IDLE: no pending review and no actionable pipeline stall found after bounded fresh inspection.
- UNKNOWN_BLOCKED: evidence is insufficient or contradictory; fail closed and name the missing evidence.

The audit must inspect only enough adjacent state to identify the next unconsumed handoff. It is not a license for an unbounded repository audit.

## Required cycle output

Every `验算...` invocation must return a `REVIEW_CYCLE_STATUS/v1` summary even when there is no new REVIEW_RESULT/v1:

```yaml
schema: REVIEW_CYCLE_STATUS/v1
project: <project>
queue_issue: <issue>
pending_exact_head_tickets: <n>
reviewed_this_cycle: <n>
pipeline_status: HEALTHY | BLOCKED | ACTIVE | IDLE | UNKNOWN
blocker_class: <class-or-NONE>
blocking_ref: <PR/Issue/head-or-NONE>
next_authority_role: INDEPENDENT_REVIEWER | ENGINEERING | CONTROL_TOWER | CANONICALIZER | NONE | UNKNOWN
next_required_action: <bounded action or NONE>
stall_fingerprint: <stable fingerprint or NONE>
stall_repeat_count: <best-effort integer when prior cycle evidence exists>
new_evidence: true | false
reviewer_mutations: NONE
```

This status is audit/coordination evidence only. It is not REVIEW_RESULT/v1 and cannot accept, merge, release, or remediate anything.

## Stall fingerprint and repeat suppression

Fingerprint stable stalls as `<project>|<blocker_class>|<blocking_ref>|<exact_head-or-main>` where available.

If the same fingerprint appears in later cycles, do not fabricate new findings or repeat an exact-head review. Report `new_evidence: false` and increment `stall_repeat_count` when prior cycle evidence makes that count reliable. At repeated stalls, explicitly route the user to the responsible authority role instead of recommending another identical review scan.

## Efficiency and quality rules

- Queue-first: exact-head review remains the primary responsibility.
- Fresh evidence only for engineering facts.
- Bounded liveness inspection: stop after identifying the first/highest-priority unconsumed handoff.
- No duplicate REVIEW_RESULT/v1 for the same exact head.
- No speculative ticket creation from off-repo candidates, chat handoffs, or draft ideas.
- No reviewer code changes, remediation, merge, canonicalization, release, or authority minting.
- CI green is evidence, not acceptance authority.
- Liveness status must distinguish `no review work` from `project healthy`.
- NORMAL_IDLE is allowed only after checking for the defined stall classes.

## Global shorthand routing

Issue #481 is the global directory. Current aliases:
- `验算` -> all registered queues, bounded cross-project batch + liveness audit.
- `验算第二大脑` -> second-brain-coordination Issue #453.
- `验算电影游戏` / `验算互动电影游戏` / `验算实时互动电影游戏` / `验算AI世界` -> ai-world-simulation-engine Issue #50.
- `验算AI导演` / `验算AI电影` / `验算AI电影导演` -> eustia-ai-film Issue #15.

Future reviewer windows must bootstrap from Issue #481 and the selected repository queue, not from chat memory. Future projects join only by registering one canonical review queue in Issue #481.
