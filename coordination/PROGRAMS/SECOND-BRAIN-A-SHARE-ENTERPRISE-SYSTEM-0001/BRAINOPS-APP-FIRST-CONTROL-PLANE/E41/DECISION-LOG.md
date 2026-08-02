# E41 Decision Log

## D-01: Durable claim authority is not local metadata

**Decision:** Use a revisioned, fixed-repository CAS gateway contract for
global authority. The local file gateway exists only as a synthetic
cross-process test double.

**Reason:** E40's local SQLite state can be replaced by a fresh process and
cannot prove a global one-shot consumption.

**Rejected:** Local SQLite as authority, process-memory locks, and owner
labels as a proxy for dispatch.

## D-02: A durable outcome dominates a stale route

**Decision:** Any persisted `CLAIMED` or terminal record blocks a route still
labelled `READY`. Canonical terminalization is verified only when a route
publisher provides the matching durable claim ID and final-state mapping.

**Reason:** `BLOCKED` alone lacks provenance and could be unrelated state.

## D-03: Invocation classification is evidence-specific

**Decision:** A claim without a receipt remains
`CONTROL_PLANE_CLAIM_ONLY`. A receipt must be correlated and durably attached
to the same claim before any App/CLI classification is allowed.

**Reason:** This prevents a selected owner, a database row, or a test label
from becoming a false execution assertion.

## D-04: Capability observations have no optimistic default

**Decision:** Missing capability evidence yields `UNKNOWN`; mismatched targets
yield `BLOCKED`.

**Reason:** E40's default `app_available=true` was an unsupported assumption.
