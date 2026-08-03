# E42 Decision Log

agent_id: `CODEX`

## D-01: Stable one-shot key, exact provenance inside the record

The durable storage ID is derived from repository, route ID, epoch, task,
canary, and nonce. Route commit/tree/blob/content and approval comment/body
identities are persisted in the record and compared on every read.

Reason: including the provenance digest in the storage ID would let the same
nonce with substituted route evidence select a second object. The stable key
makes that substitution collide with the original record and fail closed as
`PROVENANCE_MISMATCH`.

## D-02: No default network writer

`FixedGitHubContentsCasClient` implements the fixed GitHub API semantics but
accepts only an injected bounded transport. The package has no token loader,
default write opener, arbitrary URL method, or live execution entrypoint.

## D-03: Lost write response is not success

GET operations may use a bounded retry. PUT is attempted once. If the response
is lost, the adapter performs a read-only recovery observation and reports
`WRITE_OUTCOME_UNKNOWN`, even when the desired bytes are visible. It never
grants `APPLIED`, because the observer cannot prove which contender wrote them.

## D-04: Raw and Verified types are disjoint

Raw capability, invocation, and route-terminalization objects remain useful as
transport input, but downstream classification accepts only verifier-minted
objects. Process-local constructor seals are explicitly not described as
cryptographic protection.

## D-05: Effect permit is narrower than a claim record

Only a reread active claim with the exact verified provenance, claim ID, owner
type, owner instance, claimant correlation, and unexpired approval can mint
`DURABLE_CLAIM_ACQUIRED_EFFECT_MAY_PROCEED`.

## D-06: Generic BLOCKED is not terminal publication

A canonical terminal route must bind the exact durable claim and terminal
state plus the fixed remote ref/commit/tree/path/blob/content identities. A
generic blocked document reports
`DURABLE_TERMINAL_ROUTE_PUBLICATION_PENDING`.
