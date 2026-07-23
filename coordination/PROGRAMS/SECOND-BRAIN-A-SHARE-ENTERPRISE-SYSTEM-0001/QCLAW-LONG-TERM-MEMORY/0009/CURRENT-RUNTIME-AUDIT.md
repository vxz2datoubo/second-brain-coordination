# ============================================================================
# CURRENT RUNTIME AUDIT
# Task: QCLAW-LONG-TERM-MEMORY-PALACE-HYBRID-RETRIEVAL-0009
# Issue: #60
# Version: 1.0.0-M0
# ============================================================================

## Purpose

This document audits all existing infrastructure that 0009 depends on, proves
non-duplication, defines file ownership boundaries, and identifies what each
existing system provides — and does NOT provide — so that 0009 builds only
the missing pieces.

---

## 1. PR #57 — Phase 3 Offline Memory Runtime

### 1.1 What Exists

PR #57 (`feat/codex-pr-57-canonical-runtime`, merge `473d0ec`) provides the
canonical knowledge runtime. Seven components:

| Component | File | Purpose | Consumed by 0009 |
|---|---|---|---|
| **Store** | `lib/runtime/store.rb` | Persistent knowledge storage with CRUD | READ-ONLY: `store.read`, `store.list` |
| **Fusion** | `lib/runtime/fusion.rb` | Dedup, merge, reconcile conflicting facts | NOT consumed (fusion is pre-ingestion) |
| **Snapshot** | `lib/runtime/snapshot.rb` | Point-in-time snapshots, diff, rollback | NOT consumed (snapshots are runtime-internal) |
| **Retrieval** | `lib/runtime/retrieval.rb` | Semantic, vector, hybrid search | ONE of 9 retrievers in 0009's hybrid system |
| **QueryPlan** | `lib/runtime/query_plan.rb` | Query decomposition and optimization | NOT consumed (0009 has its own query parser) |
| **ContextBundle** | `lib/runtime/context_bundle.rb` | Knowledge fragment assembly | NOT consumed (0009 builds AnswerEvidenceBundle) |
| **Gateway** | `lib/runtime/gateway.rb` | HTTP/gRPC entry point, auth, routing | Bridge via Issue #38, not direct |

### 1.2 Interfaces Provided to 0009

```
Store.read(chunk_id)      → chunk content (atom data)
Store.list(filters)       → filtered atom listing
Gateway.query(query_spec) → raw retrieval results (one of 9 recall sources)
```

### 1.3 What PR #57 Does NOT Provide

PR #57 has NO concept of:

- **Memory layers** (working, episodic, semantic, procedural, etc.) — all knowledge is flat in the store
- **Lifecycle management** beyond simple read/write — no state machine, no decay
- **Memory palace navigation** — no spatial or topic-based navigation index
- **Intelligent reranking** — uses cosine similarity only, no multi-axis reranking
- **Conflict surfacing** — stores conflicts but doesn't proactively surface them in queries
- **Unknown gap-filling** — no mechanism to say "here's what we DON'T know about this query"
- **AnswerEvidenceBundle** — produces ContextBundle (fragments), not evidence with citations/confidence
- **Content-index separation** — no rebuildable indexes from canonical source
- **Embedding governance** — uses embeddings but no version tracking, rebuild policies
- **Source/auth-aware filtering** — no filtering by provenance, authority, or scope

**These are exactly the gaps 0009 fills.**

---

## 2. Issue #38 — Knowledge Gateway

### 2.1 Status

Issue #38 defines the Knowledge Gateway as Codex Phase 4 work. It has 6 work packages:

| Work Package | Owner | Status | Consumed by 0009 |
|---|---|---|---|
| C1: KnowledgeAccessDecision + RevocationReceipt | Codex | Pending | M5: auth_filter.rb |
| C2: Gateway API surface | Codex | Pending | M5: gateway/bridge.rb |
| C3: Gateway health + monitoring | Codex | Pending | NOT consumed |
| C4: AnswerEvidenceBundle spec | Codex | Pending | M2: answer_bundle.rb (CRITICAL) |
| C5: Feedback learning runtime | Codex | Pending | NOT consumed (non-goal) |
| C6: Scale/stress test harness | Codex | Pending | NOT consumed (non-goal) |

