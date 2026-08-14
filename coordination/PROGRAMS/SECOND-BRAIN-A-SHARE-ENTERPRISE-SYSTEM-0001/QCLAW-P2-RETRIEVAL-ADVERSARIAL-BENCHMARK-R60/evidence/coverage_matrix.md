# R60 Coverage Matrix

- total_cases: 90
- runnable: 60  spec_pending: 30  graded: 60
- verdicts: {'PASS': 60}

## By dimension

| dimension | total | runnable | pending | graded |
|---|---|---|---|---|
| scope_isolation_cross_domain_denial | 13 | 13 | 0 | 13 |
| current_historical_valid_at | 12 | 11 | 1 | 11 |
| stale_revoked_superseded_no_resurrection | 12 | 9 | 3 | 9 |
| channel_admission_parity | 8 | 3 | 5 | 3 |
| hidden_disallowed_relation_conflict_endpoint | 5 | 2 | 3 | 2 |
| synthetic_aggregate_no_double_vote | 4 | 1 | 3 | 1 |
| support_and_counter_alternative_coverage | 4 | 0 | 4 | 0 |
| material_unknown_and_no_evidence_abstain | 7 | 4 | 3 | 4 |
| provenance_redaction_no_raw_pointer_body | 7 | 2 | 5 | 2 |
| deterministic_ordering_dedup_budget | 9 | 7 | 2 | 7 |
| prompt_injection_secret_fail_closed | 9 | 8 | 1 | 8 |

## By slice

| slice | total | runnable | pending |
|---|---|---|---|
| P2.1 | 64 | 60 | 4 |
| P2.2 | 18 | 0 | 18 |
| P2.3 | 5 | 0 | 5 |
| P2.4 | 3 | 0 | 3 |

## Canonical contract sources

- PHASE-3/src/integrated_offline_memory/canonical.py: 2
- PHASE-3/src/integrated_offline_memory/conversation_memory.py: 2
- PHASE-3/src/integrated_offline_memory/memory_store.py: 12
- PHASE-3/src/integrated_offline_memory/retrieval.py: 46
- R116-P2/P2-UNIFIED-RETRIEVAL-AND-CONTEXT-BUNDLE-IMPLEMENTATION-PLAN.md: 26
- ROUTES/CODEX-R117-P2-1-UNIFIED-CANDIDATE-ADMISSION.yaml: 2
