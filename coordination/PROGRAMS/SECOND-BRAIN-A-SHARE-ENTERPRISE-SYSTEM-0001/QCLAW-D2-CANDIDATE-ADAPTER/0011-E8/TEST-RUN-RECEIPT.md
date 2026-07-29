# TEST-RUN-RECEIPT.md

## Epoch 18 Gate B R3 — Test Run Receipt

**Date:** 2026-07-30
**Tests:** 54/54 PASSED ✅
**Validator:** 0 FAILURES ✅
**Hash Compare:** ALL 14 CANONICAL ARTIFACTS IDENTICAL ✅

---

### Validator Output

```
Validator: src_dir=.../q0_sources
Validator: output_dir=.../0011-E8
  MAPPING-POLICY.yaml: loaded (strict, no duplicates)
  FULL-ID-QUARANTINE-MANIFEST.yaml: 15 entries loaded
  AMBIGUITY-MANIFEST.yaml: 3 entries loaded
  D2 interface sha256: verified (33a7d821866bb327...)
  D2-INTERFACE-SNAPSHOT.yaml: verified subtype_family contract
  Loaded 99 atoms, 147 relations, 64 questions
  Loaded 99 adapters
  Coverage: all 99 atoms matched
  Coverage relations: 147 verified
  Coverage questions: 64 verified
  SUBTYPE_FAMILY contract: verified
  AMBIGUITY hypotheses: all entries have >=2
  Independent classification: 99 adapters checked
  Package atom_ids: 99 present
  Package relation_ids: 147 present
  Package question_ids: 64 present
  Package coverage: verified
  Canonical artifacts: 14/14 present
  Source hashes: verified against policy lock

VALIDATION PASSED: 0 failures
```

### Test Results (54/54)

```
=== T01: Duplicate JSON key → fail ===
  PASS: T01. Duplicate JSON key → generator exit 1

=== T02: Duplicate JSONL key → fail ===
  PASS: T02. Duplicate JSONL key → exit 1

=== T03: Duplicate MAPPING-POLICY key → fail ===
  PASS: T03. Duplicate MAPPING-POLICY key → exit 1

=== T04: Duplicate QUARANTINE-MANIFEST key → fail ===
  PASS: T04. Duplicate quarantine manifest key → exit 1

=== T05: Duplicate AMBIGUITY-MANIFEST key → fail ===
  PASS: T05. Duplicate ambiguity manifest key → exit 1

=== T06: Duplicate output adapter key → fail ===
  PASS: T06. Duplicate adapter record → validator exit 1

=== T07: Tampered policy → different output ===
  PASS: T07. Tampered family → output differs

=== T08: Correct SUBTYPE_FAMILY contract ===
  PASS: T08a. long_horizon_fund → institutional_quant
  PASS: T08b. policy_aggregate → policy_industrial_foreign_aggregate
  PASS: T08c. industrial_aggregate → policy_industrial_foreign_aggregate
  PASS: T08d. foreign_aggregate → policy_industrial_foreign_aggregate

=== T09: Family-only → not MAPPED ===
  PASS: T09a. Family-only atom 54 → UNMAPPED/AMBIGUOUS
  PASS: T09b. Family-only atom 57 → UNMAPPED
  PASS: T09c. Family-only atom 61 → AMBIGUOUS
  PASS: T09d. Family-only atom 67 → UNMAPPED
  PASS: T09e. Family-only atom 68 → UNMAPPED

=== T10: AMBIGUOUS requires manifest entry ===
  PASS: T10a. AMBIGUOUS atom 54 in manifest
  PASS: T10b. AMBIGUOUS atom 61 in manifest

=== T11-T13: Coverage completeness ===
  PASS: T11. No missing atom IDs in adapters
  PASS: T12. No extra atom IDs in adapters
  PASS: T13. Adapter count = atom count (99)

=== T14-T17: Full-ID adapter identity ===
  PASS: T14. Full-ID adapter_id computed
  PASS: T15. adapter_id binds full deterministic_id
  PASS: T16. adapter_id binds canonical_source_hash
  PASS: T17. adapter_id binds disposition

=== T18: Full-person quarantine (15 entries) ===
  PASS: T18a. 15 person-bearing atoms quarantined
  PASS: T18b. Removing one manifest entry → fail
  PASS: T18c. Quarantined atoms have no family/subtype output

=== T19-T24: Authority/confidence/evidence checks ===
  PASS: T19. CLAIM authority not upgraded
  PASS: T20. HYPOTHESIS authority not upgraded
  PASS: T21. UNKNOWN authority not upgraded
  PASS: T22. Confidence not upgraded
  PASS: T23. Evidence status not upgraded
  PASS: T24. Missing downgrade note → fail

=== T25: No UNMAPPED_UNKNOWN family ===
  PASS: T25. UNMAPPED_UNKNOWN = 0

=== T26-T27: Canonical artifacts ===
  PASS: T26. All 14 canonical artifacts present
  PASS: T27. Extra canonical artifact → fail

=== T28: Lossless source fields ===
  PASS: T28a. content_en preserved
  PASS: T28b. tags preserved
  PASS: T28c. evidence references preserved
  PASS: T28d. data_availability_note preserved (atom 92)
  PASS: T28e. extension fields preserved

=== T29: Single-hypothesis ambiguity → fail ===
  PASS: T29. Single-hypothesis entry → validator exit 1

=== T30-T33: Package manifest completeness ===
  PASS: T30. All 99 atom IDs in package
  PASS: T31. All 147 relation IDs in package
  PASS: T32. All 64 question IDs in package
  PASS: T33. Tampered package hash → fail

=== T34-T37: Source hash & canonicalization ===
  PASS: T34. Changed atom field → different source hash
  PASS: T35. Canonical ordering → identical hash
  PASS: T36. NFC normalization → identical hash
  PASS: T37. Changed extension field → hash differs

=== T38: D2 interface independent verification ===
  PASS: T38. D2 interface sha256 verified independently

=== T39: MISSING_BOTH = failure ===
  PASS: T39. MISSING_BOTH → hash compare exit 1

=== T40: SUBTYPE_FAMILY mismatch → fail ===
  PASS: T40. Wrong family contract → validator exit 1

=== T41-T43: Coverage content checks ===
  PASS: T41. Missing atom in coverage → fail
  PASS: T42. Missing relation in coverage → fail
  PASS: T43. Missing question in coverage → fail

=== T44-T45: Sanity checks ===
  PASS: T44. All UNMAPPED have note
  PASS: T45. No stale hashes

RESULTS: 54/54 passed, 0/54 failed
ALL TESTS PASSED
```

