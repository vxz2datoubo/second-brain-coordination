# E40R1 Research Ledger

| ID | Claim | Evidence | Status | Downstream Limit |
| --- | --- | --- | --- | --- |
| E40R1-R-001 | A task-specific executable verifier can coexist with a fail-closed pre-canary verifier. | Isolated verifier tests; 126 local tests. | PARTIALLY_VERIFIED | Requires remote exact-head CI and GPT review. |
| E40R1-R-002 | Approval, event, outcome, and route evidence can be reserved atomically. | Concurrent-claim and terminal-state tests. | PARTIALLY_VERIFIED | Local SQLite behavior only; no distributed-lock claim. |
| E40R1-R-003 | One bounded control-plane claim completed under public approval. | `CANARY-EXECUTION-PROOF.json`. | VERIFIED_LOCAL_EVIDENCE | It is not an external process or trading action. |
