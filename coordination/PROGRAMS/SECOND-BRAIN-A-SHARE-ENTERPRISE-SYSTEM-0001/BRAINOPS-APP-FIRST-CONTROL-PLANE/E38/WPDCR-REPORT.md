# E38 Work Process and Coordination Report

## PRIMARY_WORK_AND_PROCESS_TRACE

The goal was to close E37's remaining authority, Git membership and exact-CI
gaps without running a canary. Completed stages are frozen-source import,
sealed authority replacement, bounded public transport, deterministic tests
and local public-read observation. The remaining stages are exact-head remote
CI, one receipt-only commit and GPT review. The approach changed from E37's
caller-provided proof records to transport-sealed transient documents because
the latter establishes a source boundary; the discarded approach was retained
as E37 historical evidence.

## COMMAND_CLAIM_AND_EXECUTION_TRACE

Trigger was `????`. The lease was published on Issue #116 before worktree
creation. The first authorized action was the explicit frozen-source import
from `665bed5411248f0b9926c4beac4529694387ff70`, recorded in the public
visibility packet. No read-only acknowledgement or plan-only stop occurred.

## DIFFICULTY_AND_COMPLEXITY

Planned difficulty was D2; actual difficulty is D2. The hard part was making
Python-level construction fail closed while retaining testable contracts, then
proving Git object membership without a generic network client. A first
compile command used a PowerShell literal wildcard and failed; a bounded
PowerShell file enumeration repaired it and the subsequent compile passed.
Residual difficulty is external exact-head CI, not local implementation.

## NEW_AND_UNEXPECTED_DISCOVERIES

`DISC-E38-001` is the non-empty actor-policy gap recorded in the discovery
report. It was verified by a bounded unauthenticated public GitHub read. It
affects only future approval authority and does not block the current code
tests. It does not establish a trusted actor or canary readiness.

## EXPANDABLE_IDEAS_AND_HIGH_VALUE_OPPORTUNITIES

The public Git object transport may be reusable for other control-plane reads,
but this is proposal-only: owner GPT, trigger a new task, prerequisite a
non-duplication review, and validation an independent threat review. It is not
implemented outside the E38 surface.

## UNRESOLVED_HARD_PROBLEMS_AND_UNKNOWNS

`E38-UNKNOWN-001` requires GPT to declare matching actor policies; safe
workaround is rejection. `E38-UNKNOWN-002` is public transport availability in
other runtimes; this runtime has one successful bounded read, but no universal
availability claim is made. Both closure conditions are in UNKNOWN-REGISTRY.

## PROBLEMS_FAILURES_AND_NEGATIVE_RESULTS

The inherited E37 forge paths and merge-ref CI evidence are retained as the
root cause of this task. The literal wildcard compile invocation failed with
an invalid argument and was replaced by explicit file enumeration. Regression
protection is the 103-test suite and exact-head helper test.

## COORDINATION_REQUESTS

`REQ-E38-001`: GPT must decide whether a future route should add matching
`authorized_approval_actors` fields to both route documents. Evidence is the
stable runtime reason above. Urgency is before any later canary task; no E38
work is blocked. No user decision is required for E38 completion.

## CROSS_AGENT_HANDOFF_AND_SYSTEM_IMPACT

Incoming authority is Issue #116 and the frozen PR #115 evidence. Outgoing
handoff is PR #117 plus E38 artifacts. The canonical route remains main; E38
does not modify it. Rollback is `git revert` of the final substantive commit.

## DECISIONS_ALTERNATIVES_AND_LESSONS

The chosen design is a fixed public GitHub API transport, not caller-injected
documents nor credential-backed access. It costs a small test fixture layer
but provides provenance. A private Python seal is a boundary against public
factories, not a claim of cryptographic process isolation; the true source
authority remains the bounded transport plus CI and GPT review.

## AUTONOMOUS_REMEDIATION_LEDGER

R0-001 is fully recorded in UNPLANNED-IMPROVEMENT-LEDGER. No other remediation
was used after checks.

## MODEL_REASONING_AND_EXECUTION_PROFILE

Requested model is `gpt-5.6-sol` with max reasoning and X4 intensity. Actual
model/effort metadata is `ACCESS_NOT_EXPOSED`; this environment does not expose
it, so no substitution claim is made. Permission profile used is the bounded
local environment. No fallback or escalation event occurred.

## NEXT_ACTION_AND_GATE

Next action is to commit the tested substantive surface, push it, wait for the
exact-head Python 3.11/3.13 matrix, then make one evidence-only receipt commit
and stop for GPT second pass. Gate: both CI jobs must print the exact branch
head. Stop condition: any route epoch change, CI identity mismatch, or unsafe
scope expansion.
