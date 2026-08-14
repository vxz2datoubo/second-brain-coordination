# QCLAW R60 — P2 Retrieval Adversarial Benchmark

## Task identity (frozen)

- task_id: `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60`
- repository: `vxz2datoubo/second-brain-coordination`
- target_agent: QCLAW (alias Q/QQ)
- route_epoch: 60  ·  mode: goal  ·  status: READY  ·  merge_authorized: false
- planned_branch: `qclaw/p2-retrieval-adversarial-benchmark-r60`
- active_issue: 296
- completion_signal: `QCLAW_P2_RETRIEVAL_ADVERSARIAL_BENCHMARK_R60_READY_FOR_GPT_REVIEW`
- audited_head (branch base): `33b3e0fa310ccb72b32c99f125bdacc6cb894892`

## Role (locked)

QCLAW is the **P2 batch evaluation factory** and **candidate evidence producer**,
**NOT** the runtime authority and **NOT** the final semantic judge. QCLAW output
is CANDIDATE_ONLY. GPT remains semantic/governance authority; Codex remains
runtime implementer. This benchmark exists to help GPT test Codex P2.1/P2.2
without modifying Codex runtime.

## Deliverables (all task-owned, under this program directory)

```
benchmark/schema.py                       # case contract + frozen canonical-contract registry
benchmark/generate_cases.py               # deterministic case generator
benchmark/cases/benchmark_cases.json      # 90-case corpus (PUBLIC_SAFE_SYNTHETIC)
benchmark/harness/run_benchmark.py        # read-only harness (grades runnable cases)
benchmark/coverage_matrix.py              # coverage matrix generator
evidence/harness_results.json             # machine evidence (60/60 runnable PASS)
evidence/coverage_matrix.json/.md         # dimension x slice coverage
```

## Benchmark scale & dedup

- **total cases: 90** (within the 80–120 baseline target; no quota-burning stretch)
- **dedup method:** case_id is the primary key; all 90 case_ids unique (verified).
  Content dedup is semantic-by-construction: each case targets a distinct
  contract clause / distinct forbidden outcome / distinct fixture. No two cases
  assert the same (contract, probe, forbidden) tuple.
- runnable: **60** (gradable against current Phase-3 runtime today)
- spec-pending: **30** (P2.2/P2.3/P2.4 spec that has no runtime yet — graded only
  after Codex lands the slice; traced to R116 plan / R117 route)

## Coverage by dimension (11/11 required)

| dimension | total | runnable | pending |
|---|---|---|---|
| scope_isolation_cross_domain_denial | 13 | 11 | 2 |
| current_historical_valid_at | 12 | 9 | 3 |
| stale_revoked_superseded_no_resurrection | 12 | 11 | 1 |
| channel_admission_parity | 8 | 7 | 1 |
| hidden_disallowed_relation_conflict_endpoint | 5 | 5 | 0 |
| synthetic_aggregate_no_double_vote | 4 | 1 | 3 |
| support_and_counter_alternative_coverage | 4 | 3 | 1 |
| material_unknown_and_no_evidence_abstain | 7 | 7 | 0 |
| provenance_redaction_no_raw_pointer_body | 7 | 5 | 2 |
| deterministic_ordering_dedup_budget | 9 | 4 | 5 |
| prompt_injection_secret_fail_closed | 9 | 7 | 2 |

## Coverage by P2 slice

| slice | total | runnable | pending |
|---|---|---|---|
| P2.1 | 64 | 57 | 7 |
| P2.2 | 18 | 3 | 15 |
| P2.3 | 5 | 0 | 5 |
| P2.4 | 3 | 0 | 3 |

## Machine evidence

- harness_result: **60 runnable PASS / 0 FAIL / 0 ERROR** (against the checked-out
  Phase-3 runtime, head 33b3e0f, Python 3.13).
- The 30 spec-pending cases are explicitly NOT graded (no runtime exists); they
  carry `runnable=false` and their expected outcome is traced to the R116 plan /
  R117 route text.

## Canonical-contract traceability

Every expected outcome references `canonical_contract_source` ∈ frozen registry
(schema.py), with repo-relative path + git blob SHA verified against the tree:

- retrieval.py        `40a3b50f…`
- memory_store.py     `e13b2e8f…`
- conversation_memory.py `124e2de7…`
- learning_packet.py  `4d900bdc…`
- canonical.py        `344b929c…`
- R116 P2 plan (md)   `fc4193ba…`
- R117 P2.1 route     `4257b3f6…`
- R60 route           `94209274…`

## Hard boundaries (verified)

- PHASE-3 src/** NOT edited (read-only execution only) ✅
- Codex branches NOT touched ✅
- No second memory/retrieval runtime (harness imports canonical modules) ✅
- PUBLIC_SAFE_SYNTHETIC only (all fixtures `synthetic://`) ✅
- REAL_PRIVATE_EXECUTION_NOT_RUN ✅
- FORMAL_PROMOTION_LOCKED (authority_level stays CANDIDATE_ONLY) ✅
- No scheduler / MCP / Gateway / QCLAW runtime dependency ✅
- No security/ACL/repo-visibility changes ✅
- No trading/accounts/funds/orders ✅
- No self-merge or authority upgrade ✅
