# TEST-RUN-RECEIPT.md

## Epoch 20 Gate B R5 - MACHINE-GENERATED TEST TRANSCRIPT

**Runner SHA256:** `690de16540b112acec516155753be568e31093a461da25eb8172c52e30c79530`
**Generated:** 2026-07-31T04:43:13+08:00
**Results file:** e20_test_results.json

> SUPERSEDES all false claims: E18 (54 tests), E19 (placeholder SHAs, TBD commit).
> This receipt is generated directly from machine test results.

## Results

| Case ID | Description | Action | Exit | Expected Fail | Passed |
|---------|-------------|--------|------|---------------|--------|
| A01 | Corrupt JSON in atoms | gen | 1 | True | PASS |
| A02 | Duplicate atom ID | gen | 1 | True | PASS |
| A03 | Empty atoms file | gen | 1 | True | PASS |
| A04 | Missing atoms file | gen | 1 | True | PASS |
| A05 | Remove last relation | gen | 1 | True | PASS |
| A06 | Corrupt relations | gen | 1 | True | PASS |
| A07 | Empty relations | gen | 1 | True | PASS |
| A08 | Corrupt questions | gen | 1 | True | PASS |
| A09 | Empty questions | gen | 1 | True | PASS |
| A10 | Missing policy(gen) | gen | 1 | True | PASS |
| A11 | Tampered family | val | 1 | True | PASS |
| A12 | Missing subtype mapping | val | 1 | True | PASS |
| A13 | Both audit+quarantine deleted | val | 1 | True | PASS |
| A14 | Audit person deleted | val | 1 | True | PASS |
| A15 | Quarantine person deleted | val | 1 | True | PASS |
| A16 | Fake person in audit | val | 1 | True | PASS |
| A17 | Corrupt quarantine(gen) | gen | 1 | True | PASS |
| A18 | Missing quarantine(gen) | gen | 1 | True | PASS |
| A19 | Single hypothesis ambiguity | val | 1 | True | PASS |
| A20 | Dup subtype ambiguity | val | 1 | True | PASS |
| A21 | Missing D2 snapshot(gen) | gen | 1 | True | PASS |
| A22 | Zeroed D2 hash | val | 1 | True | PASS |
| A23 | Bad JSON in adapters | val | 1 | True | PASS |
| A24 | Dup adapter id | val | 1 | True | PASS |
| A25 | Remove adapter | val | 1 | True | PASS |
| A26 | Wrong disposition | val | 1 | True | PASS |
| A27 | Missing package | val | 1 | True | PASS |
| A28 | Zeroed artifact hash | val | 1 | True | PASS |
| A29 | Wrong package count | val | 1 | True | PASS |
| A30 | Tampered CSR | val | 1 | True | PASS |
| A31 | Zeroed CSH | val | 1 | True | PASS |
| A32 | Wrong coverage | val | 1 | True | PASS |
| A33 | Missing coverage | val | 1 | True | PASS |
| A34 | Tampered source lock | val | 1 | True | PASS |
| A35 | Missing source lock | val | 1 | True | PASS |
| A36 | Wrong adapter_id | val | 1 | True | PASS |
| A37 | Missing d2_family | val | 1 | True | PASS |
| A38 | Missing gen receipt | val | 1 | True | PASS |
| A39 | CONTEXT_ONLY w family | val | 1 | True | PASS |
| A40 | UNMAPPED empty note | val | 1 | True | PASS |
| A41 | Family-only w subtype | val | 1 | True | PASS |
| A42 | Stale TBD note | val | 1 | True | PASS |

## Summary
- **Total:** 42
- **Passed:** 42
- **Failed:** 0
- **Adversarial:** 42 (required >= 40)

## Results JSON SHA-256
`992cfcb567066462599319d0a5e58321bd92fa27ca1cb19680ec0683b88a4847`

## Completion
QCLAW_E20_PR100_MACHINE_EVIDENCE_ARCHIVE_INDEPENDENCE_AND_RECEIPT_FRESHNESS_READY_FOR_GPT_REVIEW