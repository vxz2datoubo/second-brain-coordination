# QUALITY-GATE-REPORT.md — Epoch 12 Gate A: PR #96 Machine Receipt Truth

## Gate Summary
| Gate | Result |
|------|--------|
| D01 Duplicate-key rejection | PASS (3/3: JSON=1, JSONL=1, YAML=1 exit nonzero) |
| D02 Canonical ID recomputation | PASS (99+147+64 = 0 mismatches, Q0_CANONICAL_ID_V1) |
| D03 UNKNOWN registry YAML integrity | PASS (11 unknown_entries, 6 validation_tasks) |
| D04 AI_HANDOFF metadata truth | PASS (no THIS_COMMIT, no ghost files, no placeholder) |
| D05 Two independent runs | PASS (exit=0, stdout IDENTICAL, 2 clean extractions) |
| D06 External anchoring | RESOLVED (PR #96, Issue #59, Issue #31) |

## Source
- Accepted Q0 tested head: e54e04b14876017253d27c578484e0bbd9096c0b
- 2 clean independent extractions from immutable Git blobs (extract1 + extract2)
- 99 KnowledgeAtoms, 147 KnowledgeRelations, 64 AdversarialQuestions preserved
- NO atoms/relations/questions semantic content modified

## ID Canonicalization
- Version: Q0_CANONICAL_ID_V1
- Atoms: 99 regenerated, 0 mismatches
- Relations: 147 regenerated, 0 mismatches
- Questions: 64 regenerated (44 primary + 20 alternate), 0 mismatches

## Negative Fixtures
| Test | Exit | Result |
|------|------|--------|
| dup_json_key_test.py | 1 | PASS |
| dup_jsonl_key_test.py | 1 | PASS |
| dup_yaml_key_test.py | 1 | PASS |
| canonical_id_mismatch_test.py | 1 | PASS |
