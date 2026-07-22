# ============================================================================
# LONG-TERM MEMORY ARCHITECTURE
# Task: QCLAW-LONG-TERM-MEMORY-PALACE-HYBRID-RETRIEVAL-0009
# Issue: #60
# Version: 1.0.0-M0
# ============================================================================

## Overview

The QCLAW Long-Term Memory system is a **9-layer memory architecture** with a
**9-retriever hybrid retrieval engine**, a **10-state lifecycle state machine**,
and a **Memory Palace computable navigation index**. It sits on top of the
existing infrastructure:

- **Issue #59 (0008):** KnowledgeAtoms, LearningPackets — the "content"
- **PR #57:** Store, Fusion, basic retrieval — the "storage"
- **Issue #38:** Knowledge Gateway — the "gateway"
- **0009 (this task):** Memory organization, intelligent retrieval, lifecycle — the "memory"

---

## 1. System Architecture Diagram

```
                        ┌─────────────────────────────────────┐
                        │           USER / AGENT QUERY         │
                        └──────────────────┬──────────────────┘
                                           │
                        ┌──────────────────▼──────────────────┐
                        │        QUERY PARSING LAYER           │
                        │  NL Intent Extraction                │
                        │  Query Decomposition                 │
                        │  Parameter Resolution                │
                        └──────────────────┬──────────────────┘
                                           │
    ┌──────────────────────────────────────┼──────────────────────────────────────┐
    │                    HYBRID RETRIEVAL ENGINE                                   │
    │                                                                              │
    │  ┌──────────────────────────────────────────────────────────────────────┐   │
    │  │               MULTI-RECALL PARALLEL DISPATCH                          │   │
    │  │   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │   │
    │  │   │ SEM  │ │ KEY  │ │ ENT  │ │ REL  │ │ TMP  │ │ PROJ │ │ SRC  │   │   │
    │  │   └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘   │   │
    │  │      │        │        │        │        │        │        │        │   │
    │  │   ┌──┴────────┴────────┴────────┴────────┴────────┴────────┴──┐   │   │
    │  │   │   ┌──────────┐         ┌──────────┐                        │   │   │
    │  │   │   │ CONFLICT  │         │LIFECYCLE │                        │   │   │
    │  │   │   │  UNKNOWN  │         │ RETRIEVER│                        │   │   │
    │  │   │   │ RETRIEVER │         │          │                        │   │   │
    │  │   │   └──────────┘         └──────────┘                        │   │   │
    │  │   └────────────────────────────────────────────────────────────┘   │   │
    │  └─────────────────────────────────────────────────────────────────────┘   │
    │                                    │                                        │
    │  ┌─────────────────────────────────▼───────────────────────────────────┐   │
    │  │                  DEDUP & VERSION MERGE                                │   │
    │  │  Remove superseded atoms, resolve version chains,                    │   │
    │  │  merge same-atom from different recall sources                       │   │
    │  └─────────────────────────────────┬───────────────────────────────────┘   │
    │                                    │                                        │
    │  ┌─────────────────────────────────▼───────────────────────────────────┐   │
    │  │                  RELATION EXPANSION                                   │   │
    │  │  Traverse relation graph: REQUIRES → pull prerequisites              │   │
    │  │  SUPPORTS/CONTRADICTS → pull related evidence                        │   │
    │  │  GENERALIZES/REFINES → pull broader/narrower context                  │   │
    │  └─────────────────────────────────┬───────────────────────────────────┘   │
    │                                    │                                        │
    │  ┌─────────────────────────────────▼───────────────────────────────────┐   │
    │  │                  CONFLICT & UNKNOWN GAP-FILL                          │   │
    │  │  Surface contradictions: "X says A but Y says B"                     │   │
    │  │  Surface gaps: "We don't know Z; verification path is W"             │   │
    │  └─────────────────────────────────┬───────────────────────────────────┘   │
    │                                    │                                        │
    │  ┌─────────────────────────────────▼───────────────────────────────────┐   │
    │  │                  SOURCE / AUTH FILTER                                 │   │
    │  │  Filter by source provenance (trusted/untrusted)                     │   │
    │  │  Filter by authority level (CANDIDATE / REVIEWED / APPROVED)         │   │
    │  │  Filter by scope (project / user / temporal)                         │   │
    │  └─────────────────────────────────┬───────────────────────────────────┘   │
    │                                    │                                        │
    │  ┌─────────────────────────────────▼───────────────────────────────────┐   │
    │  │                  13-AXIS RERANKING                                    │   │
    │  │  Semantic | Keyword | Entity | Project/User Scope | Temporal         │   │
    │  │  Source Quality | Confidence | Lifecycle State | Relation Distance   │   │
    │  │  Importance | Recency | Conflict/Unknown Coverage | Task Relevance   │   │
    │  └─────────────────────────────────┬───────────────────────────────────┘   │
    │                                    │                                        │
    │  ┌─────────────────────────────────▼───────────────────────────────────┐   │
    │  │              BUDGET-AWARE RESULT ASSEMBLY                             │   │
    │  │  Token budget enforcement, diversity preservation,                   │   │
    │  │  mandatory conflict/unknown inclusion                                │   │
    │  └─────────────────────────────────┬───────────────────────────────────┘   │
    └────────────────────────────────────┼──────────────────────────────────────┘
                                         │
    ┌────────────────────────────────────▼──────────────────────────────────────┐
    │                  9-LAYER MEMORY SYSTEM                                      │
    │                                                                             │
    │  ┌─────────────────────────────────────────────────────────────────────┐   │
    │  │                                                                      │   │
    │  │  L0: WORKING_MEMORY              (session-scoped, high-priority)     │   │
    │  │  L1: EPISODIC_MEMORY             (time-ordered events)               │   │
    │  │  L2: SEMANTIC_MEMORY             (conceptual knowledge)              │   │
    │  │  L3: PROCEDURAL_MEMORY           (skills, methods, procedures)       │   │
    │  │  L4: AUTOBIOGRAPHICAL_USER_MEMORY (preferences, corrections, history)│   │
    │  │  L5: PROJECT_MEMORY              (project/architecture knowledge)    │   │
    │  │  L6: SOURCE_MEMORY               (provenance tracking)               │   │
    │  │  L7: CONFLICT_AND_UNKNOWN_MEMORY (contradictions + knowledge gaps)   │   │
    │  │  L8: META_MEMORY                 (memory about memory)               │   │
    │  │                                                                      │   │
    │  └─────────────────────────────────────────────────────────────────────┘   │
    │                                    │                                        │
    │  ┌─────────────────────────────────▼───────────────────────────────────┐   │
    │  │                    LIFECYCLE STATE MACHINE                             │   │
    │  │  INGESTED → CANDIDATE → ACTIVE → CONSOLIDATED                        │   │
    │  │                    ↓          ↓         ↓                             │   │
    │  │               SUPERSEDED   STALE    DISPUTED                          │   │
    │  │                    ↓          ↓         ↓                             │   │
    │  │               ARCHIVED ← REVOKED                                      │   │
    │  │                    ↓                                                  │   │
    │  │            FORGOTTEN_INDEX_ONLY                                        │   │
    │  └─────────────────────────────────────────────────────────────────────┘   │
    └────────────────────────────────────────────────────────────────────────────┘
                                         │
    ┌────────────────────────────────────▼──────────────────────────────────────┐
    │                    MEMORY PALACE (Computational Navigation Index)           │
    │                                                                             │
    │  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐          │
    │  │ Spatial     │  │ Topic Tree       │  │ Importance Graph     │          │
    │  │ Index       │  │ (hierarchical    │  │ (PageRank-scored     │          │
    │  │ (layer-to-  │  │  decomposition)  │  │  atom importance)    │          │
    │  │ layer paths)│  │                  │  │                      │          │
    │  └──────┬──────┘  └────────┬─────────┘  └──────────┬───────────┘          │
    │         │                 │                        │                       │
    │  ┌──────┴─────────────────┴────────────────────────┴───────────┐          │
    │  │                  RELATION GRAPH                               │          │
    │  │  (full relation graph with bidirectional traversal API)       │          │
    │  └──────┬───────────────────────────────────────────────────────┘          │
    │         │                                                                  │
    │  ┌──────┴──────────────────────────────────────────────────────┐          │
    │  │                  DECAY SCHEDULER                              │          │
    │  │  (per-layer decay curves, forgetting policy, time-based       │          │
    │  │   importance decay)                                           │          │
    │  └──────────────────────────────────────────────────────────────┘          │
    └────────────────────────────────────────────────────────────────────────────┘
                                         │
    ┌────────────────────────────────────▼──────────────────────────────────────┐
    │                    EMBEDDING GOVERNANCE LAYER                                │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
    │  │ Model        │  │ Index        │  │ Similarity   │  │ Rebuild      │   │
    │  │ Registry     │  │ Manager      │  │ Policy       │  │ Verification │   │
    │  │ (pluggable)  │  │ (rebuild)    │  │ (thresholds) │  │ (determinism)│   │
    │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
    └────────────────────────────────────────────────────────────────────────────┘
                                         │
    ┌────────────────────────────────────▼──────────────────────────────────────┐
    │                    CONTENT LAYER (NOT OWNED BY 0009)                         │
    │                                                                             │
    │  ┌────────────────────────────┐    ┌──────────────────────────────┐       │
    │  │ Issue #59 / 0008           │    │ PR #57 Canonical Runtime     │       │
    │  │ KnowledgeAtoms             │    │ Store, Fusion, Raw Retrieval │       │
    │  │ KnowledgeRelations         │    │ (one of 9 recall sources)    │       │
    │  │ LearningPackets            │    │                              │       │
    │  └────────────────────────────┘    └──────────────────────────────┘       │
    └────────────────────────────────────────────────────────────────────────────┘
                                         │
                        ┌────────────────┴────────────────┐
                        │                                 │
            ┌───────────▼───────────┐      ┌─────────────▼─────────────┐
            │   Issue #38 Gateway   │      │  AnswerEvidenceBundle      │
            │   (Auth, Routing,     │      │  Output: citations,        │
            │    Access Control)    │      │  confidence, conflicts,     │
            └───────────────────────┘      │  unknowns, evidence chain   │
                                           └───────────────────────────┘
```

