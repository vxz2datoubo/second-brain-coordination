# ============================================================================
# HYBRID RETRIEVAL ARCHITECTURE
# Task: QCLAW-LONG-TERM-MEMORY-PALACE-HYBRID-RETRIEVAL-0009
# Issue: #60
# Version: 1.0.0-M0
# ============================================================================

## Overview

The Hybrid Retrieval Architecture defines how queries flow from natural language
to AnswerEvidenceBundle through parallel multi-recall, dedup/merge, relation
expansion, conflict surfacing, source/auth filtering, and 13-axis reranking.

This is NOT a simple cosine-similarity search. It is a multi-dimensional,
evidence-aware retrieval pipeline that surfaces not just what we know, but also
what we DON'T know and what evidence CONTRADICTS.

---

## 1. Retrieval Pipeline Overview

```
QUERY
  │
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 1: QUERY PARSING & INTENT EXTRACTION                           │
│   Input:  Natural language query or structured query spec            │
│   Output: ParsedQueryIntent { intent_type, entities, temporal_scope, │
│            project_scope, layer_preferences, requirements }          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 2: RETRIEVER SELECTION & PARALLEL DISPATCH                     │
│   Select active retrievers based on intent → dispatch in parallel    │
│   9 retrievers: SEMANTIC, KEYWORD, ENTITY, RELATION, TEMPORAL,       │
│                 PROJECT, SOURCE, CONFLICT_UNKNOWN, LIFECYCLE         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 3: RESULT COLLECTION                                           │
│   Collect recall results from all active retrievers                  │
│   Each result: { atom_id, retriever, raw_score, retrieval_metadata } │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 4: DEDUP & VERSION MERGE                                       │
│   Same atom from multiple retrievers → single entry                  │
│   Multiple versions of same subject → keep latest (non-superseded)   │
│   Handle superseded atoms: mark as "historical context" if relevant  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 5: RELATION EXPANSION                                          │
│   For each high-relevance atom, traverse relations:                  │
│   REQUIRES → pull prerequisites                                     │
│   SUPPORTS/CONTRADICTS → pull supporting/contradictory evidence      │
│   GENERALIZES/REFINES → pull broader/narrower context                │
│   PART_OF/IS_A → pull structural context                             │
│   Expansion depth: configurable (default: 2 hops)                    │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 6: CONFLICT & UNKNOWN GAP-FILL                                 │
│   For each candidate atom, check L7 (Conflict/Unknown):              │
│   - Is this atom DISPUTED? → include conflict context                │
│   - Are there UNKNOWNs related to query entities? → include gaps     │
│   - Are there FAILURE_CONDITIONs relevant? → include failures         │
│   Output: ConflictSurfacing[] and UnknownGap[] for the bundle        │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 7: SOURCE / AUTH FILTER                                        │
│   Filter by source provenance: trusted vs. untrusted                 │
│   Filter by authority level: CANDIDATE / REVIEWED / APPROVED          │
│   Filter by scope: project / user / temporal                         │
│   Filter by lifecycle state: only query-visible states               │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 8: 13-AXIS RERANKING                                           │
│   Multi-dimensional scoring → single relevance score per atom         │
│   Configurable axis weights                                          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│ STAGE 9: BUDGET-AWARE RESULT ASSEMBLY                                │
│   Token budget enforcement, diversity preservation,                  │
│   mandatory conflict/unknown inclusion, AnswerEvidenceBundle output   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
                    AnswerEvidenceBundle
```

---

## 2. STAGE 1: Query Parsing & Intent Extraction

### 2.1 ParsedQueryIntent

```ruby
ParsedQueryIntent = {
  raw_query: String,                    # Original query text
  intent_type: Enum,                    # FACT_LOOKUP, HOW_TO, COMPARE,
                                        # TIMELINE, PROJECT_CONTEXT,
                                        # USER_PREFERENCE, SOURCE_INQUIRY,
                                        # DIAGNOSTIC
  entities: [Entity],                   # Extracted named entities
  temporal_scope: TemporalScope,        # Time range constraints
  project_scope: ProjectScope,          # Project/program constraints
  layer_preferences: [String],          # Preferred memory layers
  requires_conflicts: Boolean,          # Should conflicts be surfaced?
  requires_unknowns: Boolean,           # Should gaps be surfaced?
  requires_sources: Boolean,            # Should source provenance be included?
  confidence_threshold: Float,          # Minimum confidence required
  max_results: Integer,                 # Maximum results to return
  diversity_requirement: Float          # 0.0-1.0 diversity factor
}
```

