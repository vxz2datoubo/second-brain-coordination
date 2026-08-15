# R124 P2.3 unplanned improvement ledger

agent_id: CODEX

| Improvement | Reason | Evidence | Rollback |
| --- | --- | --- | --- |
| Deterministic assembler channel attribution | The compatibility adapter needs a unified-source explanation without a second candidate scan. | `test_r124_multichannel_attribution_is_deduplicated_and_repeatable` | Revert the additive epoch-124 commit. |
| Supplemental nonnumeric candidate ordering | The route freezes new temporal/provenance weights. | `R124-NO-NEW-CROSS-CHANNEL-WEIGHTS` in `UNKNOWN-REGISTRY.yaml` | Revert the additive epoch-124 commit. |
