# E49 Research Ledger

agent_id: CODEX

## Question

Can restart recovery complete a durable effect or invocation stage when the
process exits after a real durable compare-and-swap and before the next stage
journal write, without repeating a business mutation?

## Method

An isolated child process uses `os._exit(86)` at the actual durable mutation
cut points. A fresh parent process reconstructs the durable claim and lease
authorities from file-backed compare-and-swap state, then retries the original
request and inspects durable revisions and stage-journal phase.

## Result

Five E49 hard-crash tests cover effect CAS, claim CAS, lease CAS, journal
lease-phase interruption, and changed-time replay. Recovery only fills the
missing journal stages. Changed-time replay returns a binding mismatch before
allocating another stage operation.

## Limits

This is a synthetic storage experiment. It does not establish production
provider, durable-store, live-authority, market, or trading behavior.
