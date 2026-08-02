# E42 Execution Plan

agent_id: `CODEX`

task_id: `CODEX-BRAINOPS-TRUSTED-DURABLE-AUTHORITY-PROVENANCE-OWNER-BINDING-AND-PRODUCTION-CAS-CLOSURE-0038-E42`

route_epoch: `44`

status: `IN_PROGRESS`

boundary: `ENGINEERING_AND_SYNTHETIC_TESTS_ONLY / NO_LIVE_AUTHORITY_WRITE / NO_APP_OR_CLI_INVOCATION / NO_TRADE`

## Anchors

- canonical base: `77e29be8afed494e493923ff6344c0309843acfb`
- active issue: `#132`
- frozen source PR: `#131`
- source tested head: `ee83b857e6d6287ef50779c664d6db3c4cf12029`
- source receipt head: `75ee411aa3319b4c1f789e38d8841edb1c3d024c`
- branch: `codex/brainops-trusted-durable-authority-provenance-0038-e42`
- completion signal: `CODEX_BRAINOPS_E42_TRUSTED_DURABLE_AUTHORITY_PROVENANCE_OWNER_BINDING_PRODUCTION_CAS_READY_FOR_GPT_REVIEW`

## Goal

Close the E41 trust-boundary gaps with production-capable but unexecuted code. The
implementation will model a fixed GitHub repository, authority ref, and path
prefix; mint verified route, approval, capability, invocation, and canonical
terminalization evidence only through bounded verifier objects; bind the exact
claim holder to every state transition; and expose an effect permit only to the
verified CAS winner.

Synthetic transports are the only transports authorized by this task. Actual
GitHub write permission, branch protection, rate limits, App callbacks, and CLI
process evidence remain `UNKNOWN` until a separately approved runtime task.

## Stages

### P0 - Accountability and selective import

1. Publish this non-empty plan and the exact source import manifest.
2. Open one Draft PR from the E42 branch.
3. Import only the paths and blobs listed in `SOURCE-IMPORT-MANIFEST.yaml`.
4. Keep PR #131 and its branch immutable; do not merge or cherry-pick it.

Acceptance: branch and Draft PR exist, source lineage is machine-auditable, and
all changed files are within E42's allowlist.

### P1 - Fixed-scope production CAS adapter

1. Add an HTTP transport protocol whose implementation is supplied by the outer
   runtime and cannot redirect.
2. Implement fixed repository/ref/path-prefix reads and create/update Contents
   API writes with explicit expected blob SHA semantics.
3. Validate response repository, ref, path, blob SHA, content SHA256, commit, and
   tree identity before returning a verified result.
4. Map 404, 409, 412, 422, timeout, transport, malformed response, and identity
   drift to explicit fail-closed outcomes with bounded retries.

Acceptance: synthetic HTTP fixtures cover success, conflict, timeout, redirect,
response drift, and recovery without making a network write.

### P2 - Verified route and approval provenance

1. Introduce public `Raw*` observations and verifier-minted `Verified*` objects.
2. Bind route repository, route ID, epoch, task, canary, nonce, ref, commit, tree,
   path, blob SHA, and content SHA256.
3. Bind approval repository, comment ID, actor, issued time, body SHA256, scope,
   expiry, task, epoch, canary, and nonce.
4. Reject substitutions, stale approvals, invalid ordering, and cross-route use.

Acceptance: ordinary caller-created raw records never satisfy a verified API;
all route and approval substitutions fail closed.

### P3 - Claim-holder ownership and effect gate

1. Replace caller strings with a closed `OwnerType` enum.
2. Bind owner type, owner instance ID, and claimant correlation ID into the
   durable claim and every mutate/recovery request.
3. Require the same claim holder to attach evidence, finalize, and recover.
4. Mint `DURABLE_CLAIM_ACQUIRED_EFFECT_MAY_PROCEED` only from an internal permit
   issuer after verified provenance and a successful CAS claim.

Acceptance: a distinct owner instance, correlation, route, or approval cannot
finalize, recover, attach evidence, or receive a permit.

### P4 - Trusted execution and terminalization evidence

1. Separate raw and verified capability/invocation/terminalization objects.
2. Verify current-session, App Automation, and CLI evidence through disjoint
   bounded verifiers with owner compatibility and non-attempted-owner exclusion.
3. Enforce callback/process identity, time order, claim state, terminal result,
   log/cleanup hashes, and duplicate-callback rules.
4. Verify canonical terminalization from an exact read-only route transport and
   a matching durable final state; reject generic `BLOCKED` and pre-terminal
   publication.

Acceptance: forged records cannot classify as verified and pending publication
is reported as `DURABLE_TERMINAL_ROUTE_PUBLICATION_PENDING`.

### P5 - Adversarial validation

Cover forged evidence, owner mismatch, route/approval substitution, create and
update conflicts, all HTTP errors, redirect/drift, crash/restart, four-process
competition, replay, duplicate callback, stale READY, old approval/nonce replay,
and all transport exceptions.

Acceptance: Python 3.11 and 3.13 run the same deterministic synthetic suite with
no live endpoints or credentials.

### P6 - Exact-head evidence closure

1. Commit one substantive tested head and run exact-head CI on Python 3.11/3.13.
2. Add exactly one non-empty receipt-only commit after the tested head.
3. Run receipt-head exact CI on Python 3.11/3.13.
4. Publish the completion signal and stop for GPT second-pass review.

## Recovery

The task is isolated in one worktree and one branch. Recovery starts by rereading
`origin/main:coordination/ACTIVE-CODEX-TASK.yaml`, confirming epoch 44 is still
active, and continuing from the first incomplete stage above. Rollback is a
branch-only revert of E42 commits; this task creates no external authority record.

## Explicit Non-Claims

- Synthetic transport success is not live GitHub authority proof.
- Python constructor restrictions are process-level API controls, not
  cryptographic isolation from hostile code in the same process.
- No capability, App Automation, CLI, Canary, or production authority route is
  claimed operational by this plan.