### 2.2 Intent Type Detection

| Query Pattern | Intent Type | Active Retrievers |
|---|---|---|
| "What is X?", "Define X", "Tell me about X" | FACT_LOOKUP | SEMANTIC, KEYWORD, ENTITY |
| "How do I X?", "Steps to Y", "Process for Z" | HOW_TO | SEMANTIC, KEYWORD, ENTITY, PROCEDURAL* |
| "X vs Y", "Compare A and B", "Difference between" | COMPARE | SEMANTIC, ENTITY, CONFLICT, RELATION |
| "What happened on...", "Timeline of X", "History of Y" | TIMELINE | TEMPORAL, EPISODIC*, ENTITY |
| "In project X, ...", "Architecture of Y", "ADR for Z" | PROJECT_CONTEXT | PROJECT, SEMANTIC, RELATION |
| "What does the user prefer", "User setting X", "My preference" | USER_PREFERENCE | USER*, ENTITY |
| "Where did X come from?", "Source of Y", "Who said Z" | SOURCE_INQUIRY | SOURCE, ENTITY |
| "Memory stats", "How many atoms", "Retrieval performance" | DIAGNOSTIC | META* |

*These intents trigger layer-scoped retrievers in addition to standard retrievers.

### 2.3 Entity Extraction

```ruby
Entity = {
  name: String,           # Extracted entity name (e.g., "PR #57", "QCLAW", "atomization")
  type: Enum,             # PERSON, PROJECT, SYSTEM, CONCEPT, FILE, COMMIT, ISSUE
  confidence: Float,      # Extraction confidence
  canonical_id: String    # Linked to known entity in memory (if exists)
}
```

---

## 3. STAGE 2: The 9 Retrievers — Parallel Dispatch

### 3.1 Retriever Interface

All retrievers implement a common interface:

```ruby
module Retriever
  def name: String
  def recall(query_intent: ParsedQueryIntent) → [RecallResult]
  def priority: Integer           # Within the recall phase
  def applicable?(intent_type) → Boolean
end

RecallResult = {
  atom_id: String,
  retriever: String,              # Which retriever found this
  raw_score: Float,               # Retriever-specific relevance score
  retrieval_metadata: Hash,       # Retriever-specific metadata
  retrieved_at: Time
}
```

### 3.2 Retriever Catalog

#### 3.2.1 Semantic Retriever (SEM)
```
Type: Embedding-based semantic search
Scope: L2 (SEMANTIC_MEMORY), L5 (PROJECT_MEMORY)
Method: Cosine similarity between query embedding and atom embeddings
Index: Embedding vectors managed by IndexManager (M4)
Strengths: Conceptual similarity, paraphrase tolerance, fuzzy matching
Weaknesses: May miss exact keyword matches, embedding model dependent
Raw Score: cosine_similarity(query_vector, atom_vector) [0.0, 1.0]
Default Priority: 100 (always active for content queries)
```

#### 3.2.2 Keyword Retriever (KEY)
```
Type: BM25 / full-text search
Scope: ALL layers (text index across all atoms)
Method: BM25 ranking on canonical_statement + full_semantic_content
Index: Inverted index managed by IndexManager (M4)
Strengths: Exact term matching, handles rare/technical terms
Weaknesses: No semantic understanding, misses paraphrases
Raw Score: BM25 score [0.0, unbounded, normalized to 0.0-1.0]
Default Priority: 90
```

#### 3.2.3 Entity Retriever (ENT)
```
Type: Named entity matching
Scope: L2 (SEMANTIC_MEMORY), L5 (PROJECT_MEMORY)
Method: Match extracted query entities against atom subject/entity fields
Index: Entity-to-atom index
Strengths: Precise entity-level filtering, supports entity disambiguation
Weaknesses: Requires accurate entity extraction; entity aliases needed
Raw Score: entity_match_score (exact: 1.0, fuzzy: 0.5-0.9, no match: 0)
Default Priority: 85
```

