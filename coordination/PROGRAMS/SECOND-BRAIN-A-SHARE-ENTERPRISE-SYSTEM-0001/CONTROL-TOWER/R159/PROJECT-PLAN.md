# R159 Project Plan — Reversible Change Foundation

## Mission

Implement the must-do / very-high-value reversible-change foundation from Issues #477/#478/#479 before Continuous Engineering Verification D1.

R159 covers `CEA-SIG-001..009` and A0/A1/A2 of `CEA-SIG-027` only.

## Authority and exact scope

R159 is additive-only and may change exactly the seven paths released by Issue #479. It does not modify R149–R158 runtime, Signal truth/materializers, #453 Review Queue, #7 dispatcher, active claims, worker registry, W3/domain truth, repository settings, tags, databases, runtime snapshots, production services, secrets, accounts, orders, or funds.

All task/route/write/review/merge/release/trading authority booleans remain false. A checkpoint, assessment, publication binding, or revert plan is evidence/guard material, never execution authority.

## Reversibility contract

`ChangeReversibilityAssessment/v1` deterministically derives:

- `REVERSIBLE_GIT_ONLY`
- `REVERSIBLE_BY_VERSION_SWITCH`
- `REVERSIBLE_WITH_MIGRATION`
- `REVERSIBLE_WITH_SNAPSHOT`
- `COMPENSATABLE_ONLY`
- `IRREVERSIBLE_OR_HIGH_RISK`

Large/critical, stateful/mixed, GPT-judged-large, or explicitly marked changes require a mechanically validated rollback checkpoint before normal PASS. Stateful changes cannot become Git-only merely because source code is versioned. Irreversible external side effects cannot mint ordinary reversible status.

`validate_assessment()` re-normalizes authoritative input and re-derives classification, marker requirement, checkpoint binding, result, and authority boundary. Recomputing a digest after editing semantics cannot restore validity.

## Durable KnownGoodCheckpoint/v1

### Canonical identity binding

Capture reads the configured Git remote and canonical branch. It derives repository identity from the remote URL and reads the live canonical branch tip with `git ls-remote`; it does not trust a caller-supplied repository label or a stale local `origin/main` projection.

Capture requires:

- local `HEAD == expected canonical main`;
- live remote canonical main equals that same SHA;
- a clean worktree including untracked files;
- exact canonical tree SHA;
- at least one relevant policy/schema path, each bound to its canonical blob SHA;
- CI status `PASS` or explicitly `NOT_APPLICABLE`, with evidence references for PASS;
- deterministic verification status `PASS`, with evidence references;
- independent review status `PASS` or explicitly `NOT_APPLICABLE`, with evidence references for PASS;
- UTC timestamp, trigger/reason, previous checkpoint digest when present, provenance, and bounded evidence refs.

R159 binds these supplied evidence states and references into the checkpoint. It does **not** become the D1 authority that independently discovers or validates every CI/review provider result. Automated provider verification remains a later D1 responsibility.

### Durable recovery anchor

The recovery anchor is **not a newly minted Git object**. It is the exact canonical `main` commit that was already reachable from the live remote canonical branch when capture occurred:

`live remote canonical main == recovery_anchor_commit == canonical_main_sha`

This removes the prior `commit-tree` pre-publication gap. The anchor is already reachable before material engineering begins, so local reflog expiry / `git gc --prune=now`, process exit, serialization, or a fresh clone cannot make the recovery target disappear while canonical history is preserved.

The serialized `KnownGoodCheckpoint/v1` binds:

- repository identity derived from the configured remote;
- canonical source ref;
- exact canonical commit/tree;
- `recovery_anchor_commit`, which must equal the captured canonical main;
- policy/schema blob versions;
- CI / deterministic-verification / independent-review evidence state and refs;
- UTC capture provenance;
- deterministic checkpoint ID/digest;
- all-false authority.

No tag, branch, remote-tracking ref, Git note, repository setting, database record, snapshot, second registry, or standalone marker object is created by checkpoint capture.

### Implementation publication binding

A durable recovery anchor alone says **where to recover to**. It does not by itself prove which later implementation was protected by that checkpoint.

Therefore the first commit on the protected implementation's first-parent lineage immediately after the recovery anchor must contain the exact trailer:

`R159-Checkpoint-Digest: <checkpoint_digest>`

Post-change validation requires:

1. the recovery anchor is a strict first-parent ancestor of the supplied implementation head;
2. the first implementation commit after the anchor has the anchor as its first parent;
3. that first commit contains the exact checkpoint digest trailer.

A later second/third commit cannot retroactively add the binding. This prevents after-the-fact checkpoint laundering without introducing a separate marker commit or ref mutation.

`checkpoint_publication_state()` exposes only evidence state:

- `CAPTURED_DURABLE_CANONICAL_ANCHOR` before implementation publication;
- `PUBLISHED_IMPLEMENTATION_LINEAGE` after the exact first commit binds the checkpoint digest.

Neither state grants execution, write, review, merge, or release authority.

### Revalidation

`validate_known_good_checkpoint()` mechanically checks:

- schema/digest/ID and all-false authority boundary;
- current remote repository identity and canonical remote ref identity;
- recovery anchor/base commit existence and exact tree;
- recovery anchor equals the captured canonical main;
- current canonical main remains descended from the captured anchor, so destructive history rewrite fails closed;
- policy/schema blob bindings still match the captured anchor;
- pre-change use requires HEAD and live remote canonical main still equal the captured anchor;
- post-change use requires the supplied implementation head to be a strict descendant with the exact first-commit checkpoint publication binding.

