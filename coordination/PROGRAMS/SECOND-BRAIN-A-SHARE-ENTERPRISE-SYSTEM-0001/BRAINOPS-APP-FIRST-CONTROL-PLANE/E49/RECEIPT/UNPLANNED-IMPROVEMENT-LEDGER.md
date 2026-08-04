# E49 Improvement Ledger

agent_id: CODEX

## I-001: Stage-journal lease-phase crash cut

The initial three required crash cuts proved recovery before the next journal
write. E49 also added a process-exit cut after the journal reaches
`LEASE_MUTATION_APPLIED` and before `COMPLETED`. This directly covers the
otherwise untested partial durable journal state.

## I-002: Changed-time replay guard ordering

A replay with a changed effect timestamp is now rejected before stage-journal
allocation. The adjustment prevents a failing replay from creating an
unrelated journal operation while keeping the original recoverable stage
unchanged.

## I-003: Mutation test isolation

The initial mutation fixture accidentally failed for a second guard, which
would have exaggerated coverage. The fixture was corrected so each mutation is
killed by its named validator and target guard.