---

## 2. Memory Layer Model

### 2.1 The 9 Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY LAYER STACK                         │
│                                                               │
│  L0: WORKING_MEMORY                                            │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Active session context, immediate recall,       │     │
│      │ high priority, short TTL (session duration)     │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L1: EPISODIC_MEMORY                                          │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Time-ordered events, what happened when,        │     │
│      │ temporal indexing, sequential recall            │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L2: SEMANTIC_MEMORY                                          │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Facts, concepts, definitions, relationships,    │     │
│      │ subject-indexed, conceptual recall              │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L3: PROCEDURAL_MEMORY                                        │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Skills, methods, procedures, checklists,        │     │
│      │ step-ordered, prerequisite-aware recall         │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L4: AUTOBIOGRAPHICAL_USER_MEMORY                             │
│      ┌─────────────────────────────────────────────────┐     │
│      │ User preferences, corrections, feedback,        │     │
│      │ personal history, user-scoped recall            │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L5: PROJECT_MEMORY                                           │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Project requirements, architecture decisions,   │     │
│      │ program knowledge, project-scoped recall        │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L6: SOURCE_MEMORY                                            │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Source manifests, provenance tracking,          │     │
│      │ digest history, source-quality scoring          │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L7: CONFLICT_AND_UNKNOWN_MEMORY                              │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Conflicting atoms, unresolved contradictions,   │     │
│      │ knowledge gaps, verification paths              │     │
│      └─────────────────────────────────────────────────┘     │
│                                                               │
│  L8: META_MEMORY                                              │
│      ┌─────────────────────────────────────────────────┐     │
│      │ Memory statistics, health metrics,              │     │
│      │ index status, layer distribution,               │     │
│      │ retrieval performance history                   │     │
│      └─────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Classification Rules

