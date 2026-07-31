# E22 Gate B R7 TEST-RUN-RECEIPT

## Machine-Generated Direct-Derived Transcript | MACHINE-GENERATED
**Python version:** `3.12.10`
**Generated:** 2026-07-31T08:22:01+08:00

## Results
| Case ID | Description | Exit | Expected Fail | Result |
|---------|-------------|------|---------------|--------|
| A01 | Corrupt JSON in atoms | 1 | True | EXPECTED_FAIL |
| A02 | Duplicate atom ID | 1 | True | EXPECTED_FAIL |
| A03 | Empty atoms file | 1 | True | EXPECTED_FAIL |
| A04 | Missing atoms file | 1 | True | EXPECTED_FAIL |
| A05 | Remove last relation | 1 | True | EXPECTED_FAIL |
| A06 | Corrupt relations | 1 | True | EXPECTED_FAIL |
| A07 | Empty relations | 1 | True | EXPECTED_FAIL |
| A08 | Corrupt questions | 1 | True | EXPECTED_FAIL |
| A09 | Empty questions | 1 | True | EXPECTED_FAIL |
| A10 | Missing policy(gen) | 1 | True | EXPECTED_FAIL |
| A11 | Tampered family | 1 | True | EXPECTED_FAIL |
| A12 | Missing subtype mapping | 1 | True | EXPECTED_FAIL |
| A13 | Both audit+quarantine deleted | 1 | True | EXPECTED_FAIL |
| A14 | Audit person deleted | 1 | True | EXPECTED_FAIL |
| A15 | Quarantine person deleted | 1 | True | EXPECTED_FAIL |
| A16 | Fake person in audit | 1 | True | EXPECTED_FAIL |
| A17 | Corrupt quarantine(gen) | 1 | True | EXPECTED_FAIL |
| A18 | Missing quarantine(gen) | 1 | True | EXPECTED_FAIL |
| A19 | Single hypothesis ambiguity | 1 | True | EXPECTED_FAIL |
| A20 | Dup subtype ambiguity | 1 | True | EXPECTED_FAIL |
| A21 | Missing D2 snapshot(gen) | 1 | True | EXPECTED_FAIL |
| A22 | Zeroed D2 hash | 1 | True | EXPECTED_FAIL |
| A23 | Bad JSON in adapters | 1 | True | EXPECTED_FAIL |
| A24 | Dup adapter id | 1 | True | EXPECTED_FAIL |
| A25 | Remove adapter | 1 | True | EXPECTED_FAIL |
| A26 | Wrong disposition | 1 | True | EXPECTED_FAIL |
| A27 | Missing package | 1 | True | EXPECTED_FAIL |
| A28 | Zeroed artifact hash | 1 | True | EXPECTED_FAIL |
| A29 | Wrong package count | 1 | True | EXPECTED_FAIL |
| A30 | Tampered CSR | 1 | True | EXPECTED_FAIL |
| A31 | Zeroed CSH | 1 | True | EXPECTED_FAIL |
| A32 | Wrong coverage | 1 | True | EXPECTED_FAIL |
| A33 | Missing coverage | 1 | True | EXPECTED_FAIL |
| A34 | Tampered source lock | 1 | True | EXPECTED_FAIL |
| A35 | Missing source lock | 1 | True | EXPECTED_FAIL |
| A36 | Wrong adapter_id | 1 | True | EXPECTED_FAIL |
| A37 | Missing d2_family | 1 | True | EXPECTED_FAIL |
| A38 | Missing gen receipt | 1 | True | EXPECTED_FAIL |
| A39 | CONTEXT_ONLY w family | 1 | True | EXPECTED_FAIL |
| A40 | UNMAPPED empty note | 1 | True | EXPECTED_FAIL |
| A41 | Family-only w subtype | 1 | True | EXPECTED_FAIL |
| A42 | Stale TBD note | 1 | True | EXPECTED_FAIL |

## Summary
- **Total:** 42
- **Passed:** 42
- **Failed:** 0

## Receipt file SHA-256
`ea76df68d4fe75b8a6791f143132bf20a8f422de1aba9d4bd294a213766049df`

## Completion
QCLAW_E22_PR100_DUAL_PYTHON_PORTABLE_RUNNER_ARCHIVE_PROVENANCE_AND_CUMULATIVE_HANDOFF_READY_FOR_GPT_REVIEW