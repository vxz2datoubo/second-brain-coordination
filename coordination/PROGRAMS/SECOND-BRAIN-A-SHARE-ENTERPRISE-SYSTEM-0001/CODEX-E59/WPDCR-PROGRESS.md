# Work Process, Difficulty, Discovery, And Coordination Report

`agent_id: CODEX`

## PRIMARY_WORK_AND_PROCESS_TRACE

Created a plan-only first commit, Draft PR #198, and literal lease claims. Captured a resource baseline, replaced E58's direct-child and caller-authority assumptions with E59 task-local implementations, ran bounded P0 canaries, and built adversarial authority/source/relation/mutation tests.

## DIFFICULTY_AND_COMPLEXITY

`D3_VERY_HARD`: the task requires honesty about Python's non-security boundary while still proving a useful caller-facing capability boundary, plus Windows root-exit-first cleanup without unsafe process enumeration.

## NEW_AND_UNEXPECTED_DISCOVERIES

Repeated PowerShell/CIM scans caused canary execution timeouts; arbitrary command-line enumeration is both fragile and inappropriate. Native ToolHelp identity collection resolved both issues.

## EXPANDABLE_IDEAS_AND_HIGH_VALUE_OPPORTUNITIES

An externally deployed authority service is valuable but needs a separate C-level architecture decision; it is not silently included here.

## UNRESOLVED_HARD_PROBLEMS_AND_UNKNOWNS

Historical attribution for the 119-process event is unrecoverable from present files. Job Object assignment is not claimed. Provider matrix evidence remains pending.

## PROBLEMS_FAILURES_AND_NEGATIVE_RESULTS

Two initial P0 executions timed out due to monitoring overhead. One first authority run failed because internal raw bytes shared a mutable claim. Both failures were reproduced, repaired, and preserved in this report.

## COORDINATION_REQUESTS

No new input is required until the tested commit and Provider runs exist. GPT must independently review the eventual provider artifacts and completion receipt.

## CROSS_AGENT_HANDOFF_AND_SYSTEM_IMPACT

QCLAW E45 remains read-only. E59 does not modify QCLAW, main, routes, or production runtime. The new workflow is task-scoped.

## DECISIONS_ALTERNATIVES_AND_LESSONS

Selected a local authority host with a pinned descriptor over an in-process private class because underscore-only privacy cannot be presented as a capability boundary. Rejected production-trust-root claims because that needs a distinct ownership and deployment decision.

## NEXT_ACTION_AND_GATE

Run complete local suite and public-safety/path checks, then prepare one tested commit. Remote Provider and receipt gates remain later and must not be pre-claimed.