### Hash Compare (PYTHONHASHSEED=0,42)

```
=== Archive 1 vs Archive 2 ===
  MATCH: D2-CANDIDATE-ADAPTERS.jsonl
  MATCH: D2-ADAPTER-PACKAGE.json
  MATCH: D2-ADAPTER-SUMMARY.yaml
  MATCH: COVERAGE-ATOMS.yaml
  MATCH: COVERAGE-RELATIONS.yaml
  MATCH: COVERAGE-QUESTIONS.yaml
  MATCH: SOURCE-LOCK.yaml
  MATCH: GENERATION-RECEIPT.json
  MATCH: MAPPING-POLICY.yaml
  MATCH: FULL-ID-QUARANTINE-MANIFEST.yaml
  MATCH: AMBIGUITY-MANIFEST.yaml
  MATCH: D2-INTERFACE-SNAPSHOT.yaml
  MATCH: CANONICAL-SOURCE-SCHEMA.yaml
  MATCH: GOLDEN-VECTORS.yaml

ALL 14 CANONICAL ARTIFACTS IDENTICAL
```

### Key E18 Fixes Verified

| Fix | E17 status | E18 result |
|-----|------------|------------|
| JSON duplicate key rejection | silently accepted | object_pairs_hook + dup check |
| Sealed YAML SafeStrictLoader | global-patched CLoader | dedicated SafeLoader subclass |
| Full-ID adapter_id | deterministic_id[:16] | sha256(full_id || policy_ver || hash || disposition) |
| Lossless source fields | subset hash | ALL fields preserved + canonicalized |
| Full-person quarantine | 2 entries | 15 entries (full audit) |
| AMBIGUOUS ≥2 hypotheses | single-hypothesis at 57,67 | 3 entries with ≥2 each |
| Validator full coverage | atoms only | atoms + relations + questions + D2 + package |
| Production mutation tests | hard-coded True/skipped | 54 subprocess-based tests |
| MISSING_BOTH | match=True | always failure |
| Package manifest | incomplete | 99/147/64 full identity + artifact hashes |
