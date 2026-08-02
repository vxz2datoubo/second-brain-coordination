# E44 Execution Plan

## Objective

Close the E43 synthetic-contract gaps without treating a process-local verifier
as a live trust root.  Every positive capability decision must be derived from
a fresh, durable, challenge-bound transport attestation.  Every terminal
classification must be bound to the exact owner type, target, invocation and
terminal/exit semantics before it can reconcile a durable claim.

## Frozen Inputs And Boundaries

- Canonical base: `1b61357b150ee5bf818a207c60b4b05b017e1cd7`.
- Frozen source: PR #136, tested `80d3d87d0caad132bb59a5dfe0bc6878a6af7ec7`,
  receipt `630feade7c43d9a193d7e71578bb0d3b6e91e6b8`.
- Selected source files only; the source branch and PR remain immutable.
- Synthetic engineering only: no live GitHub authority write, Canary, App
  Automation, CLI invocation, credentials, private configuration, account or
  trading access.

## Stages

1. **P0 - accountable import**: copy only the manifest-listed E43 primitives,
   normalize generated-file hygiene, and preserve source hashes.
2. **P1 - durable ledgers**: add revisioned-CAS `ChallengeLedger` and
   `RecoveryAuthorizationLedger`; consumption is atomic across new ledger
   instances, restart and test processes.
3. **P2 - capability gate**: retain legacy capability observations only as
   context.  Positive capability needs an unconsumed, fresh, transport-bound
   challenge decision from the durable ledger.
4. **P3 - owner terminal schemas**: make Manual App, App Automation and CLI
   terminal evidence mutually exclusive, owner/target-bound, and explicit
   about dispatch/callback or launcher/process/exit/cleanup/log facts.
5. **P4 - reconciliation and tests**: enforce terminal-state and exit-code
   truth tables before the existing durable reconciliation can become positive;
   cover bypass, replay, restart, race, owner and terminal mismatches.
6. **P5 - evidence**: push one substantive tested commit, exact-head Python
   3.11/3.13 CI, then one nonempty receipt-only commit and the same matrix.

## Test Strategy

Use only deterministic local synthetic CAS roots.  The suite must prove that
challenge and recovery authorization reuse fails across instances and process
boundaries; legacy objects never produce a positive decision; mixed owner or
evidence schemas fail closed; and success requires terminal semantics plus the
same durable invocation record.  Public-safe scanning, compile, YAML parsing,
changed-path and receipt-topology checks are mandatory.

## Recovery

Each stage is independently commit-recoverable.  A failing path leaves the
frozen E43 source unchanged.  Reverting the E44 substantive commit and then
its receipt removes the synthetic contracts without revoking or changing any
external authority because this task creates none.
