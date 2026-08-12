# Unplanned Improvement Ledger — CLTM-0021 R3

`agent_id: CODEX`
`authority: epoch 79 Level A/B correctness hardening`

| Improvement | Why needed | Evidence | Rollback |
| --- | --- | --- | --- |
| Canonical conversation metadata validator | Adapter-only claim-role validation had a generic-packet bypass. | R3 generic packet negative test. | Revert this additive commit. |
| Explicit scope/time binding | Omitted QueryPlan fields admitted conversation atoms. | Missing/wrong scope adversarial tests. | Revert this additive commit. |
| Existing-store provenance projection | Recalled atoms lacked a direct audit projection to packet and episode metadata. | End-to-end provenance assertion. | Revert this additive commit. |
| Legacy-schema compatibility | Newly required 1.0 fields broke old serialized payloads. | Pre-CLTM 1.0 fixture load test. | Revert this additive commit. |
