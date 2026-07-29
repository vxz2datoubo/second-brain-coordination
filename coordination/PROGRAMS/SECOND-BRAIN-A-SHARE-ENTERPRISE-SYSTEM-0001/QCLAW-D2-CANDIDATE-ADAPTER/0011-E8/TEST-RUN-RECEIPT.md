# D2 Candidate Adapter Builder — Epoch 15 Gate B
## TEST-RUN-RECEIPT

### Task Identification
- Task ID: QCLAW-PR100-CANONICAL-D2-ONTOLOGY-TRANSLATION-AND-GENERATION-DETERMINISM-CLOSURE-0017-E15
- Route Epoch: 15
- Schema Version: 22.0
- Architecture: Generator-first
- Signal: QCLAW_E15_PR100_CANONICAL_D2_TRANSLATION_AND_GENERATION_DETERMINISM_READY_FOR_GPT_REVIEW
- Branch: qclaw/q0-d2-candidate-adapter-0011-e8
- PR #100 head: 76d447f0

### Source Q0 Package (immutable, from e54e04b)
| File | SHA-256 | Size (bytes) |
|---|---|---|
| KNOWLEDGE-ATOMS.jsonl | 47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d | 59631 |
| KNOWLEDGE-RELATIONS.jsonl | 39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a | 52892 |
| ADVERSARIAL-QUESTION-SET.jsonl | 2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927 | 40889 |
| PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml | f526d66f4c6d2de1b904607e07fa92d7691a00a4ebaa5d1844bac1378d645d25 | 7514 |

### Generator Scripts (this delivery)
| File | SHA-256 | Size (bytes) |
|---|---|---|
| generate_adapters.py | bfb939a203158d80c2fd4d0569024852a4995ac947251782b7a2108b98e5918e | 19298 |
| validate_adapters.py | 62901ab4c271020934572cb04dcc1f7c543c4b06aa7319f0e417a510703b795b | 16245 |
| hash_verify.py | 69d44541e3781fdafc9b5b94383e459ea57f564efc01058ce22794c6e9839f9b | 1872 |
| run_negative_tests.py | aba3b8f214352f2af444dbaf90c03764148c3034a504e84eb372ff6d5be48eb4 | 16220 |
| generate_adversarial_tests.py | 096c9d9e74535ca7f471cb175561ff21a2d47c89c20a234eff3be101856e06f7 | 5727 |

### Generated Outputs (canonical, byte-identical across 3 runs)
| File | SHA-256 | Size (bytes) |
|---|---|---|
| D2-CANDIDATE-ADAPTERS.jsonl | 85dd811a27073e9755e44b53206e525cb4d6a478a4f1dfb15450b2fe80b90c56 | 38566 |
| D2-ADAPTER-SUMMARY.yaml | 5d1d3f655da23c0968c744b1725161d7b6a0ea29dd6f95e9bbf2fa92b4d4c252 | 1018 |
| D2-ADAPTER-PACKAGE.json | 3c47a6a01081685d87326631a205bef01b827e41aaf852705e0e810dbe6c56a5 | 48328 |
| GENERATION-RECEIPT.json | ab271d62b616584f3e325d31591d87844aa23a94cbae601c8b8e18831e4aa484 | 1320 |

### Adapter Disposition Summary
| Disposition | Count |
|---|---|
| MAPPED | 7 |
| UNMAPPED | 4 |
| AMBIGUOUS | 7 |
| CONTEXT_ONLY | 63 |
| PERSON_IDENTITY_QUARANTINED | 18 |
| **Total** | **99** |

### D2 Participant Subtype Distribution (MAPPED only)
| Subtype | Count |
|---|---|
| retail_liquidity_taker | 2 |
| retail_anchored_holder | 1 |
| systematic_rebalancer | 1 |
| long_horizon_fund | 1 |
| event_driven_active | 1 |
| short_horizon_momentum | 1 |
| **Total** | **7** |

### Validation Results
- validate_adapters.py: 0 failures, 0 warnings — ALL VALIDATIONS PASSED
- hash_verify.py: ALL OUTPUTS BYTE-IDENTICAL across 3 runs (hashseed 0, 42, 137)
- run_negative_tests.py: 12/12 negative tests passed (all defects correctly caught)
- Adversarial test cases: 64 generated from Q0 question set

### Negative Test Fixtures (all caught)
- duplicate_key_json.json — Duplicate JSON key detection
- duplicate_key_jsonl.jsonl — Duplicate JSONL key detection
- duplicate_key_yaml.yaml — Duplicate YAML key detection
- unmapped_unknown_as_family.jsonl — UNMAPPED_UNKNOWN family forbiddance
- invalid_family.jsonl — Invalid D2 family rejection
- invalid_subtype.jsonl — Invalid D2 subtype rejection
- subtype_family_mismatch.jsonl — Subtype-family mismatch detection
- market_structure_to_named_person.jsonl — MARKET_STRUCTURE forced mapping + CLAIM upgrade + named person quarantine leak
- missing_source_atom.jsonl — Orphan source reference detection
- duplicate_deterministic_id.jsonl — Duplicate adapter ID detection
- hash_size_mismatch.jsonl — Content/hash variance detection
- generation_differs_between_runs — Byte comparison of 3 independent runs

### D2 Canonical Contract Compliance
- D2 ParticipantFamily values: retail, institutional_quant, active_capital, policy_industrial_foreign_aggregate
- D2 ParticipantSubtype values: all 9 subtypes from d2_game_core.py @ d6f9e2e4
- SUBTYPE_FAMILY consistency: all validated
- HARD RULE: UNMAPPED_UNKNOWN not emitted as any family field

### Generation Commands
```
python generate_adapters.py --q0-dir Q0_DIR --output-dir output --hash-seed 0
python validate_adapters.py --q0-dir Q0_DIR --output-dir output
python hash_verify.py --run-dirs output output_run2 output_run3
python run_negative_tests.py --fixtures-dir tests/fixtures --q0-dir Q0_DIR
```

### Boundary
- PUBLIC_SAFE / CANDIDATE_ONLY / research_only / NO_TRADE
- NO force push, NO amend, NO rebase
- NO edits to PR #96, Codex D2 core, or other branches
