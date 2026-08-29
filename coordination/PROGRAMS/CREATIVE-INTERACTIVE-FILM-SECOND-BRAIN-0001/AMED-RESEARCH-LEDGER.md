# AMED Research Ledger

agent_id: CODEX

| ID | Question | Evidence used | Result | Decision |
| --- | --- | --- | --- | --- |
| R-S00-001 | What is the immutable implementation base? | Task activation receipt and remote branch verification | `963acf85f0e38890c8eea8a0469980246ce3f1ce` | Keep branch rooted at that SHA. |
| R-S00-002 | Can local or WorkBuddy assets enter this task? | Route provenance gate | No; their provenance is unverified. | Use synthetic fixtures only. |
| R-S00-003 | Which execution boundaries must be enforceable locally? | Task brief authority invariants | Offline/mock generation, review-only knowledge, no credentials, no production/trade, no self-review/merge. | Express all eight as a machine-readable declaration. |

No external content, account data, credential, or paid service was queried for S00.
