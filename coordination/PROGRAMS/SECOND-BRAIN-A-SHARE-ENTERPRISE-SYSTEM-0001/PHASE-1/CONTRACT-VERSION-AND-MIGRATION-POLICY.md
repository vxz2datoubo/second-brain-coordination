# Contract Version and Migration Policy

## Version rule

All P1 contracts use semantic versions. Consumers accept only major version `1` in this slice. A minor/patch change may add optional fields; a major change must introduce an explicit adapter or migration plan and cannot silently reuse an old authority record.

## Read compatibility

An existing local domain object is read through an adapter/mapping. Missing values become `UNKNOWN`, `degraded`, or `rejected` with an abstention reason; the adapter never invents lineage, entitlement, exchange timestamps, raw ticks, or approval.

## Write compatibility

P1 creates no production write path. Candidate imports remain candidate. An authority write needs an approved authority reference and a human approval reference. Existing SQLite, JSON, audit logs and protected documents are out of scope.

## Migration and rollback

1. Record old/new schema versions and a mapping decision.
2. Run positive, negative, compatibility and rollback-pointer tests.
3. Preserve old record content; add a new version or mapping view rather than mutate silently.
4. Revert the isolated contract commit if acceptance fails. No data migration is performed in P1.

## Deferred

Field-specific adapters for each Python type, private-Git knowledge authority, Supabase projection and event ledger migration require separately activated tasks.
