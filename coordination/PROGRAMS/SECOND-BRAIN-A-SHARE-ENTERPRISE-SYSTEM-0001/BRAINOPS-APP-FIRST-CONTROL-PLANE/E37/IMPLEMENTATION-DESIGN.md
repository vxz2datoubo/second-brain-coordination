# E37 Implementation Design

## Reservation transaction

`MetadataStore.reserve_canary_event` inserts the approval consumption, event
reservation, and verified two-file route proof in one SQLite `BEGIN IMMEDIATE`
transaction. The approval key is exactly `(task_id, route_epoch, canary_id,
approval_nonce)`. Any conflict rolls back every insert, so a failed event insert
does not burn a nonce.

## Approval provenance

`ReadOnlyApprovalVerifier` derives `ApprovalEvidence` from a transient,
read-only comment document. The approved record binds the repository, issue,
comment, actor, issued time, body SHA256, canonical approval reference, and
hash of the approval bindings. A direct caller cannot construct a verified
result through the public result constructor.

## Remote route proof

`ReadOnlyRouteProofVerifier` recomputes Git's SHA1 blob identity and SHA256
content hash for both canonical route files. It requires the exact supplied
remote main commit, `refs/heads/main`, matching repository, non-future
observation, and an observation age of at most 300 seconds.

## Non-execution boundary

There is no transport client, webhook handler, process runner, UI bridge, or
canary executor in E37. A synthetically eligible decision remains shadow-only.
