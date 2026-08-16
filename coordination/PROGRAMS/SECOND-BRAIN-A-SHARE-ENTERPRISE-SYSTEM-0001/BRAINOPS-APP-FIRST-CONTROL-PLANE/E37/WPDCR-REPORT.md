# E37 Work Process and Coordination Report

## PRIMARY_WORK_AND_PROCESS_TRACE

The goal is a pre-canary security closure, not an execution feature. The work
imported immutable E35/E36 code, then replaced caller-trusted approval and route
hash handling with independently recomputed read-only proof contracts. The
result remains `LOCAL_FIRST / PUBLIC_SAFE / NO_TRADE` and has no executor.

## COMMAND_CLAIM_AND_EXECUTION_TRACE

Trigger phrase: `读取任务`. The active route, Issue #114, source PR #113, AMED,
forecast, lease, PMA-BIG, PDER, WPDCR, and final-head protocol were read before
the lease claim. First substantive action: an isolated E37 worktree based on
the reviewed base, followed by source import without superseded route files.

## DIFFICULTY_AND_COMPLEXITY

Actual difficulty: D2. A simple boolean or free-form reference cannot prove an
external approval. The design therefore separates transient fetched documents
from persisted public metadata, makes proof-result construction verifier-only,
and places nonce consumption after every precondition but inside the same
transaction as event reservation.

## NEW_AND_UNEXPECTED_DISCOVERIES

`DISC-E37-001` is an S2 material finding: a public dataclass representing a
verified result could itself be forged by an in-process caller. E37 closes that
specific contract-level hole with verifier-sealed factory methods and a
regression test. This does not prove an external process is maliciously
isolated; that remains outside E37's no-service/no-IPC boundary.

## EXPANDABLE_IDEAS_AND_HIGH_VALUE_OPPORTUNITIES

`OPP-E37-001`: a future read-only GitHub transport adapter can feed transient
documents to these verifiers. Owner: GPT route. Trigger: separate capability
and credential-free transport task. Gate: independent transport identity and
failure-mode tests. Status: proposal only.

## UNRESOLVED_HARD_PROBLEMS_AND_UNKNOWNS

No signed-webhook route exists, and no live canary was run. E37 therefore uses
only `READ_ONLY_FETCH_VERIFIED`, never a webhook signature claim. Closure needs
a separately routed implementation and independent review.

## PROBLEMS_FAILURES_AND_NEGATIVE_RESULTS

The local machine lacks Python 3.11; local 3.13 regression is available. This
does not substitute for the required GitHub Actions Python 3.11/3.13 matrix.
The final acceptance evidence must come from exact-head CI.

## COORDINATION_REQUESTS

None before final review. After the Draft PR has its tested head and receipt,
GPT must perform the required second pass. No user decision or WorkBuddy/QCLAW
input is needed for the current bounded scope.

## CROSS_AGENT_HANDOFF_AND_SYSTEM_IMPACT

PR #113 is immutable source evidence; PR #115 is the only E37 delivery branch.
The data contracts are isolated to BrainOps control-plane paths. Rollback is a
revert of E37 task-owned commits; no live system state is affected.

## DECISIONS_ALTERNATIVES_AND_LESSONS

Rejected alternative: trust a matching nonce and approval reference. It cannot
detect comment substitution or replay. Rejected alternative: add an automated
GitHub fetcher. It would exceed E37's proof-only boundary. Reusable lesson:
one-shot authorization requires a consumption ledger, immutable source binding,
and exact route-state proof together.

## NEXT_ACTION_AND_GATE

Run public-safe scans and exact final CI after the substantive commit, create
one evidence-only receipt, validate receipt topology, then stop for GPT review.
