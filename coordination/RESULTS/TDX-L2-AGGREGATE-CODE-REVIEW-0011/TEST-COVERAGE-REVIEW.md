# TEST-COVERAGE-REVIEW

## Test Command

```text
C:\Users\Administrator\miniconda3\python.exe -m unittest tests.test_realtime_l2_aggregate tests.test_foundation_data_governance
```

cwd: `F:\aidanao`

python_version: `3.13.13 | packaged by Anaconda, Inc. | (main, Apr 14 2026, 06:12:50) [MSC v.1942 64 bit (AMD64)]`

exit_code: `0`

stdout:

```text

```

stderr:

```text
...........
----------------------------------------------------------------------
Ran 11 tests in 0.455s

OK

```

## 11 Tests

### test_normalizes_tdx_l2_aggregates_without_promoting_raw_ticks

- purpose: TDX 13 aggregate fields normalize and do not promote raw ticks/orders
- input: 13-field synthetic payload
- assertions: 13 fields, blocked raw caps, vendor_defined Zjl/Zjl_HB
- failure path coverage: partially
- None/empty/0/negative/error/permission coverage: 0 covered for OpenZTBuy only; None/empty/error/permission not covered
- cross-day reset coverage: no
- field semantics version variation coverage: constant version only
- self-proof risk: medium self-proof risk

### test_tdx_snapshot_adapter_declares_l2_aggregates_but_not_true_ddx

- purpose: Adapter declares five-level snapshot and unverified true ddx/raw streams
- input: capability_descriptor()
- assertions: no ddx in snapshot, l2_aggregate partial, raw caps fallback blocked
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: low

### test_low_cost_broker_questions_cover_required_entitlements

- purpose: Outreach questions contain key fields
- input: function output
- assertions: ten_level/raw/order_queue/market_data_only present
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: medium self-proof risk

### test_public_crawler_policy_stays_auxiliary_only

- purpose: Crawler stays auxiliary only
- input: policy dict
- assertions: role and forbidden uses; reliability <0.6
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: medium; threshold not empirically justified

### test_broker_outreach_pack_has_schema_and_scorecard_fields

- purpose: Schema and scorecard contain required columns
- input: JSON and CSV files
- assertions: raw_trade/order/queue/auction fields present
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: low

### test_broker_classifier_keeps_raw_l2_claim_in_review_without_evidence

- purpose: Broker raw claim without evidence stays review
- input: broker reply missing evidence
- assertions: needs_review, candidates not verified
- failure path coverage: yes
- None/empty/0/negative/error/permission coverage: unknown/missing only
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: good

### test_broker_classifier_promotes_complete_reply_only_to_runtime_probe_candidate

- purpose: Complete broker reply reaches probe candidate only
- input: complete broker reply
- assertions: raw_l2_candidate, evidence gaps empty
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: medium; positive path only

### test_historical_replay_adapter_preserves_lineage_and_quality

- purpose: Foundation historical adapter lineage
- input: sample CSV
- assertions: source/lineage/quality/price bars
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: low

### test_capability_negotiation_blocks_sequence_sensitive_analysis

- purpose: Capability negotiation blocks sequence-sensitive mock analysis
- input: MockMbo descriptor
- assertions: no_signal, blocked sequence
- failure path coverage: yes
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: low

### test_data_layer_policies_map_to_current_runtime_boundaries

- purpose: Data layer policies tracked/nontracked and storage targets
- input: root policies
- assertions: raw not git, reports git, runtime immutable
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: low

### test_foundation_report_writes_back_into_mother_system

- purpose: Foundation writeback into temp mother system
- input: temp SuperBrain
- assertions: records and status written
- failure path coverage: no
- None/empty/0/negative/error/permission coverage: no
- cross-day reset coverage: no
- field semantics version variation coverage: no
- self-proof risk: medium; tests writeback in temp only

## Coverage Gaps

- Missing explicit tests for None, empty string, negative numeric values, permission-denied sentinels, and interface error sentinels in aggregate payloads.
- Missing cross-day reset and delta-computation tests.
- Missing field semantics version migration tests.
- Classifier edge cases reveal logic gaps not covered by unit tests: missing timestamp/sequence and no-local-storage can still reach `raw_l2_candidate_needs_runtime_probe`.
- Some tests are self-referential because they assert the current policy constants rather than validating against independent fixtures.