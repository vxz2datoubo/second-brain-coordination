# E59 Rollback

`agent_id: CODEX`

## Scope

E59 is isolated to `CODEX-E59/**` and one task-specific GitHub Actions workflow. It does not modify main, E58, QCLAW E45, live services, credentials, data, or trading code.

## Before Provider Evidence

The plan commit remains an independent recovery point. The substantive implementation commit can be reverted from the E59 branch without touching the frozen E58 branch or other worktrees.

## After Receipt Delivery

The receipt-only commit must be a direct child of the tested commit and contain only receipt/governance/evidence files. Rollback is two ordinary revert commits, in reverse order: receipt first, then tested implementation. Do not reset, rebase, amend, force-push, or delete unrelated worktrees.

## Runtime Recovery

The only local runtime child is the bounded synthetic authority host or P0 canary tree. `OwnedProcessTree` rechecks PID and creation time before cleanup, uses no executable-name global kill, and leaves unrelated processes untouched. If an owned descendant remains after grace, stop the task and report `RESOURCE_BUDGET_VIOLATION`; do not proceed to Provider evidence.
