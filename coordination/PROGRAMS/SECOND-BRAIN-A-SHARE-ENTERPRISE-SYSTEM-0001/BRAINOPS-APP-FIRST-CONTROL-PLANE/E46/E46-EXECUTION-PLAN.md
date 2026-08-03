# E46 Execution Plan

## Lease

- task_id: `CODEX-BRAINOPS-MANDATORY-EXECUTION-LEASE-ATTESTED-TERMINAL-MUTATION-CLOSURE-0042-E46`
- route_epoch: `48`
- mode: `project_plan`
- agent_id: `CODEX`
- reviewer: `GPT`
- accepted_base: `3403a94bc8486c07eded5c5f949ae08fe4f427f7`
- frozen_source_pr: `#142`
- frozen_source_tested_head: `a4fb916d8e0d56cee9085e5e38a04d49175c2218`
- frozen_source_receipt_head: `cbb2d964a8dd91f4b9c9754e7af62469637a6d79`
- branch: `codex/brainops-mandatory-execution-lease-terminal-mutation-0042-e46`
- hard_state: `research_only / NO_TRADE`

`读取任务` has been treated as read, claim, and immediate execution. E46 is the
only active Codex route. PR #142 remains frozen and is used only as a selected
source of reviewed implementation ideas and blobs.

## Root Objective

Close the remaining BrainOps enforcement gap by making one durable execution
lease the mandatory state machine for capability attestation, effect
authorization, invocation attachment, terminal attestation, and terminal
commit. No terminal owner mutation may succeed through a legacy or parallel
positive path.

The monotonic state chain is:

```text
CAPABILITY_ATTESTED
  -> EFFECT_AUTHORIZED
  -> INVOCATION_ATTACHED
  -> TERMINAL_ATTESTED
  -> TERMINAL_COMMITTED
```

## Frozen Boundaries

- Do not merge or cherry-pick PR #142.
- Do not modify PR #142 or revive its branch.
- Do not call live GitHub authority, canary, app automation, CLI launchers,
  model settings, credentials, accounts, market data, or trading interfaces.
- Do not write outside the route allowlist.
- Do not establish Python sealing as a production trust root; it is an offline
  executable contract and adversarial-test boundary only.
- Do not start any later Gate.

## Selected Source Import

The substantive commit will import only the minimum E45 runtime and test files
needed to preserve prior reviewed behavior. `IMPORTED-SOURCE-MANIFEST.yaml` will
record each imported path, source commit, source blob SHA, disposition, and E46
change reason. E45 status, receipt, handoff, generated evidence, and publication
helpers will not be imported as runtime authority.

## Implementation Phases

### P0 - Plan and external anchor

1. Commit this plan as the sole file in commit 1.
2. Push the branch and open the single Draft PR.
3. Publish an in-progress visibility packet with base, parent, tree, branch,
   route epoch, scope, and recovery command.

### P1 - Durable execution lease

Implement a durable, monotonic lease record that binds:

- capability provenance digest and durable storage identity;
- claim identity, holder identity, target identity, task ID, route epoch,
  canary identity, nonce, issue time, and expiry;
- exactly one nonempty invocation identity attached only after effect
  authorization;
- terminal evidence digest and terminal commit receipt.

All transitions will compare the full binding and fail closed on stale version,
illegal order, expiry, replay, cross-claim, cross-route, cross-owner, or
cross-target use.

### P2 - Verifier-minted identities and mandatory effect path

Introduce a sealed `AttestedExecutionIdentity` family for Manual App,
Automation, and CLI evidence. Constructors accept verifier-owned raw evidence;
callers cannot mint an identity by copying correct-looking strings.

Effect permits will be issued only through the lease transition from
`CAPABILITY_ATTESTED` to `EFFECT_AUTHORIZED`. Legacy effect-permit issuance will
fail closed.

### P3 - Invocation, terminal attestation, and terminal mutation

- Attach exactly one unique nonempty invocation ID through the lease.
- Mint terminal evidence from the attached invocation and verifier identity.
- Permit terminal owner mutation only through
  `finalize_with_attested_terminal()`.
- Make legacy `finalize()` and the process-local terminal-attestation positive
  path fail closed.
- Bind classification and reconciliation to the same lease and terminal commit
  receipt.

### P4 - Durable recovery journal

Persist operation phases sufficient to distinguish:

- request not applied;
- mutation applied and response returned;
- mutation applied but response lost;
- compare-and-swap conflict;
- reconciliation required or complete.

The recovery test will simulate response loss after the claim CAS has applied,
restart from durable state, reconcile without a second mutation, and produce a
stable terminal receipt.

### P5 - Verification and evidence

Run focused tests under Python 3.11 and Python 3.13, including all prior E45
tests plus mandatory bypass and recovery negatives. Run the same matrix at the
tested head and receipt-only head in GitHub Actions.

## Mandatory Negative Matrix

The substantive test suite will reject at least:

1. unused or foreign capability decision;
2. legacy direct effect permit issuance;
3. legacy direct terminal finalize;
4. null or empty invocation identity;
5. caller-cloned Manual App, Automation, or CLI identity strings;
6. identity, permit, or evidence replay;
7. cross-claim, cross-route, cross-holder, cross-target, and stale-lease use;
8. skipped, reversed, or repeated lease transitions;
9. terminal mutation without attested evidence;
10. process-local attestation used as durable authority;
11. post-apply response loss followed by duplicate mutation;
12. tampered operation journal or terminal receipt.

## Commit Topology

Exactly three nonempty commits are allowed:

1. this plan only;
2. selected source manifest, implementation, tests, workflow, and substantive
   evidence;
3. receipt-only delivery evidence and handoff, with no runtime or test changes.

Every commit message ends with `[agent:CODEX]`. No amend, rebase, force-push, or
direct write to `main` is permitted.

## Acceptance

- One Draft PR exists for E46 and PR #142 remains unchanged.
- All positive authority paths require the same durable lease.
- Exactly one invocation is attached before terminal attestation.
- Terminal mutation is impossible without verifier-minted identity and
  attested terminal evidence.
- Response-loss recovery proves at-most-once mutation after restart.
- Python 3.11 and 3.13 CI pass at both final heads.
- Public-safe scans find no credentials, account data, market data, or trading
  execution surface.
- Delivery contains AMED execution, research, improvement, discovery, WPDCR,
  UNKNOWN, test, rollback, and AI handoff evidence.

## Rollback and Recovery

The branch is isolated. Before merge, rollback is deletion of the branch and
worktree; no production or external authority state is touched. During work,
resume from the latest committed checkpoint after re-reading the remote route.
The substantive commit will keep all state fixtures in temporary directories so
test failure cannot alter repository or user runtime state.
