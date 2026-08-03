# E46 Mandatory Execution Lease Architecture

## Authority chain

```text
verified route and approval provenance
  -> durable claim CAS winner
  -> consumed transport-attested capability challenge
  -> CAPABILITY_ATTESTED lease
  -> EFFECT_AUTHORIZED + sealed lease permit
  -> durable claim invocation attach
  -> INVOCATION_ATTACHED lease
  -> transport capture + verifier-minted execution identity
  -> verifier-minted terminal evidence
  -> TERMINAL_ATTESTED lease + sealed terminal authorization
  -> durable claim terminal CAS + operation journal
  -> TERMINAL_COMMITTED lease + terminal commit receipt
```

The claim remains the terminal owner-state record. The lease is the mandatory
authorization and evidence state machine. The operation journal records
cross-object mutation uncertainty and recovery.

## Monotonic states

| State | Version | Required new binding |
|---|---:|---|
| `CAPABILITY_ATTESTED` | 1 | capability decision, witness attestation, provenance, holder, target |
| `EFFECT_AUTHORIZED` | 2 | exact authorization time and sealed permit |
| `INVOCATION_ATTACHED` | 3 | one unique, nonempty invocation ID |
| `TERMINAL_ATTESTED` | 4 | verifier identity and terminal evidence digests |
| `TERMINAL_COMMITTED` | 5 | durable terminal receipt digest |

Skipped, repeated, reversed, expired, stale, foreign, or tampered transitions
fail closed. Record hashes and CAS revisions provide deterministic corruption
and concurrency detection; neither is claimed as a cryptographic production
trust root.

## Identity attestation

Three closed identity families are modeled:

- Manual App: session, owner instance, correlation, transport.
- Automation: dispatch, run, callback, callback identity, owner, correlation,
  transport.
- CLI: launcher, PID, start token, process identity, owner, correlation,
  transport.

Plain caller objects and copied strings are observations only. A positive
identity requires a transport-minted capture plus a verifier-minted sealed
identity bound to the exact invocation-attached lease. The synthetic transport
and verifier factories exist only for deterministic offline tests.

## Fail-closed legacy surface

- `DurableClaimAuthority.acquire_effect_permit()` always returns `None`.
- `DurableClaimAuthority.attach_invocation()` returns `EFFECT_BLOCKED`.
- `DurableClaimAuthority.finalize()` returns `EFFECT_BLOCKED`.
- `validate_owner_terminal_evidence()` rejects legacy decisions and
  caller-populated evidence; it accepts only the current invocation-attached
  lease plus verifier-minted terminal evidence.
- `TerminalExecutionReconciler.reconcile()` accepts only an E46 durable
  terminal commit receipt for a positive result.

The only positive claim mutations are
`attach_invocation_with_effect_permit()` and
`finalize_with_attested_terminal()`, each requiring a sealed object minted by a
persisted lease transition.

## Recovery model

The operation journal hash-chains monotonic events. It distinguishes:

- request recorded but claim not applied;
- claim applied with response returned;
- claim CAS applied but response lost;
- lease commit applied but response lost;
- CAS conflict;
- reconciliation required;
- reconciliation completed;
- terminal receipt committed.

After an ambiguous response, a restarted authority rereads both durable claim
and lease. Matching terminal state is committed exactly once; a nonterminal
claim is classified `CLAIM_NOT_APPLIED`. Recovery never fabricates a second
invocation or repeats the claim mutation.

## Production boundary

This implementation makes the contract and bypass behavior executable using
file-backed synthetic CAS. Production still needs an externally authenticated
transport verifier and durable remote trust root. No live GitHub authority,
Codex App session, automation, CLI process, credentials, account, market-data,
or trading surface is invoked in E46.
