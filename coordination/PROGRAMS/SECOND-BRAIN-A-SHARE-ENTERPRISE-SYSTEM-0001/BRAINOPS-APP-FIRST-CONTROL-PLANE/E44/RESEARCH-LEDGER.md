# E44 Research Ledger

## Scope

Synthetic control-plane contract work only. No live GitHub authority operation,
Canary, App Automation, Codex CLI execution, credential access, market data or
trade action was attempted.

## Preserved Findings

1. A `VerifiedCapabilityObservation` is useful history but cannot be a positive
   runtime authority. E44 now classifies it as observational and blocks it at
   the capability gate.
2. Restart safety needs storage-backed compare-and-swap consumption, not an
   in-memory flag. Both challenge and recovery ledgers are exercised across a
   new ledger instance and a spawned process.
3. A terminal label alone is inadequate. Positive reconciliation now requires
   the same owner, target, invocation, terminal time, log hash, evidence family
   and exit semantics from one owner-specific decision.

## Negative Evidence

- No live external authorization was created or consumed.
- No real App, App Automation or CLI process evidence exists.
- The synthetic file CAS adapter is a deterministic test fixture, not proof of
  production GitHub behavior.
