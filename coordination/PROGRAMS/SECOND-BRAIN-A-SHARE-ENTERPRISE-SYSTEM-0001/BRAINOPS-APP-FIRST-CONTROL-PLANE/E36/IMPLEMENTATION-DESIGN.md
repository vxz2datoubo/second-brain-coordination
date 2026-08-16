# E36 Observable One-shot Canary Design

## Scope

E36 hardens the E35 read-only control plane. It does not contain an executor,
does not invoke a desktop automation API or CLI, and cannot create a review,
commit, pull request, service, network listener, or trade.

## Corrections over E35

| Concern | E36 behavior |
| --- | --- |
| Payload identity | `CanaryEvent.payload_hash` is exactly 64 lowercase hexadecimal characters. |
| Approval | `BoundCanaryApproval` binds canary ID, task ID, epoch, scope, expiry, nonce and public approval reference. |
| Manual owner | `MANUAL_APP` is not an automatic owner and cannot emit `WOULD_DISPATCH`. |
| Idempotency | Event ID and idempotency key are persisted with unique constraints. A repeated event is `DUPLICATE_SUPPRESSED`. |
| Lease recovery | Explicit caller time expires stale leases; fence generations may only increase. |
| State proof | One transaction records the event and the hashes of both active route-state sources. |
| Sensitive values | Key-name and value-pattern redaction occur before metadata persistence. |

## Exact canary boundary

Only `BRAINOPS-E36-CANARY-0001` can become shadow-eligible. A canary can only
produce `CANARY_ELIGIBLE_SHADOW_ONLY`; there is deliberately no dispatch
function. The current route declares `automatic_dispatch_allowed: false` and
no bound approval exists, so an actual canary is not run.

## Route-state evidence

`RouteStateEvidence` contains a `RouteRef` plus SHA256 values for
`ACTIVE-CODEX-TASK` and central coordination state. `MetadataStore` writes this
pair only in the same transaction that reserves a new canary event. A duplicate
rolls back the whole attempted transaction, so it cannot add a second state
record, receipt, commit, or external action.

## Supported-surface distinction

The locally observed Codex CLI exposes a noninteractive command surface, and
the host exposes automation management. Those are capability observations,
not execution authorization. E36 retains `BLOCKED_APPROVAL_NOT_BOUND` until an
independent approval record supplies all exact bindings from the E36 template.
