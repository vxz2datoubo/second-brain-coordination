# TEST-RUN-RECEIPT (P0)
# QCLAW-0017-D0-INDEPENDENT-AUDIT-PREREGISTRATION-0020Q-P0
# Frozen: 2026-07-24T02:30:00+08:00

| Field | Value |
|---|---|
| Task ID | QCLAW-0017-D0-INDEPENDENT-AUDIT-PREREGISTRATION-0020Q-P0 |
| Agent | QCLAW |
| Phase | P0_PREREGISTRATION_ONLY |
| Python | 3.12.10 |
| PyYAML | 6.0.3 |
| Validator | validate_preregistration.py |
| Completion Signal | QCLAW_0017_D0_AUDIT_PREREGISTRATION_FROZEN_FOR_GPT_REVIEW |

## Machine Validator Results

| Check | Result |
|---|---|
| Required Outputs | 12/12 PRESENT |
| YAML + UTF-8 + Dup-Key | ALL PASS |
| Question ID Uniqueness | Q01-Q42 complete, no duplicates |
| Dimension Weights | sum=100.0 |
| Rubric Weights | sum=1.0 |
| Secret Pattern Scan | 0 secrets |
| Completion Signal | PASS |
| Placeholder Detection | 0 unfilled |
| Manifest SHA-256 Cross-Check | ALL MATCH |
| Exit Code | 0 |

## Frozen Manifest

| File | SHA-256 |
|---|---|
| BAR-ONLY-SCOPE-GUARD.yaml | 720c022221b5052efde954f44e93a3ce14195145667bc77e2832b151f7a1fe79 |
| D0-AUDIT-QUESTION-FREEZE.yaml | c2e695e41d362facaf929221f5c8082ceec2d75e4d36be7e4a06fb361bfa84ba |
| D0-SCORING-RUBRIC-FREEZE.yaml | 1e8cd67fd61a1820fc8d0da67c031062bb84d43f369b8e927252dff7ee0e0066 |
| EVIDENCE-REQUIREMENT-MATRIX.yaml | 0054673b2ad0784f6e0401c58d06b386ab2ac8248a251482eb130e26be81323f |
| EXPECTED-AND-FORBIDDEN-BEHAVIOR.yaml | ab57bac9a76b81e5b9428b884154423b489d6b7eb346cdfe5dc1ddd42cb59ca8 |
| INDEPENDENCE-AND-NON-CONTAMINATION-ATTESTATION.yaml | a6a24b5d6dd4f6dec60dd6fabb4bd6405253090f0bcac64c96f91278e82ae0ce |
| LOCAL-REALITY-AND-REPLAY-RECEIPT-CHECKLIST.yaml | 7575edd7a4fce8b67a841c56d957b0622832984b5ab773dd93b0082abd04c5a7 |
| UNKNOWN-AND-ABSTENTION-CONTRACT.yaml | 9a2287f7dce68f90d735d3cbfae0f3d1e942867a3e0e27e2ca69414a6c01956f |
| validate_preregistration.py | c7a5807b4f1a2f0d7527fbdd07849178ecba926350007e79771a0c7bf4dfb4cc |

**Combined Hash:** (see FROZEN-MANIFEST.yaml — not repeated here to avoid circular hash dependency)

## Preregistration Gate

- Codex D0 Status at Freeze: `DOES_NOT_EXIST`
- Codex D0 Branch: `DOES_NOT_EXIST`
- Codex D0 Draft PR: `DOES_NOT_EXIST`
- Gate Result: `PASS — FREEZE IS VALID PREREGISTRATION`

## Safety

- PUBLIC_SAFE / CANDIDATE_ONLY / NO_TRADE
- No Codex D0 access
- No brain_core inspection
- No trade/account/credential access
