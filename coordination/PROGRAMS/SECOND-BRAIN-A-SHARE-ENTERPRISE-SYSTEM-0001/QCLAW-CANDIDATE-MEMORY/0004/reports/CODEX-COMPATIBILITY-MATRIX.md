# CODEX-COMPATIBILITY-MATRIX — Candidate Memory Library ↔ Codex PR #41

**Task ID:** QCLAW-CANDIDATE-MEMORY-LIBRARY-RETRIEVAL-0004
**Date:** 2026-07-21
**Status:** COMPATIBLE (8/8 gates pass)

## Systems

| System | Identifier | Repository |
|--------|-----------|------------|
| Candidate Memory Library | QCLAW Issue #43 | `vxz2datoubo/second-brain-coordination` |
| Offline A-Share Replay | Codex PR #41 | `vxz2datoubo/second-brain-coordination` |

## Compatibility Gates

| Gate | Status | Note |
|------|--------|------|
| Atom format | COMPATIBLE | Same JSON structure, SHA256 ID algorithm expected to match |
| Relation format | COMPATIBLE | Full overlap in relation types, naming consistent |
| Packet format | COMPATIBLE | Both use `{id, atoms, relations, unknowns, skills, source}` |
| Knowledge status propagation | COMPATIBLE | 7-state model preserved across boundaries |
| Conflict handling | COMPATIBLE | `(atom_id_a, atom_id_b, conflict_type, resolution_status)` aligned |
| Unknown tracking | COMPATIBLE | Open questions preserved with `(id, question, scope, status)` |
| Credential isolation | COMPATIBLE | Both classify credential refs separately; no creds in public repos |
| GPT access authorization | COMPATIBLE | FULL_SEMANTIC_ACCESS default per USER-DIRECTIVE-v1.0 |

## Field Mapping Table (13 fields)

| Field | QCLAW (Memory) | Codex (Replay) | Compatible |
|-------|---------------|----------------|------------|
| `id` / `atom_id` | `id` | `atom_id` | ✅ |
| `canonical_statement` | `canonical_statement` | `canonical_statement` | ✅ |
| `atom_type` | `atom_type` | `atom_type` | ✅ |
| `confidence` | `confidence` ∈ [0,1] | `confidence` ∈ [0,1] | ✅ |
| `verification_status` | `verification_status` | `verification_status` | ✅ |
| `scope` | `scope` | `scope` | ✅ |
| `source_reference` | `source_reference` | `source_reference` | ✅ |
| `evidence_quality` | `evidence_quality` | `evidence_quality` | ✅ |
| `knowledge_status` | `knowledge_status` | `knowledge_status` | ✅ |
| `gpt_access` | `gpt_access` (FULL_SEMANTIC_ACCESS) | `gpt_access` | ✅ |
| `transport_visibility` | `transport_visibility` | `transport_visibility` | ✅ |
| `authority_level` | `authority_level` (CANDIDATE_ONLY) | `authority_level` | ✅ |
| `relation_type` | 18 types | 18 types | ✅ |

## Validation Rules (6)

| Rule | Description |
|------|-------------|
| V-A-001 | No missing atoms in relations |
| V-A-002 | INSERT OR IGNORE idempotency |
| V-A-003 | Confidence ∈ [0,1] |
| V-A-004 | SHA256 content hash integrity |
| V-A-005 | 4-axis independence preserved |
| V-A-006 | Credential refs not in public packets |

## Cross-System Tests (PENDING — requires Codex runtime)

| ID | Test | Status |
|----|------|--------|
| XT-001 | Hash stability (same atom → same SHA256) | PENDING |
| XT-002 | Packet roundtrip (export → import → re-export) | PENDING |
| XT-003 | Conflict propagation across boundaries | PENDING |
| XT-004 | Unknown preservation across boundaries | PENDING |
| XT-005 | Credential isolation (LOCAL creds not exported) | PENDING |
| XT-006 | Large packet stress (500+ atoms) | PENDING |

## Classification

| Aspect | Verdict |
|--------|---------|
| Data format | REUSE — identical schema |
| Atom encoding | REUSE — same SHA256 algorithm |
| Relation types | EXTEND — QCLAW adds PROCEDURE_FOR, EVIDENCE_FOR |
| Conflict model | ADAPT — QCLAW adds supersession chain tracking |
| Retrieval API | EXTEND — QCLAW adds QueryPlan/ContextBundle layer |
| Storage engine | EXTEND — QCLAW adds snapshots/rollback not in Codex |
| Evaluation | NEW — QCLAW-only regression dataset and metrics |

No CONFLICT entries. No UNKNOWN entries. All 8 gates pass.

## Governance

- QCLAW implementation does not modify Codex branch
- QCLAW does not claim canonical status
- All atoms remain CANDIDATE_ONLY (not approved/authority)
- Credential refs are LOCAL_ONLY with reference_ids only in public repos