#### 3.2.4 Relation Retriever (REL)
```
Type: Graph traversal from known entities
Scope: All layers (via relation graph)
Method: From matched entity atoms, traverse relation graph (BFS/DFS with scoring)
        REQUIRES, SUPPORTS, CONTRADICTS, IS_A, PART_OF, GENERALIZES, REFINES
Index: Relation graph (M3: memory_palace/relation_graph.rb)
Strengths: Discovers contextually related knowledge, prerequisite chains
Weaknesses: Graph explosion risk; need hop limit (default: 3)
Raw Score: 1.0 / (1 + graph_distance) [decays with hop distance]
Default Priority: 70
```

#### 3.2.5 Temporal Retriever (TMP)
```
Type: Time-scoped recall
Scope: L1 (EPISODIC_MEMORY), L2 (with time_scope), any atom with temporal metadata
Method: Filter atoms by temporal_scope overlap with query temporal range
        Score by recency: more recent → higher score
Index: Temporal index
Strengths: Time-accurate recall, chronological ordering
Weaknesses: Only useful for temporal queries; missed if query doesn't specify time
Raw Score: temporal_relevance (overlap ratio + recency bonus)
Default Priority: 60 (only active when temporal intent detected)
```

#### 3.2.6 Project Retriever (PROJ)
```
Type: Project/program scoped search
Scope: L5 (PROJECT_MEMORY)
Method: Filter atoms by project/program ID; rank by decision recency
Index: Project scope index + importance graph (M3)
Strengths: Contextual to specific project, keeps results relevant
Weaknesses: Requires project scope to be specified
Raw Score: project_relevance (project match: 1.0, related project: 0.5)
Default Priority: 80 (active when project scope detected)
```

#### 3.2.7 Source Retriever (SRC)
```
Type: Source provenance filtering
Scope: L6 (SOURCE_MEMORY)
Method: Filter by source_id, source_type, source_quality
Index: Source-to-atom index
Strengths: Answers "where did this come from?" queries
Weaknesses: Not useful for content queries; only for provenance queries
Raw Score: source_match_score
Default Priority: 50 (only active for SOURCE_INQUIRY intent)
```

#### 3.2.8 Conflict/Unknown Retriever (CFU)
```
Type: Gap and contradiction retrieval
Scope: L7 (CONFLICT_AND_UNKNOWN_MEMORY)
Method: Match query entities against conflict pairs and unknown questions
        Always returns conflicts/unknowns related to query entities
Index: Conflict pair index + unknown question index
Strengths: Surfaces what we DON'T know, not just what we do
Weaknesses: Can overwhelm results if too many conflicts; needs relevance filtering
Raw Score: conflict_relevance (entity match score)
Default Priority: 65 (always active — mandatory for evidence completeness)
```

#### 3.2.9 Lifecycle Retriever (LC)
```
Type: State-aware retrieval
Scope: All layers
Method: Filter by lifecycle state (only query-visible states)
        Boost CONSOLIDATED atoms, penalize STALE atoms
Index: Lifecycle state index
Strengths: Ensures only appropriate states are returned
Weaknesses: Not a standalone retriever; operates as a filter/boost on other results
Raw Score: state_boost (CONSOLIDATED: +0.2, CANDIDATE: +0.0, STALE: -0.1, DISPUTED: -0.05)
Default Priority: 0 (applied as modifier, not independent recall)
```

### 3.3 Retrieval Dispatch Strategy

```
For each query:
  1. Determine active retrievers from intent type
  2. Launch all active retrievers in parallel
  3. Each retriever returns up to max_results * 3 candidates (for headroom)
  4. Collect all RecallResults with timeout (default: 500ms per retriever)
  5. Timeout → partial results from completed retrievers
```

---

## 4. STAGE 4: Dedup & Version Merge

### 4.1 Algorithm

```
Input:  [RecallResult] from all retrievers
Output: [DedupedAtom] with merged metadata

For each atom_id in results:
  1. Group all RecallResults by atom_id
  2. Merge retriever metadata:
     - retrieved_by: union of all retriever names
     - recency_boost: from temporal retriever (if found)
     - relation_distance: from relation retriever (if found)
     - entity_match: from entity retriever (if found)
  3. Keep atom with highest raw_score as primary
  4. If atom is SUPERSEDED:
     - Follow superseded_by chain to find latest active version
     - Include latest active version in results
     - Optionally include superseded atom as historical context
  5. If multiple versions of same subject:
     - Keep the non-superseded version
     - Mark superseded versions as "available_in_history"
```

---

## 5. STAGE 5: Relation Expansion

### 5.1 Expansion Rules

