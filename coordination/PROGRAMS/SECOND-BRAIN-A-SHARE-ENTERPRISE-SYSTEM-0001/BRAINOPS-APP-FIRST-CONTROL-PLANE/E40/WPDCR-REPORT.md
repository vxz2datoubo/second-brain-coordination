# WPDCR: E40R1 Bounded Engineering Canary

## Work Process and Difficulty

- `agent_id`: `CODEX`
- Difficulty planned / observed: `D3 / D3`
- Work: preserve the accepted fail-closed pre-canary verifier; add a separate
  executable verifier; bind public route and approval proof; reserve one nonce
  and terminal outcome atomically; keep ordinary dispatch disabled.

The hard part was not calling a tool. It was preventing the permission change
needed for this one canary from weakening the accepted pre-canary default. The
result therefore uses an explicit executable verifier rather than changing the
read-only verifier's behavior.

## Findings

1. A single transaction can bind approval consumption, event reservation,
   one-shot ownership, and route proof, so concurrent claims leave one winner.
2. The task's owner designation is useful control-plane evidence but does not
   prove cross-process identity; it remains an UNKNOWN.
3. Existing E37/E39 workflow tests referenced files outside the E40R1 allowed
   surface. The tests were migrated to the authorized workflow rather than
   widening the task scope.

## Future Proposal (Not Implemented)

`C_PROPOSAL_ONLY`: a later task could add independently signed host-process
reservations. It requires its own route, threat model, and approval because it
would cross this task's bounded engineering-claim boundary.

## Model Advisory

- Recommended model: user or GPT selects the highest available reasoning model
  for future multi-process authority work.
- Runtime model: `ACCESS_NOT_EXPOSED`.
- Agent changed model setting: `false`.
- Restore exception: `false`.

## Rollback

After review, revert the substantive E40R1 commit and then its receipt-only
commit. No external service state, model setting, or trading state exists to
restore.
