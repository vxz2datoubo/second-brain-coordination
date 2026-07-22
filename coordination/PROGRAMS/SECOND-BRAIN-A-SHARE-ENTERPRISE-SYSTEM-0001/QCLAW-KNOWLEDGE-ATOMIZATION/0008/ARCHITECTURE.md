# ============================================================================
# QCLAW KNOWLEDGE ATOMIZATION ARCHITECTURE
# Program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001
# Task:    QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
# Version: 1.0.0
# ============================================================================

## Overview

QCLAW is the knowledge atomization architect and continuous digestion engine for the
Second Brain enterprise system. This document defines the complete architecture for
transforming raw knowledge sources into deterministic, traceable, and reusable
KnowledgeAtoms, KnowledgeRelations, and canonical-compatible LearningPackets.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     DISCOVERY LAYER                          │
│  KnowledgeSourceManifest → KnowledgeDigestQueue              │
│  Sources: files, conversations, issues, PRs, research,      │
│           design docs, failure reviews, agent handoffs      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    SECURITY LAYER                            │
│  SecretScanReceipt → Exact Redaction                        │
│  Only hard-sensitive: API keys, tokens, passwords,          │
│  private keys, financial auth secrets                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    PARSE LAYER                               │
│  KnowledgeDocument → KnowledgeSegment                       │
│  Format adapters: Markdown, TXT, JSON, JSONL, code, YAML    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 DECOMPOSITION LAYER                          │
│  Segment → Candidate Atoms                                  │
│  Minimum complete semantic unit extraction                  │
│  Preserves: conditions, exceptions, failures,               │
│             counterexamples, negations, time scope           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 STRUCTURING LAYER                            │
│  KnowledgeAtom + KnowledgeRelation + KnowledgeConflict       │
│  + KnowledgeUnknown + KnowledgeSkill + KnowledgeStructure    │
│  Deterministic ID generation                                │
│  Source lineage and version chains                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  QUALITY LAYER                               │
│  Quality gate checks:                                       │
│  - Atom too long/short                                       │
│  - Conditions/exceptions/negations lost                      │
│  - Subject mismatch / causality overreach                    │
│  - Opinion presented as fact                                 │
│  - Source chain broken                                       │
│  - Conflicts overwritten / UNKNOWN deleted                   │
│  - Duplicate inflation / secret leakage                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   OUTPUT LAYER                               │
│  LearningPacket (canonical-compatible)                       │
│  AtomizationRunManifest                                      │
│  KnowledgeDigestReceipt                                      │
│  QualityGateReport                                           │
│  → Public GitHub / Local Architecture / Both                │
└─────────────────────────────────────────────────────────────┘
```

## Component Catalog

### 1. KnowledgeSourceManifest
Declares a source of knowledge to be digested.
- `source_id`: deterministic ID derived from source hash
- `source_type`: FILE, ISSUE, PR, CONVERSATION, RESEARCH, DESIGN, FAILURE_REVIEW, AGENT_HANDOFF
- `source_location`: URI, path, or Issue/PR number
- `source_hash`: SHA-256 of source content
- `license_or_publication_basis`: ownership, license, or authorization

### 2. KnowledgeDocument
The parsed, structured representation of a source.
- Segments the document into logical sections
- Preserves heading hierarchy, code blocks, quoted text, lists
- Attaches source lineage

### 3. KnowledgeSegment
A single logical section or paragraph within a document.
- `segment_id`: deterministic ID
- `raw_text`: original text
- `segment_type`: HEADING, PARAGRAPH, CODE_BLOCK, LIST_ITEM, TABLE, QUOTE
- `position`: ordinal position in document

### 4. KnowledgeAtom
The core unit of knowledge. See KNOWLEDGE-ATOM.schema.json for full definition.
- Minimum complete semantic unit
- Carries conditions, exceptions, failures, counterexamples
- Deterministic ID from semantic content
- Version chain via supersedes/superseded_by

### 5. KnowledgeRelation
A typed relationship between two atoms. See KNOWLEDGE-RELATION.schema.json.
- 26+ relation types
- Bidirectional or directional
- Preserves original relation semantics

### 6. KnowledgeConflict
An explicit recording of contradictory atoms.
- `conflict_id`: deterministic
- `atom_id_a`, `atom_id_b`
- `conflict_type`: DIRECT, INDIRECT, TEMPORAL, SCOPE, METHODOLOGICAL
- `resolution_status`: UNRESOLVED, RESOLVED_BY_EVIDENCE, RESOLVED_BY_SUPERSEDES, ACKNOWLEDGED_PARADOX

### 7. KnowledgeUnknown
An explicit recording of what is NOT known.
- `unknown_id`: deterministic
- `question`: what is unknown
- `what_is_known`: surrounding established knowledge
- `verification_path`: how to resolve
- `impact_if_unresolved`: why it matters

### 8. KnowledgeSkill
A procedural or methodological atom. Steps, prerequisites, outcomes.
- `skill_id`
- `skill_type`: METHOD, PROCEDURE, CHECKLIST, TECHNIQUE
- `steps`: ordered list
- `prerequisites`, `expected_outcomes`, `failure_modes`

### 9. KnowledgeStructure
A hierarchical grouping of atoms (e.g., a concept map, topic tree).
- `structure_id`
- `structure_type`: TAXONOMY, CONCEPT_MAP, TOPIC_TREE, DECISION_TREE, PIPELINE
- `root_atom_id`
- `children`: ordered list of atom/structure references

### 10. AtomizationDecision
Records every decision made during atomization.
- Why a segment was split or merged
- Why a relation type was chosen
- Why a confidence level was assigned
- Why an extraction was deferred or rejected

### 11. AtomizationRunManifest
The complete record of one atomization run.
- Input sources, output atoms, relations, conflicts, unknowns
- Timing, errors, warnings
- Quality gate results

### 12. KnowledgeDigestQueue
The prioritized queue of sources waiting to be digested.
- Ordered by priority and dependency
- Each entry has status: PENDING, IN_PROGRESS, DIGESTED, FAILED, WAITING_SOURCE, WAITING_AUTHORIZATION

### 13. SecretScanReceipt
Proof that secret scanning was performed and results.
- Never contains actual secret values
- Records: scan_timestamp, secrets_found_count, redaction_positions, hash_after_redaction

### 14. LearningPacket
The canonical output format, compatible with Phase 3 memory runtime (PR #57).
- Contains: atoms, relations, conflicts, unknowns, source manifest
- Deterministic hash for integrity verification

## Deterministic Identity

All IDs are derived from semantic content using SHA-256:
```
atom_id = "AMNS-" + SHA256(canonical_statement + scope + time_scope)[:8]
relation_id = "REL-" + SHA256(atom_id_a + atom_id_b + relation_type)[:8]
conflict_id = "CNF-" + SHA256(atom_id_a + atom_id_b + conflict_type)[:8]
unknown_id = "UNK-" + SHA256(question)[:8]
source_id = "SRC-" + SHA256(source_location)[:8]
skill_id = "SKL-" + SHA256(skill_name + skill_type)[:8]
```

Same semantic input always produces the same ID. ID regeneration after
redaction or correction creates a new ID (old atom is superseded).

## Storage and Transport Policy

All six fields are independent:
- `privacy_class`: describes knowledge source/property (PRIVATE_KNOWLEDGE, PUBLIC_KNOWLEDGE, etc.)
- `storage_targets`: where to store (PUBLIC_GITHUB, LOCAL_KNOWLEDGE_ARCHITECTURE, or both)
- `transport_visibility`: who can see it (PUBLIC_ALLOWED, RESTRICTED, etc.)
- `gpt_access`: can GPT read full semantics (FULL_SEMANTIC_ACCESS, METADATA_ONLY)
- `authority_level`: knowledge trust (CANDIDATE_ONLY, REVIEWED, APPROVED)
- `knowledge_status`: lifecycle (candidate, active, superseded, revoked)

**privacy_class does NOT block public storage.** Only hard-sensitive secret values
(authentication, access, financial) are permanently denied from all outputs.

## Quality Gates

### Automatic Detection
1. Atom length: < 30 chars (too short) or > 2000 chars (too long)
2. Missing conditions: atom mentions "if/when" in source but lacks conditions field
3. Missing exceptions: source has "except/unless/but not" missing from atom
4. Negation loss: source has "not/never/no" missing from canonical_statement
5. Time scope loss: source has dates/times missing from time_scope
6. Subject mismatch: atom's subject differs from source's actual subject
7. Causality overreach: correlation worded as causation without evidence
8. Opinion-as-fact: CLAIM without confidence basis presented as FACT
9. Source chain broken: atom references source_id that doesn't exist
10. Conflict overwritten: both sides of a known conflict not preserved
11. UNKNOWN deleted: source's stated unknowns not carried forward
12. Duplicate inflation: two atoms with identical canonical_statement
13. Secret leakage: regex scan for credential patterns
14. Post-redaction semantic damage: redaction changes meaning critically
15. Queue omission: source in digest path not in KnowledgeDigestQueue
16. Field pollution: privacy/storage/transport/GPT fields contradict each other

## Compatibility with Canonical Runtime

QCLAW does NOT implement:
- SQLite store or database
- Fusion engine
- Snapshot system
- Retrieval engine
- QueryPlan generator
- ContextBundle assembler
- Knowledge gateway

QCLAW DOES produce:
- KnowledgeAtoms and KnowledgeRelations in canonical format
- LearningPackets compatible with Phase 3 runtime ingestion
- Schema files that the canonical runtime can consume
- Quality reports for handoff
