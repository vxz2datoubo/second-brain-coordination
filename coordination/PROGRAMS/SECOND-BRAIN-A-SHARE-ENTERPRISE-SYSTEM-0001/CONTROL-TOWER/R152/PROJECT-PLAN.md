# R152 — Idle Signal Auto-Release Apply Transaction

Issue: #463
Draft PR: #464

Base main at engineering start: `9ba2fa2346fcb813782a840a781de1ad7338663a`

## Purpose

R151 deliberately stops at `IdleSignalAutoReleaseAuthorization/v1` plus a logical side-effect plan. R152 makes the handoff to GitHub / Control Tower mechanically safe without creating a second task, route, claim, worker, Signal, R145, R149, R150 or R151 authority.

## Fresh architecture reconciliation

R152 reuses canonical R151 by replaying `evaluate_idle_signal_startup(...)` at apply time. Caller priority input remains additive only. A caller cannot attest current priority completeness or present a stale authorization as current truth.

A canonical R144 constraint shapes the apply transaction: every ACTIVE or RESERVED GPT worker slot must carry complete Issue / PR / branch / provenance binding, and its Work Claim identity and surface must exactly match. Therefore R151's five logical side-effect capabilities cannot safely become five immediate canonical writes before a real Draft implementation PR exists.

R152 preserves the R151 logical authorization while materializing it through two governed stages and a trusted post-activation readback.

## Stage 1 — NONEXECUTABLE BOOTSTRAP

R152 first:

1. binds to exact current canonical main;
2. fresh-replays R151/R150/R149;
3. proves no current P0/P1/P2 or active Claim/worker-slot blocker;
4. derives the **next canonical route epoch** by scanning retained canonical Route artifacts;
5. rejects any caller-selected reused/stale route epoch;
6. derives deterministic task / route / worker-slot / branch identity from the R151 authorization digest;
7. emits only the instructions needed to create an implementation Issue and an empty-commit Draft implementation PR.

The bootstrap stage grants no implementation-file write and no execution authority.

Caller bootstrap evidence is **selectors only**:

- Issue number
- implementation PR number
- deterministic branch
- bootstrap head

The caller is no longer allowed to attest `draft=true`, `empty_bootstrap_commit=true`, or `file_mutations=[]`.

R152 reuses the retained R137 public GitHub on-demand provider and freshly verifies:

- exact Issue is open and is not a PR;
- Issue contains exact R151 authorization / Signal / task markers;
- implementation PR is open, Draft, unmerged, same repository, base=`main`;
- implementation PR branch/head are exact and its body contains the same markers plus the Issue reference;
- bootstrap commit has exactly one parent;
- parent is the R151 authorization's canonical main;
- bootstrap commit tree is byte-identical at Git-tree identity level to the parent tree.

Only that last tree-equality proof establishes `EMPTY_BOOTSTRAP_COMMIT`. Caller prose does not.

## Stage 2 — ACTIVATION GATE CANDIDATE

After trusted bootstrap readback, R152 fresh-replays R151 again and requires:

- exact current main still equals the authorization main;
- original `TaskReleaseProposal/v1` surface equals requested apply surface;
- no W3 / Signal runtime / trade / secret / production / destructive expansion;
- target Lane is currently closed and its canonical reopen rule permits the release reason;
- no competing ACTIVE/RESERVED Work Claim or GPT worker slot;
- deterministic Route identity does not already exist;
- route epoch is still the next canonical epoch.

R152 then creates an **expected-state manifest**, not a mutation executor.

The activation gate is restricted to exactly three changed paths:

1. the one deterministic new Route artifact;
2. `coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml`;
3. `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`.

Path-level restriction alone is insufficient because same-file collateral mutation is possible. Therefore the manifest also binds:

- complete baseline digest of the Work Claim document;
- complete expected post-activation Work Claim document, changing only the selected Lane;
- complete baseline digest of the GPT worker registry;
- complete expected post-activation worker registry, adding only the selected slot;
- exact Route payload;
- exact task / epoch / Issue / PR / branch / read/write/interface/domain/authority surface across Route + Claim + slot.

The gate must be a separate PR, independently exact-head reviewed, and merged with normal two-parent `merge` semantics. The manifest itself grants no execution or merge authority.

## Independent review binding

A field named `reviewed_head` is not evidence.

Before post-activation verification can succeed, R152 freshly reads canonical Review Queue #453 and requires the current gate PR lineage to contain an exact `(PR, head)` `REVIEW_RESULT/v1` with:

- `verdict: ACCEPT`;
- `review_channel: GITHUB_APPROVE | EXACT_HEAD_COMMENT_ATTESTATION`;
- `reviewer_agent_id: GPT_INDEPENDENT_REVIEWER`;
- `independence_attestation: NO_PRODUCTION_CODE_OR_REMEDIATION_ON_REVIEWED_HEAD`;
- non-empty `review_evidence_ref`.

R152 then also reads the PR's actual review submissions and requires that `review_evidence_ref` resolve to a review submission on the same exact head:

- `APPROVED` for `GITHUB_APPROVE`, or
- `COMMENTED` for same-account `EXACT_HEAD_COMMENT_ATTESTATION`.

Thus Queue metadata cannot self-prove acceptance without matching PR review evidence.

## Trusted post-activation readback

Caller post-apply input is also selectors only. It does not supply Route, Claim, slot or canonical-state truth.

R152 freshly verifies through the retained R137 provider:

