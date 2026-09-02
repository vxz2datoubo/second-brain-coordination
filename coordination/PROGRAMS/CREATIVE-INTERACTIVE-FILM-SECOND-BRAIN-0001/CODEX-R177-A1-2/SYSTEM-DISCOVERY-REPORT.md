# R177 system discovery and opportunity report

`agent_id: CODEX`

The persistent catalog is a content authority only. Keeping it separate from
player state prevents a shared script update from silently rewriting individual
campaign facts. The same separation also lets many players reuse one immutable
script payload while storing only their own event-ledger deltas later.

The strongest integrity boundary is not filesystem read-only metadata. It is
revalidation at every restart and DirectorBrief/v2 consumption: exact catalog,
package, revision, style, asset-manifest and source-provenance hashes must still
agree. This makes copied, stale and relabeled bindings observable.

Future expansion should proceed in this order:

1. Satisfy the R176 independent-acceptance and canonicalization dependency.
2. Integrate the content binding into the full DirectorBrief/v2 compiler without
   granting the director campaign or session write authority.
3. Let WorkBuddy validate filesystem-specific atomicity and stale-lock operation
   on the intended local storage hardware.
4. Set catalog size and performance limits only after target-hardware measurements.

No external model, user asset, platform comment, credential, deployment or
canonical knowledge path was needed or discovered in this slice.