### 2.2 Interfaces 0009 Needs

From Issue #38, 0009 requires:

1. **AnswerEvidenceBundle contract (C4)** — This is the output format for all 0009 queries.
   Without it, 0009 cannot finalize the retrieval API. 0009 will define a provisional
   contract in M2 that conforms to Issue #38's expected shape, pending C4 specification.

2. **KnowledgeAccessDecision (C1)** — Used by `filters/auth_filter.rb` to determine
   which atoms a given user/context can access. Without C1, auth filter defaults
   to permissive (all atoms accessible).

3. **Gateway API surface (C2)** — `gateway/bridge.rb` in M5 sends queries through
   the Knowledge Gateway. Without C2, bridge operates in standalone mode.

### 2.3 Gaps and Mitigations

| Gap | Impact on 0009 | Mitigation |
|---|---|---|
| C4 spec not finalized | M2 answer_bundle cannot conform | 0009 defines provisional schema; conforms when C4 is ready |
| C1 not implemented | M5 auth filter has no backend | Auth filter is pluggable; defaults to permissive |
| C2 not implemented | M5 gateway bridge cannot connect | Bridge has standalone fallback; tests use mock |

---

## 3. Issue #59 — Atomization Architecture (0008)

### 3.1 Status

Issue #59 / Task 0008 is IN PROGRESS. It provides the knowledge atomization
engine that produces KnowledgeAtoms, KnowledgeRelations, KnowledgeConflicts,
KnowledgeUnknowns, and LearningPackets.

### 3.2 Available Artifacts

| Artifact | Path | What It Provides | Consumed by 0009 |
|---|---|---|---|
| **KNOWLEDGE-ATOM.schema.json** | 0008/schemas/ | Core atom: 32 types, full metadata, deterministic ID | M1: layer classification input |
| **KNOWLEDGE-RELATION.schema.json** | 0008/schemas/ | 30 relation types, bidirectional | M2: relation_retriever, M3: relation_graph |
| **KNOWLEDGE-CONFLICT.schema.json** | 0008/schemas/ | 12 conflict types, resolution tracking | M1: conflict_and_unknown_memory |
| **KNOWLEDGE-UNKNOWN.schema.json** | 0008/schemas/ | 15 unknown types, verification paths | M1: conflict_and_unknown_memory |
| **KNOWLEDGE-SKILL.schema.json** | 0008/schemas/ | Procedural knowledge | M1: procedural_memory |
| **KNOWLEDGE-STRUCTURE.schema.json** | 0008/schemas/ | Hierarchical grouping | M3: topic_tree |
| **LEARNING-PACKET.schema.json** | 0008/schemas/ | Canonical output format | M1: ingestion pipeline |
| **ATOM-TYPE-TAXONOMY.yaml** | 0008/ | 32 atom types with definitions | M1: layer classification rules |
| **PIPELINE.yaml** | 0008/ | 8-stage processing pipeline | M1: understanding ingestion flow |

### 3.3 What 0008 Does NOT Provide

Issue #59 provides **atoms, relations, conflicts, unknowns, and packets** — the
*building blocks* of knowledge. It does NOT provide:

- **Memory organization** — atoms are flat; no classification into cognitive layers
- **Lifecycle management** — atoms have `knowledge_status` field but no state machine engine
- **Memory palace navigation** — no index for traversing knowledge space
- **Hybrid retrieval** — atoms are queryable via raw search, not intelligent multi-recall
- **Reranking** — atoms have confidence but no ranking across 13 axes
- **AnswerEvidenceBundle** — packets are raw data, not query-ready evidence
- **Decay and forgetting** — atoms don't decay; they're static unless superseded
- **Embedding governance** — no index rebuild, version tracking, similarity policies