```
For each high-relevance atom (initial_score > threshold):
  Traverse relation graph:

  REQUIRES (outgoing):
    → Pull prerequisite atoms (they're needed for understanding)
    → Score: 1.0 / (1 + distance) * prerequisite_importance

  SUPPORTS (incoming):
    → Pull atoms that support this one (provides evidence weight)
    → Score: 0.5 / (1 + distance)

  CONTRADICTS (incoming):
    → Pull contradictory atoms (critical for evidence completeness)
    → Score: 0.8 / (1 + distance)  # High — contradictions are important

  GENERALIZES / REFINES:
    → Pull broader/narrower concepts for context
    → Score: 0.3 / (1 + distance)

  PART_OF / IS_A:
    → Pull structural context
    → Score: 0.4 / (1 + distance)

  MAX_HOPS: 2 (configurable)
  MAX_EXPANDED_ATOMS: 50 (prevents graph explosion)
```

---

## 6. STAGE 6: Conflict & Unknown Gap-Fill

### 6.1 Conflict Surfacing

```
For each atom in final results:
  Check if atom is DISPUTED (in L7):
    → Look up conflict pair: (atom, conflicting_atom)
    → Create ConflictSurfacing:
      - conflict_id
      - atom_a: { id, statement }
      - atom_b: { id, statement }
      - conflict_type: DIRECT_FACTUAL | METHODOLOGICAL | INTERPRETIVE | TEMPORAL | SCOPE
      - resolution_status: UNRESOLVED | RESOLVED_BY_* | ACKNOWLEDGED_PARADOX
      - impact_on_query: "This conflict directly affects your query because..."

  If query has requires_conflicts: true
    → Also scan L7 for conflicts matching query entities (beyond results)
```

### 6.2 Unknown Gap-Filling

```
For query entities:
  Scan L7 for UNKNOWN atoms whose question or domain matches:
    → Create UnknownGap:
      - unknown_id
      - question: "What we don't know"
      - what_is_known: "What we DO know around this gap"
      - verification_path: "How to resolve this gap"
      - impact_on_query: "This gap affects your query because..."

  If query has requires_unknowns: true
    → Always scan for unknown gaps regardless of entity match
```

---

## 7. STAGE 7: Source / Auth Filter

### 7.1 Filter Pipeline

```
SourceFilter:
  1. If source_ids specified: keep only atoms from those sources
  2. If source_quality_threshold: remove atoms from low-quality sources
  3. If source_type_filter: remove atoms from excluded source types

AuthFilter:
  1. If authority_level_threshold: remove atoms below threshold
     (CANDIDATE_ONLY < REVIEWED < APPROVED)
  2. If user/tenant context: apply KnowledgeAccessDecision (Issue #38 C1)
  3. If privacy boundary: remove atoms with conflicting transport_visibility

ScopeFilter:
  1. If project_scope: keep only atoms with matching project scope
  2. If user_scope: keep only atoms with matching user scope
  3. If temporal_scope: keep only atoms within temporal range

StateFilter:
  1. Remove atoms in non-query-visible states:
     INGESTED, SUPERSEDED, REVOKED, ARCHIVED, FORGOTTEN_INDEX_ONLY
  2. STALE atoms: keep but mark as stale
  3. DISPUTED atoms: keep but MUST include conflict context
```

---

## 8. STAGE 8: 13-Axis Reranking

### 8.1 The 13 Axes

Not just cosine similarity — full multi-dimensional relevance scoring:

| # | Axis | Description | Score Range | Weight |
|---|---|---|---|---|
| 1 | **Semantic Similarity** | Cosine similarity between query and atom embeddings | [0.0, 1.0] | 0.15 |
| 2 | **Keyword Match** | BM25 score / exact term match quality | [0.0, 1.0] | 0.10 |
| 3 | **Entity Match** | How well atom entities match query entities | [0.0, 1.0] | 0.10 |
| 4 | **Project/User Scope** | How well atom scope matches query scope | [0.0, 1.0] | 0.08 |
| 5 | **Temporal Validity** | How current/relevant the temporal scope is | [0.0, 1.0] | 0.08 |
| 6 | **Source Quality** | Reliability score of the atom's source | [0.0, 1.0] | 0.07 |
| 7 | **Confidence** | Atom-level confidence (LOW→0.3, MEDIUM→0.6, HIGH→0.8, VERY_HIGH→1.0) | [0.0, 1.0] | 0.10 |
| 8 | **Lifecycle State** | State-based boost/penalty | [-0.2, +0.2] | 0.05 |
| 9 | **Relation Distance** | Hops from query entity (closer = better) | [0.0, 1.0] | 0.05 |
| 10 | **Importance** | PageRank-scored importance in memory palace | [0.0, 1.0] | 0.07 |
| 11 | **Recency** | How recently was this atom created/updated/accessed | [0.0, 1.0] | 0.05 |
| 12 | **Conflict/Unknown Coverage** | Bonus if atom has associated conflict or unknown gap surfaced | [0.0, 0.1] | 0.05 |
| 13 | **Task Relevance** | LLM-judged relevance to the specific task/query intent | [0.0, 1.0] | 0.05 |

