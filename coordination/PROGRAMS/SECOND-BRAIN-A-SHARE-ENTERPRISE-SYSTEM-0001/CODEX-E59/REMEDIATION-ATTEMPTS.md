# E59 Remediation Attempt Ledger

`agent_id: CODEX`
`classification: VERIFIED_LOCAL`

| Attempt | Result | Evidence retained | Interpretation |
|---|---|---|---|
| P0-A | `FAIL_CLOSED` | `CPU_THROTTLE_REQUIRED`; 23.77 GiB available RAM; CPU sample 100.0% | No synthetic child was admitted. The single-sample rule was later found inconsistent with the binding 15-second sustain requirement. |
| P0-B | `FAIL_CLOSED` | `CPU_THROTTLE_REQUIRED`; 23.49 GiB available RAM; CPU sample 100.0% | Reproduced the same transient-sample behavior before the sustain-window correction. |
| P0-C | `PASS` | `P0-BOUNDED-DESCENDANT-CANARY-RECEIPT.json` | After the correction, all seven bounded scenarios returned zero owned descendants, zero orphans and zero unrelated terminations. |
| Final local evidence capture | `PASS` | `TEST-RUN-RECEIPT.md` | Recovery check, 48 tests, P0 and all nine mutations exited zero; command outputs are represented by the recorded SHA-256 values. |

The two failed P0 attempts are retained as negative evidence. They do not establish a production CPU condition and do not justify weakening any resource limit.