**0009 takes Issue #59's atoms and builds memory on top of them.**

---

## 4. Non-Duplication Matrix

### 4.1 M1 — Memory Layers vs. Existing Infrastructure

| M1 Deliverable | PR #57 Overlap Check | Issue #59 Overlap Check | Verdict |
|---|---|---|---|
| `layers/working_memory.rb` | PR #57 has no working memory concept | 0008 has no session-scoped memory | ✅ NO DUPLICATION |
| `layers/episodic_memory.rb` | PR #57 has flat store, no event taxonomy | 0008 has atoms but no temporal layer | ✅ NO DUPLICATION |
| `layers/semantic_memory.rb` | PR #57 has store but no semantic layer | 0008 has atoms but no conceptual layer | ✅ NO DUPLICATION |
| `layers/procedural_memory.rb` | PR #57 has no skill/method taxonomy | 0008 has SKILL type but no layer | ✅ NO DUPLICATION |
| `layers/autobiographical_user_memory.rb` | PR #57 has no user memory concept | 0008 has USER_PREFERENCE type but no layer | ✅ NO DUPLICATION |
| `layers/project_memory.rb` | PR #57 has no project scoping | 0008 has PROJECT_REQUIREMENT type but no layer | ✅ NO DUPLICATION |
| `layers/source_memory.rb` | PR #57 has no source tracking | 0008 has source manifest but no indexed layer | ✅ NO DUPLICATION |
| `layers/conflict_and_unknown_memory.rb` | PR #57 has no gap surfacing | 0008 has conflicts/unknowns but no retrieval layer | ✅ NO DUPLICATION |
| `layers/meta_memory.rb` | PR #57 has no memory-about-memory | 0008 has no statistics/health layer | ✅ NO DUPLICATION |
| `lifecycle/state_machine.rb` | PR #57 has no state machine | 0008 has `knowledge_status` field only | ✅ NO DUPLICATION |

### 4.2 M2 — Hybrid Retrieval vs. Existing Infrastructure

| M2 Deliverable | PR #57 Overlap Check | Issue #59 Overlap Check | Verdict |
|---|---|---|---|
| `query_parser.rb` | PR #57 has QueryPlan but for SQL-like queries | 0008 has no query parsing | ✅ NO DUPLICATION — 0009 parses NL intent |
| `dispatcher.rb` | PR #57 has no parallel recall dispatch | 0008 has no dispatch | ✅ NO DUPLICATION |
| 9 retrievers | PR #57 has ONE retrieval engine (cosine) | 0008 has no retrieval | ✅ NO DUPLICATION — PR #57 retrieval is ONE source |
| `dedup_merge.rb` | PR #57 fusion merges atoms, not recall results | 0008 has no dedup | ✅ NO DUPLICATION — 0009 merges recall RESULTS |
| `relation_expander.rb` | PR #57 has no relation traversal | 0008 has relations but no expander | ✅ NO DUPLICATION |
| `conflict_gap_filler.rb` | PR #57 has no gap filling | 0008 has conflicts/unknowns but no filler | ✅ NO DUPLICATION |
| `reranker.rb` | PR #57 uses cosine similarity only | 0008 has no reranking | ✅ NO DUPLICATION — 13-axis vs. 1-axis |
| `answer_bundle.rb` | PR #57 has ContextBundle (fragments) | 0008 has no bundle assembly | ✅ NO DUPLICATION — EvidenceBundle vs. FragmentBundle |

### 4.3 M3 — Memory Palace vs. Existing Infrastructure

