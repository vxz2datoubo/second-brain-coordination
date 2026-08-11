# Canonical W3 runtime audit

> `agent_id: CODEX`
> `canonical_main_reviewed: 6dbc83bdd1c42f9c78493ad93e01ba6dd6533eb3`

## Existing canonical capability

The Phase 3 integrated offline-memory package provides a research-only, candidate-only path: source manifest -> validation/replay -> `LearningPacket` -> SQLite `MemoryStore` -> `QueryPlan` -> `ContextBundle`. It already has deterministic packet identity, source references, relations, conflicts, UNKNOWN records, lexical/entity-like retrieval and secret-shaped value rejection. Its public delivery forbids raw source export and automatic authority write.

## Reuse boundary

This is the only identified local W3 runtime to extend. CLTM must add adapters/contracts to it, not copy its store, packet, query or bundle types. `MODULE_0020` is a separately owned derived normalization/graph projection and is REFERENCE_ONLY until QCLAW E48 R3 is independently accepted.

## Gaps that a later implementation route must close

| Area | Present now | CLTM extension required |
| --- | --- | --- |
| Conversation evidence | Generic source refs | `ConversationSourceManifest`, `ConversationEpisode`, turn references, coverage and privacy-minimized pointers. |
| Candidate memory | Candidate-only packets and atoms | Conversation-candidate adapter with deterministic duplicate identity and explicit speaker/claim role. |
| Temporal semantics | `updated_at` and revisions | Valid-time plus record-time, correction/supersession/revocation events and historical lookup. |
| Current recall | `QueryPlan` defaults include `superseded` | Current default must exclude superseded/revoked/stale; historical intent must be explicit. |
| Scope | One free-form `scope` field | Separate user, project, privacy and memory-type constraints. |
| Trust | Retrieval filters candidate access/visibility | Memory Trust Gate before bundle admission, including source role, temporal status, conflict, UNKNOWN and injection policy. |
| Hybrid retrieval | Lexical terms and relation expansion | Verify actual vector/graph availability/value; add only proven adapters. |
| Formal persistence | Explicitly denied | Remains locked; E66 is a reference control pattern only. |

## Negative findings

- The existing runtime is not proof that a ChatGPT account can be read in the background or that every response invokes recall.
- Existing `MemoryStore.update_atom` is an upsert and is not an acceptable correction model without a versioned extension.
- Existing Phase 3 success receipts are historical evidence, not current CLTM production readiness.
