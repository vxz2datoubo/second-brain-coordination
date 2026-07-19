# CLASSIFIER-LIFECYCLE-RECOMMENDATION

## Current Four-State Design

Current states:

- `insufficient`
- `needs_review`
- `raw_l2_candidate_needs_runtime_probe`
- `blocked`

This is adequate for an experimental first gate, but too coarse for production governance.

## Recommended Future Lifecycle

Adopt the proposed lifecycle in a future task, not in this review:

- `insufficient`
- `needs_documentation`
- `qualified_for_readonly_probe`
- `runtime_probe_failed`
- `runtime_verified_research_only`
- `approved_for_governed_integration`
- `blocked`

## Design Findings

1. SDK contains trading methods: current classifier does not automatically block merely because an SDK contains trading methods. It blocks when `account_or_order_functions_required=yes`. This is directionally correct.
2. Read-only isolation: future classifier should explicitly model `readonly_process_supported`, `method_whitelist_supported`, and `separate_market_data_entitlement`.
3. Blocked condition: should only apply when market data requires account/asset/position/trading-password/order linkage, or when license forbids automation/storage.
4. Level-2 marketing claim: current classifier is too permissive for `ten_level_book=yes`; it can add `TEN_LEVEL_SNAPSHOT` to allowed capabilities without requiring official docs.
5. Required evidence: current classifier requires docs/sample for raw L2 candidates, but does not require exchange timestamp and sequence to be present before `raw_l2_candidate_needs_runtime_probe`.

## Must-Fix Before Formal Phase 1

- Missing exchange timestamp and sequence should prevent raw L2 probe-candidate status.
- `local_storage_allowed=no` should prevent any route requiring replay/local raw storage from reaching raw probe-candidate status.
- Ten-level snapshot claims should require official field list or sample payload before entering `allowed_capabilities`.
- Add explicit `needs_documentation` state to distinguish oral claims from partially documented routes.
