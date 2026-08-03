# E41 Execution Plan: Durable One-shot Authority and Truthful Execution Evidence

`task_id: CODEX-BRAINOPS-DURABLE-GLOBAL-ONE-SHOT-CONSUMPTION-AND-REAL-EXECUTION-EVIDENCE-CLOSURE-0037-E41`
`route_epoch: 43`
`mode: project_plan`
`boundary: ENGINEERING_AND_TESTS_ONLY / NO_NEW_CANARY / NO_APP_OR_CLI_INVOCATION`

## Goal and Non-goals

E41 converts the reusable E40R1 local state-machine primitives into a
testable design that cannot confuse a local claim with either a globally
durable consumption or a real Codex execution. The authority must survive a
fresh local database, process restart, and competing worker.

E41 does **not** run a new Canary, App Automation, or Codex CLI process. It
does not reuse E40R1 approval `5155930613`, its nonce, or any E40 authority.
It does not modify canonical `main`; canonical route content may only be
terminalized by its authorized publisher.

## Inputs and Reuse Boundary

- Canonical route at claim: `f7d3d195af3f7b12465706ceda4550ce92e443db`.
- Frozen source: PR #127 receipt
  `b7c83e503b4ed69156627a8ba594d1682c37de5e`.
- Reuse only the files marked in `SOURCE-IMPORT-MANIFEST.yaml`; no branch
  merge or cherry-pick is allowed.
- Reused local SQLite remains a test-local primitive only. It is explicitly
  not the global authority.

## Architecture Decision

### Selected Design: CAS-backed Durable Claim Ledger

Define a `DurableClaimAuthority` contract with a fixed-repository content/ref
compare-and-swap (CAS) adapter. A claim record is immutable after creation and
uses `(repository, route_id, route_epoch, canary_id, nonce)` as its durable
uniqueness key. The adapter returns a public-safe revision token, never a
credential.

1. Read the durable record and canonical route snapshot.
2. CAS an immutable `CLAIMED` record with the expected revision.
3. Only the holder of that durable claim may attach an invocation receipt.
4. Write a terminal `SUCCEEDED`, `FAILED`, `TIMED_OUT`, or
   `RECOVERY_REQUIRED` record through CAS; no path reopens a claim.
5. Any claimed or terminal durable record overrides a stale route that still
   says `READY` for execution purposes.

The production GitHub transport is an interface and is not called in E41. A
deterministic in-memory/file-backed fake supplies CAS race and restart tests.
An unavailable adapter produces `UNKNOWN` or a fail-closed block; it never
falls back to a local database or a default-true capability flag.

### Rejected Alternatives

- Temporary SQLite as global authority: process-local and restartable.
- A `selected_owner` label as execution evidence: it records intent only.
- A default `app_available=true` preflight: not observable capability proof.
- Updating the active route before durable claim: allows split-brain replay.
- Live GitHub/App/CLI probing during E41: exceeds the engineering-only route.

## Truthful Evidence Model

The code will use disjoint evidence types:

| Type | Minimum evidence | Does not prove |
| --- | --- | --- |
| `CONTROL_PLANE_CLAIM_ONLY` | durable claim ID and route evidence | an App/CLI process ran |
| `CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION` | current-session manual action receipt | a new App run was dispatched |
| `APP_AUTOMATION_DISPATCHED_NEW_RUN` | bounded dispatch receipt plus callback/correlation | CLI execution |
| `CODEX_CLI_PROCESS_INVOKED` | process invocation and terminal receipt | App automation |

All invocation receipts require an invocation ID, parent correlation ID, owner
type, start/end time, terminal or exit status, non-attempted owner, redacted
log hash, and cleanup proof. Missing evidence downgrades classification rather
than inferring an invocation.

## Staged Engineering Plan

1. **P0: Plan and import accountability**
   - Publish this plan and the source-import manifest.
   - Open the sole Draft PR after this nonempty commit.
2. **P1: Contracts and selected-source migration**
   - Import only listed E40 source primitives.
   - Add durable record, CAS adapter, route-terminal decision, capability
     evidence, and invocation-evidence contracts.
3. **P2: Global authority implementation**
   - Implement atomic durable claim/finalization and crash reconciliation.
   - Preserve the existing local store as an explicitly non-authoritative test
     double.
4. **P3: Fail-closed execution interpretation**
   - Reject stale `READY` route execution after a durable claim or terminal
     record.
   - Remove default availability and require timestamped adapter evidence.
5. **P4: Adversarial validation**
   - Fresh database/restart, four-worker CAS race, crash-after-claim, timeout,
     duplicate callback, dual owner, old approval replay, and stale-ready
     conflict.
6. **P5: Evidence closure**
   - One substantive tested commit, exact Python 3.11/3.13 CI, one nonempty
     receipt-only commit, then receipt-head CI and GPT second pass.

## Tests and Acceptance

Tests will use synthetic durable namespaces and fake CAS adapters only. They
must prove one winner across fresh local states, fail closed when the authority
adapter is unavailable, and preserve a claimed record through simulated crash
recovery. A test may never classify a claim as an App/CLI invocation without
the matching receipt type.

The final CI workflow will check the exact PR head under Python 3.11 and 3.13.
No performance, market, account, order, or trade test is in scope.

## Risks, Unknowns, and Coordination

- The future production GitHub CAS transport may need a separately governed
  credential/runtime integration. E41 implements its contract and fake only.
- Canonical route-file mutation is owned by the route publisher; E41 instead
  makes durable terminal authority override stale route content.
- Whether a future host can prove cross-process App ownership remains UNKNOWN;
  E41 refuses to elevate an owner label into that proof.

Rollback is a reverse revert of task-owned E41 commits. No external runtime,
service, credential, or trading state is created by this plan.
