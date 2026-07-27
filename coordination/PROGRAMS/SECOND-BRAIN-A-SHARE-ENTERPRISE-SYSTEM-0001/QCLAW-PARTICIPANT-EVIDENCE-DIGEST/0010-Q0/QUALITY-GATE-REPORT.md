# QUALITY-GATE-REPORT.md — Epoch 12 Gate A R1: 3-archive receipt truth

## Gate Summary
| Gate | Result |
|------|--------|
| D01 Duplicate-key rejection | PASS (JSON/JSONL/YAML: 3/3 exit nonzero) |
| D02 Canonical ID | PASS (99+147+64, 0 mismatches) |
| D03 UNKNOWN registry | PASS |
| D04 AI_HANDOFF metadata | PASS (no THIS_COMMIT, no ghost files) |
| D05 3 independent archives | PASS (exit=0, stdout IDENTICAL, 0 failures) |
| D06 External anchoring | RESOLVED (PR #96, Issue #59, Issue #31) |

## 3-Archive Determinism
| Archive | Exit | Failures | stdout_sha256 |
|---------|------|----------|---------------|
| 1 | 0 | 0 | c43a22c0b299fa1e5efdaec833acdd1e... |
| 2 | 0 | 0 | c43a22c0b299fa1e5efdaec833acdd1e... |
| 3 | 0 | 0 | c43a22c0b299fa1e5efdaec833acdd1e... |

Determinism: **IDENTICAL**
Source Q0 head: e54e04b14876017253d27c578484e0bbd9096c0b
Content: 99 Atoms, 147 Relations, 64 Questions — preserved.
Cross-receipt consistency: ALL_PASS (CROSS-RECEIPT-CONSISTENCY.yaml)
**0 FAILURES, 0 WARNINGS**
