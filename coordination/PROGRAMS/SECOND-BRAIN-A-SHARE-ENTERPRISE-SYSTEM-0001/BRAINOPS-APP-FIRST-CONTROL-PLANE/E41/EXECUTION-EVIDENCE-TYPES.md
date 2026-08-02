# E41 Execution Evidence Types

| Type | Minimum positive evidence | Explicit non-proof |
| --- | --- | --- |
| `CONTROL_PLANE_CLAIM_ONLY` | durable claim ID with no receipt | no App or CLI process ran |
| `CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION` | manually created, correlated and durably attached receipt | no new App run was dispatched |
| `APP_AUTOMATION_DISPATCHED_NEW_RUN` | dispatch receipt, callback proof hash, cleanup proof and durable correlation | no CLI execution occurred |
| `CODEX_CLI_PROCESS_INVOKED` | correlated process receipt with exit code, log and cleanup hashes | no App automation occurred |

All entries require a start/end time, invocation ID, parent correlation ID,
owner, terminal status, non-attempted owner, log hash, and cleanup hash. A
missing or mismatched receipt fails closed. E41 creates no positive runtime
receipt; its tests construct only synthetic contract examples.
