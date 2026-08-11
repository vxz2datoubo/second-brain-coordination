# E64 — GitHub-only formal knowledge promotion

agent_id: CODEX

## Objective

Build a small, public-safe, GitHub-native candidate-to-formal-promotion
candidate.  It must bind an approved candidate to an exact identity, reject
stale or replayed promotion, and make only truthful application-integrity
claims.  This is not an external cryptographic trust root and it does not
unlock a real formal knowledge write.

## Frozen inputs

- Canonical base: `88367196d8a5985624e62afb960eb0abab34e9a0`.
- Active route: E64, epoch 72, Issue #224.
- E48 R2 live integration: blocked pending independent acceptance.  Tests use
  typed synthetic E48 digest fixtures only; no competing digest schema is
  introduced.
- Repository visibility remains public.

## Deliverables

1. Threat model and public/private/secret admission contract.
2. Typed E48 adapter, approval packet, immutable candidate identity, one-time
   promotion ledger, expected-parent/CAS guard, and deterministic verifier.
3. Adversarial unit tests plus bounded Python 3.11/3.13 GitHub Actions CI.
4. Unknown registry, execution receipt, and GPT handoff.

## Safety limits

No AWS, external issuer, private-repository work, credential handling, real
user knowledge promotion, direct-main write, merge, history rewrite, or
repository-visibility change is in scope.

## Acceptance evidence

The candidate will be reviewed only after stdlib tests exercise digest,
approval, target, provenance, expiry, replay, concurrency/CAS, and content
classification failures; CI is syntactically checked; and no task-owned
process remains after test execution.
