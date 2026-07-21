# Security and Recovery

## Hard Boundaries

- No realtime market data, broker, account, position, order, or trade path.
- No credential value may enter a query, packet, bundle, audit record, exception, public receipt, or committed fixture.
- Private knowledge bodies remain local and are never added to the public repository.
- Candidate knowledge cannot write approved or authority state.
- Unknown or undeclared license evidence cannot activate a local source.

## Local Read-Only Rule

The adapter receives an exact local path at runtime, resolves it, verifies type, size, SHA256, declared format, manifest identity, and access policy, and never writes to the source. Public receipts contain only hashes, counts, contract states, and deterministic semantic result hashes.

## Runtime Recovery

1. Stop before any source or credential boundary is crossed.
2. Read the four recovery control files.
3. Verify the latest Issue #38 task index and input commit.
4. Run the four baseline suites.
5. Restore a verified SQLite snapshot when runtime state must roll back.
6. Compare semantic state hashes after restore or rebuild.
7. Resume from the first incomplete 20/40/60/80/100 checkpoint.

## Git Recovery

Each checkpoint receives a separate commit ending in `[agent:CODEX]`. Do not amend or force-push. Revert checkpoint commits in reverse order if GPT rejects the implementation. Local source files are read-only and therefore require no source rollback.