Atoms are classified into layers based on their `atom_type` from Issue #59:

| atom_type | Primary Layer | Secondary Layers |
|---|---|---|
| FACT, OBSERVATION | L2: SEMANTIC | L5: PROJECT (if scoped) |
| CLAIM, HYPOTHESIS | L2: SEMANTIC | L7: CONFLICT_AND_UNKNOWN (if disputed) |
| CAUSAL_CLAIM, CORRELATION | L2: SEMANTIC | L5: PROJECT |
| DEFINITION, CONCEPT | L2: SEMANTIC | — |
| RULE, CONSTRAINT | L2: SEMANTIC | L5: PROJECT |
| CONDITION, EXCEPTION | L2: SEMANTIC | L3: PROCEDURAL |
| FAILURE_CONDITION, COUNTEREXAMPLE | L7: CONFLICT_AND_UNKNOWN | L2: SEMANTIC |
| RISK | L2: SEMANTIC | L7: CONFLICT_AND_UNKNOWN |
| UNKNOWN, QUESTION | L7: CONFLICT_AND_UNKNOWN | — |
| DECISION, RATIONALE | L5: PROJECT | L1: EPISODIC |
| METHOD, PROCEDURE, SKILL | L3: PROCEDURAL | — |
| CHECKLIST_ITEM | L3: PROCEDURAL | L5: PROJECT |
| CASE | L1: EPISODIC | L2: SEMANTIC |
| METRIC, PARAMETER | L5: PROJECT | L8: META_MEMORY |
| SOURCE_ASSERTION | L6: SOURCE | — |
| USER_PREFERENCE, USER_CORRECTION | L4: AUTOBIOGRAPHICAL_USER | — |
| TEMPORAL_UPDATE | L1: EPISODIC | Any relevant content layer |
| PROJECT_REQUIREMENT, ARCHITECTURE_DECISION | L5: PROJECT | — |
| FAILURE_LESSON | L7: CONFLICT_AND_UNKNOWN | L3: PROCEDURAL |
| OPPORTUNITY | L5: PROJECT | — |