1. current `main` equals the claimed activation merge commit;
2. activation-gate PR is closed, merged, non-Draft and still bound to the independently accepted exact head;
3. merge commit has exactly two parents:
   - parent 1 = base main before activation;
   - parent 2 = independently reviewed exact head;
4. merge tree equals the reviewed-head tree;
5. reviewed head changed exactly the three manifest-approved paths and no fourth path;
6. implementation PR remains open/Draft and its head is still the empty bootstrap head, proving implementation did not start early;
7. Route payload on canonical main exactly equals the manifest;
8. the **entire** canonical Work Claim document exactly equals the expected document and digest;
9. the **entire** canonical GPT worker registry exactly equals the expected document and digest.

Only then is `TrustedIdleSignalAppliedStateObservation/v1` produced.

The resulting `IdleSignalApplyReceipt/v1` explicitly separates:

- `base_main_before_activation`;
- `activation_gate_reviewed_head`;
- `activation_gate_merge_commit`;
- `current_main_after_activation`.

The receipt is evidence-only. It does not itself grant execution, merge, deployment, W3, Signal runtime, secret/permission or trading authority.

## First implementation validation

Earlier R152 head `aa119e3b67fd38dceec4bfe28ba5ddd7d04345fd` passed the first engineering validation round:

- R152: 24/24
- retained R151: 21/21
- retained R150: 16/16
- retained R149: 23/23
- full Control Tower: 262/262
- Python 3.11 + 3.13
- dedicated run `32989759914`: SUCCESS
- Foundation `32989758473`: SUCCESS
- Phase 3 `32989758352`: SUCCESS

That head is **historical engineering evidence only**, not the final review candidate. Subsequent self-adversarial hardening invalidates it as a review target.

## Current adversarial target

The hardened R152 suite includes attacks against:

- main drift;
- new P1/P2 after scheduling;
- forged R151 authorization;
- opportunity mismatch;
- write-path/domain/authority/interface expansion;
- reused route epoch;
- ambiguous canonical route epoch;
- caller self-attested Draft/empty/file-mutation claims;
- invalid Lane reopen;
- duplicate active Claim/slot;
- partial/reordered logical plan;
- high-risk/excluded side effects;
- non-empty bootstrap commit;
- wrong bootstrap parent main;
- non-Draft bootstrap PR;
- Queue ACCEPT without canonical independence fields;
- Queue ACCEPT without matching exact-head PR review submission;
- current-main/activation-merge mismatch;
- merge-parent mismatch;
- activation gate fourth-path smuggling;
- same-file collateral Work Claim mutation;
- implementation PR moving past bootstrap before activation readback;
- forged/partial post-apply selector state.

## Hard locks

- `NO_SECOND_TASK_AUTHORITY`
- `NO_SECOND_ROUTE_AUTHORITY`
- `NO_SECOND_WORK_CLAIM_AUTHORITY`
- `NO_SECOND_WORKER_SLOT_AUTHORITY`
- `NO_SECOND_SIGNAL_STORE`
- `NO_SECOND_R145_R149_R150_R151`
- `NO_CALLER_PRIORITY_COMPLETENESS`
- `NO_STALE_R151_AUTHORIZATION`
- `NO_CALLER_BOOTSTRAP_TRUTH_ATTESTATION`
- `NO_CALLER_POST_APPLY_TRUTH_ATTESTATION`
- `NO_REUSED_ROUTE_EPOCH`
- `NO_SURFACE_DOMAIN_INTERFACE_AUTHORITY_EXPANSION`
- `NO_PARTIAL_CONTROL_PLANE_APPLY`
- `NO_SAME_FILE_COLLATERAL_MUTATION`
- `NO_ACTIVE_SLOT_WITHOUT_PR_BINDING`
- `NO_INVALID_LANE_REOPEN`
- `NO_REVIEW_RESULT_WITHOUT_MATCHING_PR_REVIEW_EVIDENCE`
- `NO_IMPLEMENTATION_BEFORE_ACTIVATION_READBACK`
- `NO_W3_WRITE`
- `NO_SIGNAL_TOWER_RUNTIME_WRITE`
- `NO_TRADE`
- `NO_ACCOUNT_ORDER_FUND`
- `NO_SECRET_PERMISSION_VISIBILITY_EXPANSION`
- `NO_PRODUCTION_DEPLOY`
- `NO_DESTRUCTIVE_HISTORY_REWRITE`
- `NO_SELF_REVIEW`
- `NO_SELF_MERGE`

## Implementation PR scope

PR #464 itself may modify only:

1. `coordination/CONTROL-TOWER/idle_signal_apply.py`
2. `coordination/CONTROL-TOWER/tests/test_idle_signal_apply.py`
3. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R152/PROJECT-PLAN.md`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R152/IDLE-SIGNAL-APPLY-CONTRACT.schema.json`
5. `.github/workflows/program-control-tower-r152-idle-signal-apply.yml`

It MUST NOT modify `coordination/ACTIVE-*`, `coordination/ROUTES/**`, current `LANE-WORK-CLAIMS.yaml`, W3, Signal Tower runtime, trading or production authority surfaces.

## Stop gate

Final exact-head Python 3.11 + 3.13 R152 CI, retained R151/R150/R149, full Control Tower, Foundation, Phase 3, changed-path allowlist, authority-boundary checks and `git diff --check` must all pass before a `REVIEW_REQUEST/v1` is appended to #453.

No self-review. No merge before independent exact-head ACCEPT.

Completion signal:

`R152_IDLE_SIGNAL_AUTO_RELEASE_APPLY_TRANSACTION_READY_FOR_INDEPENDENT_REVIEW`
