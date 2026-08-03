# E47 Execution Plan

## Lease

- task_id: `CODEX-BRAINOPS-RECOVERABLE-LEASE-TRANSITIONS-CROSS-RECORD-JOURNAL-EXACT-HEAD-CI-AND-RECEIPT-CLOSURE-0043-E47`
- route_epoch: `49`
- agent_id: `CODEX`
- mode: `project_plan`
- canonical repository: `vxz2datoubo/second-brain-coordination`
- canonical main at claim: `7aff9c1a57b6a8fbcb7cab2c66fd97866e478bbb`
- active issue: `#150`
- frozen source: Issue `#144`, PR `#146`, substantive head `dcf0e099fb2abc50fbb04fb95a1a7c39d4f38231`
- target branch: `codex/brainops-recoverable-lease-transitions-exact-ci-0043-e47`
- completion signal: `CODEX_BRAINOPS_E47_RECOVERABLE_LEASE_TRANSITIONS_EXACT_HEAD_CI_RECEIPT_READY_FOR_GPT_REVIEW`

## Goal

Replace E46's durable-state-plus-process-local-permit gap with one synthetic,
fail-closed lifecycle in which an already-applied positive transition can be
identified, checked against its original request, and resumed after response
loss or restart without a second state mutation.

The lifecycle is:

```text
CAPABILITY_ATTESTED
  -> EFFECT_AUTHORIZED
  -> CLAIM_INVOCATION_ATTACHED
  -> LEASE_INVOCATION_ATTACHED
  -> TERMINAL_ATTESTED
  -> CLAIM_TERMINAL_COMMITTED
  -> LEASE_TERMINAL_COMMITTED
```

This route is engineering and synthetic-test work only. It does not perform a
live authority write, Canary, application/CLI invocation, credential use,
trading, account access, or production release.

## Source and Ownership

E46 is frozen. E47 will use only selected paths and exact Blob IDs from
`dcf0e099fb2abc50fbb04fb95a1a7c39d4f38231`; it will not merge, cherry-pick,
amend, rebase, force-push, or modify PR #146. A source manifest will classify
each imported path as `REUSE`, `MODIFY`, or `EXCLUDE`.

The E46 shared-repository Git identity discrepancy is recorded as
`UNKNOWN_NOT_PROOF_OF_UNAUTHORIZED_EXECUTION`. E47 commits will use a
per-command Codex identity environment, leaving shared repository Git
configuration unchanged.

## Implementation Stages

1. Import E46's selected BrainOps contracts and tests through a source
   manifest. Preserve its fail-closed legacy entrypoints and synthetic identity
   boundaries.
2. Add a durable lifecycle journal and transition receipts. Each receipt binds
   the request digest, purpose, lease, claim, route, provenance, holder,
   target, and stage-specific invocation or evidence digest.
3. Make effect authorization, claim invocation, lease invocation, terminal
   attestation, claim terminal commit, and lease terminal commit recoverable.
   An identical retry returns a stable `ALREADY_*` result. Any changed binding
   fails closed with a concrete mismatch reason.
4. Add a deterministic reconciler for every cross-record partial state. It may
   finish only the missing matching mutation; it must never repeat an already
   applied mutation or guess a result from memory.
5. Add mutation-backed response-loss tests. Each positive stage will first
   demonstrate the broken behavior with an injected post-apply error, then
   prove restart recovery, exact-replay idempotency, mismatched-replay rejection,
   and one underlying mutation count.
6. Add exact-head CI. The E47 workflow will explicitly check out
   `github.event.pull_request.head.sha || github.sha`, fetch enough history for
   diff validation, assert the checked-out SHA, and run the full suite on Python
   3.11 and 3.13.
7. Add a product-level pre-receipt validator. It will reject absent or wrong
   exact-head CI, placeholders, missing lifecycle coverage, invalid receipt
   topology, and receipt commits that change runtime or tests.
8. After a green tested head, create exactly one nonempty evidence-only receipt
   commit. After its separate green exact-head matrix, publish the cumulative
   AMED, WPDCR, UNKNOWN, handoff, test and rollback evidence for GPT review.

## Acceptance Gates

- Every positive stage has post-apply response-loss, restart, identical replay,
  mismatched replay, tamper, and mutation-count coverage.
- Legacy effect, direct attach, and direct finalize paths remain non-mutating.
- Cross-claim, route, holder, target, invocation, and terminal-evidence replay
  attempts fail closed.
- The full synthetic suite passes locally and in an E47-named exact-head GitHub
  Actions matrix on Python 3.11 and 3.13.
- The pre-receipt validator passes only after the tested head is green; the
  receipt-only head receives a second green exact-head matrix.

## Bounded Initiative

Authorized A/B work: tests, contracts, validators, journal reconciliation,
observability, rollback evidence, and CI correctness inside the route allowlist.

Proposal-only C work: production trust roots, real GitHub authority execution,
remote credentials, and any cross-agent or canonical-runtime migration.

Stop/D work: account, order, funds, position, trading, real Canary, secrets,
private configuration, direct main writes, and changes to frozen E46 assets.

## Recovery

If interrupted, re-read canonical `main`, Issue #150, this plan, the active
route, and the latest E47 PR. Resume from the first incomplete stage, preserve
all commits, and publish an in-progress packet before any material pause or
route transition.
