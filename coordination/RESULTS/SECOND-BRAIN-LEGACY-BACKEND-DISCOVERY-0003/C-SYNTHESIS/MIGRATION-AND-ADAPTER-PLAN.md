# Migration and Adapter Plan

- **agent_id:** CODEX
- **task_id:** SECOND-BRAIN-LEGACY-BACKEND-DISCOVERY-0003C
- **status:** planning only
- **scope:** legacy-backend reuse and migration design
- **non-goals:** service activation, port changes, data copy, database migration, credential access, Supabase creation, and trading execution

## Architectural Position

The target is a single governed knowledge-access contract, not a second replacement backend running beside the first.

- A future **private Git knowledge repository** is the canonical record.
- A future **Supabase** instance is a rebuildable serving projection.
- The legacy 8766 server is a temporary compatibility source behind a narrow wrapper.
- The stdio MCP is a temporary client adapter after tool-level gating.
- The 8799 bridge is migrated as an ingestion pattern, not retained as a durable authority.
- Both 8767 implementations remain preserved and unactivated until their ownership and port conflict are resolved.
- The trading domain is a tagged, research-only consumer of knowledge. It does not get execution authority through this integration.

## Target Data Flow

```text
legacy files and 8766 read surface
  -> source manifest (hashes, provenance, privacy class, retention)
  -> read-only export / quarantine
  -> normalized KnowledgePacket
  -> private Git canonical commit
  -> idempotent projector
  -> Supabase serving projection
  -> governed read MCP/API
  -> Codex / GPT / WorkBuddy / QCLAW / trading research clients
```

Every serving result must carry a source reference, version, content hash, retrieval route, conflict status, and capability classification. The client receives context, not a hidden direct write path.

## Capability-Adapter Matrix

| Existing component | Future adapter | Allowed operations | Explicitly prohibited |
|---|---|---|---|
| 8766 legacy HTTP | `LegacyReadAdapter` | approved read-only retrieval and typed health metadata | direct canonical writes, automatic sync, broad network exposure |
| stdio MCP | `GovernedMCPAdapter` | allow-listed read tools returning provenance envelopes | write tools, arbitrary local-file access, trade/account/action tools |
| 8799 local bridge | `IngestionRequestAdapter` | produce a durable candidate ingestion request | browser/session credential forwarding, in-memory-only final delivery |
| deep 8767 | none until review | source preservation only | startup, port registration, client routing |
| legacy HTTP MCP 8767 | none until review | source preservation only | startup, port registration, client routing |
| F:/ai history | `HistoricalSourceCatalog` | metadata/provenance catalog after approval | deletion, bulk copy, automatic import |

## Migration Phases

### M0: Approval and Contract Freeze

**Inputs:** this Phase C decision; Issue #21 target blueprint; data-owner approval.

**Work:**
1. Approve the target authority boundary and private-repository destination.
2. Freeze source-manifest and KnowledgePacket schemas.
3. Define privacy, licensing, retention, and quarantine labels.
4. Create a read-only capability allow-list for 8766 and stdio MCP.
5. Assign owners for the two 8767 implementations and the 8799 intake path.

**Acceptance:** signed decision record; no data or service state changes.

**Rollback:** revoke approval; no file/record changes exist.

### M1: Immutable Source Inventory

**Inputs:** approved source scope only.

**Work:**
1. Enumerate approved legacy objects without changing them.
2. Record file/database-object identity, SHA-256, size, timestamp, source component, privacy class, and retention classification.
3. Generate a manifest that distinguishes knowledge content, category/index material, audit events, logs, and historical archives.
4. Record unknown or inaccessible objects separately; never infer completeness.

**Acceptance:** deterministic repeat run yields the same manifest for unchanged sources; no source mtime/content changes.

**Rollback:** remove generated manifest from the new workspace; source remains untouched.

### M2: Read-only Export and Normalization Dry Run

**Inputs:** M1 manifest, frozen schemas, sanitized non-sensitive fixture set.

**Work:**
1. Export only approved fixture or locally retained test data to a quarantine directory.
2. Convert records to `SourceDocument`, `KnowledgePacket`, `KnowledgeAtom`, `RelationEdge`, and usage snapshot candidates.
3. Preserve original path, original hash, parser version, and transformation ID.
4. Report unparseable fields and semantic collisions rather than dropping them.

**Acceptance:** every normalized object links back to a source hash and parser version; no duplicates under the defined idempotency key.

**Rollback:** delete only quarantine-derived artifacts; do not alter sources.

