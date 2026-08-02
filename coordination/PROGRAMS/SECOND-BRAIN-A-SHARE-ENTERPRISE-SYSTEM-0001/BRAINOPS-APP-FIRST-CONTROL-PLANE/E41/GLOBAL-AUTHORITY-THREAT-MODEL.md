# E41 Global Authority Threat Model

## Assets and boundary

The protected asset is a single future one-shot authority identified by the
fixed repository, route ID/epoch, task, canary ID, and nonce. E41 itself
creates no real authority object, performs no App/CLI call, and reads no
credential.

## Threats and controls

| Threat | Control | Test evidence |
| --- | --- | --- |
| Fresh local state replays a prior authority | Authority key is stored through revisioned CAS, outside local metadata | restart and fresh-authority tests |
| Concurrent owners claim together | Atomic compare-and-set and a four-process race | exactly one `CLAIMED` result |
| Crash after claim | `CLAIMED` persists before any future effect; expiry becomes `RECOVERY_REQUIRED` | crash/recovery test |
| Duplicate callback overwrites identity | Invocation ID is durable and write-once | duplicate and competing-callback tests |
| Route remains stale `READY` | durable state blocks execution; terminal route needs exact binding | stale-ready and terminal-binding tests |
| Fabricated availability | no observation maps to `UNKNOWN`, not supported | preflight tests |
| Claim label becomes execution claim | receipt type and durable correlation are mandatory | claim-only and receipt tests |

## Residual unknowns

- A GitHub Contents/ref CAS implementation must later be reviewed for actual
  conditional-update behavior, permissions, rate limits, and failure recovery.
- A current Codex App session cannot establish that a new App run was
  dispatched. E41 has no runtime proof of either App automation or CLI use.
- Canonical route publication is owned by the route publisher; this branch
  only verifies a future structural binding.

## Rollback

No external durable object exists from E41. Repository rollback is a reverse
revert of the E41 substantive commit and its receipt. A future runtime must
write terminal reconciliation before deleting no authority state; deletion is
not a valid replay recovery path.
