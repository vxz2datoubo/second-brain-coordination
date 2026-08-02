# E43 Test Matrix

| Area | Synthetic coverage |
|---|---|
| Legacy E42 CAS/provenance | create/update conflict, timeout, redirect, readback ambiguity, owner/provenance substitution |
| Lifecycle | claimed receipt, terminal-before-start, late callback, durable terminal time/status mismatch |
| Freshness | expiry, stale observation, future observation, nonce/owner/target substitution, one-shot replay |
| Transport | raw identity string rejection and sealed-envelope constructor rejection |
| Recovery | bounded time window, separate recovery principal, no permit, no holder impersonation |
| Error taxonomy | invocation mismatch remains invocation-specific rather than provenance tamper |

The suite is deterministic and synthetic. It does not call GitHub, App
Automation, Codex CLI, a Canary, credentials, accounts, or trading systems.
