# QUALITY-GATE-REPORT.md

## Epoch 18 Gate B R3 — Quality Gate Report

**PR**: #100  
**Task ID**: QCLAW-PR100-STRICT-CANONICAL-IDENTITY-LOSSLESS-QUARANTINE-AND-EXECUTABLE-EVIDENCE-CLOSURE-0020-E18  
**Schema**: 25.0  
**Route Epoch**: 18  
**Date**: 2026-07-30  

---

### Gate Status: PASSED ✅

| Check | Result |
|-------|--------|
| Generator exits 0 | ✅ PASS |
| Validator exits 0 (0 failures) | ✅ PASS |
| 54 production tests | ✅ 54/54 PASSED |
| Deterministic output (PYTHONHASHSEED 0=42) | ✅ IDENTICAL |
| D2 interface sha256 verified | ✅ 33a7d821... |
| All 14 canonical artifacts present | ✅ PASS |
| Full-ID quarantine (15 Liu Xin atoms) | ✅ PASS |
| Ambiguity ≥2 hypotheses (3 entries) | ✅ PASS |
| Source hashes match policy lock | ✅ PASS |
| No stale/patterned hashes | ✅ PASS |
| MISSING_BOTH = FAILURE | ✅ E18-B09 |

---

### Disposition Summary

| Disposition | Count |
|-------------|-------|
| MAPPED | 25 |
| AMBIGUOUS | 3 |
| CONTEXT_ONLY | 38 |
| UNMAPPED | 18 |
| PERSON_IDENTITY_QUARANTINED | 15 |
| **Total** | **99** |

---

### 10 Defects Fixed

| ID | Defect | Status |
|----|--------|--------|
| E18-B01 | JSON DUPLICATE KEYS STILL ACCEPTED | ✅ FIXED |
| E18-B02 | YAML LOADER NOT SEALED SAFE-STRICT | ✅ FIXED |
| E18-B03 | ADAPTER IDENTITY TRUNCATES SOURCE ID | ✅ FIXED |
| E18-B04 | SOURCE HASH AND OUTPUT NOT LOSSLESS | ✅ FIXED |
| E18-B05 | NAMED-PERSON QUARANTINE IS INCOMPLETE | ✅ FIXED |
| E18-B06 | AMBIGUITY WITH ONE HYPOTHESIS | ✅ FIXED |
| E18-B07 | VALIDATOR DOES NOT CLOSE PACKAGE AND COVERAGE | ✅ FIXED |
| E18-B08 | PRODUCTION TEST COUNT INCLUDES NON-TESTS | ✅ FIXED |
| E18-B09 | HASH COMPARE MATCHES MISSING_BOTH | ✅ FIXED |
| E18-B10 | PACKAGE MANIFEST INCOMPLETE | ✅ FIXED |

---

### Completion Signal

```
QCLAW_E18_PR100_STRICT_CANONICAL_IDENTITY_LOSSLESS_QUARANTINE_AND_EXECUTABLE_EVIDENCE_READY_FOR_GPT_REVIEW
```


## E22 Gate B R7 - 2026-07-31T08:23:00+08:00

### Status: PASSED - PENDING GPT REVIEW
- **Dual Python:** 3.11.10 42/42, 3.12.10 42/42
- **Commands:** Symbolic (zero hardcoded paths)
- **D05:** Git-archive bound to exact E22 tested commit
- **Receipts:** Machine-generated, runner-SHA-bound
- **actual_result:** EXPECTED_FAIL / UNEXPECTED_FAIL / PASS (safe semantics)


## E23 Gate B R8 - 2026-07-31T23:13:54+08:00
### Status: PASSED (0 failures) - PENDING GPT REVIEW

| Check | 3.11 | 3.13 | Result |
|-------|------|------|--------|
| Generator | exit 0 | exit 0 | PASS |
| Validator | 0 failures | 0 failures | PASS |
| D2 Interface | verified | verified | PASS |
| Receipt | SHA bound | SHA bound | PASS |

- WPDCR: 17 artifacts hash/size verified
- NEG-HIST: E21/E22 evidence retained
- D2: Reconstructed from D2-INTERFACE-SNAPSHOT
