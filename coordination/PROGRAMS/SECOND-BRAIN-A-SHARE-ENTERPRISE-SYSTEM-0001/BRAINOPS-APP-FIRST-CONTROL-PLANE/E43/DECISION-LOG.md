# E43 Decision Log

## D-001: E43 owns positive execution classification

**Decision:** E42 `classify_execution()` is reduced to an observational result.
It cannot return a positive App or CLI execution classification, even for a
verified process-local receipt. Only
`TerminalExecutionReconciler.classify()` can return
`DURABLE_TERMINAL_RECONCILED`.

**Reason:** Leaving the older classifier positive would preserve the exact
`CLAIMED + completed receipt` bypass identified in the E42 review.

**Alternative rejected:** Treat a sealed E42 receipt as a final terminal fact.
That would retain a cooperative same-process API boundary as an execution proof.

**Rollback:** Revert the E43 branch commits. No external authority state exists.

## D-002: Challenge reuse is denied, not inferred away

**Decision:** each bounded transport observation consumes exactly one challenge.
The target, owner instance, task, epoch, canary, nonce, issue/expiry window and
maximum age must all match before an envelope can be minted.

**Reason:** a reliable terminal assertion needs current, scoped evidence rather
than a long-lived `SUPPORTED` observation or a copied transport label.

## D-003: Recovery principal is not a claim holder

**Decision:** `RecoveryPrincipal` and `RecoveryAuthorization` are separate from
`ClaimHolder`. Recovery may mark a timed-out claim `RECOVERY_REQUIRED`; it cannot
attach evidence, impersonate the holder, finalize a success/failure result, or
receive an effect permit.

**Reason:** crash recovery must be possible without silently turning a recovery
operator into an execution authority.

## D-004: Transport envelope remains an explicit non-cryptographic boundary

**Decision:** require a sealed envelope from `BoundedTransportAttestor`, while
documenting that Python seals do not protect against hostile code in the same
process.

**Future gate:** a real runtime must supply a separate process, signed envelope,
or externally verifiable attestor before it can claim production trust.
