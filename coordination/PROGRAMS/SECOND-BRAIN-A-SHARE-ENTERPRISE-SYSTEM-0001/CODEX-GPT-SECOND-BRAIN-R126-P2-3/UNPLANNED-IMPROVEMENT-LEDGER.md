# R126 P2.3 unplanned improvement ledger

agent_id: CODEX

| Improvement | Reason | Evidence | Rollback |
| --- | --- | --- | --- |
| Internal exact atom-ID admission proof | A statement-ranked one-item proof falsely rejects a valid duplicate-statement atom. | `test_r126_exact_proof_handles_budget_omitted_duplicate_statement_from_newer_episode` | Revert the additive epoch-126 commit. |
| Legacy-tie regression witness | The test proves that ordinary ranking picks the older atom while exact admission proves the intended newer atom. | Same focused test, with `budget=50` omission and `budget=1` legacy tie assertions. | Revert the additive epoch-126 commit. |
