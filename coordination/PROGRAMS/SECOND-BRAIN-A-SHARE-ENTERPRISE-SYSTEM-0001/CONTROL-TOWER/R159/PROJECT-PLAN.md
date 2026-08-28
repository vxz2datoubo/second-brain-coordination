# R159 Project Plan — Reversible Change Foundation

## Mission

Implement the first high-value landing slice from Issue #478 before Continuous Engineering Verification D1.

Source requirements:
- Architecture: Issue #477.
- Durable master checklist: Issue #478.
- Exact task: Issue #479.
- Bootstrap pre-change recovery anchor: Issue #478 comment `5450964841`.
- Base: `a65488b9be4d60ac5198201fdd7872df1e2f4957`.

This slice implements `CEA-SIG-001..009` and A0/A1/A2 of `CEA-SIG-027`.

## Why this is first

The system should not automate longer engineering/review loops before it can cheaply answer:

1. Is this change actually reversible?
2. Does this change need a rollback marker before work starts?
3. What exact Git commit/tree is the recovery anchor?
4. Does source rollback also require state migration, snapshot restore, version switch, or compensation?
5. Is the rollback itself governed and re-verified?

For ordinary code/config changes, Git already supplies the durable content history. R159 adds classification and exact recovery binding rather than copying repository contents into a second backup store.

## Reuse and non-duplication

R159 reuses:
- Git commit/tree as code-state provenance and recovery substrate;
- a deterministic Git marker ref derived from the checkpoint digest as the trust-bearing proof that the rollback marker was actually minted;
- existing Phase-1 reversible/irreversible semantics as historical foundation;
- existing Phase-3 evidence that Git branch rollback and runtime snapshot rollback are separate concerns;
- Issue #453 as the only Independent Review Queue;
- existing Control Tower release/merge authority.

R159 does not create:
- a second Git history;
- a snapshot/database runtime;
- a second Review Queue;
- a second dispatcher;
- a task/release/merge authority;
- a stateful migration authority;
- a W3 or domain truth source.

## Contracts

### ChangeReversibilityAssessment/v1

Inputs are normalized into:
- change surface kind;
- blast radius;
- explicit user rollback-marker request;
- GPT large-change judgment;
- persistent-state mutation;
- external irreversible side effect;
- declared recovery mechanism;
- rollback checkpoint digest if required.

Outputs distinguish:
- `REVERSIBLE_GIT_ONLY`
- `REVERSIBLE_BY_VERSION_SWITCH`
- `REVERSIBLE_WITH_MIGRATION`
- `REVERSIBLE_WITH_SNAPSHOT`
- `COMPENSATABLE_ONLY`
- `IRREVERSIBLE_OR_HIGH_RISK`

A large/stateful/explicitly-marked change without a **Git-verified checkpoint object** fails closed to `REQUIRES_ROLLBACK_MARKER`. A caller-supplied 64-hex digest alone cannot satisfy the marker requirement, and a caller-recomputed full JSON checkpoint cannot satisfy it unless the corresponding deterministic Git marker ref actually exists and binds the exact checkpoint commit/tree lineage.

A stateful change cannot become Git-only merely because source code is versioned.

`validate_assessment()` is a semantic trust gate, not a checksum gate. It re-normalizes the embedded input and deterministically re-derives classification, marker requirements, checkpoint-binding semantics and final assessment result. A caller cannot alter those decisions and restore validity merely by recomputing SHA-256.

### KnownGoodCheckpoint/v1

A checkpoint:
- derives the exact checked-out commit and tree from Git;
- requires a clean worktree;
- requires the configured canonical branch, default `main`;
- rejects expected-head drift;
- binds the trigger source and reason;
- has a deterministic semantic digest;
- mints `refs/tags/r159-known-good/<checkpoint_digest>` as the Git-native rollback-marker proof;
- re-verifies that marker ref -> exact commit, commit -> exact tree, and source branch still contains the checkpoint commit before trusted use;
- carries evidence references only as references, never as acceptance authority;
- grants no execution/review/merge/release authority.

The Git marker is deliberately not a second source-history store. It is only a tiny trust-bearing pointer into existing Git history. Re-validation requires repository state, so a serialized checkpoint mapping by itself is evidence, not authority.

`DESIGNATED_RECOVERY_ANCHOR` means the user/GPT selected this exact code state as the recovery target. It does not claim that referenced CI/review evidence was independently revalidated by R159.

### GovernedRevertPlan/v1

A revert plan can be created only from:
- a currently Git-verified checkpoint;
- a semantically re-derived valid PASS assessment;
- exact checkpoint-digest binding.

