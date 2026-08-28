# R159 Project Plan — Reversible Change Foundation

## Mission

Implement the reversible-change foundation from Issues #477/#478/#479 before Continuous Engineering Verification D1.

R159 covers `CEA-SIG-001..009` and A0/A1/A2 of `CEA-SIG-027`.

## Authority and scope boundary

R159 is additive-only and may change exactly seven released paths. It does **not** modify R149-R158 runtime, Signal truth, Review Queue, dispatcher, claims, worker registry, W3, domain truth, repository settings, Git tags/refs, databases, runtime snapshots, production services, secrets, accounts, orders, or funds.

All R159 authority booleans are false.

## Reversibility contract

`ChangeReversibilityAssessment/v1` deterministically derives one of:

- `REVERSIBLE_GIT_ONLY`
- `REVERSIBLE_BY_VERSION_SWITCH`
- `REVERSIBLE_WITH_MIGRATION`
- `REVERSIBLE_WITH_SNAPSHOT`
- `COMPENSATABLE_ONLY`
- `IRREVERSIBLE_OR_HIGH_RISK`

A large/critical, stateful/mixed, GPT-judged-large, or explicitly marked change requires a valid checkpoint before a normal PASS can be produced.

Stateful changes cannot become Git-only merely because source code is versioned. External irreversible side effects cannot mint a normal reversible result.

`validate_assessment()` is a semantic trust gate. It re-normalizes the embedded input and re-derives classification, marker requirement, checkpoint-binding state and result. Recomputing SHA-256 after changing those semantics does not restore validity.

## KnownGoodCheckpoint/v1

Checkpoint capture:

- reads exact `HEAD` and `HEAD^{tree}` from Git;
- requires the expected exact head;
- requires the configured source branch, default `main`;
- requires a clean worktree including untracked files;
- binds trigger source, reason, optional prior checkpoint digest and evidence references;
- computes a deterministic semantic digest;
- grants no execution/review/merge/release authority;
- performs **no repository mutation**.

### Trust model

Issue #479 explicitly forbids tag mutation in this slice. Therefore R159 does not create tags, refs, branches, commits, settings, durable registries, snapshots or any second checkpoint authority.

A freshly captured checkpoint is wrapped in an invocation-local sealed mapping created by a private closure. Authority-bearing use requires that sealed object plus fresh Git revalidation of:

- checkpoint commit existence;
- commit -> exact tree;
- source branch existence;
- checkpoint commit ancestry under the source branch.

`checkpoint_evidence()` or JSON serialization intentionally strips the invocation-local seal. The resulting `KnownGoodCheckpoint/v1` JSON remains deterministic evidence, but it cannot by itself satisfy a rollback-marker trust gate.

This is fail-closed by design. Durable cross-process checkpoint attestation is deferred to a separately authorized future slice; R159 does not smuggle in a tag/registry/signature authority to obtain persistence.

## GovernedRevertPlan/v1

A governed plan requires:

- a currently sealed and Git-revalidated checkpoint;
- a semantically re-derived PASS assessment;
- exact checkpoint digest binding.

Recovery strategy is derived, never caller-selected:

- Git-only -> `FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT`
- policy/behavior -> version switch or feature flag
- migration -> forward source revert plus down migration
- snapshot -> forward source revert plus snapshot restore
- compensatable external effect -> compensating action plus forward source revert

Every plan preserves history, forbids destructive history rewrite, requires exact-head reverification, requires independent review for MEDIUM/LARGE/CRITICAL changes, and grants no merge/release authority.

`validate_governed_revert_plan()` revalidates the sealed checkpoint, re-derives the assessment, reconstructs canonical strategy/review/approval semantics, and rejects recomputed-digest laundering.

## Review remediation history

### Review 1 — `pullrequestreview-5050614237`

Closed:
1. full caller-forged checkpoint object could self-mint trust;
2. assessment/revert-plan semantic fields could be changed and re-digested.

The semantic re-derivation closure is retained.

### Review 2 — `pullrequestreview-5050837907`

Finding:
- the first anti-forgery repair created `refs/tags/r159-known-good/...`, violating Issue #479's explicit `No modification of ... tags` boundary.

Current bounded remediation:
- removes all tag/ref creation and `git update-ref`;
- keeps fresh Git commit/tree/source-ref ancestry revalidation;
- replaces durable tag proof with invocation-local sealed checkpoint identity;
- makes serialized/plain/deep-copied checkpoint mappings evidence-only;
- adds source and workflow guards proving no tag/ref mutation API is present.

No scope amendment or new authority is claimed.

## User trigger

The literal phrase `做个滚回记号` maps to `USER_EXPLICIT_ROLLBACK_MARKER`.

The phrase is only a trigger. It does not itself mint a checkpoint or grant authority.

## Exact seven-file scope

1. `coordination/CONTROL-TOWER/reversible_change.py`
2. `coordination/CONTROL-TOWER/tests/test_reversible_change.py`
3. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/CHANGE-REVERSIBILITY-ASSESSMENT.schema.json`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/KNOWN-GOOD-CHECKPOINT.schema.json`
5. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/GOVERNED-REVERT-PLAN.schema.json`
6. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/PROJECT-PLAN.md`
7. `.github/workflows/program-control-tower-r159-reversible-change.yml`

## Adversarial regression matrix

The R159 suite covers at least:

- small code-only change without heavyweight marker;
- literal user trigger;
- large/GPT-judged-large marker requirement;
- digest string alone cannot satisfy marker;
- checkpoint capture changes no refs/tags;
- plain serialized checkpoint cannot regain trusted status;
- deep-copy loses trusted status;
- full forged mapping cannot satisfy large-change gate;
- valid sealed checkpoint satisfies the gate;
- checkpoint remains valid after descendant HEAD advance;
- commit/tree/source-ref ancestry is re-read from Git;
- dirty/untracked/head/branch drift fails closed;
- stateful Git-only false reversibility;
- migration/snapshot/version-switch/compensation classes;
- external irreversible effect user gate;
- ordinary digest tamper;
- recomputed-digest stateful->Git-only laundering;
- recomputed marker bypass;
- forged checkpoint-verified bit;
- assessment authority escalation;
- strategy laundering;
- independent-review suppression;
- user-approval suppression;
- destructive-history-rewrite laundering;
- plan authority escalation;
- plain checkpoint cannot build revert plan;
- unknown intent fields fail closed;
- CLI checkpoint emits evidence without Git mutation;
- CLI serialized checkpoint cannot be promoted back into trust;
- module source contains no `update-ref`, `refs/tags/`, or `git tag`;
- no exported seal/mint helper exists;
- all authority booleans remain false.

## CI gate

Python 3.11 and 3.13:

- exact PR head + current base verification;
- compile module/tests;
- parse all schemas;
- run R159 adversarial suite;
- run complete retained Control Tower suite;
- exact seven-file additive-only diff;
- static authority boundary checks;
- static no-tag/no-ref-mutation checks;
- `git diff --check`;
- unfinished-marker rejection.

## Stop gate

Engineering stops after a final exact head has green CI, an engineering handoff, and a new exact-head `REVIEW_REQUEST/v1` in Issue #453.

No self-review, Ready transition, or merge before a matching independent exact-head ACCEPT.

## Next slice

Only after governed R159 merge and post-merge reconciliation may Issue #478 D1 begin:

`Deterministic Evidence + Verification MVP`
