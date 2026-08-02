# E41 Research Ledger

## Retained negative evidence

- E40R1's `selected_owner=CODEX_APP` did not prove a new App Automation run.
- An ephemeral local SQLite `SUCCEEDED` record did not prove global
  consumption across a fresh process.
- `app_available=true` without a bounded observation did not prove capability.
- A route written as `READY` cannot defeat a persisted durable claim.

## E41 changes under test

- fixed-repository CAS boundary contract with opaque revisions and verified
  payload digest;
- synthetic cross-process CAS only for offline proof, never production;
- write-once invocation attachment and terminal claim states;
- exact terminal route binding rather than generic route-state inference;
- four explicit evidence types with no default availability.

## Unknown retained for later work

- real GitHub CAS operational semantics;
- approved route publisher terminalization workflow;
- real App automation dispatch and Codex CLI receipt evidence.
