# R163 A migration notes

## Authority and provenance

The legacy authority is canonical commit `027642a231e214f8649b273f44de65c82a4901f9`, specifically its `apps/cli/creativectl.py`, `creative_runtime/ledger.py`, and `creative_runtime/contracts.py`. PR #493 is consulted only under the registered `REFERENCE_ONLY_UNACCEPTED_CANDIDATE` source-selection record. Nothing in PR #493 is accepted by reuse.

## Genuine legacy format

Canonical S00-S06 stores `CreativeSession/v1` directly at workspace root `session.json`. Its initial state is `synthetic_archive / arrival` and its old legal vocabulary includes `listen`, `approach`, and `leave`. Fixtures under `tests/fixtures/r163/` are mechanically reconstructed with the canonical baseline event material and SHA-256 event-chain algorithm.

The multi-action fixture executes `listen -> approach -> leave`. It ends on legacy `courtyard` with Mira relationship `+1`, known fact `a witness is inside`, risk `+1`, and `meeting=offered`.

The resolution fixture executes `approach -> listen`. It ends on legacy `resolution` with Mira relationship `+2`, risk `-1`, and `arrival=announced`.

## Explicit mapping

- `arrival/listen` -> `archive_gate/echo` via `listen`
- `arrival/approach` -> `interior_archive/threshold` via `knock`
- `arrival/leave` -> `dawn_courtyard/return` via `defer`
- `echo/approach` -> `interior_archive/threshold` via `knock`
- `echo/leave` -> `dawn_courtyard/return` via `record`
- `threshold/listen` -> `interior_archive/accord` via `promise`, followed by an explicit terminal location patch to `dawn_courtyard/return` when the legacy terminal is `resolution`
- `threshold/leave` -> `dawn_courtyard/return` via `retreat`

Every old action must carry the exact canonical old `resulting_patch`; a correct action ID with a changed patch is rejected. Migration replays the old chain, applies the new graph transition, compares relationship / known-fact / risk / flag semantics after every action, and rebuilds a new v2 event hash chain. The receipt links every new event to its legacy event ID and records the source baseline and source-record digest.

## Fail-closed incompatibility

Unknown old action/beat pairs, noncanonical patches, invalid event hashes, malformed JSON, unsupported schemas, or graph mismatches do not produce a default v2 save. `terminal_loop()` checks root `session.json` before initializing a new `saves/default.json`, reports incompatibility to the user, and preserves the original legacy bytes. Successful migration also leaves the root legacy file byte-identical and writes the migrated copy separately.

## Idempotency

After a valid migrated `saves/default.json` exists, subsequent startup loads that v2 slot and does not migrate or rewrite the legacy source again.

## Still out of scope at A checkpoint

S08 per-event prefix timeline truth is intentionally deferred to B. Full final exact-head evidence and #453 handoff remain C/D work.
