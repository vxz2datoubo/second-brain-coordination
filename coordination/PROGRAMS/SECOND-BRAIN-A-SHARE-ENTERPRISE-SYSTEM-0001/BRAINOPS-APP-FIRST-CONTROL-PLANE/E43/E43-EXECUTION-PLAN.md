# E43 Execution Plan

agent_id: `CODEX`

task_id: `CODEX-BRAINOPS-TERMINAL-EXECUTION-ATTESTATION-RECOVERY-AUTHORITY-AND-FRESHNESS-CLOSURE-0039-E43`

route_epoch: `45`

mode: `project_plan`

status: `IN_PROGRESS`

boundary: `ENGINEERING_AND_SYNTHETIC_TESTS_ONLY / NO_LIVE_AUTHORITY_WRITE / NO_CANARY / NO_APP_OR_CLI_INVOCATION / NO_TRADE`

## Anchors

- canonical base: `925cc111c433823530adbdbef4ded5e332d88afe`
- active issue: `#134`
- frozen source PR: `#133`
- source tested head: `7d288a35674f7947536de85a647ab88c2d04028e`
- source receipt head: `d38d2e71f86bdfcd3915ae5bd8b2d6e8b97b3189`
- branch: `codex/brainops-terminal-attestation-recovery-freshness-0039-e43`
- completion signal: `CODEX_BRAINOPS_E43_TERMINAL_ATTESTATION_RECOVERY_AUTHORITY_FRESHNESS_READY_FOR_GPT_REVIEW`

## Fundamental Goal

E42 made one-shot authority and ownership contracts production-shaped, but it
still allowed an invocation receipt to look terminal while its durable claim was
only `CLAIMED`. E43 makes the order of proof explicit:

```text
invocation starts
  -> terminal observation is transport-attested and challenge-fresh
  -> durable claim is reconciled to the same terminal fact
  -> positive execution classification is allowed
```

An active claim is therefore not proof of a completed, failed, or otherwise
terminal App/CLI execution. The design also introduces a narrowly governed
recovery principal that can reconcile an expired claim but cannot impersonate a
claim holder, attach execution, or receive an effect permit.

## Stages

### P0 - Accountability, lineage, and plan

1. Create this non-empty plan commit and the selected-file source manifest.
2. Open the sole E43 Draft PR.
3. Preserve PR #133 as frozen; no branch merge or cherry-pick is permitted.

Acceptance: exact source blobs and intended dispositions are auditable, and no
changed path falls outside the E43 allowlist.

### P1 - Lifecycle and durable reconciliation

1. Model `INVOCATION_STARTED`, `INVOCATION_TERMINAL_OBSERVED`, and
   `DURABLE_TERMINAL_RECONCILED` as separate states.
2. Reject a positive terminal classification while the durable record remains
   `CLAIMED`, even when a receipt says `completed` or `failed`.
3. Require the same invocation ID, holder, terminal status, and monotonic time
   sequence on durable reconciliation.

Acceptance: duplicate, late, terminal-before-start, receipt-after-terminal,
and terminal mismatch cases fail closed with state-specific reasons.

### P2 - Freshness and transport-attested evidence

1. Bind capability and invocation evidence to an expiring one-shot challenge,
   target, task, epoch, canary, nonce, and exact owner instance.
2. Introduce a bounded transport-attested envelope. A raw object carrying the
   same transport string cannot substitute for it.
3. Enforce maximum observation age, expiry, no future observation, and no
   cross-owner/cross-route challenge reuse.

Acceptance: stale `SUPPORTED`, replayed challenge, forged identity string, and
future-time observations cannot reach a positive verdict.

### P3 - Least-privilege recovery and error taxonomy

1. Add a closed recovery principal and a distinct recovery authorization.
2. Permit recovery only after a bounded timeout and only to
   `RECOVERY_REQUIRED` or restricted reconciliation.
3. Prohibit recovery from attaching new execution, impersonating the holder, or
   receiving an effect permit.
4. Preserve distinct provenance, owner, state, time, invocation, transport, and
   CAS conflict result codes.

Acceptance: recovery overreach and each error family are adversarially tested.

### P4 - Evidence closure

1. Commit one substantive tested head after the full synthetic suite passes.
2. Run exact-head GitHub Actions on Python 3.11 and 3.13.
3. Add one non-empty evidence-only receipt commit, then run receipt-head CI on
   the same versions.
4. Re-read canonical main before publication, then request GPT second pass.

## Design Boundaries and Non-Claims

- Python-level seals and factories are still API boundaries, not a cryptographic
  root against hostile code in the same process.
- Synthetic envelope verification is not a claim about real GitHub, App,
  callback, CLI, branch-protection, permission, or rate-limit behavior.
- E43 does not run a Canary, live authority write, App Automation, or Codex CLI.
- No recovery path can become a proxy for execution authority.

## Recovery and Rollback

Work is isolated in this branch and worktree. On interruption, re-read canonical
`main`, `ACTIVE-CODEX-TASK.yaml`, Issue #134, and the E43 PR before continuing
from the first incomplete stage. Rollback is a branch-only revert of E43
commits. This task creates no external authority object.
