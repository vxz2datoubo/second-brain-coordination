# ============================================================================
# CANONICAL RUNTIME BOUNDARY
# Task:    QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
# Version: 1.0.0
# ============================================================================

## What QCLAW Does NOT Build

QCLAW is the knowledge atomization agent. The canonical runtime (Phase 3 offline memory,
PR #57 merge `473d0ec`) provides all storage, retrieval, and gateway capabilities.
QCLAW must not duplicate or replace any of these.

### Prohibited Implementations

| Component | Why Prohibited | Who Owns It |
|---|---|---|
| **SQLite database / knowledge store** | PR #57 provides the sole candidate memory store | Phase 3 runtime |
| **Fusion engine** | PR #57 provides the atom fusion pipeline | Phase 3 runtime |
| **Snapshot system** | PR #57 provides deterministic snapshots | Phase 3 runtime |
| **Retrieval engine** | PR #57 provides multi-language retrieval | Phase 3 runtime |
| **QueryPlan generator** | PR #57 provides structured query planning | Phase 3 runtime |
| **ContextBundle assembler** | PR #57 provides evidence compilation | Phase 3 runtime |
| **Knowledge gateway** | Issue #38 defines this as Codex Phase 4 | Codex |
| **AnswerEvidenceBundle** | Codex Phase 4 work package C4 | Codex |
| **Feedback learning runtime** | Codex Phase 4 work package C5 | Codex |
| **Scale/stress test harness** | Codex Phase 4 work package C6 | Codex |
| **KnowledgeAccessDecision** | Codex Phase 4 work package C1 | Codex |
| **RevocationReceipt** | Codex Phase 4 work package C1 | Codex |

### Allowed Implementations

| Component | Description | QCLAW Scope |
|---|---|---|
| **KnowledgeAtom** | Core unit of knowledge | Full ownership — schema, generation, quality |
| **KnowledgeRelation** | Typed relationship between atoms | Full ownership |
| **KnowledgeConflict** | Explicit contradiction recording | Full ownership |
| **KnowledgeUnknown** | Explicit knowledge gap recording | Full ownership |
| **KnowledgeSkill** | Procedural knowledge | Full ownership |
| **KnowledgeStructure** | Hierarchical organization | Full ownership |
| **KnowledgeSourceManifest** | Source declaration and tracking | Full ownership |
| **LearningPacket** | Canonical output format | Full ownership — must be Phase 3 compatible |
| **SecretScanReceipt** | Proof of secret scanning | Full ownership |
| **AtomizationDecision** | Decision audit trail | Full ownership |
| **QualityGateReport** | Quality check results | Full ownership |
| **AtomizationRunManifest** | Run-level metadata | Full ownership |
| **KnowledgeDigestQueue** | Source priority queue | Full ownership |
| **Atomization Pipeline** | 8-stage processing pipeline | Full ownership |

## Interface Contract

QCLAW produces **LearningPackets** that the Phase 3 runtime (Codex) ingests:

```
QCLAW                              Codex (Phase 3 Runtime)
─────                              ───────────────────────
KnowledgeSource                    ─┐
  → Parse                          │
  → Decompose                      │  ← This is QCLAW's domain
  → Structure                      │
  → Quality Gate                   │
  → LearningPacket ────────────────┼→ Ingest into SQLite
                                   │   → Build indexes
                                   │   → Generate QueryPlans
                                   │   → Assemble ContextBundles
                                   │   → Serve retrieval queries
                                   │   ← This is Codex's domain
```

### Schema Compatibility

QCLAW's `KNOWLEDGE-ATOM.schema.json` must produce atoms that the Phase 3 runtime can consume.
The LearningPacket envelope (`LEARNING-PACKET.schema.json`) is the interface contract.

**Required fields for Phase 3 compatibility:**
- `atom_id` (deterministic, non-colliding)
- `canonical_statement`
- `atom_type`
- `knowledge_status`
- `authority_level`
- `gpt_access`
- `transport_visibility`
- `sources` (with source_id, source_type, source_hash)
- `relations` (with relation_type, target_atom_id)
- `confidence` and `confidence_basis`

**Fields QCLAW adds beyond Phase 3 minimum:**
- `privacy_class` (knowledge nature classification)
- `storage_targets` (explicit storage location decision)
- `full_semantic_content` (extended context)
- `failure_modes` (for method/skill atoms)
- `digest_run_id` (traceability)
- `extraction_decision_id` (decision audit link)
- `tags`

Phase 3 runtime should accept (or ignore) these additional fields without error.

## Coordination Protocol

1. **QCLAW writes** → coordination/PROGRAMS/.../QCLAW-KNOWLEDGE-ATOMIZATION/0008/
2. **Codex reads** → coordination/PROGRAMS/.../QCLAW-KNOWLEDGE-ATOMIZATION/0008/learning-packets/
3. **Codex ingests** → Phase 3 SQLite store
4. **Neither modifies the other's files** unless explicitly authorized via Issue comment
5. **Cross-agent issues** go through Issue #38 (coordination) or dedicated sub-issues

## Error Handling Across the Boundary

| Scenario | QCLAW Action | Expected Codex Response |
|---|---|---|
| QCLAW produces atom with invalid schema | Quality gate QG-COM-001 fails before output | N/A — blocked at source |
| QCLAW atom references unknown source | Quality gate QG-SRC-001 fails | N/A — blocked at source |
| Phase 3 runtime rejects packet | QCLAW receives error via Issue comment | Fix schema incompatibility, regenerate |
| Phase 3 runtime needs new atom type | Codex opens sub-issue or comments | QCLAW evaluates: add to taxonomy or negotiate |
| Duplicate atoms from different digests | QCLAW's deterministic IDs prevent true duplicates (same content = same ID) | Codex handles merge/supersede via atom version chain |

## Sharing Policy

- **Schemas:** QCLAW and Codex share schema definitions. Changes to schemas must be
  coordinated via Issue comments.
- **LearningPackets:** QCLAW owns the packets. Codex reads them. Neither party
  modifies the other's output files.
- **Runtime code:** Codex owns all runtime code. QCLAW never modifies Codex branches
  or runtime files.
- **Governance files:** Each agent owns its own TASK-EXECUTION-PLAN, FEEDBACK,
  AI_HANDOFF, etc. Cross-referencing is done via Issue comments.
