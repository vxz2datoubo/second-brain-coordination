# R165 System Discovery and Opportunity Report

`agent_id: CODEX`

## Discovery

The old ledger treated an append-only event hash as sufficient for replaying a
generic state patch. A hash is an integrity proof, not a capability. This
distinction applies beyond this game: any replayable event system should bind
state-changing authority to a constrained transition or mechanically validated
source artifact rather than merely accepting a recomputed digest.

## Reusable opportunity

The `SceneGraph` plus `SaveStore` pattern is intentionally local and offline.
It can be proposed later as a reusable “integrity is not authority” guard for
other creative runtimes, but this task does not promote it to canonical
knowledge or alter another system record source.

## Risk and ownership

Future reuse requires a separate route, a domain owner, and independent tests.
No cross-project code or knowledge write is made by this report.
