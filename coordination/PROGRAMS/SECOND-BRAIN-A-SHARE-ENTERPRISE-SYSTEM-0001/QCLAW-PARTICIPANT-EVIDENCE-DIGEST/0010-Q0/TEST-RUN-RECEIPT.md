# TEST-RUN-RECEIPT.md — Epoch 14 Remote Lineage Truth Correction

**task_id:** QCLAW-PR96-REMOTE-LINEAGE-TRUTH-AND-EXTERNAL-ATTESTATION-CORRECTION-0016-E14
**completion_signal:** QCLAW_E14_PR96_REMOTE_LINEAGE_TRUTH_AND_EXTERNAL_ATTESTATION_READY_FOR_GPT_REVIEW
**route_epoch:** 14

## Actual Remote Git Chain
| Role | SHA |
|------|-----|
| source_q0_head | e54e04b14876017253d27c578484e0bbd9096c0b |
| gate_reviewed_head | 9dd292c910142b56303a46ea7136eaafb5610132 |
| gate_tested_head | d748191e4aaef28336f4cea4dab551de1a5b8451 |
| gate_receipt_head | 5d57dae029632fcceb9cfcd4ab242b34ad200f1f |
| receipt_parent | d748191e4aaef28336f4cea4dab551de1a5b8451 |

## Receipt Commit Delta (verified via GitHub Compare API)
Receipt commit `5d57dae029632fcceb9cfcd4ab242b34ad200f1f` changed exactly 1 file from tested `d748191e4aaef28336f4cea4dab551de1a5b8451`:
- CROSS-RECEIPT-CONSISTENCY.yaml

## Receipt Files (E14 post-correction, actual on-disk)
| File | Size | SHA-256 |
|------|------|---------|
| AI_HANDOFF.yaml | 962 | 195adcc5bfcec3a68fd868da22b58cd50ff80f3f37ed0d19ce894202a18099bf |
| CROSS-RECEIPT-CONSISTENCY.yaml | 1244 | 920652eb7840190dc83dd0cbb899727c78b96a1844705d85155b2adc469e03c3 |
| D05-COMMAND-EVIDENCE.yaml | 1189 | fc445b2aa1f54824e354b426e63a4eccd6e3010289a97e68b7aad425089cecad |
| R1-TWO-RUN-DETERMINISM-RECEIPT.yaml | 688 | 36501878b098c45e1529268ed345847a7a6629bf88393a11fccee65a32e64b4e |

## Source Blobs (immutable, from e54e04b14876)
| File | Size | SHA-256 |
|------|------|---------|
| KNOWLEDGE-ATOMS.jsonl | 59631 | 47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d |
| KNOWLEDGE-RELATIONS.jsonl | 52892 | 39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a |
| ADVERSARIAL-QUESTION-SET.jsonl | 40889 | 2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927 |

## Validation Evidence
- 3 archive runs: exit=0, 0 content FAIL, stdout IDENTICAL
- 4 negative fixtures: all exit nonzero
- 99 Atoms, 147 Relations, 64 Questions — preserved
- Determinism: IDENTICAL

## E14 Corrections Applied
- AI_HANDOFF: stale heads corrected to remote truth (no b5c4ec6/713c035d/9dd292c)
- Receipt file count: truthfully 1 (CROSS-RECEIPT-CONSISTENCY), not 6
- post_push_receipt_identity: VERIFIED
- No self-referencing SHA anywhere

**0 FAILURES, 0 WARNINGS**
