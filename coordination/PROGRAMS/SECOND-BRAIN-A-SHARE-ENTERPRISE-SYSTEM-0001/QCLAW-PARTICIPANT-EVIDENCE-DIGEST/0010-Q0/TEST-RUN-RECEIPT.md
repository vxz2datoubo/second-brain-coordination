# TEST-RUN-RECEIPT.md — Epoch 12 Gate A R1: 3-archive receipt truth

**task_id:** QCLAW-SEQUENTIAL-Q0-RECEIPT-ONTOLOGY-ARCHITECTURE-LTM-AND-SUPPLY-CHAIN-CLOSURE-0014-E12
**completion_signal:** QCLAW_E12_SEQUENTIAL_KNOWLEDGE_SUPPLY_TRUTH_AND_UNIFIED_INDEX_READY_FOR_GPT_REVIEW
**tested_commit:** e54e04b14876017253d27c578484e0bbd9096c0b

## Receipt Files
| File | Size | SHA-256 |
|------|------|---------|
| D05-COMMAND-EVIDENCE.yaml | 2002 | 909d119830f924f7565575ca3b8608d859d713df52c756309952a75aa5d5aec1 |
| AI_HANDOFF.yaml | 547 | a990d9a37a5be851f7ac7b6e7349799e49f74e0eda4fa5a03d2a8be24eeab536 |
| R1-TWO-RUN-DETERMINISM-RECEIPT.yaml | 642 | da092a0491cea1a2563eb5733d6cee4b7c37e17be490268e8bd95111a78a5c3c |
| CROSS-RECEIPT-CONSISTENCY.yaml | 425 | d82e0c80fe11d975d80a996f9ad9c3602896a8400b9a1becbf5213eeb5b06f10 |

## Source Blobs (immutable from e54e04b14876)
| File | Size | SHA-256 |
|------|------|---------|
| KNOWLEDGE-ATOMS.jsonl | 59631 | 47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d |
| KNOWLEDGE-RELATIONS.jsonl | 52892 | 39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a |
| ADVERSARIAL-QUESTION-SET.jsonl | 40889 | 2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927 |

## 3-Archive Validation
| Archive | Exit | stdout_sha256 |
|---------|------|---------------|
| 1 | 0 | c43a22c0b299fa1e5efdaec833acdd1e... |
| 2 | 0 | c43a22c0b299fa1e5efdaec833acdd1e... |
| 3 | 0 | c43a22c0b299fa1e5efdaec833acdd1e... |

## Summary
- Atoms: 99 (0 mismatches), Relations: 147 (0 mismatches), Questions: 64 (0 mismatches)
- D01: 4/4 negative fixtures exit nonzero
- D02: 0 canonical ID mismatches
- D03: UNKNOWN registry clean
- D04: AI_HANDOFF truthful
- D05: 3 independent archives, exit=0 (content: 0 failures), stdout IDENTICAL
- D06: PR #96, Issue #59, Issue #31

**ALL 0 FAILURES, 0 WARNINGS**
