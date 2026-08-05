# E44 Unplanned Improvement Ledger

## UI-001: recovery storage identity validation

- Discovery: the durable claim storage identity is a canonical SHA-256 value,
  not a human-readable identifier.
- Risk: validating it as a short identifier would reject a correctly bound
  recovery authorization before its one-shot guard was evaluated.
- Change: validate `storage_id` with the SHA-256 validator while retaining
  identifier checks for authorization, task, canary, nonce, claim and reason.
- Test: recovery binding, restart replay rejection and spawned-process replay
  rejection.

## UI-002: evidence-family and exit-code same-object binding

- Discovery: an owner terminal decision and the raw terminal observation could
  otherwise agree on labels while disagreeing on evidence family or exit code.
- Risk: a manual App terminal could inherit a process-style success exit code.
- Change: reconciliation now requires an exact evidence-type mapping and exact
  exit-code agreement before positive classification.
- Test: manual evidence with a process exit code is rejected.
