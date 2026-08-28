# R159 Project Plan — Reversible Change Foundation

## Mission

Implement the must-do / very-high-value reversible-change foundation from Issues #477/#478/#479 before Continuous Engineering Verification D1.

R159 covers `CEA-SIG-001..009` and A0/A1/A2 of `CEA-SIG-027` only.

## Authority and exact scope

R159 is additive-only and may change exactly the seven paths released by Issue #479. It does not modify R149–R158 runtime, Signal truth/materializers, #453 Review Queue, #7 dispatcher, active claims, worker registry, W3/domain truth, repository settings, tags, databases, runtime snapshots, production services, secrets, accounts, orders, or funds.

All task/route/write/review/merge/release/trading authority booleans remain false. A checkpoint, assessment, or revert plan is evidence/guard material, never execution authority.

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

R159 binds these supplied evidence states and references into the marker. It does **not** become the D1 authority that independently discovers or validates every CI/review provider result. Automated provider verification remains a later D1 responsibility.

### Durable marker commit

The trust root is a Git commit object created with `git commit-tree`:

`canonical remote main -> zero-tree-change checkpoint marker -> implementation descendants`

The marker:

- has exactly one parent: the captured canonical main SHA;
- has exactly the canonical main tree, so it changes no tracked file;
- embeds the canonical `KnownGoodCheckpoint/v1` envelope in its commit message;
- is identified by `marker_commit` in serialized checkpoint evidence;
- does not create or move a tag, branch, remote-tracking ref, repository setting, database record, snapshot, or second checkpoint registry.

The capture operation itself does not move refs. Normal separately authorized engineering publication must make the material implementation lineage descend from the marker. If no implementation occurs after capture, there is nothing new to roll back.

A serialized checkpoint can therefore be revalidated in a later process/clone once the marker is present in the implementation history. Trust is re-derived from Git rather than from a process-local secret.

### Revalidation

`validate_known_good_checkpoint()` mechanically checks:

- schema/digest/ID and all-false authority boundary;
- current remote repository identity and canonical remote ref identity;
- canonical base and marker commit existence;
- exact base tree and zero-tree-change marker tree;
- marker has exactly the canonical base as its sole parent;
- marker commit message exactly reproduces the serialized checkpoint envelope;
- canonical base remains an ancestor of current canonical main;
- policy/schema blob bindings still match the captured base;
- pre-change use requires HEAD and current remote canonical main still equal the captured base;
- post-change use requires a supplied implementation head that is a **strict descendant** of the marker.

Git graph/object checks run with replacement objects disabled so local `git replace` state cannot launder parent/tree/ancestry evidence.

## GovernedRevertPlan/v1

A governed plan binds:

- checkpoint ID/digest;
- checkpoint marker commit;
- target canonical commit/tree;
- exact implementation head being reverted;
- semantically re-derived PASS assessment.

Recovery strategy is derived, not caller-selected:

- Git-only -> `FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT`
- policy/behavior -> `VERSION_SWITCH_OR_FEATURE_FLAG`
- migration -> `FORWARD_REVERT_PLUS_DOWN_MIGRATION`
- snapshot -> `FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE`
- compensatable external effect -> `COMPENSATING_ACTION_PLUS_FORWARD_REVERT`

Every plan preserves history, forbids destructive history rewrite, requires exact-head reverification, requires independent review for MEDIUM/LARGE/CRITICAL changes, and requires user approval for critical/compensatable recovery where derived. `validate_governed_revert_plan()` revalidates checkpoint + implementation ancestry, re-derives assessment and plan semantics, and rejects recomputed-digest laundering.

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

Current remediation replaces invocation-local trust with the durable zero-tree-change Git marker commit protocol, live remote repository/main re-derivation, policy/schema blob binding, CI/deterministic/review evidence envelope, UTC provenance, and strict marker->implementation ancestry. No tag/ref registry or D1 verification authority is introduced.

## Adversarial regression matrix

The R159 suite covers at least:

- small/medium/large/critical and GPT/user-trigger marker matrix;
- stateful snapshot/migration/Git-only and mixed surfaces;
- policy version-switch and external compensation/irreversible surfaces;
- digest-only marker spoofing;
- serialized/deep-copied cross-process checkpoint revalidation;
- JSON mutation + recomputed-digest forgery;
- repository-label substitution and remote-identity substitution;
- live remote-main drift at capture;
- dirty and untracked worktree rejection;
- required policy/schema paths and missing-path failure;
- CI FAIL and deterministic INCONCLUSIVE rejection;
- PASS state without evidence refs rejection;
- exact marker parent/tree/payload validation;
- marker strict ancestry to implementation head;
- unrelated implementation head and marker-as-head rejection;
- `git replace` laundering resistance;
- assessment marker-bit/classification laundering;
- revert strategy/review/history/authority laundering;
- CLI checkpoint serialization and later reuse;
- no mutable tag/ref seam;
- all authority booleans false.

## CI gate

Python 3.11 and 3.13 must both pass:

- exact PR head + current base provenance;
- compile module/tests;
- all three schemas parse;
- R159 adversarial suite;
- complete retained Control Tower suite;
- exact seven-file additive-only diff;
- durable-marker/canonical-binding/all-false-authority static invariants;
- no mutable tag/ref or destructive-history seam;
- `git diff --check` and unfinished-marker rejection.

## Stop gate

Engineering stops after a final exact head has green CI, an engineering handoff, and a new exact-head `REVIEW_REQUEST/v1` in Issue #453. No self-review, Ready transition, or merge before a matching independent exact-head ACCEPT.

## Next slice

Only after governed R159 merge and fresh post-merge priority reconciliation may another implementation slice start. #478 D1 remains the intended Continuous Engineering Verification successor unless a higher-priority canonical issue (currently #308 P0 is a candidate) wins the fresh priority scan.
