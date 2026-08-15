# R125 P2.3 unplanned improvement ledger

agent_id: CODEX

| Improvement | Reason | Evidence | Rollback |
| --- | --- | --- | --- |
| Omission-only exact-recall proof | R124's single-authority migration exposed a pre-existing 50-item proof cap. | `test_r125_capture_exact_recall_survives_same_episode_budget_saturation` | Revert the additive epoch-125 commit. |
| Foreign/absent proof equivalence regression | A proof helper must not become a scope discovery oracle. | `test_r125_proof_path_makes_foreign_identity_equivalent_to_absence` | Revert the additive epoch-125 commit. |
