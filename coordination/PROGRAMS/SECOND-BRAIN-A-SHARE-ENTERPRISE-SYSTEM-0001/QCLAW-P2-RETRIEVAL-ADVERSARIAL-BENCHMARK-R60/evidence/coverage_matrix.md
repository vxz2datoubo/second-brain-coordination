# R60 Coverage Matrix — current remediation

- total cases: 90
- runnable: 60
- spec-pending retained: 30
- current runnable verdicts: **58 PASS / 2 FAIL / 0 ERROR**
- targeted blocker/current-contract regressions: **5 PASS / 0 FAIL / 0 ERROR**
- historical 60/60: **REJECTED_INVALID_FALSE_GREEN**
- NEEDS_REVALIDATION: `r60-013`, `r60-025`

| dimension | total | runnable | pending | pass | fail |
|---|---:|---:|---:|---:|---:|
| scope_isolation_cross_domain_denial | 13 | 13 | 0 | 13 | 0 |
| current_historical_valid_at | 12 | 11 | 1 | 11 | 0 |
| stale_revoked_superseded_no_resurrection | 12 | 9 | 3 | 8 | 1 |
| channel_admission_parity | 8 | 3 | 5 | 3 | 0 |
| hidden_disallowed_relation_conflict_endpoint | 5 | 2 | 3 | 2 | 0 |
| synthetic_aggregate_no_double_vote | 4 | 1 | 3 | 1 | 0 |
| support_and_counter_alternative_coverage | 4 | 0 | 4 | 0 | 0 |
| material_unknown_and_no_evidence_abstain | 7 | 4 | 3 | 3 | 1 |
| provenance_redaction_no_raw_pointer_body | 7 | 2 | 5 | 2 | 0 |
| deterministic_ordering_dedup_budget | 9 | 7 | 2 | 7 | 0 |
| prompt_injection_secret_fail_closed | 9 | 8 | 1 | 8 | 0 |

The original slice/runnable labels are retained as corpus material. Canonical P2 has evolved, so the 30 original pending cases are not bulk-promoted without case-by-case revalidation.

## Current revalidation contracts
- current `retrieval.py`: `9e896cc56aa0a8274a83615118c91f233f3d0040`
- R118 public-report route: `b86d6a1060317fce3cccecae1dc45b04a7f46c4e`
- R119 endpoint-safe route: `f3890a960636597e6515c3154f17bb33f3e78327`