---

## 3. Hybrid Retrieval Architecture

### 3.1 The 9 Retrievers

```
 ┌─────────────────────────────────────────────────────────────┐
 │  1. SEMANTIC RETRIEVER        — Embedding-based similarity   │
 │  2. KEYWORD RETRIEVER         — BM25 / text search          │
 │  3. ENTITY RETRIEVER          — Named entity matching        │
 │  4. RELATION RETRIEVER        — Graph traversal via relations│
 │  5. TEMPORAL RETRIEVER        — Time-scoped recall           │
 │  6. PROJECT RETRIEVER         — Project/program scope        │
 │  7. SOURCE RETRIEVER          — Source provenance filter     │
 │  8. CONFLICT/UNKNOWN RETRIEVER— Gap and contradiction recall │
 │  9. LIFECYCLE RETRIEVER       — State-aware retrieval        │
 └─────────────────────────────────────────────────────────────┘
```

### 3.2 Multi-Recall Flow

```
Query → Parse Intent → Decide Active Retrievers → Parallel Dispatch
                                                         │
     ┌───────────────────────────────────────────────────┤
     │   ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐       │
     │   │ SEM   │ │ KEY   │ │ ENT   │ │ ...   │       │
     │   │ (L2)  │ │ (ALL) │ │ (L2)  │ │       │       │
     │   └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘       │
     │       │         │         │         │             │
     │       └─────────┼─────────┼─────────┘             │
     │                 │         │                       │
     │         ┌───────▼─────────▼───────┐               │
     │         │    RESULT COLLECTION     │               │
     │         └───────────┬─────────────┘               │
     │                     │                              │
     │         ┌───────────▼─────────────┐               │
     │         │    DEDUP + VERSION       │              │
     │         │    MERGE                 │              │
     │         └───────────┬─────────────┘               │
     │                     │                              │
     │         ┌───────────▼─────────────┐               │
     │         │  RELATION EXPANSION     │               │
     │         └───────────┬─────────────┘               │
     │                     │                              │
     │         ┌───────────▼─────────────┐               │
     │         │  CONFLICT/GAP FILL      │              │
     │         └───────────┬─────────────┘               │
     │                     │                              │
     │         ┌───────────▼─────────────┐               │
     │         │   SOURCE/AUTH FILTER    │               │
     │         └───────────┬─────────────┘               │
     │                     │                              │
     │         ┌───────────▼─────────────┐               │
     │         │   13-AXIS RERANKER      │               │
     │         └───────────┬─────────────┘               │
     │                     │                              │
     │         ┌───────────▼─────────────┐               │
     │         │  AnswerEvidenceBundle   │              │
     │         └─────────────────────────┘               │
```