### M3: Private Git Canonical Ingestion

**Inputs:** approved normalized packet; private repository; CI schema validation.

**Work:**
1. Commit packets and manifests to a dedicated branch in the private knowledge repository.
2. Review private-content classification before merge.
3. Retain legacy source pointers and version links.
4. Keep public coordination repository limited to schema, code, and sanitized reports.

**Acceptance:** CI validates schema/provenance; repeated packet import produces an existing-idempotency result; no private content appears in public repository.

**Rollback:** revert the private canonical commit or mark the packet quarantined; do not edit source history.

### M4: Idempotent Serving Projection

**Inputs:** approved private Git revision and projector implementation.

**Work:**
1. Project canonical knowledge to Supabase transactionally.
2. Store `git_commit_sha`, `git_path`, schema/protocol version, content hash, import run, and idempotency key.
3. Index structured, full-text, relation, and embedding records without overwriting older knowledge versions.
4. On failure, leave the prior projection published and record an import failure event.

**Acceptance:** empty projection can be rebuilt from a known Git revision; duplicate projection run makes no duplicate atoms/edges.

**Rollback:** repoint serving projection to the prior successful Git revision; rebuild if necessary.

### M5: Governed Read Adapters

**Inputs:** M4 projection; read contract; security review.

**Work:**
1. Build a `LegacyReadAdapter` only for validated 8766 read endpoints.
2. Gate stdio MCP tools through the same policy and response envelope.
3. Implement private-Git retrieval as a documented degraded read path.
4. Return explicit `source_route`, `freshness`, `provenance`, `conflicts`, and `capability_level`.

**Acceptance:** a test suite proves that unapproved tools and action-like parameters are rejected; Git and projection routes agree on a fixed retrieval corpus.

**Rollback:** disable new adapter routes using feature flags; preserve legacy process and clients.

### M6: Controlled Cutover Review

**Inputs:** dual-read comparison results, privacy review, user approval.

**Work:**
1. Compare legacy 8766 read results against canonical/projection results for a fixed set.
2. Evaluate coverage gaps, semantic differences, duplicate aliases, and stale entries.
3. Retire only a route explicitly approved after equivalence and rollback tests.
4. Keep historical provenance even if a legacy process is later retired.

**Acceptance:** all required test cases pass; error budget and downgrade route documented; user approves cutover.

**Rollback:** restore the prior route selection; rebuild serving projection from prior canonical commit. Do not mutate legacy stores.

## 8767 Resolution Protocol

The shared static port is a blocking architectural ambiguity, not an invitation to start both services.

1. Identify the intended owner and any active user workflow for each source.
2. Produce separate static capability maps for `deep_server.py` and `mcp/brain_server.py`.
3. Allocate a unique non-conflicting port only after a written approval and service-registry change request.
4. Run an isolated read-only probe only after the owner confirms it is safe.
5. Decide then whether either becomes `WRAP`, `MIGRATE`, `ARCHIVE`, or `DEPRECATE`.
6. Until then, keep both `UNKNOWN` and do not route clients to 8767.

## Security and Governance

- Do not use legacy live data as the new canonical record without hash and provenance.
- Do not expose 8766 beyond its approved local scope until bind/auth/firewall review passes.
- Do not let MCP tool names imply authority. Every tool gets an operation class: `read`, `request_write`, `admin`, or `prohibited`.
- `request_write` creates a reviewable candidate only. It cannot update canonical knowledge directly.
- All trading-domain context remains `research_only`; no adapter may invoke brokerage, account, portfolio, order, cancel, or execution functions.
- Do not copy browser states, tokens, cookies, credential files, private source bodies, or proprietary market data into the public coordination repository.

## Required Future Tests

1. Manifest determinism and no-source-mutation test.
2. Hash-to-normalized-object provenance test.
3. Idempotent packet and projector test.
4. Legacy read adapter allow-list/deny-list test.
5. MCP initialize and read-tool response-envelope test.
6. Cross-route retrieval consistency test.
7. Quarantine and conflict-version preservation test.
8. Supabase rebuild-from-Git test.
9. Public-repository secret/private-content scan.
10. Trading no-action regression test.

## Decisions Deferred

- Whether 8766 is restricted to loopback, placed behind a reverse proxy, or replaced after migration.
- Whether either 8767 implementation supplies unique reusable behavior.
- Which legacy SQLite/JSON/JSONL collections pass privacy and data-quality review.
- Any Supabase project, credential, or private-repository creation.
- Any active client cutover.