### 8.2 Scoring Formula

```
FINAL_SCORE = Σ (axis_i.score × axis_i.weight) for i in 1..13

Where:
  total_weight = Σ(weight_i) = 1.0
  FINAL_SCORE ∈ [0.0, 1.0]

Additional modifiers:
  - Diversity penalty: if two atoms are too similar (cosine > 0.95), slightly
    penalize the lower-scored one by diversity_factor
  - Layer priority boost: atoms from higher-priority layers get a small boost
  - Mandatory inclusion: DISPUTED atoms and UNKNOWN gaps CANNOT be scored below
    a minimum threshold (0.3) to ensure they pass budget assembly
```

### 8.3 Axis Weight Configuration

Axis weights are configurable per query type. Default weights shown above.
Can be tuned per intent:

```
FACT_LOOKUP:     SEM(0.20), KEY(0.15), ENT(0.12), CONF(0.12), ...
HOW_TO:          SEM(0.12), KEY(0.12), CONF(0.08), PROC_BOOST(0.15), ...
TIMELINE:        TEMP(0.20), RECENCY(0.15), EPISODIC_BOOST(0.10), ...
PROJECT_CONTEXT: PROJ(0.18), IMPORTANCE(0.12), ENT(0.10), ...
```

### 8.4 Reranking Algorithm

```
Input:  [FilteredAtom] from Stage 7
Output: [RankedAtom] sorted by FINAL_SCORE descending

1. For each atom, compute all 13 axis scores
2. Apply axis weights (configurable per intent type)
3. Compute weighted sum → raw_score
4. Apply diversity penalty:
   - Pairwise cosine similarity check
   - If two atoms similarity > 0.95, reduce lower-scored by diversity_factor
5. Apply mandatory inclusion boost:
   - DISPUTED atoms and UNKNOWN gaps get min_score = 0.3
6. Sort by final_score descending
7. Return top N (max_results)
```

---

## 9. STAGE 9: Budget-Aware Result Assembly

### 9.1 Assembly Algorithm

```
Input:  [RankedAtom], Conflicts, Unknowns, MaxTokens
Output: AnswerEvidenceBundle

1. Initialize bundle with empty evidence, conflicts, unknowns
2. Allocate token budget:
   - 70% for evidence items
   - 15% for conflicts
   - 15% for unknowns
3. Fill evidence:
   - Take ranked atoms in order
   - Each atom consumes: length(canonical_statement) + citation overhead
   - Stop when 70% budget is reached
   - If mandatory items remain (disputed atoms), exceed budget with warning
4. Fill conflicts:
   - Include ConflictSurfacing items related to evidence atoms
   - Stop when 15% budget is reached
5. Fill unknowns:
   - Include UnknownGap items related to query entities
   - Stop when 15% budget is reached
6. Compute overall confidence:
   - Weighted average of evidence atom confidences
   - Penalized by unresolved conflicts (-0.1 per unresolved conflict)
   - Penalized by unknown gaps (-0.05 per gap)
7. Assemble trace:
   - Retriever performance (latency, recall counts)
   - Filter statistics (how many filtered out)
   - Reranker statistics (score distribution)
8. Return AnswerEvidenceBundle
```

### 9.2 Diversity Preservation

```
During assembly, ensure diversity within evidence:
- Track subject clusters
- If >3 atoms share the same subject, keep top 3, demote rest
- Ensure at least 2 different sources are represented (if available)
- Ensure at least 2 different layers are represented (if applicable)
```

---

## 10. AnswerEvidenceBundle — Output Contract

