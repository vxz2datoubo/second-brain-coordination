task_id: CODEX-BRAINOPS-TRUSTED-PROVIDER-ATTESTATION-CORRECT-GIT-GRAPH-CLEAN-CLONE-REPRODUCTION-AND-STRICT-RECEIPT-VALIDATION-CLOSURE-0046-E50
route_epoch: 52
agent_id: CODEX
completion_signal: CODEX_BRAINOPS_E50_TRUSTED_PROVIDER_RELEASE_VALIDATION_READY_FOR_GPT_REVIEW
base_head: 7481fb645e8fd7b032fab6451128eecfadfedfaa
plan_head: 1ca2e59283c154f5256132e0b25f2e5544116d51
tested_head: 49ee251ed33c1f33e336bc59b0c485c279e9eaa3

The first provider design exposed an impossible self-blob reference. E50 now
uses a canonical-main payload plus a separate external identity envelope. The
first Actions run also revealed that a disposable clone needs its own synthetic
author identity before the post-receipt mutation can be constructed.