Recovery strategy is derived from the reversibility class:
- Git-only -> forward revert PR or corrective commit;
- policy/behavior -> version switch or feature flag;
- migration -> source revert plus down migration;
- snapshot -> source revert plus snapshot restore;
- compensatable external side effect -> compensating action plus forward source revert.

Every plan:
- preserves history;
- forbids destructive history rewrite;
- requires exact-head re-verification;
- requires independent review for MEDIUM/LARGE/CRITICAL blast radius;
- cannot grant merge/release authority.

`validate_governed_revert_plan()` re-verifies the checkpoint, re-derives the assessment, and reconstructs the canonical strategy/review/approval semantics from those trusted inputs. Recomputed-digest changes to strategy, independent-review requirement, user-approval requirement, history preservation or authority boundaries are rejected.

## Independent review remediation — exact head predecessor `e99456e7...`

Independent review `pullrequestreview-5050614237` returned `CHANGES_REQUIRED` with two P1 blockers:

1. a full caller-forged `KnownGoodCheckpoint/v1` could previously recompute digest/id and set `git_binding_verified: true` without any trust-bearing Git provenance;
2. assessments and revert plans could previously alter semantic decisions and recompute ordinary digests without deterministic re-derivation.

Bounded remediation keeps the same seven-file slice and closes those failure classes by:
- requiring a real deterministic Git marker ref for trusted checkpoint use;
- re-reading commit/tree/source-ref lineage from Git;
- requiring repository context whenever a checkpoint is used to satisfy a trust gate;
- semantic re-derivation for assessment validators;
- semantic re-derivation for governed revert-plan validators;
- adversarial regressions for complete checkpoint forgery, stateful->Git-only/PASS laundering, marker bypass, strategy laundering, independent-review suppression, user-approval suppression, history-rewrite laundering and authority escalation.

No second checkpoint authority, signature authority, review authority or merge authority is introduced.

## User phrase

The literal phrase `做个滚回记号` maps to `USER_EXPLICIT_ROLLBACK_MARKER`.

The phrase detector is a convenience signal only. The resulting checkpoint must still be created through the exact Git-bound checkpoint contract.

## Seven-file additive scope

1. `coordination/CONTROL-TOWER/reversible_change.py`
2. `coordination/CONTROL-TOWER/tests/test_reversible_change.py`
3. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/CHANGE-REVERSIBILITY-ASSESSMENT.schema.json`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/KNOWN-GOOD-CHECKPOINT.schema.json`
5. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/GOVERNED-REVERT-PLAN.schema.json`
6. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R159/PROJECT-PLAN.md`
7. `.github/workflows/program-control-tower-r159-reversible-change.yml`

All are additive relative to the canonical base. No pre-R159 Control Tower runtime or authority file is modified.

## Test matrix

R159 unit/adversarial tests cover:
- small code-only low-cost behavior;
- explicit phrase and GPT large-change marker triggers;
- large change checkpoint requirement;
- invalid/missing checkpoint reference;
- full caller-recomputed checkpoint mapping without real Git marker;
- moved/deleted marker ref;
- commit/tree/source-ref binding;
- stateful Git-only false-reversibility rejection;
- migration and snapshot classes;
- policy version-switch class;
- compensation versus irreversible external effect;
- unknown field/enum rejection;
- clean Git checkpoint capture;
- dirty/untracked/head/branch drift rejection;
- ordinary digest tamper rejection;
- recomputed-digest assessment semantic laundering;
- recomputed-digest revert strategy laundering;
- independent-review suppression laundering;
- user-approval suppression laundering;
- history-rewrite laundering;
- authority escalation laundering;
- checkpoint-to-assessment exact binding;
- history-preserving recovery strategies;
- exact-head re-verification requirement;
- independent-review requirement for material rollback;
- zero authority grants.

## CI gate

Python 3.11 and 3.13:
- exact PR head and base verification;
- compile R159 module/tests;
- parse all three JSON schemas;
- run R159 tests;
- run complete retained Control Tower suite;
- prove exact seven-file additive-only diff;
- static authority-boundary checks;
- `git diff --check`;
- reject unfinished markers.

## Stop gate

Engineering stops after:
- Draft PR;
- exact-head CI green;
- engineering handoff;
- new exact-head `REVIEW_REQUEST/v1` in Issue #453.

No self-review, Ready transition, or merge before a matching independent exact-head ACCEPT.

## Next slice

Only after R159 is independently accepted, governed-merged, and post-merge reconciled should Issue #478 D1 begin:

`Deterministic Evidence + Verification MVP`

D1 must not be bundled into R159.
