# E47 Recoverable Lifecycle Architecture

## Scope

E47 is a synthetic, fail-closed control-plane contract. It does not invoke a
GitHub App, live authority, Codex App, CLI, canary, market, account, or trading
surface. The imported E46 entrypoints remain regression-tested and fail closed.

## Durable transition model

```text
lease record:  CAPABILITY -> EFFECT -> CLAIM-INVOCATION -> LEASE-INVOCATION
                                 -> TERMINAL -> CLAIM-COMMIT -> LEASE-COMMIT
claim record:                     CLAIM-INVOCATION              CLAIM-COMMIT
journal record: effect, each claim/lease invocation, terminal, each commit
```

Each stage persists a receipt whose structural digest binds the lease, claim,
provenance, storage, holder, target, task, route epoch, stage purpose, and the
specific request digest. Cross-record stages first write their claim-side
receipt, then write the matching lease-side stage. A post-apply response loss
does not grant a new mutation: a restarted authority rereads durable receipts,
checks the exact request digest, and applies only a missing matching stage.

## Hash boundary

The E46 `canonical_hash` remains imported for public-safe reporting. E47 uses a
separate deterministic structural digest for internal replay bindings because a
public redaction hash intentionally hides values under secret-shaped key names.
No raw request body is emitted by the E47 journal or receipt API.

## Journal rules

Every mutation has one operation ID, an immutable purpose, a request digest,
and a chained phase log. Legal phases are `REQUESTED`, `CLAIM_APPLIED`,
`LEASE_APPLIED`, `RESPONSE_LOST`, `RECONCILED`, and `COMPLETED`. Skip, reversal,
substitution, deletion, and record-hash tampering fail closed.

## Receipt gate

`pre_receipt_validator` is offline. It rejects a receipt preparation unless the
tested exact head has a successful 3.11/3.13 matrix, all lifecycle stages have
coverage, evidence contains no placeholder marker, and the later receipt commit
is a nonempty evidence-only child of the tested head. The receipt head then
needs its own exact-head matrix.

## Rollback

E47 is isolated to its branch and allowlisted paths. Reverting its substantive
commit removes its new synthetic lifecycle, tests, documents, and workflow;
the frozen E46 source remains untouched. No external durable state is created.
