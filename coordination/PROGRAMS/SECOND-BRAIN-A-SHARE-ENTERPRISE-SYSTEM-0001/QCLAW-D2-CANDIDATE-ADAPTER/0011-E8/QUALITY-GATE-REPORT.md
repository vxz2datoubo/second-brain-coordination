# QUALITY-GATE-REPORT — Epoch 15 Gate B
## D2 Candidate Adapter Builder: Quality Gate Assessment

### Gate 1: Source Integrity
- Status: PASS
- Q0 atoms SHA-256: 47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d
- Q0 relations SHA-256: 39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a
- Q0 questions SHA-256: 2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927
- Exact source-set equality: 99 atoms = 99 adapters (1:1)

### Gate 2: D2 Contract Compliance
- Status: PASS
- All d2_participant_family values in D2_VALID_FAMILIES
- All d2_participant_subtype values in D2_VALID_SUBTYPES
- All subtype-family relationships validated against SUBTYPE_TO_FAMILY
- HARD RULE: zero UNMAPPED_UNKNOWN family values

### Gate 3: Disposition Rules
- Status: PASS
- Named-person atoms → PERSON_IDENTITY_QUARANTINED (18 atoms)
- MarketStructure atoms → CONTEXT_ONLY (63 atoms)
- Ambiguous cases → AMBIGUOUS with multiple hypotheses (7 atoms)
- Direct mappings → MAPPED (7 atoms)
- No family match → UNMAPPED (4 atoms)
- CLAIM/HYPOTHESIS/UNKNOWN atoms mapped as CANDIDATE_ONLY (downgrade_note present)

### Gate 4: Determinism
- Status: PASS
- 3 independent runs (PYTHONHASHSEED=0,42,137)
- D2-CANDIDATE-ADAPTERS.jsonl: 85dd811a... (byte-identical)
- D2-ADAPTER-SUMMARY.yaml: 5d1d3f65... (byte-identical)
- D2-ADAPTER-PACKAGE.json: 3c47a6a0... (byte-identical)

### Gate 5: Negative Testing
- Status: PASS
- 12/12 negative test fixtures correctly caught defects
- Duplicate key detection: JSON, JSONL, YAML
- UNMAPPED_UNKNOWN forbiddance
- Invalid family/subtype rejection
- Subtype-family mismatch detection
- MARKET_STRUCTURE forced mapping detection
- CLAIM-to-FACT upgrade detection
- Named person quarantine leak detection
- Missing source atom detection
- Duplicate adapter ID detection

### Gate 6: Adversarial Coverage
- Status: PASS
- 64 adversarial test cases generated from Q0 question set
- 8 categories: identity_overreach, market_outlook_leakage, correlation_to_causation,
  participant_family_misclassification, access_advantage_inflation, narrative_certainty,
  temporal_smuggling, subtype_mapping_correctness

### Gate 7: Boundary Compliance
- Status: PASS
- PUBLIC_SAFE / CANDIDATE_ONLY / research_only / NO_TRADE
- No named person agent identity emitted
- No price-direction predictions
- No trade signals

### Overall Quality Gate
- Status: PASS — READY FOR GPT REVIEW
- Signal: QCLAW_E15_PR100_CANONICAL_D2_TRANSLATION_AND_GENERATION_DETERMINISM_READY_FOR_GPT_REVIEW