Git graph/object checks run with replacement objects disabled so local `git replace` state cannot launder tree/ancestry evidence.

## GovernedRevertPlan/v1

A governed plan binds:

- checkpoint ID/digest;
- `checkpoint_recovery_anchor_commit`;
- `checkpoint_publication_binding_commit`;
- target canonical commit/tree;
- exact implementation head being reverted;
- semantically re-derived PASS assessment.

Recovery strategy is derived, not caller-selected:

- Git-only -> `FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT`
- policy/behavior -> `VERSION_SWITCH_OR_FEATURE_FLAG`
- migration -> `FORWARD_REVERT_PLUS_DOWN_MIGRATION`
- snapshot -> `FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE`
- compensatable external effect -> `COMPENSATING_ACTION_PLUS_FORWARD_REVERT`

Every plan preserves history, forbids destructive history rewrite, requires exact-head reverification, requires independent review for MEDIUM/LARGE/CRITICAL changes, and requires user approval for critical/compensatable recovery where derived. `validate_governed_revert_plan()` revalidates checkpoint + publication lineage, re-derives assessment and plan semantics, and rejects recomputed-digest laundering.

## User trigger

Literal phrase `做个滚回记号` maps to `USER_EXPLICIT_ROLLBACK_MARKER`. The phrase creates a requirement; it does not itself grant write/merge/release authority.

## Independent review remediation history

### Review 1 — `pullrequestreview-5050614237`

Found and remediated:
1. full caller-forged checkpoint mappings could self-mint trust;
2. assessment/revert-plan semantics could be changed and re-digested.

Semantic re-derivation remains mandatory.

### Review 2 — `pullrequestreview-5050837907`

Found: first anti-forgery repair created `refs/tags/r159-known-good/...` using `git update-ref`, violating the explicit no-tag boundary.

Remediation removed tag/ref mutation and retained semantic re-derivation.

### Review 3 — `pullrequestreview-5051429387`

Found:
1. invocation-local seal could not survive process/serialization boundaries and therefore was not a durable rollback marker;
2. repository/canonical-main identity and the CEA-SIG-003 minimum evidence envelope were incomplete/caller-asserted.

Remediation added live remote repository/main re-derivation, policy/schema blob binding, CI/deterministic/review evidence envelope, UTC provenance, and cross-process Git validation.

### Review 4 — `pullrequestreview-5052766026`

Found: the zero-tree-change `git commit-tree` marker was an unreachable Git object until later implementation publication, so standard Git GC could prune the supposed rollback anchor during the exact pre-publication window it was meant to protect.

The reviewer reproduced the mechanism in an unrelated temporary repository with `git fsck --unreachable --no-reflogs`, reflog expiry, and `git gc --prune=now`.

Current remediation removes the standalone marker object entirely. The recovery target is the already-reachable canonical main commit. A separate first-implementation-commit trailer binds the exact checkpoint digest to the protected implementation lineage. This closes the GC window without tags/refs or a new durable authority.

The review-4 non-blocking carry-forward remains: CI / deterministic-verification / independent-review references are bound evidence in R159, not provider-verified truth; D1 must validate providers before treating them as such.

## Adversarial regression matrix

The R159 suite covers at least:

- small/medium/large/critical and GPT/user-trigger marker matrix;
- stateful snapshot/migration/Git-only and mixed surfaces;
- policy version-switch and external compensation/irreversible surfaces;
- digest-only marker spoofing;
- serialized/deep-copied cross-process checkpoint revalidation;
- repository-label substitution and remote-identity substitution;
- live remote-main drift at capture;
- destructive canonical-history rewrite rejection;
- dirty and untracked worktree rejection;
- required policy/schema paths and missing-path failure;
- CI FAIL and deterministic INCONCLUSIVE rejection;
- PASS state without evidence refs rejection;
- canonical recovery anchor exact commit/tree binding;
- recovery anchor survival across reflog expiry and `git gc --prune=now`;
- serialized checkpoint survival across GC/restart boundary;
- fresh clone validation after implementation publication;
- exact first-commit publication trailer binding;
- rejection of unbound descendants;
- rejection of late second-commit checkpoint binding;
- implementation head strict ancestry;
- `git replace` laundering resistance;
- assessment marker-bit/classification laundering;
- revert strategy/review/history/authority laundering;
- CLI checkpoint serialization and later reuse;
- no mutable tag/ref/standalone-commit-tree seam;
- all authority booleans false.

## CI gate

Python 3.11 and 3.13 must both pass:

- exact PR head + current base provenance;
- compile module/tests;
- all three schemas parse;
- R159 adversarial suite;
- complete retained Control Tower suite;
- exact seven-file additive-only diff;
- durable canonical-anchor/publication-binding/all-false-authority static invariants;
- no mutable tag/ref, standalone `commit-tree`, or destructive-history seam;
- `git diff --check` and unfinished-marker rejection.

## Stop gate

Engineering stops after a final exact head has green CI, an engineering handoff, and a new exact-head `REVIEW_REQUEST/v1` in Issue #453. No self-review, Ready transition, or merge before a matching independent exact-head ACCEPT.

## Next slice

Only after governed R159 merge and fresh post-merge priority reconciliation may another implementation slice start. #478 D1 remains the intended Continuous Engineering Verification successor unless a higher-priority canonical issue (currently #308 P0 is a candidate) wins the fresh priority scan.
