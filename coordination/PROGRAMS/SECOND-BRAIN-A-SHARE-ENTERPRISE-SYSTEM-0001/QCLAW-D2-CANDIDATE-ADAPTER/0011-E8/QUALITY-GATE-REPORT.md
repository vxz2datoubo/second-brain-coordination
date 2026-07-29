# QUALITY-GATE-REPORT.md — Epoch 16 Gate B R1

## Gate B Quality Gate Report

**Task:** QCLAW-PR100-SOURCE-DERIVED-SEMANTIC-MAPPING-AND-EXECUTABLE-EVIDENCE-CLOSURE-0018-E16
**Route Epoch:** 16
**Schema Version:** 23.0
**Timestamp:** 2026-07-29T23:50:00+08:00

## Defect Remediation

| ID   | Defect | Status | Evidence |
|------|--------|--------|----------|
| D01  | Atom-index classification removed | FIXED | Source-field-driven classify_atom() in generate_adapters.py |
| D02  | Validator covers 147 relations, 64 questions | FIXED | validate_source_set_equality() verifies exact coverage |
| D03  | Source lock SHA256 comparison | FIXED | lock_sources() compares actual vs EXPECTED_SOURCE_LOCK |
| D04  | Negative tests call real entry points | FIXED | run_negative_tests.py imports generator/validator |
| D05  | PYTHONHASHSEED in shell env | FIXED | $env:PYTHONHASHSEED set in PowerShell before each run |
| D06  | Receipt-only commit (pending post-test) | PENDING | Will push receipt-only commit |
| D07  | Lossless source field preservation | FIXED | compute_source_field_hash() + validator step 8 |

## Gate B Defect Remediation (E16-B01~B07)

| ID   | Defect | Status | Evidence |
|------|--------|--------|----------|
| B01  | Atoms 14-20 incorrectly CONTEXT_ONLY | FIXED | All 7 atoms 14-20 now MAPPED with correct D2 family/subtype |
| B02  | Full coverage validation | FIXED | Validator step 2: 99 atoms, 147 relations, 64 questions |
| B03  | Source lock comparison | FIXED | Validator step 1: all 4 source files compared |
| B04  | Real entry points in negative tests | FIXED | 8 negative tests calling real generator/validator |
| B05  | PYTHONHASHSEED shell env | FIXED | Script sets via os.environ after shell $env |
| B06  | Receipt commit (post-test) | PENDING | Will follow tested commit |
| B07  | Lossless source field preservation | FIXED | source_field_hash verified in step 8 |

## Results Summary

- **Generator:** 3 runs, all exit=0, all output IDENTICAL byte-for-byte
- **Validator:** 0 failures, 0 warnings
- **Adapters:** 99 (26 MAPPED, 4 AMBIGUOUS, 39 CONTEXT_ONLY, 12 UNMAPPED, 18 PERSON_IDENTITY_QUARANTINED)
- **Negative Tests:** 8/8 correct rejection (all exit != 0)
- **Adversarial Tests:** 22/22 caught by validator
- **Archive Byte Identity:** 3/3 files IDENTICAL across 3 runs
- **UNMAPPED_UNKNOWN:** Never emitted as family (confirmed in step 3)
- **Atoms 14-20:** All MAPPED (B01 fixed)