| M3 Deliverable | PR #57 Overlap Check | Issue #59 Overlap Check | Verdict |
|---|---|---|---|
| `spatial_index.rb` | PR #57 has no spatial memory concept | 0008 has no navigation index | ✅ NO DUPLICATION |
| `topic_tree.rb` | PR #57 has no topic hierarchy | 0008 has no topic decomposition | ✅ NO DUPLICATION |
| `importance_graph.rb` | PR #57 has no importance scoring | 0008 has no PageRank-style graph | ✅ NO DUPLICATION |
| `relation_graph.rb` | PR #57 has no relation graph | 0008 has relations but no graph | ✅ NO DUPLICATION |
| `decay_scheduler.rb` | PR #57 has no decay/forgetting | 0008 has no temporal decay | ✅ NO DUPLICATION |
| `palace.rb` | PR #57 has no palace concept | 0008 has no palace | ✅ NO DUPLICATION |

### 4.4 M4 — Embedding Governance vs. Existing Infrastructure

| M4 Deliverable | PR #57 Overlap Check | Issue #59 Overlap Check | Verdict |
|---|---|---|---|
| `governance.rb` | PR #57 uses embeddings but no governance | 0008 has no embedding policies | ✅ NO DUPLICATION |
| `index_manager.rb` | PR #57 has index but no rebuild management | 0008 has no index | ✅ NO DUPLICATION — 0009 indexes memory layers |
| `model_registry.rb` | PR #57 has no model pluggability | 0008 has no embedding model | ✅ NO DUPLICATION |
| `similarity_policy.rb` | PR #57 has threshold but no policy framework | 0008 has no similarity policy | ✅ NO DUPLICATION |
| `rebuild_verification.rb` | PR #57 has no rebuild verification | 0008 has no rebuild verification | ✅ NO DUPLICATION |

### 4.5 M5 — Integration vs. Existing Infrastructure

| M5 Deliverable | PR #57 Overlap Check | Issue #38 Overlap Check | Verdict |
|---|---|---|---|
| `memory_api.rb` | PR #57 has gateway but different API | Issue #38 gateway is different surface | ✅ NO DUPLICATION — 0009 API wraps memory system |
| `query_api.rb` | PR #57 has query but different format | Issue #38 has query but different contract | ✅ NO DUPLICATION — 0009 uses AnswerEvidenceBundle |
| `ingestion_api.rb` | PR #57 has ingestion via gateway | Issue #38 has no ingestion | ✅ NO DUPLICATION — 0009 ingests LearningPackets |
| `admin_api.rb` | PR #57 has no admin API | Issue #38 has no admin API | ✅ NO DUPLICATION |
| `gateway/bridge.rb` | PR #57 gateway is different | Issue #38 gateway is different | ✅ NO DUPLICATION — bridge, not reimplementation |
| Filters (`source`, `auth`, `scope`) | PR #57 has tenant filter only | Issue #38 has access decision but not filters | ✅ NO DUPLICATION |

---

## 5. File Ownership Boundaries

### 5.1 PR #57 (Codex) — ABSOLUTE BOUNDARY

```
lib/runtime/          ← Codex owns ALL files
├── store.rb          ← 0009: READ ONLY
├── fusion.rb         ← 0009: DO NOT TOUCH
├── snapshot.rb       ← 0009: DO NOT TOUCH
├── retrieval.rb      ← 0009: CONSUME via gateway
├── query_plan.rb     ← 0009: DO NOT TOUCH
├── context_bundle.rb ← 0009: DO NOT TOUCH
└── gateway.rb        ← 0009: CONSUME via HTTP/gRPC
```

### 5.2 Issue #59 / 0008 (QCLAW Atomization) — READ ONLY for 0009

```
coordination/PROGRAMS/.../QCLAW-KNOWLEDGE-ATOMIZATION/0008/
├── schemas/                     ← 0009: READ schemas for interface consumption
│   ├── KNOWLEDGE-ATOM.schema.json
│   ├── KNOWLEDGE-RELATION.schema.json
│   ├── KNOWLEDGE-CONFLICT.schema.json
│   ├── KNOWLEDGE-UNKNOWN.schema.json
│   ├── KNOWLEDGE-SKILL.schema.json
│   ├── KNOWLEDGE-STRUCTURE.schema.json
│   ├── LEARNING-PACKET.schema.json
│   └── ...
├── learning-packets/            ← 0009: READ packets for ingestion
├── ARCHITECTURE.md              ← 0009: REFERENCE only
├── ATOM-TYPE-TAXONOMY.yaml      ← 0009: CONSUME for layer classification rules
└── ... (rest of 0008 owned by 0008)
```

