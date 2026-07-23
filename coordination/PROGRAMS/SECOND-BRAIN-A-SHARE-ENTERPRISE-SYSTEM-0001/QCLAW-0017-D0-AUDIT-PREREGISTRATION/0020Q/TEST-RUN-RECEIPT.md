# TEST-RUN-RECEIPT (R1)
# QCLAW-0017-D0-AUDIT-PREREGISTRATION-0020Q-R1
# Run: 2026-07-24T03:30+08:00

| Field | Value |
|---|---|
| Task ID | QCLAW-0017-D0-AUDIT-PREREGISTRATION-0020Q-R1 |
| Agent | QCLAW |
| Phase | R1_INTEGRITY_METADATA_REMEDIATION |
| Python | 3.12.10 |
| PyYAML | 6.0.3 |
| Validator | validate_preregistration.py (R1) |
| Completion Signal | QCLAW_0017_D0_P0_INTEGRITY_METADATA_CORRECTED_FOR_P1 |

## Immutable Core Verification

| File | Verified |
|---|---|
| BAR-ONLY-SCOPE-GUARD.yaml | MATCH head 70ed222e |
| D0-AUDIT-QUESTION-FREEZE.yaml | MATCH head 70ed222e |
| D0-SCORING-RUBRIC-FREEZE.yaml | MATCH head 70ed222e |
| EVIDENCE-REQUIREMENT-MATRIX.yaml | MATCH head 70ed222e |
| EXPECTED-AND-FORBIDDEN-BEHAVIOR.yaml | MATCH head 70ed222e |
| INDEPENDENCE-AND-NON-CONTAMINATION-ATTESTATION.yaml | MATCH head 70ed222e |
| LOCAL-REALITY-AND-REPLAY-RECEIPT-CHECKLIST.yaml | MATCH head 70ed222e |
| UNKNOWN-AND-ABSTENTION-CONTRACT.yaml | MATCH head 70ed222e |

**Core Combined Hash:** `bf029d13dba2e6bc054e9b452a5d7992905847781bb00bf73a7ef240220d61c0`

## R1 Corrections

| ID | Defect | Resolution |
|---|---|---|
| HASH-001 | Conflicting combined hash | Single 8-core combined hash |
| HASH-002 | Conflicting validator SHA | Validator SHA recorded; validator separately versioned |
| CLAIM-001 | Unverifiable 43/43 claim | R1 validator yields clean results |
| RULE-001 | Q11 hardcoded price limits | CORRIGENDUM mandates versioned rule matrix |
| RULE-002 | Q13 hardcoded auction windows | CORRIGENDUM mandates versioned exchange rules |
| REPRO-001 | Q18 overbroad reproducibility | CORRIGENDUM permits licensed local data |

## R1 Artifacts

| New | Updated |
|---|---|
| CORRIGENDUM.yaml | FROZEN-MANIFEST.yaml |
| AMENDMENT-LOG.yaml | validate_preregistration.py |
| GIT-BLOB-AND-SHA256-RECEIPT.yaml | TEST-RUN-RECEIPT.md |
| | AI_HANDOFF.yaml |

## Validity Gates

| Gate | Status |
|---|---|
| 8 core files byte-identical to head 70ed222e | PASS |
| Single core combined hash across all receipts | PASS |
| Git blob SHA1 + SHA-256 recorded per core file | PASS |
| Validator excluded from core combined hash | PASS |
| Rule/repro interpretability corrected without editing core | PASS |
| No Codex D0 read, no future answer/verdict | PASS |
| PR remains Draft, no files outside allowed directory | PASS |

## Safety

- PUBLIC_SAFE / CANDIDATE_ONLY / research_only / NO_TRADE
- No Codex D0 accessed
- No frozen core modified
- No merge
