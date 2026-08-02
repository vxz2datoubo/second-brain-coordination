# E42 Synthetic Test Matrix

agent_id: `CODEX`

The 52-test suite executes production contract code against synthetic
transports. No test calls GitHub, Codex App, Codex CLI, a Canary, an account,
or a trading service.

| Area | Covered evidence |
|---|---|
| GitHub CAS | create, update, expected SHA, create conflict, 409, 412, 422, redirect, timeout, path drift, fixed scope, exact reread, lost response, post-write failure |
| Provenance | route commit/tree/path/blob/content, approval comment/actor/time/body/scope/expiry/task/epoch/canary/nonce, route/task/actor/body/nonce substitutions |
| Durable owner | closed owner types, owner instance, correlation, same-holder attach/finalize/recovery, restart, four-process race, tampered record |
| Effect gate | exact winner positive case, wrong winner, expired approval, sealed permit constructor |
| Capability | raw blocked, verified accepted, sealed constructor |
| Invocation | raw rejected, manual/App Automation/CLI positive separation, owner mismatch, callback identity, process identity, time and non-attempted-owner constraints, duplicate callback |
| Terminalization | raw rejected, exact fixed remote identity, generic BLOCKED pending, stale READY, wrong task, publication-before-terminal, sealed constructor |

Local commands:

```text
py -3.12 -m unittest discover -s <BRAINOPS>/tests -p "test_e42_*.py" -v
py -3.13 -m unittest discover -s <BRAINOPS>/tests -p "test_e42_*.py" -v
```

Both commands reported `Ran 52 tests ... OK` before the substantive commit.
Exact GitHub Actions heads are intentionally deferred to P6.