### 5.3 Issue #38 (Codex Knowledge Gateway) — CONSUME via API

```
coordination/PROGRAMS/.../PHASE-4-KNOWLEDGE-EVALUATION/
├── CANONICAL-RUNTIME-BOUNDARY.md ← 0009: RESPECT boundary
└── ... (rest owned by 0007/0008/Codex)
```

### 5.4 THIS TASK 0009 (QCLAW Memory) — FULL OWNERSHIP

```
coordination/PROGRAMS/.../QCLAW-LONG-TERM-MEMORY/0009/
├── PROJECT-PLAN.md              ← M0 deliverable
├── CURRENT-RUNTIME-AUDIT.md     ← M0 deliverable (this file)
├── LONG-TERM-MEMORY-ARCHITECTURE.md ← M0 deliverable
├── MEMORY-LAYER-TAXONOMY.yaml   ← M0 deliverable
├── MEMORY-LIFECYCLE.schema.json ← M0 deliverable
├── HYBRID-RETRIEVAL-ARCHITECTURE.md ← M0 deliverable
├── NON-DUPLICATION-MATRIX.yaml  ← M0 deliverable
├── PROGRESS-CHECKPOINT.yaml     ← M0 deliverable
├── lib/                         ← M1-M5: ALL CODE goes here
│   ├── layers/                  ← 9 memory layer classes
│   ├── lifecycle/               ← 10-state lifecycle engine
│   ├── memory_palace/           ← Memory palace computational model
│   ├── retrieval/               ← Hybrid retrieval engine
│   ├── embeddings/              ← Embedding governance
│   ├── api/                     ← API surface
│   ├── gateway/                 ← Issue #38 bridge
│   └── filters/                 ← Source/auth/scope filters
├── evaluation/                  ← M6: evaluation code and data
├── docs/                        ← M6: documentation
└── schemas/                     ← 0009-owned schemas
    └── MEMORY-LIFECYCLE.schema.json
```

---

## 6. Summary: What 0009 ADDS vs. What Already Exists

| Capability | PR #57 | Issue #59 | Issue #38 | 0009 ADDS |
|---|---|---|---|---|
| Store atoms | ✅ | ❌ | ❌ | ❌ (uses PR #57) |
| Create atoms | ❌ | ✅ | ❌ | ❌ (uses Issue #59) |
| Classify into memory layers | ❌ | ❌ | ❌ | ✅ NEW |
| Lifecycle management (10 states) | ❌ | ❌ | ❌ | ✅ NEW |
| Memory palace navigation | ❌ | ❌ | ❌ | ✅ NEW |
| 9-retriever hybrid recall | 1 retriever | ❌ | ❌ | ✅ 8 MORE |
| 13-axis reranking | 1 axis (cosine) | ❌ | ❌ | ✅ 12 MORE |
| Conflict surfacing | ❌ | Stores conflicts | ❌ | ✅ Proactive surfacing |
| Unknown gap-filling | ❌ | Stores unknowns | ❌ | ✅ Gap-fill in queries |
| AnswerEvidenceBundle | ❌ ContextBundle | ❌ | Spec pending | ✅ Full implementation |
| Content-index separation | ❌ | ❌ | ❌ | ✅ NEW |
| Embedding governance | ❌ | ❌ | ❌ | ✅ NEW |
| Decay and forgetting | ❌ | ❌ | ❌ | ✅ NEW |
| Source/auth/scope filtering | ❌ Tenant only | ❌ | Access decisions | ✅ 3-axis filtering |
| Gateway | ✅ | ❌ | ✅ (pending) | Bridge only |

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0-M0 | 2026-07-22 | QCLAW 0009 | M0 infrastructure audit |