---

## 4. Memory Palace — Computational Model

### 4.1 Definition

The Memory Palace is a **computable navigation index** — NOT a UI, NOT a
visualization. It maps the 9-layer memory space into traversable structures
that enable efficient query resolution.

### 4.2 Components

| Component | Function |
|---|---|
| **Spatial Index** | Maps conceptual distances between memory layers; enables "navigate from X to related Y" |
| **Topic Tree** | Hierarchical decomposition of knowledge domains; enables drill-down from broad to specific |
| **Importance Graph** | PageRank-scored atom importance; enables "what's actually important about this topic?" |
| **Relation Graph** | Full directed graph of KnowledgeRelations; enables "what supports/contradicts/requires this?" |
| **Decay Scheduler** | Per-layer time-based decay curves; enables "what's still relevant vs. stale?" |

### 4.3 Content-Index Separation

```
┌─────────────────────────────────────┐
│          ISSUE #59 / 0008           │
│  KnowledgeAtoms (content)           │  ← CANONICAL SOURCE OF TRUTH
│  LearningPackets                    │
└──────────────┬──────────────────────┘
               │ NEVER DUPLICATED
               │ Only index pointers
┌──────────────▼──────────────────────┐
│           0009 MEMORY               │
│  ┌──────────────────────────────┐  │
│  │ Layer classification         │  │  ← atom_id → layer mapping
│  │ Lifecycle state              │  │  ← atom_id → state mapping
│  │ Embedding vectors            │  │  ← atom_id → vector (rebuildable)
│  │ Topic tree position          │  │  ← atom_id → tree node mapping
│  │ Importance score             │  │  ← atom_id → score (computable)
│  │ Decay level                  │  │  ← atom_id → decay (computable)
│  │ Relation graph adjacency     │  │  ← relation_id → edges (rebuildable)
│  │ Retrieval performance stats  │  │  ← aggregate statistics
│  └──────────────────────────────┘  │
│                                     │
│  ALL INDEXES ARE REBUILDABLE FROM   │
│  CANONICAL ATOMS (Issue #59)        │
└─────────────────────────────────────┘
```

### 4.4 Rebuild Principle

