# Classifier v0.2 Lifecycle

Current emitted pre-probe statuses:

- `insufficient`
- `needs_documentation`
- `qualified_for_readonly_probe`
- `blocked`

Reserved future statuses, not emitted by v0.2:

- `runtime_probe_failed`
- `runtime_verified_research_only`
- `approved_for_governed_integration`

## Hard Gates

- Oral claims, UI screenshots, or `capabilities=yes` do not enter `allowed_capabilities` without official field table, SDK doc, or sanitized sample payload.
- Raw tick requires field list, SDK doc, sample payload, explicit time semantics, and a stable sequence/event key.
- Raw order/order queue/cancel additionally require channel/partition evidence, day-start baseline, recovery document, and disconnect/recovery information.
- `local_storage_allowed=no` and `automation_allowed=no` cannot enter `qualified_for_readonly_probe`.
- SDKs containing trading methods are not automatically blocked if a read-only process, method whitelist, or separate market-data entitlement is confirmed.
- Market data paths requiring account/order/trading password/trading counter without isolation are `blocked`.
