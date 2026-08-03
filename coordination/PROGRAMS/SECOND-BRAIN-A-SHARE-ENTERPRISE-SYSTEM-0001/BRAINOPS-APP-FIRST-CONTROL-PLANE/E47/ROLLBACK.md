# E47 Rollback and Recovery

## Git rollback scope

The tested implementation is isolated to these authorized surfaces:

- `.github/workflows/brainops-e47.yml`
- `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/**`

Reverting the E47 substantive commits removes only the selected E46 import,
the E47 lifecycle, its tests, workflow, and its route documents. It does not
mutate source PR #146, `main`, external data, credentials, accounts, or
runtime services.

## Durable-state recovery behavior

The test-only `SyntheticFileCasGateway` is created in temporary test paths and
is not committed. After an injected post-apply response loss, a new authority
instance rereads the claim, lease, and journal records. A matching request
returns an `ALREADY_*` code or applies only the missing mirror transition. A
different binding or request fails closed.

## Known boundary

No production storage migration or rollback is claimed. That remains outside
this synthetic engineering route and requires a separately approved trust-root
task.