```ruby
AnswerEvidenceBundle = {
  # Query context
  query: String,
  parsed_intent: ParsedQueryIntent,
  
  # Synthesized answer (optional — GPT can synthesize from evidence)
  answer: String | nil,
  answer_confidence: Float,           # Overall confidence with penalty for conflicts/gaps
  
  # Evidence
  evidence: [EvidenceItem],
  
  # Gaps and contradictions
  conflicts: [ConflictSurfacing],
  unknowns: [UnknownGap],
  
  # Metadata
  retrieval_metadata: {
    total_candidates: Integer,        # Before filtering
    total_after_dedup: Integer,
    total_after_filter: Integer,
    total_after_rerank: Integer,
    total_in_bundle: Integer,
    retrieval_time_ms: Float,
    retrievers_used: [String],
    retriever_stats: {
      semantic: { recall_count: Integer, time_ms: Float },
      keyword: { recall_count: Integer, time_ms: Float },
      # ... per active retriever
    },
    relation_expansion: {
      expanded_from: Integer,         # Starting atom count
      expanded_to: Integer,           # After expansion
      max_hops_used: Integer          # Actual hops reached
    }
  },
  
  # Token budget info
  budget: {
    total_allocated: Integer,
    used: Integer,
    breakdown: {
      evidence: Integer,
      conflicts: Integer,
      unknowns: Integer
    }
  },
  
  # Debug trace
  trace: {
    trace_id: String,
    query_parsing_ms: Float,
    recall_ms: Float,
    dedup_ms: Float,
    expansion_ms: Float,
    filter_ms: Float,
    rerank_ms: Float,
    assembly_ms: Float,
    total_ms: Float
  }
}

EvidenceItem = {
  atom_id: String,
  canonical_statement: String,
  relevance_score: Float,             # From reranker (FINAL_SCORE)
  axis_scores: {                      # Per-axis breakdown
    semantic: Float,
    keyword: Float,
    entity: Float,
    project_scope: Float,
    temporal_validity: Float,
    source_quality: Float,
    confidence: Float,
    lifecycle_state: Float,
    relation_distance: Float,
    importance: Float,
    recency: Float,
    conflict_coverage: Float,
    task_relevance: Float
  },
  source_citation: String,            # Human-readable: "PR #57 merge 473d0ec"
  source_quality: Float,              # 0.0-1.0
  source_id: String,
  confidence: Float,                  # 0.0-1.0 mapped from LOW/MEDIUM/HIGH/VERY_HIGH
  confidence_basis: String,
  layer: String,                      # Primary memory layer
  state: String,                      # Lifecycle state
  atom_type: String,                  # From Issue #59 taxonomy
  retrieved_by: [String],             # Which retrievers found this
  relation_distance: Integer | nil,   # Hops from query entity
  is_disputed: Boolean,               # Has unresolved conflict
  dispute_context: ConflictSurfacing | nil  # If disputed
}

ConflictSurfacing = {
  conflict_id: String,
  atom_a: { id: String, statement: String, source: String },
  atom_b: { id: String, statement: String, source: String },
  conflict_type: String,              # DIRECT_FACTUAL, METHODOLOGICAL, INTERPRETIVE, TEMPORAL, SCOPE
  resolution_status: String,          # UNRESOLVED | RESOLVED_BY_*
  resolution_evidence: String | nil,
  impact_on_query: String             # How this affects the answer
}

UnknownGap = {
  unknown_id: String,
  question: String,                   # What we don't know
  what_is_known: String,              # Surrounding established knowledge
  verification_path: String,
  impact_on_query: String             # How this gap affects the answer
}
```

---

## 11. Performance Budget

| Stage | Target Latency | Notes |
|---|---|---|
| Query Parsing | < 50ms | Lightweight NL parsing |
| Parallel Recall | < 500ms | 9 retrievers in parallel, 500ms timeout each |
| Dedup & Merge | < 50ms | Index-based merge |
| Relation Expansion | < 100ms | BFS with hop limit, bounded |
| Conflict/Gap Fill | < 50ms | Index lookups |
| Source/Auth Filter | < 50ms | Simple filter checks |
| 13-Axis Reranking | < 100ms | Per-atom scoring (capped at 500 atoms) |
| Budget Assembly | < 50ms | Token budget enforcement |
| **TOTAL** | < 1000ms | End-to-end target |

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0-M0 | 2026-07-22 | QCLAW 0009 | M0 hybrid retrieval architecture |
