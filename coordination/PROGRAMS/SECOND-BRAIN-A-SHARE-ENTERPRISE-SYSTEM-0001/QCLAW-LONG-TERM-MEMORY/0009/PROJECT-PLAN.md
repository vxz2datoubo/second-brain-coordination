# ============================================================================
# PROJECT PLAN — QCLAW LONG-TERM MEMORY PALACE WITH HYBRID RETRIEVAL
# Task: QCLAW-LONG-TERM-MEMORY-PALACE-HYBRID-RETRIEVAL-0009
# Issue: #60
# Program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001
# Phase: 5 — Long-Term Memory & Hybrid Retrieval
# Version: 1.0.0-M0
# ============================================================================

## Executive Summary

This project delivers the **QCLAW Long-Term Memory Palace** — a 9-layer memory
architecture with a 9-retriever hybrid retrieval engine that sits ON TOP OF the
existing infrastructure (PR #57 canonical runtime, Issue #59 atomization pipeline,
Issue #38 Knowledge Gateway). It does NOT build storage, fusion, or raw retrieval.
It builds the *organization* (memory layers), *navigation* (memory palace), and
*intelligent retrieval* (hybrid multi-recall with 13-axis reranking) that transform
raw KnowledgeAtoms into a living, useful long-term memory system.

The core insight: PR #57 provides a **store** and Issue #59 provides **atoms**, but
neither provides **memory** — the ability to organize knowledge by cognitive layer,
retrieve it with intelligence (not just cosine similarity), surface conflicts,
fill gaps, and present evidence-bundled answers. That is what 0009 builds.

## Phase Breakdown

### M0 — AUDIT AND PROJECT PLAN [CURRENT ← 20%]
**Objective:** Establish the architectural foundation, audit existing infrastructure,
prove non-duplication, and produce a complete project plan.

**Deliverables:**
- PROJECT-PLAN.md — This document
- CURRENT-RUNTIME-AUDIT.md — Infrastructure audit and non-duplication proof
- LONG-TERM-MEMORY-ARCHITECTURE.md — High-level system architecture
- MEMORY-LAYER-TAXONOMY.yaml — 9 memory layer definitions
- MEMORY-LIFECYCLE.schema.json — 10-state lifecycle state machine
- HYBRID-RETRIEVAL-ARCHITECTURE.md — 9-retriever architecture with 13-axis reranking
- NON-DUPLICATION-MATRIX.yaml — Comprehensive non-duplication proof
- PROGRESS-CHECKPOINT.yaml — M0 complete (20%)

**Success Gate:** All 7 files exist and pass internal consistency review.
All interfaces to PR #57, Issue #59, and Issue #38 are documented.
Non-duplication matrix proves zero overlap with existing code.

**Estimated Effort:** 1 session (current)

---

### M1 — MEMORY LAYER IMPLEMENTATION
**Objective:** Implement the 9 memory layer classes with lifecycle management,
content-index separation, and embedding governance.

**Deliverables:**
- `layers/working_memory.rb` — Short-lived, high-priority, session-scoped
- `layers/episodic_memory.rb` — Time-ordered events with temporal indexing
- `layers/semantic_memory.rb` — Conceptual knowledge, subject-indexed
- `layers/procedural_memory.rb` — Skills, methods, checklists, procedures
- `layers/autobiographical_user_memory.rb` — User preferences, corrections, history
- `layers/project_memory.rb` — Project/architecture knowledge, program-scoped
- `layers/source_memory.rb` — Source manifests, provenance tracking
- `layers/conflict_and_unknown_memory.rb` — Conflicts, gaps, unknowns
- `layers/meta_memory.rb` — Memory about memory: statistics, health, indexes
- `lifecycle/state_machine.rb` — 10-state lifecycle engine
- `lifecycle/guard_conditions.rb` — Transition validation
- `memory_palace/navigation_index.rb` — Content-index separation computable index

**Success Gate:** All 9 layers instantiate correctly. Lifecycle state machine passes
unit tests for all valid transitions and blocks all invalid ones. Memory palace index
builds from canonical atoms without duplication.

**Estimated Effort:** 3 sessions

---

### M2 — HYBRID RETRIEVAL ENGINE
**Objective:** Implement the 9-retriever dispatch, query parsing, dedup/merge,
reranking, and AnswerEvidenceBundle assembly.

**Deliverables:**
- `retrieval/query_parser.rb` — NL/structured query → intent + params
- `retrieval/dispatcher.rb` — Parallel multi-recall across 9 retrievers
- `retrieval/retrievers/semantic_retriever.rb` — Embedding-based semantic search
- `retrieval/retrievers/keyword_retriever.rb` — BM25/text search
- `retrieval/retrievers/entity_retriever.rb` — Named entity matching
- `retrieval/retrievers/relation_retriever.rb` — Graph traversal via relations
- `retrieval/retrievers/temporal_retriever.rb` — Time-scoped recall
- `retrieval/retrievers/project_retriever.rb` — Project/program scoped search
- `retrieval/retrievers/source_retriever.rb` — Source provenance filtering
- `retrieval/retrievers/conflict_unknown_retriever.rb` — Conflict and gap retrieval
- `retrieval/retrievers/lifecycle_retriever.rb` — State-aware retrieval
- `retrieval/dedup_merge.rb` — Version-aware dedup and atom supersede
- `retrieval/relation_expander.rb` — Traverse relations for context enrichment
- `retrieval/conflict_gap_filler.rb` — Surface contradictions and unknowns
- `retrieval/reranker.rb` — 13-axis multi-dimensional reranking
- `retrieval/answer_bundle.rb` — AnswerEvidenceBundle assembly with source citations

**Success Gate:** Query parser correctly extracts intent from natural language.
All 9 retrievers produce recall results. Dedup correctly handles superseded atoms.
Reranker produces deterministic ranking. AnswerEvidenceBundle includes sources,
confidence, conflicts, and unknowns.

**Estimated Effort:** 4 sessions

---

### M3 — MEMORY PALACE COMPUTATIONAL MODEL
**Objective:** Build the Memory Palace as a computable navigation index that maps
the 9-layer memory space into traversable, query-optimized structures.

**Deliverables:**
- `memory_palace/spatial_index.rb` — Layer-to-layer navigation paths
- `memory_palace/topic_tree.rb` — Hierarchical topic decomposition
- `memory_palace/importance_graph.rb` — PageRank-style importance scoring
- `memory_palace/relation_graph.rb` — Full relation graph with traversal API
- `memory_palace/decay_scheduler.rb` — Time-based decay and forgetting
- `memory_palace/palace.rb` — Orchestrator: index builds, queries, updates

**Success Gate:** Memory palace index builds from a LearningPacket.
Spatial navigation returns correct layer-to-layer paths.
Topic tree reflects actual concept hierarchy.
Decay scheduler assigns correct decay curves per layer.

**Estimated Effort:** 3 sessions

---

### M4 — EMBEDDING GOVERNANCE
**Objective:** Define the embedding architecture (model-agnostic), index rebuild
policies, and similarity governance without selecting a final model.

**Deliverables:**
- `embeddings/governance.rb` — Embedding policies: when, how, version tracking
- `embeddings/index_manager.rb` — Index creation, rebuild, incremental update
- `embeddings/model_registry.rb` — Pluggable model interface (no final model selected)
- `embeddings/similarity_policy.rb` — Thresholds, distance metrics, normalization
- `embeddings/rebuild_verification.rb` — Deterministic rebuild from canonical atoms

**Success Gate:** Model registry accepts pluggable embedding backends.
Index manager can rebuild all indexes from canonical atoms.
Rebuild verification confirms deterministic reproduction.
Similarity policies are documented and configurable.

**Estimated Effort:** 2 sessions

---

### M5 — INTEGRATION & API SURFACE
**Objective:** Wire everything together, build the API surface, implement
source/auth filtering, and integrate with the Knowledge Gateway (Issue #38).

**Deliverables:**
- `api/memory_api.rb` — Complete memory system API
- `api/query_api.rb` — Query endpoint with full AnswerEvidenceBundle response
- `api/ingestion_api.rb` — LearningPacket ingestion → layer classification
- `api/admin_api.rb` — Lifecycle management, decay control, rebuild triggers
- `gateway/bridge.rb` — Bridge to Issue #38 Knowledge Gateway
- `filters/source_filter.rb` — Source provenance filtering
- `filters/auth_filter.rb` — Authority and access filtering
- `filters/scope_filter.rb` — Project/user/temporal scope filtering

**Success Gate:** Full ingestion pipeline: LearningPacket → lifecycle → layers → retrievable.
Query API returns AnswerEvidenceBundle with correct reranking.
Knowledge Gateway bridge passes health check.
All filters correctly exclude atoms by source, authority, and scope.

**Estimated Effort:** 3 sessions

---

### M6 — EVALUATION, DOCUMENTATION & DELIVERY
**Objective:** Comprehensive evaluation, full documentation, and delivery handoff.

**Deliverables:**
- `evaluation/retrieval_quality.rb` — Recall, precision, relevance benchmarks
- `evaluation/lifecycle_integrity.rb` — State transition correctness
- `evaluation/memory_palace_navigation.rb` — Navigation path accuracy
- `evaluation/answer_bundle_quality.rb` — Evidence completeness scoring
- `docs/README.md` — Complete system documentation
- `docs/ARCHITECTURE.md` — Final architecture documentation
- `docs/API.md` — API reference
- `AI_HANDOFF.yaml` — Handoff to Codex/next agent

**Success Gate:** All evaluation metrics pass thresholds.
Documentation is complete and accurate.
Handoff file covers all interfaces and known limitations.

**Estimated Effort:** 2 sessions

---

## Dependency Graph

```
                    ┌──────────────────────────┐
                    │     PR #57 Runtime        │
                    │  (Store, Fusion, Retrieval)│
                    └────────────┬─────────────┘
                                 │ provides: storage, raw retrieval
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
┌──────────▼──────────┐ ┌───────▼────────┐ ┌─────────▼─────────┐
│   Issue #59 / 0008  │ │  Issue #38 GW  │ │    THIS TASK 0009 │
│  Atomization Engine │ │  Knowledge GW  │ │  Memory Palace +   │
│  (KnowledgeAtoms,   │ │  (C1-C6 packs) │ │  Hybrid Retrieval  │
│   LearningPackets)  │ │                │ │                    │
└──────────┬──────────┘ └───────┬────────┘ └─────────┬─────────┘
           │                    │                     │
           │ provides: atoms,   │ provides: gateway   │ builds: layers,
           │ relations, packets │ API, auth, access   │ palace, reranking,
           │                    │                     │ evidence bundles
           │                    │                     │
           └────────────────────┼─────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────┐
│                     M0 → M1 → M2 → M3 → M4 → M5 → M6        │
│  M0: Audit/Plan                                              │
│  M1: Memory Layers (depends on: Issue #59 schemas)           │
│  M2: Hybrid Retrieval (depends on: M1 layers)                │
│  M3: Memory Palace (depends on: M1 layers, M2 retrievers)    │
│  M4: Embeddings (depends on: M1 layers)                      │
│  M5: Integration (depends on: M1-M4, Issue #38 C1)           │
│  M6: Evaluation (depends on: M1-M5)                          │
└──────────────────────────────────────────────────────────────┘
```

### External Dependencies

| Dependency | Owner | Required By Phase | Critical Interface |
|---|---|---|---|
| PR #57 Store | Codex | M1 | `store.read`, `store.list` for atom consumption |
| PR #57 Retrieval | Codex | M2 | `retrieval.search` as one of 9 retrievers |
| Issue #59 Schemas | QCLAW 0008 | M1 | KNOWLEDGE-ATOM.schema.json, KNOWLEDGE-RELATION.schema.json |
| Issue #59 LearningPackets | QCLAW 0008 | M1 | Ingest packets into memory layers |
| Issue #38 KnowledgeAccessDecision | Codex C1 | M5 | Auth filtering in source/auth_filter.rb |
| Issue #38 AnswerEvidenceBundle spec | Codex C4 | M2 | Output contract for retrieval/answer_bundle.rb |

### Internal Phase Dependencies

```
M0 ──► M1 ──► M2 ──► M5 ──► M6
  │      │      │
  │      │      └──► M3 (memory palace uses retrievers)
  │      └──► M4 (embeddings need layer structure)
  │
  └──► All phases (M0 establishes architecture)
```

M1 (Layers) is the critical path — everything depends on it.
M3 and M4 can proceed in parallel after M1.
M2 needs M1 complete (retrievers query layers).
M5 needs M1-M4 plus Issue #38 integration.
M6 gates on M5.

---

## Risk Register

| Risk ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-001 | PR #57 runtime interface changes during development | MEDIUM | HIGH | Pin to known commit hash; re-validate on PR merge |
| R-002 | Issue #59 atom schema evolves incompatibly | LOW | MEDIUM | Schema version pinning; QCLAW owns both 0008 and 0009 |
| R-003 | Issue #38 Knowledge Gateway not ready by M5 | MEDIUM | HIGH | M5 bridge is pluggable; can mock gateway for M2-M4 |
| R-004 | Embedding model selection blocks M4 | LOW | LOW | M4 is model-agnostic by design; registry pattern |
| R-005 | 9-layer taxonomy overly complex for initial implementation | MEDIUM | MEDIUM | Layers are lightweight classifiers; can start with 5 core layers and expand |
| R-006 | Reranking performance degrades with scale | MEDIUM | MEDIUM | M6 evaluation includes scale testing; configurable axis weights |
| R-007 | Content-index rebuild performance unacceptable | LOW | HIGH | Index is rebuildable from canonical atoms; incremental updates exist |
| R-008 | Duplication with PR #57 retrieval | HIGH (before audit) → LOW (after M0) | CRITICAL | M0 NON-DUPLICATION-MATRIX.yaml proves zero overlap; runtime retrieval is ONE of 9 retrievers |

---

## Decision Points

| Decision | Must Be Resolved By | Options | Recommended |
|---|---|---|---|
| Which 5 core layers to implement first if 9 is too many? | M1 Start | WORKING, EPISODIC, SEMANTIC, PROJECT, META | Start with 5; add 4 more in M1.2 |
| Embedding dimension and model family | M4 Start | OpenAI ada-002 (1536d), text-embedding-3 (256-3072d), Cohere, open-source | Defer to M4; build model-agnostic |
| Vector store backend | M4 Start | pgvector, Qdrant, Milvus, FAISS | Defer; M4 builds interface, not backend |
| Whether memory palace needs a UI | NEVER | N/A | MEMORY PALACE IS COMPUTATIONAL, NOT UI |
| Reranking axis weights | M2 End | Equal weights, configurable, learned | Start equal; add learned weights in M6 |
| Decay function per layer | M1 End | Exponential, linear, custom per layer | Custom per layer per MEMORY-LAYER-TAXONOMY |

---

## Non-Goals (Explicitly Out of Scope)

1. **Storage Engine** — PR #57 provides SQLite/store. 0009 does NOT build storage.
2. **Atomization** — Issue #59/0008 provides atomization. 0009 does NOT decompose knowledge.
3. **Fusion Engine** — PR #57 provides fusion. 0009 does NOT merge atoms.
4. **Knowledge Gateway API** — Issue #38 provides the gateway. 0009 builds a BRIDGE to it, not the gateway itself.
5. **Embedding Model Training** — 0009 is model-agnostic. No model training or selection.
6. **UI / Visualization** — Memory Palace is a computational navigation index, not a visual interface. No HTML/CSS/React.
7. **Snapshot System** — PR #57 provides snapshots. 0009 does NOT create snapshots.
8. **Real-time Streaming** — Retrieval is request-response, not streaming.
9. **Multi-Tenant Isolation** — Scoping is per-project/user, but full multi-tenant isolation is Issue #38 territory.
10. **Scale Testing Beyond Unit** — M6 evaluation tests correctness, not production-scale stress.
11. **Feedback Learning** — Issue #38 work package C5. 0009 does NOT implement feedback loops.
12. **Direct Runtime Patching** — 0009 never modifies PR #57 runtime code (violates CANONICAL-RUNTIME-BOUNDARY.md).

---

## File Ownership Boundaries

All files created by this task live under:
```
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/
└── QCLAW-LONG-TERM-MEMORY/0009/
    ├── lib/                          ← M1-M5 code
    │   ├── layers/                   ← 9 memory layer classes
    │   ├── lifecycle/                ← 10-state lifecycle engine
    │   ├── memory_palace/            ← Memory palace computational model
    │   ├── retrieval/                ← Hybrid retrieval engine
    │   ├── embeddings/               ← Embedding governance
    │   ├── api/                      ← API surface
    │   ├── gateway/                  ← Issue #38 bridge
    │   └── filters/                  ← Source/auth/scope filters
    ├── evaluation/                   ← M6 evaluation
    ├── docs/                         ← M6 documentation
    ├── schemas/                      ← 0009-owned schemas
    │   └── MEMORY-LIFECYCLE.schema.json
    └── *.md, *.yaml                  ← M0 deliverables
```

QCLAW (this task) OWNS all files in the 0009/ directory.
Codex OWNS all files in `lib/runtime/` (PR #57).
QCLAW 0008 OWNS all files in `QCLAW-KNOWLEDGE-ATOMIZATION/0008/`.
Cross-boundary reads are permitted; writes are PROHIBITED without explicit coordination.

---

## Architecture Principles (Non-Negotiable)

1. **PR #57 is the ONLY canonical runtime** — no second store, no second fusion, no second snapshot system
2. **All indexes MUST be rebuildable from canonical atoms** — zero state that cannot be regenerated from LearningPackets
3. **No final embedding model selected in M0-M4** — architecture is model-agnostic
4. **Memory Palace is a computable navigation index** — NOT a UI concept, NOT a visualization
5. **AnswerEvidenceBundle is the ONLY output contract for retrieval** — consistent format for all queries
6. **Reranking is NOT just cosine similarity** — 13-axis multi-dimensional ranking
7. **Content-Index separation** — content lives in atoms (Issue #59), indexes live in memory layers (0009)
8. **Layers classify, not duplicate** — atoms are classified INTO layers; layers do not copy atoms

---

## Timeline Summary

| Phase | Description | Sessions | Cumulative % |
|---|---|---|---|
| M0 | Audit & Project Plan | 1 | 20% |
| M1 | Memory Layers | 3 | 40% |
| M2 | Hybrid Retrieval | 4 | 60% |
| M3 | Memory Palace | 3 | 75% |
| M4 | Embedding Governance | 2 | 85% |
| M5 | Integration & API | 3 | 95% |
| M6 | Evaluation & Delivery | 2 | 100% |
| **Total** | | **18 sessions** | |

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0-M0 | 2026-07-22 | QCLAW 0009 | M0 initial project plan |
