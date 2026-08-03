# E37 Decision Log

## D-001: Treat E36 as an immutable input, not an active route

E37 imports the accepted control-plane implementation from PR #113 without
restoring its route files. E36 remains historical evidence and cannot be
modified by this task.

## D-002: Close proof gaps before any execution discussion

The authorization nonce, immutable approval provenance, and two-file remote
route proof are all required for a reservation. This task contains no executor
and cannot run a canary.

## D-003: Use read-only proof vocabulary truthfully

Only `READ_ONLY_FETCH_VERIFIED` can pass the approval gate. No webhook or
signature-verification claim is made because no signed webhook path exists.
