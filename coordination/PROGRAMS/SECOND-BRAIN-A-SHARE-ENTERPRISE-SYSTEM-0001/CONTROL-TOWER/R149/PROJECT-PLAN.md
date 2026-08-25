# R149 Task Release Impact & Composition Gate — Slice 1 Plan

Issue: #451
Base main: `71c70f6bc3683eff4c19020a7d4cc998517c6ba1`
Branch: `gpt/r149-task-release-impact-composition-gate`
Mode: `ARCHITECTURE_CONTRACTS_EVALS_ONLY`

## 1. Reuse decision

R149 is **not** a new Control Tower.

Fresh audit found that existing `coordination/CONTROL-TOWER/control_tower.py` already owns:

- O0–O4 path/interface/domain/authority collision classification;
- Desired vs Observed foundation scanning;
- WIP/resource and stale-view checks.

Existing `lane_claims.py` and R144 worker-slot governance already own:

- Task/route/claim/worker-slot binding;
- current implementation occupancy;
- reviewer/executor separation and execution fencing.

Therefore the R149 implementation decision is:

`EXTEND existing Program Control Tower with evidence-only pre-release impact evaluation`.

It must not duplicate collision, lease, route, claim, Signal, W3, domain-authority or execution logic.

## 2. Reused upstream semantics

### #310 Program Control Tower

Directly reuse existing collision vocabulary and release-authority boundary. A R149 receipt is only evidence consumed by the existing release process.

### #421 Harness V2

Generalize only the reusable architecture principles:

- capability discovery before vendor/module branching;
- existing-system inventory before new implementation;
- facade/adapter instead of duplicate core where possible;
- one canonical writer per object;
- stable contract plus optional/namespaced capability extensions;
- removable optional capability/provider/plugin;
- no silent canonical replacement.

No Harness runtime is implemented by R149.

### #30 Engineering Learning

R149 records the **pre-task structural impact decision** only. Outcome calibration and long-term engineering-learning history remain owned by #30 surfaces. R149 does not create a second learning store.

### #312 Method Discovery / Effective Challenge

R149 reuses structural-fit, prerequisite, conflict, evidence-completeness, materiality and abstention concepts only for task-release architecture reasoning. It does not create a second method router.

### R145 domain authority

Owner-domain and writeback-owner compatibility are mandatory evidence. Cross-domain visibility never grants write ownership. R149 itself performs no domain write.

## 3. Minimal implementation

New module:

`coordination/CONTROL-TOWER/task_release_impact.py`

It imports and reuses `control_tower.classify_collision` rather than reimplementing path/interface/authority overlap.

Public function:

`evaluate_release_candidate(candidate) -> TaskReleaseImpactReceipt/v1`

The function is deterministic and side-effect free.

It does **not**:

- create or modify Task;
- create Route;
- create Work Claim;
- mint an authorization witness;
- grant execution authority;
- grant domain/W3/Signal write;
- merge a PR.

## 4. Decision vocabulary

Capability inventory decisions:

- `REUSE_AS_IS`
- `EXTEND`
- `WRAP_ADAPT`
- `MODIFY`
- `REPLACE`
- `MERGE`
- `DEPRECATE`
- `NEW_MODULE_JUSTIFIED`
- `REFERENCE_ONLY`
- `UNKNOWN`

`NEW_MODULE_JUSTIFIED` requires explicit evidence that existing capabilities are insufficient and a non-empty justification. Caller-provided final disposition is forbidden.

## 5. Relationship / impact vocabulary

Release-planning relations:

- `REQUIRES`
- `REQUIRED_BY`
- `CONFLICTS_WITH`
- `OVERLAPS`
- `REUSES`
- `EXTENDS`
- `SUPERSEDES`
- `MUST_CHANGE_WITH`
- `PROVIDES_CAPABILITY`
- `CONSUMES_CAPABILITY`
- `AUTHORITY_OWNER`
- `WRITEBACK_OWNER`
- `CONTRACT_COMPATIBILITY`
- `MIGRATION_DEPENDENCY`

These are receipt evidence, not a second knowledge/dependency truth.

## 6. Reverse-consumer contract

Each known consumer is classified as one of:

- `NO_CONSUMER_CHANGE`
- `CONSUMER_REVALIDATION_ONLY`
- `SYNCHRONIZED_CHANGE_REQUIRED`
- `MIGRATION_REQUIRED`
- `UNKNOWN_CONSUMERS_BLOCK_RELEASE`

For material/high shared-contract work, incomplete consumer inventory fails closed to `NEEDS_REVALIDATION`.

A `MUST_CHANGE_WITH` target absent from the synchronized change set is an `ARCHITECTURE_CONFLICT` rather than an artificially narrow Task.

## 7. Composition / removability rule

Question:

`CAN_THIS_BE_COMPOSED_INSTEAD_OF_EMBEDDED?`

If capability is optional and composable, release should prefer `WRAP_ADAPT` / `RELEASE_AS_ADAPTER_OR_PLUGIN` only when:

- removal preserves unrelated core operation;
- missing capability yields `UNSUPPORTED` or `ABSTAIN`;
- the optional implementation does not become a second canonical writer/truth.

Foundational invariants are not forced into plugin form. `core_invariant=true` with explicit justification is valid.

## 8. Final dispositions

- `RELEASE_BOUNDED_TASK`
- `RELEASE_AS_EXTENSION`
- `RELEASE_AS_ADAPTER_OR_PLUGIN`
- `MERGE_WITH_EXISTING_TASK`
- `MODIFY_EXISTING_TASK`
- `DEFER_DEPENDENCY`
- `NEEDS_REVALIDATION`
- `ARCHITECTURE_CONFLICT`
- `NO_TASK_ALREADY_SATISFIED`
- `ABSTAIN`

Disposition precedence is fail-closed: second writer/truth, authority incompatibility and incoherent synchronized-change surfaces block before any positive release result.

## 9. Receipt authority boundary

Every `TaskReleaseImpactReceipt/v1` mechanically records:

```yaml
authority_boundary:
  evidence_only: true
  creates_task: false
  creates_route: false
  creates_work_claim: false
  grants_execution_authority: false
  grants_domain_write: false
  grants_merge_authority: false
```

This receipt cannot substitute for current Control Tower route/claim/release/witness authorization.

Slice 1 validates caller-supplied candidate evidence as a contract fixture; it does not authenticate caller declarations as canonical observations. Any later production integration must source current active-work, owner-domain/writeback, and canonical-head observations from the existing trusted Control Tower/R145 surfaces before a receipt can participate in release. This slice intentionally stops before that integration seam.

## 10. Slice 1 acceptance

The regression suite covers all 14 Issue #451 stories plus:

- caller cannot inject final disposition;
- `NEW_MODULE_JUSTIFIED` requires positive insufficiency proof;
- UNKNOWN-only capability inventory abstains;
- integer truthy values cannot impersonate booleans in authority/composition/capability fields;
- receipt generation is deterministic and input-digest bound.

No production auto-release integration is included in Slice 1.

Stop after exact-head CI at:

`R149_TASK_RELEASE_IMPACT_COMPOSITION_GATE_READY_FOR_INDEPENDENT_REVIEW`
