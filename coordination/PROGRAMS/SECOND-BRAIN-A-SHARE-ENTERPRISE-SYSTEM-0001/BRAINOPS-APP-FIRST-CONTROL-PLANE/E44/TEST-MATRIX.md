# E44 Test Matrix

| Area | Evidence | Expected result |
| --- | --- | --- |
| Legacy capability | legacy verified observation | blocked as observational |
| Challenge ledger | fresh matching witness | one durable consumed decision |
| Challenge replay | new instance and spawned process | `ALREADY_CONSUMED` |
| Recovery authorization | bound claim, restart and spawned process | one durable consumption |
| Recovery substitution | different claim | `BINDING_MISMATCH` |
| Owner schemas | manual, automation, CLI | mutually exclusive fields and target/owner checks |
| Terminal truth | state, type, time, log and exit code | mismatch blocks reconciliation |
| Imported regression | E43 contracts | remains green under E44 gate |

The synthetic suite contains 83 tests. GitHub Actions runs the same suite on
Python 3.11 and 3.13 at the pull-request head.
