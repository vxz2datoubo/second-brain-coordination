# TEST-RUN-RECEIPT.md 鈥?Epoch 13 Gate A Finalization

**task_id:** QCLAW-PR96-RECEIPT-LINEAGE-POST-PUSH-ATTESTATION-FINALIZATION-0015-E13
**completion_signal:** QCLAW_E13_PR96_RECEIPT_LINEAGE_AND_POST_PUSH_ATTESTATION_READY_FOR_GPT_REVIEW
**route_epoch:** 13

## Head Lineage
| Role | SHA |
|------|-----|
| source_q0_head | e54e04b14876017253d27c578484e0bbd9096c0b |
| gate_reviewed_head | b5c4ec6bd4da3480ac378d55c43c21151310f4c5 |
| gate_tested_head | 713c035d327d194e3c44a2256eb4e27596659f52 |
| receipt_parent | 9dd292c910142b56303a46ea7136eaafb5610132 |

## Receipt Files (Epoch 13)
| File | Size | SHA-256 |
|------|------|---------|
| D05-COMMAND-EVIDENCE.yaml | 1156 | 3183cce3595d9b58bbd776733efad05a2f7fe7063abf631d653cf3866b68a343 |
| AI_HANDOFF.yaml | 790 | c0c81163b55d5f7ad143f0a6d6403407786c4bfaa452c4d10417086520a9e966 |
| R1-TWO-RUN-DETERMINISM-RECEIPT.yaml | 682 | c138d310d761f3a9a7d1c800ef11bc91c5df4b7b195b43fc8836c6b2d953ed47 |
| CROSS-RECEIPT-CONSISTENCY.yaml | 1267 | 0a9fe10249cfb704992ba49d6a7db99b64acca4ed3eb9f96613c6f8e1ce70d2b |

## Source Blobs (immutable from e54e04b14876)
| File | Size | SHA-256 |
|------|------|---------|
| KNOWLEDGE-ATOMS.jsonl | 59631 | 47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d |
| KNOWLEDGE-RELATIONS.jsonl | 52892 | 39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a |
| ADVERSARIAL-QUESTION-SET.jsonl | 40889 | 2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927 |

## 3-Archive Validation (content checks)
| Archive | Exit | stdout_sha256 |
|---------|------|---------------|
| 1 | 0 | 28b4215d6d48a8ba6125e759e370be32... |
| 2 | 0 | 28b4215d6d48a8ba6125e759e370be32... |
| 3 | 0 | 28b4215d6d48a8ba6125e759e370be32... |

## Summary
- Source Q0 head: e54e04b14876017253d27c578484e0bbd9096c0b
- Gate tested head: 713c035d327d194e3c44a2256eb4e27596659f52
- Receipt parent: 9dd292c910142b56303a46ea7136eaafb5610132
- 99 Atoms, 147 Relations, 64 Questions 鈥?preserved
- 3 archives: exit=0, 0 failures, stdout=28b4215d6d48a8ba6125e759e370be32...
- 4/4 negative fixtures exit nonzero
- Determinism: IDENTICAL
- Cross-receipt: ALL_PASS

**ALL 0 FAILURES, 0 WARNINGS**
