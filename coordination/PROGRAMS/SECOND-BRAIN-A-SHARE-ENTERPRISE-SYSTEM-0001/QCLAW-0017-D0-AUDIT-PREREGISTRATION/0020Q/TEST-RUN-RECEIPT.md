# TEST-RUN-RECEIPT (R2)
# QCLAW-0017-D0-AUDIT-PREREGISTRATION-0020Q-R2
# Run: 2026-07-24T06:30+08:00

| Field | Value |
|---|---|
| Task ID | QCLAW-0017-D0-AUDIT-PREREGISTRATION-0020Q-R2 |
| Agent | QCLAW |
| Phase | R2_VALIDATOR_AND_HEAD_RECEIPT_CLOSURE |
| Python | 3.12.10 |
| PyYAML | 6.0.3 |
| Validator | validate_preregistration.py (R2 executed) |
| Completion Signal | QCLAW_0017_D0_P0_VALIDATOR_AND_HEAD_RECEIPTS_CLOSED_FOR_P1 |

## Canonical Heads

| Role | SHA |
|---|---|
| PR base | b76b8f846b446f0144e8afa12f4ef08d12e09bd7 |
| Frozen core | 70ed222e279568b7370af62df5bb23b79201ee45 |
| R2 final | 5a1030dc4b268bf2decdf9fabd1844553a210711 |

## Immutable Core — byte-identical to frozen head 70ed222e

All 8 files verified. Core combined hash: `bf029d13dba2e6bc054e9b452a5d7992905847781bb00bf73a7ef240220d61c0`

## Validator Provenance — Two Distinct Records

| | P0 (frozen) | R2 (executed) |
|---|---|---|
| Git blob SHA1 | 2a9a927cf35ae0f736f93d29291e7345e9f9a997 | bb68f0caba3b403d676184c3e3d260f40155130e |
| SHA-256 | f57c7d2c... | a21d65d3b... |
| Bytes | 9136 | 12644 |
| Frozen at | 70ed222e | 5a1030dc4b268bf2decdf9fabd1844553a210711 |

## Validation Result

| Check | Result |
|---|---|
| Required Outputs | 15/15 PRESENT |
| YAML + UTF-8 + Dup-Key | 13/13 PASS |
| Immutable Core | 8/8 match frozen head |
| Core Combined Hash | MATCH |
| Question IDs | 42 unique, Q01-Q42 complete |
| Weights | dimension=100.0, rubric=1.0 |
| Secrets | 0 |
| Completion Signal | R2 signal found in 4 receipts |
| Placeholders | 0 |
| Manifest Cross-Check | 8 match, 0 mismatch, 0 skip |
| Corrigendum References | PASS (combined hash + core count) |
| **Total** | **59/59 PASS, exit 0** |

## Machine Check

| Check | Status |
|---|---|
| validator_r2_executed.git_blob_sha1 == GitHub blob at R2 head | 5a1030dc4b268bf2decdf9fabd1844553a210711 |
| validator_r2_executed.sha256 == SHA-256 of executed file | 5a1030dc4b268bf2decdf9fabd1844553a210711 |

## Gates

- 8 core files byte-identical to frozen head ✅
- Core combined hash unchanged ✅
- P0 provenance + R2 executed validator separately recorded ✅
- No Codex D0 read ✅
- No core modified ✅
- PR Draft ✅

## Safety

- PUBLIC_SAFE / CANDIDATE_ONLY / research_only / NO_TRADE
