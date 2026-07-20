# Legacy Backend Discovery: Phase C Synthesis and Reuse Decision

- **agent_id:** CODEX
- **task_id:** SECOND-BRAIN-LEGACY-BACKEND-DISCOVERY-0003C
- **parent_issue:** #22
- **dependencies:** #24 / Phase A accepted at `48cc8dbea8283275bb24e0bb6e62889cea2fbb18`; #25 / Phase B accepted at `67ab449473d48aad7a7ba79646dc4b262a4d6689`
- **mode:** project_plan
- **execution boundary:** read-only analysis and planning; research_only / NO_TRADE
- **evidence cutoff:** 2026-07-20T10:30:00+08:00 for runtime facts
- **no service lifecycle or data migration was performed in Phase C**

## Decision Summary

The present operational fact and the future architectural authority must be separated.

1. `SB-HTTP-8766` is the only backend confirmed listening at the Phase B check time. It should be **WRAP**, not promoted to a new canonical source. It remains a legacy operational store and a temporary, governed read source.
2. Both implementations declared on `8767` are **UNKNOWN**. Their absence at one check time is not deprecation evidence. They must remain preserved but disabled until an explicitly approved isolated capability review resolves the port collision and ownership.
3. `SB-MCP-STDIO` should be **WRAP** as the transition-facing MCP adapter, after a future read-only handshake and action-gate review. It is not a store of record.
4. `SB-CHATGPT-BRIDGE-8799` should be **MIGRATE** by preserving the integration intent while replacing the ephemeral/local bridge path with the governed ingestion contract. Do not reactivate it as a default public-facing service.
5. `F:/ai` is **ARCHIVE** as a historical evidence root. It is not an active backend candidate, and it must not be deleted or silently imported.

No candidate is classified `REUSE_AS_IS` or `DEPRECATE`. The evidence does not justify either conclusion.

## Evidence and Authority Boundary

| Layer | Current evidence | Phase C decision |
|---|---|---|
| Legacy live service | `server.py` on `0.0.0.0:8766` answered the Phase B search endpoint; it uses `F:/aidanao/data` | Treat as a bounded compatibility source. Do not grant it authority to overwrite the target knowledge system. |
| Legacy stores | JSON graph/category files, `super_brain_v01.sqlite`, and JSONL audit path are statically/runtime located but content quality and completeness were not assessed | Treat as candidate import sources requiring immutable manifests and approval. |
| Future authority | Issue #21 blueprint designates a private GitHub knowledge repository as canonical and Supabase as a rebuildable serving projection | Preserve this target boundary. Legacy stores are inputs, not competing authorities. |
| Client access | stdio MCP forwards selected reads to 8766; 8799 forwards ingestion to 8766 | Clients must converge on one governed read contract and one approved ingestion pipeline. |
| Trading domain | Mother-system bulletin shows research-only, no-trade governance; legacy backend discovery did not verify any trade execution capability | Trading knowledge may be retrieved as tagged context only. No MCP or adapter path may expose brokerage, account, execution, or autonomous action tools. |

## Candidate Decisions

### SB-HTTP-8766: WRAP

**Evidence:** Phase A ties `F:/aidanao/server.py`, the service registry, and MCP configuration to 8766. Phase B verified a listening Python process, root UI, `POST /api/retrieve/search`, and data directory candidates. It is the sole active candidate at the recorded check time.

**Counterevidence and limits:** `/health` returned error HTML rather than a dedicated health document; `/api/digest/text` was 404; no authentication, firewall, write-path, data integrity, storage contents, or full API contract was verified. The bind address is `0.0.0.0`, so LAN exposure is possible but unverified.

**Dependencies:** explicit owner approval; security review; frozen source manifest; read-only capability contract; private canonical repository; later migration test data.

**Risk:** legacy mutable APIs or an unauthenticated bind could bypass the target governance model; direct client dependence would create dual authority.

**Rollback:** keep the existing process and stores untouched. The future wrapper is opt-in and feature-flagged; disabling it restores direct legacy access without data mutation.

### SB-DEEP-HTTP-8767: UNKNOWN

**Evidence:** `F:/aidanao/deep_server.py` declares a separate HTTP service with deep-thinking, episodic-memory, and continual-learning concepts.

**Counterevidence and limits:** it was not listening in Phase B; its exact data root and operational capability are unverified; it conflicts statically with the legacy HTTP MCP service on port 8767.

**Dependencies:** user-approved owner/maintenance decision; unique port or isolated non-production test environment; read-only capability inventory; source-to-data dependency mapping.

**Risk:** starting it before ownership and port reconciliation could conflict with another service or produce a second stateful memory authority.

**Rollback:** no activation or source change is planned. Preserve source and metadata; remove only future experimental wrapper configuration if rejected.

### SB-LEGACY-HTTP-MCP-8767: UNKNOWN

**Evidence:** `F:/aidanao/mcp/brain_server.py` statically exposes a legacy document bridge over HTTP and references `second-brain` and `core/logs`.

**Counterevidence and limits:** it was not listening in Phase B, has no verified endpoint contract, and shares 8767 with the deep service. The newer stdio MCP already exists as a potential interface direction, but no functional equivalence test was performed.

**Dependencies:** port/ownership decision; read-only endpoint inventory; data provenance inspection; comparison with stdio MCP.

**Risk:** the bridge could duplicate or diverge from current legacy knowledge, and moving it prematurely could discard document-specific behavior.

**Rollback:** preserve as a non-running candidate. Any future adapter is removable independently and must never overwrite `second-brain` documents.

### SB-MCP-STDIO: WRAP

