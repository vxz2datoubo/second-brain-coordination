# QCLAW Knowledge Atomization Architecture
## Task: QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008 | Issue #59 | Phase 4

QCLAW is the knowledge atomization architect and continuous digestion engine.
This directory contains the complete architecture, schemas, pipeline, and learning packets.

## 📂 Directory Structure

```
0008/
├── README.md                          ← You are here
├── ARCHITECTURE.md                    ← Complete architecture: layers, component catalog, deterministic identity
├── ATOMIZATION-PRINCIPLES.md          ← 20 principles, anti-patterns, atom quality checklist
├── ATOM-TYPE-TAXONOMY.yaml            ← 32 atom types with definitions and decision tree
├── PIPELINE.yaml                      ← 8-stage processing pipeline with error recovery
├── QUALITY-GATES.yaml                 ← 28 quality gate definitions across 8 categories
├── TASK-EXECUTION-PLAN.yaml           ← Work packages, deliverables, checkpoints (→ this is the plan)
├── CANONICAL-RUNTIME-BOUNDARY.md      ← Explicit boundaries: what QCLAW does NOT build
├── KNOWLEDGE-DIGEST-QUEUE.yaml        ← Priority queue of knowledge sources
├── SECRET-SCAN.yaml                   ← Secret scanning patterns and configuration
│
├── schemas/                           ← All JSON Schema v2020-12 definitions
│   ├── KNOWLEDGE-ATOM.schema.json     ← Core atom: 32 types, full metadata, deterministic ID
│   ├── KNOWLEDGE-RELATION.schema.json ← 30 relation types, bidirectional support
│   ├── KNOWLEDGE-CONFLICT.schema.json ← 12 conflict types, resolution tracking
│   ├── KNOWLEDGE-UNKNOWN.schema.json  ← 15 unknown types, verification paths
│   ├── KNOWLEDGE-SKILL.schema.json    ← Procedural knowledge: steps, prerequisites, failure modes
│   ├── KNOWLEDGE-STRUCTURE.schema.json← Hierarchical grouping: taxonomy, concept map, decision tree
│   ├── KNOWLEDGE-SOURCE-MANIFEST.schema.json ← Source declaration and digester queue status
│   ├── LEARNING-PACKET.schema.json    ← Canonical output format, Phase 3 compatible
│   ├── SECRET-SCAN-RECEIPT.schema.json← Proof of scanning without exposing secret values
│   ├── ATOMIZATION-DECISION.schema.json← Every decision recorded for audit and reproducibility
│   └── QUALITY-GATE-REPORT.schema.json← Quality check results with pass/warn/fail
│
└── learning-packets/                  ← Generated LearningPackets (digest runs)
    ├── digest-001-*.json              ← META-DIGEST: architecture knowledge atoms
    ├── digest-002-*.json              ← Issue #38 knowledge (preserved as knowledge)
    ├── digest-003-*.json              ← Issue #59 knowledge (self-referential)
    ├── digest-004-*.json              ← PR #57 runtime contracts
    ├── digest-005-*.json              ← Meta-atomization knowledge
    ├── digest-006-*.json              ← Remaining queue items
    └── *-manifest.yaml                ← AtomizationRunManifest for each digest
```

## 🚀 Quick Start

1. **Read the architecture:** `ARCHITECTURE.md` → understand the 8-layer pipeline
2. **Read the principles:** `ATOMIZATION-PRINCIPLES.md` → 20 rules for quality atoms
3. **Check the schemas:** `schemas/` → exact JSON Schema definitions
4. **Run the pipeline:** `PIPELINE.yaml` → 8-stage processing with checkpoints
5. **Quality control:** `QUALITY-GATES.yaml` → 28 automated and manual checks

## 🔑 Key Design Decisions

| Decision | Rationale |
|---|---|
| 32 atom types | Covers facts, claims, methods, conditions, exceptions, failures, unknowns, decisions, and project structures |
| Deterministic IDs from SHA-256 | Same semantic content always produces same ID; enables rebuild verification |
| 30 relation types | Preserves original semantics rather than reducing to generic "related_to" |
| privacy_class ≠ storage control | Six independent fields: privacy_class, storage_targets, transport_visibility, gpt_access, authority_level, knowledge_status |
| Hard boundary only on secret VALUES | Credential/financial values are permanently denied; metadata about them is allowed |
| Candidate ≠ inaccessible | CANDIDATE_ONLY atoms have FULL_SEMANTIC_ACCESS by default |
| Conflicts are knowledge | Both sides preserved; CONFLICT_NOT_RETURNED is a critical evaluation failure |
| UNKNOWN is knowledge | Gaps documented with verification paths; never deleted |
| Phase 3 compatibility | LearningPackets conform to PR #57 canonical runtime ingestion contracts |

## ⚠️ Runtime Boundaries

QCLAW does NOT build:
- SQLite database or store → Phase 3 runtime provides this
- Fusion engine → Phase 3 runtime provides this
- Retrieval engine → Phase 3 runtime provides this
- QueryPlan generator → Phase 3 runtime provides this
- ContextBundle assembler → Phase 3 runtime provides this
- Knowledge gateway → Phase 3 runtime provides this

QCLAW builds:
- Knowledge atoms with full semantics, conditions, exceptions, negations
- Typed relations, conflicts, unknowns
- Deterministic, hash-verifiable LearningPackets
- Quality reports, secret scan receipts, atomization decisions
- The complete architecture for continuous knowledge digestion

## 📊 Status

- **Task:** QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
- **Issue:** #59 (READY)
- **Phase:** 4
- **Parent Program:** #31
- **Canonical Runtime:** PR #57 (merge 473d0ec)
- **Progress:** P0 IN_PROGRESS → targeting 20% checkpoint
- **Branch:** `qclaw/knowledge-atomization-digestion-0008`

## 🔗 Related

- [Issue #59](https://github.com/vxz2datoubo/second-brain-coordination/issues/59) — Task definition
- [Issue #38](https://github.com/vxz2datoubo/second-brain-coordination/issues/38) — Previous task (adversarial evaluation, preserved as knowledge)
- [PR #57](https://github.com/vxz2datoubo/second-brain-coordination/pull/57) — Canoniacal Phase 3 runtime
- [Issue #31](https://github.com/vxz2datoubo/second-brain-coordination/issues/31) — Parent program
