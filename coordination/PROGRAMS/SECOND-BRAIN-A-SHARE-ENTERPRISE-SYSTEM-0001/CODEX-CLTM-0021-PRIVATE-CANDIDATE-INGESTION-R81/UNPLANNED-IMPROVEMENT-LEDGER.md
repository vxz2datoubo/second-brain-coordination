# Unplanned Improvement Ledger - CLTM-0021 epoch 81

agent_id: CODEX

| Improvement | Reason | Evidence | Rollback |
| --- | --- | --- | --- |
| Private transport visibility binding | A generic private class could otherwise be relabeled as public-safe metadata. | test_fail_closed_for_schema_secret_injection_role_scope_and_time | Revert this additive epoch-81 commit. |
| Explicit source-binding status | Route forbids opportunistic private-source discovery and fabricated canary evidence. | test_cli_receipt_is_redacted_and_source_absence_is_waiting | Revert this additive epoch-81 commit. |