**Evidence:** `mcp/brain_bridge.py` is a stdio JSON-RPC MCP adapter with read-oriented tools and resources; it is configured to use 8766 and has a local `SuperBrainV01` fallback.

**Counterevidence and limits:** a live MCP handshake was deliberately not run; the fallback path and all tools have not been safety-reviewed; it is not an independent store.

**Dependencies:** future MCP initialize/list-tools probe using a strict read-only allow-list; tool-by-tool authorization classification; provenance-bearing response envelope; target read contract.

**Risk:** a bridge may expose a legacy data model or fallback behavior inconsistent with canonical versioning. Tool expansion without approval could create an action path.

**Rollback:** retain the current file untouched. Any new wrapper configuration is separate and removable; clients can fall back to the private GitHub read channel while the MCP route is unavailable.

### SB-CHATGPT-BRIDGE-8799: MIGRATE

**Evidence:** `chatgpt_bridge/bridge.py` and its design document describe a FastAPI local bridge with in-memory queues forwarding ingestion to 8766.

**Counterevidence and limits:** not listening in Phase B; its browser/session integration and delivery guarantees were not verified; an in-memory queue cannot be the durable ingestion record.

**Dependencies:** canonical KnowledgePacket schema; authenticated ingestion worker; idempotency key; failure queue; explicit user approval before replacing any existing workflow.

**Risk:** reactivating it as-is could leak browser/session context, lose in-flight input, or create a second direct-write route to the legacy store.

**Rollback:** retain the historical implementation. The replacement is a new, gated adapter; disabling it leaves no changed legacy state.

### F:/ai Historical Root: ARCHIVE

**Evidence:** Phase B confirmed the directory and historical coordination/QClaw/TDX artifacts. No active candidate service ran from it. Static `core/qclaw.py` references are path-drift evidence.

**Counterevidence and limits:** some contents may retain useful project or data lineage; contents were not classified or copied.

**Dependencies:** owner approval, data sensitivity/licensing classification, and content hashes before any selective import.

**Risk:** treating it as disposable could lose provenance; treating it as live could reintroduce stale paths and duplicate stores.

**Rollback:** no movement, deletion, or import is planned. Any later import is content-addressed and reversible by removing the new target version only.

## Data Location and Reuse Map

| Legacy location | Observed role | Target handling |
|---|---|---|
| `F:/aidanao/data/knowledge-graph.json` | confirmed existence; legacy graph candidate | Preserve in place; read-only snapshot; normalize to versioned atoms/edges only after approval. |
| `F:/aidanao/data/category-index.json` | confirmed existence; category/index candidate | Preserve in place; map to aliases/categories as a derived projection. |
| `F:/aidanao/data/super_brain_v01.sqlite` | candidate SQLite store; not opened in A/B | Inventory schema and hash in a future approved read-only migration task; do not assume it is canonical. |
| `F:/aidanao/data/audit/events.jsonl` | static audit path | Import as immutable usage/audit snapshots, never as knowledge-authority edits. |
| `F:/aidanao/second-brain` and `core/logs` | document/log roots referenced by old 8767 bridge | Preserve; classify documents and logs separately; logs are not automatically knowledge packets. |
| `F:/ai` | historical root | Archive/provenance only pending approval. |

## Target Integration

The Issue #21 target remains: **private GitHub knowledge repository as canonical source; Supabase as rebuildable serving projection; a single governed read contract for AI clients.**

Legacy content enters only through a versioned ingestion path:

`legacy source -> immutable manifest + hashes -> quarantine/normalization -> KnowledgePacket -> private Git canonical commit -> idempotent projector -> Supabase serving projection -> governed read MCP/API`

The resulting ContextBundle must include provenance, source version, conflict state, temporal scope, and retrieval route. A trading-domain tag is permitted, but it remains research-only and cannot authorize trade execution.

## Approval Gates and Unknowns

1. **User approval:** whether legacy 8766 may be wrapped for future read-only access; whether any local historical data may leave the machine for a private repository or cloud projection.
2. **Security approval:** LAN exposure and auth posture of 8766 before any broad client registration.
3. **Owner/maintainer decision:** intended future of each 8767 source before activation, port reassignment, or archival labeling beyond this evidence-based UNKNOWN state.
4. **Runtime verification:** stdio MCP handshake and tool allow-list review; this was intentionally not performed.
5. **Data governance:** schema, privacy, licensing, retention, and hash inventory for SQLite/JSON/JSONL/legacy documents.
6. **No-trade gate:** any trading-domain materials remain read-only research data. No broker, account, execution, or action command is in scope.

## Next Approved-Task Shape

Create one bounded follow-up task: **LEGACY-8766-READONLY-CAPABILITY-AND-EXPORT-PLAN**. It should produce only a capability contract, security threat model, source manifest schema, and a dry-run export test design. It must not start/stop services, read credentials, copy private data to GitHub, or modify legacy storage.

## Validation Performed

- Confirmed the remote Issue #26 status and its sole Phase C scope.
- Read Phase A static evidence and candidate allow-list from accepted commit `48cc8d...`.
- Read Phase B runtime report and endpoint status from accepted commit `67ab449...`.
- Read Issue #21 body/comments and its GitHub + Supabase enterprise blueprint.
- Read the local mother-system bulletin, service registry, and root collaboration rules for boundary alignment.
- No service, port, API, MCP, data-store, credential, trade, or migration operation was performed by Phase C.

## Outcome

**SUCCESS_WITH_FINDINGS**: the required evidence synthesis and planning decision are complete. The main findings are the active-but-not-canonical 8766 backend, the unresolved 8767 collision, the safe transitional role for stdio MCP, and the requirement to preserve historical paths without importing or deleting them.
