# R156 — Trusted P3/P4 Epistemic Priority Classification Evidence

Issue: #471

Base canonical main: `ecdb45fe093c910cf21351d2e2c14139e4b8483a`

## Why this exists

R154 intentionally emitted `P3_BOUNDED_IMPROVEMENT` for every eligible idle Signal because no canonical research-priority classifier existed. R151 already has distinct P3/P4 scheduling semantics, so leaving all opportunities at P3 makes the P4 lane inert.

R156 activates only the narrow research distinction that is already machine-verifiable from canonical S0C truth. It does not guess task type from prose and it does not create a second scheduler.

## Canonical composition

`S0C canonical replay`
→ retained R153 owner reconciliation / GAP / R150-R149
→ retained R154 ranking baseline
→ retained R155 explicit user-value upgrade
→ `TrustedIdlePriorityClassificationEvidence/v1`
→ updated opportunity priority only
→ retained R151 selector/release authority.

R156 consumes the `epistemic_state` that R153 copied from replay-proven S0C into the validated opportunity. It requires the exact R155 opportunity digest plus S0C and R155 evidence refs before changing the priority feature.

## V1 policy

- `USER_EXPLICIT` → `P3_BOUNDED_IMPROVEMENT`
- `CONFIRMED_FACT` → `P3_BOUNDED_IMPROVEMENT`
- `HIGH_CONFIDENCE_INFERENCE` → `P3_BOUNDED_IMPROVEMENT`
- `CANDIDATE_HYPOTHESIS` → `P4_RESEARCH`

`UNKNOWN` and `NEEDS_REVALIDATION` are not P4. They remain upstream ineligible states under retained R153/R151 semantics.

V1 deliberately does not classify from:
- Signal kind;
- desired-effect/problem/success prose;
- urgency adjectives;
- sentiment;
- embeddings or fuzzy similarity;
- behavioral/private context;
- caller-supplied priority;
- model judgment.

This means R156/v1 is a conservative epistemic research-demotion rule, not a universal natural-language research classifier.

## Trust and anti-injection boundary

R154 remains the expected starting priority and must still be P3. R155 must have already produced an exact `r155://ranking-upgrade/...` evidence ref. R156 binds its evidence to that exact post-R155 opportunity digest.

A caller cannot pass `priority_class`, `signal_kind`, free text, or a classifier/provider object to `derive_trusted_priority_evidence()`. The production materializer computes the R156 evidence internally.

R156 can therefore demote a replay-proven `CANDIDATE_HYPOTHESIS` from P3 to P4, but cannot use caller input to promote an opportunity or turn `UNKNOWN` into a releaseable research task.

## Authority boundary

R156 evidence does not:
- create or mutate Signal truth;
- select an opportunity;
- release a Task;
- create Issue/Route/Work Claim/worker slot;
- grant execution/domain/W3/merge authority;
- mutate R151 priority ordering.

R151 remains the sole selector/release authority and still orders P3 ahead of P4 after P0/P1/P2 reconciliation.

## Successor workflow compatibility

Changing `signal_opportunity_materializer_current.py` legitimately triggers the retained R155 workflow. The R155 workflow must therefore preserve its historical exact six-additive-file mode while recognizing one exact R156 successor mode. It must not be weakened into a generic allowlist.

R156 successor mode is exactly seven changed paths relative to this task's canonical base:

1. `coordination/CONTROL-TOWER/signal_priority_classification.py`
2. `coordination/CONTROL-TOWER/signal_opportunity_materializer_current.py`
3. `coordination/CONTROL-TOWER/tests/test_signal_priority_classification.py`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R156/PROJECT-PLAN.md`
5. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R156/TRUSTED-IDLE-PRIORITY-CLASSIFICATION.schema.json`
6. `.github/workflows/program-control-tower-r156-trusted-priority.yml`
7. `.github/workflows/program-control-tower-r155-explicit-user-value.yml`

No R151/R150/R149/R152 code, S0C implementation, live routes/claims/worker slots, W3, trading, secrets, permissions or deployment surfaces are changed.

## Stop gate

- exact-head Python 3.11 + 3.13;
- R156 adversarial tests;
- retained R155/R154/R153/R152/R151/R150/R149;
- full Control Tower suite;
- retained R155 successor-compatibility workflow;
- exact seven-file successor scope;
- trust/authority boundary checks;
- Draft PR and independent exact-head review through #453;
- no self-review and no merge before governed ACCEPT.

Completion signal:

`R156_TRUSTED_P3_P4_EPISTEMIC_PRIORITY_READY_FOR_INDEPENDENT_REVIEW`
