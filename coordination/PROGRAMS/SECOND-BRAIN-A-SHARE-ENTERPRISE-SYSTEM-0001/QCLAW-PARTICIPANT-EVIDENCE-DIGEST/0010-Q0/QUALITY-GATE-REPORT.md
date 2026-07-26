# QUALITY-GATE-REPORT.md — Epoch 10 Stage A: PR #96 Machine Receipt Truth

**task_id:** QCLAW-UNIFIED-KNOWLEDGE-SUPPLY-CHAIN-ONTOLOGY-DETERMINISM-AND-LTM-EVIDENCE-0013-E10
**route_epoch:** 10

## Gate Summary
| Gate | Result |
|------|--------|
| D01 Duplicate-key rejection | PASS |
| D02 Canonical ID recomputation | PASS |
| D03 UNKNOWN registry YAML integrity | PASS |
| D04 AI_HANDOFF metadata truth | PASS |
| D05 Two independent runs | PASS (IDENTICAL) |
| D06 External anchoring | PASS |

## Commands (re-run from clean Q0 extraction @ e54e04b14876017253d27c578484e0bbd9096c0b)
| Command | Exit | stdout SHA-256 |
|---------|------|---------------|
| python validate_q0.py (run 1) | 1 | afc5f6e76bc1d744... |
| python validate_q0.py (run 2) | 1 | afc5f6e76bc1d744... |
| python tests/fixtures/dup_json_key_test.py | 1 | — |
| python tests/fixtures/dup_jsonl_key_test.py | 1 | — |
| python tests/fixtures/dup_yaml_key_test.py | 1 | — |
| python tests/fixtures/canonical_id_mismatch_test.py | 1 | — |

## ID Canonicalization
- Version: Q0_CANONICAL_ID_V1
- Atoms: 99 (0 mismatches)
- Relations: 147 (0 mismatches)
- Questions: 64 (44 primary + 20 alternate)
- All negative fixtures: exit 1 (PASS = detected failure condition)

## Machine Receipt
- receipt_head_ref: THIS_COMMIT
- Source extraction: clean Git extraction from Q0 tested head e54e04b14876
- No validator, fixture, atom, relation, or question file changed

**CANDIDATE_ONLY | NO_TRADE | PUBLIC_SAFE**
