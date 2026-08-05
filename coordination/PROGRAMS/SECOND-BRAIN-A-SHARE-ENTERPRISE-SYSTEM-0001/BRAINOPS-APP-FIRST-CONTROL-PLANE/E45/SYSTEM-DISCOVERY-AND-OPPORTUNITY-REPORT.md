# E45 System Discovery

## Confirmed

- E44 already had durable CAS storage, challenge issuance and recovery-grant records.
- Its positive witness was a public dataclass and its recovery grant ledger was not invoked by the mutation method.
- The source `terminal_attestation` contracts remain valuable evidence and lifecycle scaffolding, but are not the E45 capability authority path.

## Improvement applied

The recovery ledger is now a precondition in the mutation method itself. Capability promotion now separates raw observations, attested witnesses, preliminary challenge consumption, claim binding and one-shot decision use.

## Deliberately not pursued

- No real transport attestor, live GitHub authority write, canary, application automation or CLI process was invoked.
- No production cryptographic root is claimed for Python-only seals.
