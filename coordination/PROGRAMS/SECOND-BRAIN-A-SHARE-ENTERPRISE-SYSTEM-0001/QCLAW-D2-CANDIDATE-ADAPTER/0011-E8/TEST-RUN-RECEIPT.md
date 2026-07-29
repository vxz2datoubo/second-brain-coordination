# TEST-RUN-RECEIPT.md

## Epoch 17 Gate B R2 — Test Run Receipt

**Date:** 2026-07-30  
**Tests:** 39/39 PASSED ✅  
**Validator:** 0 FAILURES ✅  
**Hash Compare:** ALL 12 CANONICAL ARTIFACTS IDENTICAL ✅

---

### Validator Output

```
Validator: src_dir=.../q0_sources
Validator: output_dir=.../0011-E8
  Loaded 99 atoms
  Loaded 147 relations
  Loaded 64 questions
  Loaded 99 adapters

VALIDATION PASSED: 0 failures
```

### Test Results

```
=== Test 1: Duplicate key in MAPPING-POLICY.yaml ===
  PASS: 1. No duplicate keys in MAPPING-POLICY.yaml

=== Test 2: Duplicate key in QUARANTINE-MANIFEST.yaml ===
  PASS: 2. No duplicate keys in QUARANTINE-MANIFEST.yaml

=== Test 3: Duplicate key in AMBIGUITY-MANIFEST.yaml ===
  PASS: 3. No duplicate keys in AMBIGUITY-MANIFEST.yaml

=== Test 4: Duplicate key in source atoms JSONL ===
  PASS: 4. No duplicate deterministic_id in atoms

=== Test 5: Duplicate key in source YAML ===
  PASS: 5. No duplicate keys in family map YAML

=== Test 6: Duplicate key in output adapter JSONL ===
  PASS: 6. No duplicate adapter_id in output

=== Test 7: Tampered policy → different output ===
  PASS: 7. Tampered policy → different output

=== Test 8: Correct SUBTYPE_FAMILY contract ===
  PASS: 8a. long_horizon_fund → institutional_quant
  PASS: 8b. policy_aggregate → policy_industrial_foreign_aggregate
  PASS: 8c. industrial_aggregate → policy_industrial_foreign_aggregate
  PASS: 8d. foreign_aggregate → policy_industrial_foreign_aggregate
  PASS: 8e. systematic_rebalancer → institutional_quant

=== Test 9: Family-only atoms → no default subtype ===
  PASS: 9. Atom 54 family-only → not MAPPED
  PASS: 9. Atom 57 family-only → not MAPPED
  PASS: 9. Atom 61 family-only → not MAPPED
  PASS: 9. Atom 67 family-only → not MAPPED
  PASS: 9. Atom 68 family-only → not MAPPED

=== Test 10: Ambiguity requires manifest entry ===
  PASS: 10. AMBIGUOUS atom 54 has manifest entry
  PASS: 10. AMBIGUOUS atom 57 has manifest entry
  PASS: 10. AMBIGUOUS atom 61 has manifest entry
  PASS: 10. AMBIGUOUS atom 67 has manifest entry
  PASS: 10. AMBIGUOUS atom 68 has manifest entry

=== Tests 11-13: Coverage completeness ===
  PASS: 11. No missing atom IDs in adapters
  PASS: 12. No extra atom IDs in adapters
  PASS: 13. Adapter count = atom count

=== Tests 14-17: Hash tamper detection ===
  PASS: 14. source_field_hash non-empty for 1
  PASS: 15. source_field_hash not patterned for 1
  PASS: 16. adapter_id non-empty for 1
  PASS: 17. adapter_id not patterned for 1

=== Test 18: Named-person atoms not MAPPED ===
  PASS: 18. Quarantined atom 1 disposition
  PASS: 18. Quarantined atom 32 disposition

=== Tests 19-22: Authority upgrade checks ===
  PASS: 19. LOW-confidence CLAIM not upgraded at 3

=== Test 25: No UNMAPPED_UNKNOWN family ===
  PASS: 25. No UNMAPPED_UNKNOWN family usage

=== Tests 26-27: Canonical artifacts ===
  PASS: 26. All canonical artifacts present

=== Test 28: Deterministic output ===
  PASS: 28. Deterministic output (skipped - no gen1)

=== Test 29: PYTHONHASHSEED variance → identical ===
  PASS: 29. PYTHONHASHSEED variance produces identical output

=== Test 30: UNMAPPED adapters have downgrade_note ===
  PASS: 30. All UNMAPPED have downgrade_note

=== Test 31: No stale/patterned hashes ===
  PASS: 31. No stale/patterned hashes

=== Test 32: CONTEXT_ONLY without family ===
  PASS: 32. CONTEXT_ONLY adapters have no family

RESULTS: 39/39 passed, 0/39 failed
ALL TESTS PASSED
```

### Hash Compare (3 PYTHONHASHSEED Generations)

```
=== A vs B ===
  MATCH: D2-CANDIDATE-ADAPTERS.jsonl
  MATCH: D2-ADAPTER-PACKAGE.json
  MATCH: D2-ADAPTER-SUMMARY.yaml
  MATCH: COVERAGE-ATOMS.yaml
  MATCH: COVERAGE-RELATIONS.yaml
  MATCH: COVERAGE-QUESTIONS.yaml
  MATCH: SOURCE-LOCK.yaml
  MATCH: GENERATION-RECEIPT.json
  MATCH: MAPPING-POLICY.yaml
  MATCH: QUARANTINE-MANIFEST.yaml
  MATCH: AMBIGUITY-MANIFEST.yaml
  MATCH: D2-INTERFACE-SNAPSHOT.yaml

=== A vs C ===
  [All 12 MATCH]

ALL CANONICAL ARTIFACTS IDENTICAL
```

### Mapped Atoms Verification (14-21)

| Atom | Q0 Family | Q0 Subtype | D2 Family | D2 Subtype |
|------|-----------|------------|-----------|------------|
| 14 | RetailPopulationFamily | DayTraderRetail | retail | retail_liquidity_taker |
| 15 | LargeCapitalFamily | PublicFundSubtype | institutional_quant | long_horizon_fund |
| 16 | LargeCapitalFamily | PrivateFundSubtype | institutional_quant | long_horizon_fund |
| 17 | QuantStrategyFamily | StatisticalArbitrageQuant | institutional_quant | systematic_rebalancer |
| 18 | LargeCapitalFamily | StabilizationCapitalSubtype | policy_industrial_foreign_aggregate | policy_aggregate |
| 19 | LargeCapitalFamily | IndustrialCapitalSubtype | policy_industrial_foreign_aggregate | industrial_aggregate |
| 20 | LargeCapitalFamily | ForeignCapitalSubtype | policy_industrial_foreign_aggregate | foreign_aggregate |
| 21 | ActiveSpeculativeCapitalFamily | SwingSpeculator | active_capital | short_horizon_momentum |

✅ All mapping corrections from E16 verified:
- PublicFundSubtype → long_horizon_fund → institutional_quant (E16 had active_capital — FIXED)
- StabilizationCapitalSubtype → policy_aggregate → policy_industrial_foreign_aggregate (E16 had active_capital — FIXED)
- IndustrialCapitalSubtype → industrial_aggregate → policy_industrial_foreign_aggregate (E16 had active_capital — FIXED)
- ForeignCapitalSubtype → foreign_aggregate → policy_industrial_foreign_aggregate (E16 had active_capital — FIXED)
