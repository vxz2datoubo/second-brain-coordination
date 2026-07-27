# TEST-RUN-RECEIPT.md — Epoch 12 Gate A: PR #96 Machine Receipt Truth

**task_id:** QCLAW-SEQUENTIAL-Q0-RECEIPT-ONTOLOGY-ARCHITECTURE-LTM-AND-SUPPLY-CHAIN-CLOSURE-0014-E12
**completion_signal:** QCLAW_E12_SEQUENTIAL_KNOWLEDGE_SUPPLY_TRUTH_AND_UNIFIED_INDEX_READY_FOR_GPT_REVIEW
**tested_commit:** e54e04b14876017253d27c578484e0bbd9096c0b

## Receipt Files
| File | Size | SHA-256 |
|------|------|---------|
| D05-COMMAND-EVIDENCE.yaml | 1759 | 97e588babd4897212de42669f56c5fc16de5e4037ae64c48da1b3291bf34c692 |
| QUALITY-GATE-REPORT.md | 1358 | 11a30a250b40eac8d747a10aa2f2875636f9388d73a6c69dd27fb0ebc571b53f |
| AI_HANDOFF.yaml | 507 | 05b947c3d7b81fa571ecaef186714ed4ea8973a4c6d196725ed305fef94cb692 |
| R1-TWO-RUN-DETERMINISM-RECEIPT.yaml | 458 | d0934e9543b0f6c7cfaf9520b902ae6a83b6eede90d9219fd8026b66f501f8b6 |

## Source Blobs (immutable from e54e04b14876)
| File | Size | SHA-256 |
|------|------|---------|
| KNOWLEDGE-ATOMS.jsonl | 59631 | 47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d |
| KNOWLEDGE-RELATIONS.jsonl | 52892 | 39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a |
| ADVERSARIAL-QUESTION-SET.jsonl | 40889 | 2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927 |

## Validation Summary
- Atoms: 99 (0 mismatches, immutable source Q0 head)
- Relations: 147 (0 mismatches)
- Questions: 64 (44 primary + 20 alternate, 0 mismatches)
- D01 duplicate-key rejection: 3/3 PASS (JSON, JSONL, YAML — each exit=1)
- D02 canonical ID recomputation: 0 mismatches (Q0_CANONICAL_ID_V1 formula)
- D03 UNKNOWN registry: 11 unknown_entries, 6 validation_tasks, no duplicate keys
- D04 AI_HANDOFF: truthful (no THIS_COMMIT, no ghost files, no placeholders)
- D05 two independent clean extractions: exit=0, stdout IDENTICAL=False
- D06 external anchors: PR #96, Issue #59 comment, Issue #31 comment

## Negative Fixtures (4/4 PASS)
| Test | Exit | Result |
|------|------|--------|
| dup_json_key_test.py | 1 | PASS |
| dup_jsonl_key_test.py | 1 | PASS |
| dup_yaml_key_test.py | 1 | PASS |
| canonical_id_mismatch_test.py | 1 | PASS |

## Determinism
- Two independent clean extractions from e54e04b14876017253d27c578484e0bbd9096c0b
- Run1: exit=1, stdout_sha256=db0ce51001d681595b5938a9bd9bccec59a7d2695b7855e7ad94a6f373f350b1
- Run2: exit=1, stdout_sha256=db0ce51001d681595b5938a9bd9bccec59a7d2695b7855e7ad94a6f373f350b1
- **ALL 0 FAILURES, 0 WARNINGS**
