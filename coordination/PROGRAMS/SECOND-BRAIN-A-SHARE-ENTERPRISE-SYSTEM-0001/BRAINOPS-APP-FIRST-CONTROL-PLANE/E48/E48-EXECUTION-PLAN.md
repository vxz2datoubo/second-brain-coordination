# E48 Execution Plan

## Lease

- agent_id: CODEX
- task_id: CODEX-BRAINOPS-INTEGRATED-RECOVERABLE-MANDATORY-AUTHORITY-ATTESTED-IDENTITY-EXPIRY-AND-EXECUTABLE-RELEASE-GATE-CLOSURE-0044-E48
- route_epoch: 50
- canonical_main_at_claim: ac17da81cd2ea019786e9f1d229eaede944756d9
- source_issue: 150
- source_pull_request: 151
- frozen_source_receipt: 20fc964e6f67c817742e8e8a7a34858a8305fea9
- target_branch: codex/brainops-integrated-recoverable-authority-release-gate-0044-e48
- completion_signal: CODEX_BRAINOPS_E48_INTEGRATED_RECOVERABLE_AUTHORITY_RELEASE_GATE_READY_FOR_GPT_REVIEW

## Fundamental Constraint

E48 will expose exactly one positive execution authority chain. Recovery state will be integrated into the actual `DurableExecutionLeaseAuthority` and `DurableClaimAuthority` path. No caller-constructible lifecycle authority, mirror claim authority, or plain terminal evidence may become a positive path.

## Scope and Source Discipline

Only these paths may change:

1. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/**`
2. `.github/workflows/brainops-e48.yml`

Source code and tests will be imported only as selected files/blobs from frozen E47. Before any import, E48 will record each source path, blob SHA256, destination, reuse rationale, and exclusion rationale. No branch merge, cherry-pick, mutation of E47, or use of E47's public `RecoverableLifecycleAuthority` as an authority is allowed.

## Implementation Sequence

1. Materialize a selected E47 source manifest and add failing integration tests against the actual durable claim and lease entrypoints. The first tests must demonstrate the pre-integration response-loss and caller-mintable parallel-authority defects.
2. Import only the mandatory-path foundation and replace all positive exports with a single integrated facade. Internal recovery helpers must require verified provenance, an actual durable claim, and a consumed verifier-minted capability decision.
3. Make capability, effect, invocation, terminal attestation, terminal claim mutation, and lease commit recoverable from request-bound durable journals. Prove actual `DurableClaimRecord` and lease CAS mutation at most once under restart and response loss.
4. Require verifier-minted `AttestedExecutionIdentity` and `AttestedTerminalEvidence`, including owner, target, transport, source, invocation, and terminal semantics. Reject copied strings, plain objects, substituted claims, and stale evidence.
5. Recheck expiry, temporal order, request binding, route, approval, provenance, and challenge validity at every positive or `ALREADY_*` path. Expired replay must fail closed with no mutation.
6. Add a repository-backed release-gate command that derives graph, topology, allowlist, source-manifest, workflow and generated-provider facts from the checked-out repository. In-job output remains pre-evidence only; final provider conclusion and post-receipt immutability remain GPT review-time checks.
7. Add an isolated active mutation harness. Each required implementation or workflow mutation must execute a real validator/test and yield a recorded nonzero result before restoration.
8. Add `.github/workflows/brainops-e48.yml` with exact-head checkout/assertion, Python 3.11/3.13 full suite, E48 integration suite, release gate, mutation harness, public-safety scan, and canonical pre-evidence artifact.
9. Designate a tested head only after local gates are green, then wait for exact-head CI. Add one nonempty evidence-only receipt commit only after tested-head CI is green. Receipt-head CI may report only `PENDING_GPT_REMOTE_HEAD_RECHECK` for post-receipt immutability.

## Required Test Families

- unique exported positive authority and parallel-authority rejection
- actual durable claim invocation and terminal mutation under response loss/restart
- verifier-minted capability, identity, and terminal evidence rejection tests
- capability creation partial-state, replay, substitution, and conflict recovery
- expiry boundary, post-expiry replay, and temporal ordering for every stage
- repository-backed release-gate failures for graph, topology, provider evidence, scope, and placeholders
- active mutations for all eight required weakness classes
- exact-head workflow policy parser validation on temporary workflow copies

## Boundaries and Unknowns

- Engineering and synthetic tests only. No real authority, Canary, App, CLI, credential, account, market, or trading invocation.
- E48 cannot self-certify a finished GitHub run inside that same run. Provider finality and post-receipt branch immutability remain explicit GPT review gates.
- Production trust roots, authenticated transport, and branch-protection configuration stay `UNKNOWN` or proposal-only.

## Checkpoints and Rollback

The first commit contains this plan only. Subsequent implementation commits may be reverted as ordinary commits before the designated tested head. The sole receipt commit is evidence-only and will be the final commit. No external mutable state is created by this task.
