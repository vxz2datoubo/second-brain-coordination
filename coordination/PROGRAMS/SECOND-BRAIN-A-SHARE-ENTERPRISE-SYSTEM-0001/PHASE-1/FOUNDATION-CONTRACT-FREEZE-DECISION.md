# Foundation Contract Freeze Decision

- agent_id: CODEX
- task_id: A-SHARE-FOUNDATION-CONTRACT-FREEZE-0001
- status: IMPLEMENTED_FOR_RESEARCH_CONTRACTS
- boundary: research_only / NO_TRADE

## Decision

Freeze a narrow, public-safe envelope for the first offline A-share replay **before** implementing replay behavior. It defines identity, schema/version, producer/run/trace, lineage, temporal semantics, quality, capability, approval, abstention, and rollback. Domain objects keep their existing ownership; this envelope is a compatibility boundary, not a second domain model.

## Authority and compatibility

The P1 schemas are the declared public contract for cross-module exchange in the first slice. Existing local Python objects remain domain records and are mapped through `EXISTING-TYPE-COMPATIBILITY-MATRIX.yaml`; they are not overwritten. Protected blueprints remain L0 authority. Raw market artifacts and future private knowledge repositories remain outside this public package.

## Explicit non-goals

- no replay execution, strategy logic, real-time adapter, L2 promotion, MARL, broker/account access, service lifecycle, private upload, cloud creation, or protected-blueprint modification;
- no migration of current SQLite/JSON runtime stores;
- no claim that a JSON schema alone promotes a candidate to authority.

## Required behavior

1. `available_at` later than a requested `as_of` must reject the record as future leakage.
2. Missing/unknown entitlement or capability must degrade/reject with an abstention reason.
3. Candidate material cannot write to an authority store.
4. This phase remains `no_trade_gate: true`; execution actions are invalid.
5. Irreversible changes require an approval reference and rollback pointer.

## Rollback

This package is isolated to public-safe P1 schemas, fixtures, documentation and tests. Revert its commits or delete the isolated worktree/branch; no local runtime data, service, credential or protected blueprint is changed.
