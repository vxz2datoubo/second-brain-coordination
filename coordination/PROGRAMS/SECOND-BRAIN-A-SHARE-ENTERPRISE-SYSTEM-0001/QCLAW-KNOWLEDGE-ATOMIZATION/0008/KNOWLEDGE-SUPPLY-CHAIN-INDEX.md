# QCLAW Knowledge Supply Chain Index

**task_id:** QCLAW-MULTI-PR-TRUTH-ADAPTER-ATOMIZATION-LTM-CONSISTENCY-0012-E9
**route_epoch:** 9
**stage:** Stage E: Cross-PR Supply Chain Index

## Supply Chain Graph
```
PR #93 (Source Evidence)
  → PR #96/0010-Q0 (Knowledge Atomization: 99 atoms, 147 rels, 64 questions)
    ├─→ PR #100 (D2 Candidate Adapter: 4-family mapping)
    ├─→ PR #64 (Atomization Architecture: schemas + pipeline docs)
    └─→ PR #65 (Long-Term Memory Plan: retrieval + memory palace)
```

## Canonical Base
| Artifact | PR | SHA | Status |
|----------|-----|-----|--------|
| Phase 3 Offline Memory | #57 | 473d0ec15b28ac5e1b70db0b8a6a9ab17738161b | MERGED_CANONICAL |
| Phase 4 Knowledge Gateway | #58 | — | OPEN_CANDIDATE (Codex) |
| Source Evidence | #93 | — | CANDIDATE_SOURCE |

## Knowledge Supply Chain Status
| PR | Role | HEAD | Status |
|----|------|------|--------|
| #96 | Atomization Q0 | b1d88bf95d052a34bb9fecbb1ff31778740abd16 | Receipt Truth Finalized (E9-A) |
| #100 | D2 Adapter | 137ea13440ed61de9b240e475db8ffd081a217c9 | Candidate Adapter Remediated (E9-B) |
| #64 | Architecture | [THIS_COMMIT] | Architecture Truth Remediated (E9-C) |
| #65 | LTM Plan | [THIS_COMMIT] | Plan Truth Remediated (E9-D) |

## Count Source-of-Truth Manifest
| Metric | Value | Source |
|--------|-------|--------|
| Atoms | 99 | 0010-Q0/KNOWLEDGE-ATOMS.jsonl @ e54e04b14876017253d27c578484e0bbd9096c0b |
| Relations | 147 | 0010-Q0/KNOWLEDGE-RELATIONS.jsonl @ e54e04b14876017253d27c578484e0bbd9096c0b |
| Questions | 64 | 0010-Q0/ADVERSARIAL-QUESTION-SET.jsonl @ e54e04b14876017253d27c578484e0bbd9096c0b |
| Atom types | 10 | Derived from atoms (above) |
| Relation types | 7 | Derived from relations (above) |
| D2 families | 4 | PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml @ e54e04b14876017253d27c578484e0bbd9096c0b |
| Adapter cases | 78 | PR #100 (72 positive + 6 negative) |

## CODE-D2-CANDIDATE-HANDOFF.yaml
- Exposes: candidate family envelopes (4 families + UNMAPPED_UNKNOWN)
- Exposes: ontology translation rules (source→canonical D2)
- Does NOT expose: raw atoms, person identities, trading signals
- Quarantine: person_identity_quarantine ACTIVE on all person-name atoms

## Authority Matrix (Consolidated)
| Authority Level | PR | Scope |
|----------------|-----|-------|
| CANONICAL | #57 | Knowledge store |
| CANDIDATE_REFERENCE | #96 | Atomization output |
| CANDIDATE_ADAPTER | #100 | D2 family mapping |
| CANDIDATE_ARCHITECTURE | #64 | Architecture docs |
| PLAN_ONLY | #65 | Retrieval design |

**NO_TRADE | PUBLIC_SAFE | CANDIDATE_ONLY | NO_NEW_CANONICAL | NO_AUTHORITY_PROMOTION**
