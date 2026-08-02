# TEST-RUN-RECEIPT (R3)
# QCLAW-0017-D0-AUDIT-PREREGISTRATION-0020Q-R3
# 2026-07-24T07:03:02+08:00

| Field | Value |
|---|---|
| Task ID | QCLAW-0017-D0-AUDIT-PREREGISTRATION-0020Q-R3 |
| Phase | R3_EXACT_TWO_HEAD_EVIDENCE_CLOSURE |
| Completion Signal | QCLAW_0017_D0_R3_EXACT_TWO_HEAD_EVIDENCE_CLOSED_FOR_GPT_REVIEW |

## Canonical Heads

| Role | SHA |
|---|---|
| PR base | b76b8f846b446f0144e8afa12f4ef08d12e09bd7 |
| Frozen core | 70ed222e279568b7370af62df5bb23b79201ee45 |
| Tested head | 8ebb27211999e3b14cd0f9e493aedf9d3bd2a7fc |
| Receipt head | WILL_BE_REPORTED_AFTER_PUSH |

## Immutable Core

8/8 byte-identical to frozen head 70ed222e.
Core combined hash: bf029d13dba2e6bc054e9b452a5d7992905847781bb00bf73a7ef240220d61c0

## Validator

| | P0 (frozen) | At tested_head (R3 recomputed) |
|---|---|---|
| Git blob | 2a9a927c... | a438921c... |
| SHA-256 | f57c7d2c... | 1d5f5c2c... |
| Bytes | 9136 | 13024 |

## R2 Superseded Claims

| Claim | R2 Value | R3 Reality |
|---|---|---|
| Validator blob | bb68f0ca... | a438921c... (verified at tested_head) |
| SHA-256 | a21d65d3... | 1d5f5c2c... (recomputed from tested_head bytes) |
| Bytes | 12644 | 13024 (recomputed) |

R2 values do not match any Git object at PR head 8ebb272. Likely intermediate local state.
Explicitly superseded, not silently overwritten.

## Test Execution

| Attribute | Value |
|---|---|
| Python | 3.12.10 |
| PyYAML | 6.0.3 (preinstalled, pip fallback NOT triggered) |
| Command | python validate_preregistration.py |
| Working dir | 0020Q/ |
| Exit code | 0 |
| PASS | 59 |
| FAIL | 0 |
| SKIP | 0 |
| Normalized output SHA-256 | 7d2aba7a41f889ba8ee7bc8b0763577f5654ce9be74fe7ad18febe19e017800d |

## R3 Evidence Files

| New | Updated |
|---|---|
| R3-TWO-HEAD-EVIDENCE-ANCHOR.yaml | FROZEN-MANIFEST.yaml |
| R3-NORMALIZED-TEST-OUTPUT.txt | AMENDMENT-LOG.yaml |
| | GIT-BLOB-AND-SHA256-RECEIPT.yaml |
| | AI_HANDOFF.yaml |
| | TEST-RUN-RECEIPT.md |

## Gates

| Gate | Status |
|---|---|
| 8 core byte-identical to frozen head | PASS |
| tested_head is concrete full SHA | PASS |
| Validator blob at tested_head == a438921c | PASS |
| Validator SHA-256 recomputed from tested_head bytes | PASS |
| PyYAML preinstalled, pip fallback not triggered | PASS |
| R2 claims superseded not overwritten | PASS |
| No core or validator modified | PASS |
| No Codex D0 read | PASS |
| PR Draft | PASS |

## Safety

PUBLIC_SAFE / CANDIDATE_ONLY / research_only / NO_TRADE
