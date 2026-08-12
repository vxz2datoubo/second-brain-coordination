# Unplanned Improvement Ledger — CLTM-0021 R3

`agent_id: CODEX`
`authority: epoch 79 Level A/B correctness hardening`

| Improvement | Why needed | Evidence | Rollback |
| --- | --- | --- | --- |
| Canonical conversation metadata validator | Adapter-only claim-role validation had a generic-packet bypass. | R3 generic packet negative test. | Revert this additive commit. |
| Explicit scope/time binding | Omitted QueryPlan fields admitted conversation atoms. | Missing/wrong scope adversarial tests. | Revert this additive commit. |
| Existing-store provenance projection | Recalled atoms lacked a direct audit projection to packet and episode metadata. | End-to-end provenance assertion. | Revert this additive commit. |
| Legacy-schema compatibility | Newly required 1.0 fields broke old serialized payloads. | Pre-CLTM 1.0 fixture load test. | Revert this additive commit. |
| Immutable conversation closure | Derived correction closure invalidated an old atom's packet-declared identity. | R4 supersession identity test. | Revert the R4 additive commit. |
| Required packet lineage | Self-consistent direct conversation atoms could be retrieved without packet provenance. | R4 direct-insert and packet-lineage adversarial tests. | Revert the R4 additive commit. |
| Canonical injection and instant checks | Generic packet callers bypassed adapter-only injection screening and offset ordering used strings. | R4 generic injection and non-Z offset tests. | Revert the R4 additive commit. |