Every index in the Memory Palace MUST be rebuildable from canonical atoms
(Issue #59 LearningPackets). No index stores derived data that cannot be
regenerated.

```
Rebuild(LearningPackets[]) → MemoryPalace
  ├── Rebuild layer classifications from atom_type
  ├── Rebuild lifecycle states from knowledge_status + time
  ├── Rebuild embedding vectors from canonical_statements (plug model)
  ├── Rebuild topic tree from KnowledgeStructures
  ├── Rebuild importance scores from relation graph + PageRank
  ├── Rebuild decay levels from created_at + per-layer decay curves
  └── Rebuild relation graph from KnowledgeRelations
```

---

## 5. Embedding Governance Architecture

### 5.1 Model-Agnostic Design

0009 does NOT select a final embedding model. Instead, it provides a pluggable
model registry:

```
EmbeddingModel (interface)
├── embed(text) → Vector
├── dimension → Integer
├── version → String
└── metadata → Hash
```

Concrete implementations (post-0009):
- OpenAI text-embedding-3 (256d-3072d)
- Cohere Embed v3
- Open-source (all-MiniLM-L6-v2, etc.)
- Custom fine-tuned models

### 5.2 Index Manager

```
IndexManager
├── create_index(layer, model_version) → IndexID
├── incremental_update(atoms[]) → nil
├── rebuild_all() → nil          # From canonical atoms
├── verify_integrity() → Report  # Rebuild + compare hash
├── index_status() → Status[]
└── switch_model(new_model) → nil  # Rebuild with new model
```

### 5.3 Similarity Policy

```
SimilarityPolicy
├── threshold: Float           # Minimum similarity to consider a match
├── metric: Enum               # COSINE | DOT_PRODUCT | EUCLIDEAN
├── normalization: Enum        # L2 | NONE
├── layer_weights: Hash        # Per-layer importance weight in similarity
└── diversity_factor: Float    # Penalize too-similar results
```

---

## 6. Lifecycle State Machine

### 6.1 Overview

The 10-state lifecycle manages the evolution of every knowledge atom through
the memory system:

```
INGESTED ──► CANDIDATE ──► ACTIVE ──► CONSOLIDATED
                │             │            │
                ▼             ▼            ▼
           SUPERSEDED      STALE       DISPUTED
                │             │            │
                └─────────┬───┘            │
                          ▼                │
                       REVOKED ◄───────────┘
                          │
                          ▼
                      ARCHIVED
                          │
                          ▼
                  FORGOTTEN_INDEX_ONLY
```

### 6.2 State Definitions

| State | Definition | Caused By |
|---|---|---|
| **INGESTED** | Atom received in a LearningPacket, not yet classified | New packet ingestion |
| **CANDIDATE** | Classified into layers, awaiting review/promotion | Layer classification |
| **ACTIVE** | Reviewed, serving queries, current truth | Manual or automated promotion |
| **CONSOLIDATED** | Long-standing, high-confidence, infrequently changing | Extended ACTIVE duration + high confidence |
| **SUPERSEDED** | Replaced by a newer atom (version chain) | Newer atom with same subject |
| **STALE** | Not accessed, no updates, past decay threshold | Time-based decay |
| **DISPUTED** | Has an unresolved conflict with another atom | Conflict detection |
| **REVOKED** | Explicitly withdrawn (source retraction, user correction) | Manual revocation |
| **ARCHIVED** | No longer serving queries, preserved for history | Manual or automatic archival |
| **FORGOTTEN_INDEX_ONLY** | Content removed, index entry only (hash + metadata) | Deep decay or manual forget |

---

## 7. AnswerEvidenceBundle — Output Contract

The ONLY output format for the retrieval system:

```ruby
AnswerEvidenceBundle = {
  query: String,                          # Original query
  parsed_intent: QueryIntent,             # Parsed query intent
  answer: String,                         # Synthesized answer (if applicable)
  evidence: [EvidenceItem],               # Evidence items with citations
  conflicts: [ConflictSurfacing],         # Conflicting evidence
  unknowns: [UnknownGap],                 # Knowledge gaps
  confidence: Float,                      # Overall answer confidence
  retrieval_metadata: RetrievalMetadata,  # Performance, recall sources
  trace: TraceInfo                        # Debug/trace information
}

EvidenceItem = {
  atom_id: String,
  canonical_statement: String,
  relevance_score: Float,                 # From reranker
  source_citation: String,                # Human-readable source
  source_quality: Float,                  # Source trustworthiness
  confidence: Float,                      # Atom-level confidence
  layer: String,                          # Which memory layer
  state: String,                          # Lifecycle state
  retrieved_by: [String],                 # Which retrievers found it
  relation_distance: Integer              # Hops from query entity
}

ConflictSurfacing = {
  conflict_id: String,
  atom_a: { id: String, statement: String },
  atom_b: { id: String, statement: String },
  conflict_type: String,
  resolution_status: String,
  impact_on_query: String               # How this affects the query answer
}

UnknownGap = {
  unknown_id: String,
  question: String,
  what_is_known: String,
  verification_path: String,
  impact_on_query: String               # How this gap affects the query answer
}
```

---

## 8. Key Architectural Decisions

| Decision | Rationale |
|---|---|
| 9 layers, not fewer | Covers cognitive memory taxonomy comprehensively; layers are lightweight classifiers |
| Layers classify, never duplicate | Atoms live in PR #57 store; layers hold only atom_id → layer mapping |
| All indexes rebuildable | Zero persistent state that cannot be regenerated from LearningPackets |
| Model-agnostic embeddings | Future-proof; embedding model can change without restructuring |
| Memory Palace = computational | Not a UI; searchable, traversable, not renderable |
| 13-axis reranking | Cosine similarity alone is insufficient; multi-dimensional relevance scoring |
| AnswerEvidenceBundle mandatory | Forces comprehensive evidence: facts + conflicts + unknowns + citations |
| No final model/backend selection | Architecture over implementation; defer concrete choices |

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0-M0 | 2026-07-22 | QCLAW 0009 | M0 architecture document |
