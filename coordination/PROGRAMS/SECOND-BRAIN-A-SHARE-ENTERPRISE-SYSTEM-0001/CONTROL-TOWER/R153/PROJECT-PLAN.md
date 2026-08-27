# R153 — Durable Signal Opportunity Materializer

Issue: #465

Base main at engineering start: `450dc7ba20dcc8425d970f4f0657e28a833e4cee`

## Why this exists

Canonical R151 can rank `DigestedSignalOpportunity/v1` values and R152 can safely apply a valid R151 authorization, but the pre-R151 opportunity used to be planner supplied. R153 closes that seam without becoming a second Signal, owner, priority, task, route, claim, worker, or semantic authority.

The first production dogfood is durable Signal `signal:r147-4a6244d5b465ca2ce8e9cdd26d870f60`. AI Film Issue #16 / PR #17 already owns overlapping production validation. Correct autonomous behavior is reuse/abstain while that exact owner work is current.

## Canonical flow

`canonical S0C DurableSignalLedger`
→ exact effective Signal + semantic origin
→ read-only S0C canonical replay/content-integrity proof
→ retained R145 owner authority/freshness
→ governed owner-domain reconciliation evidence through retained R137 GET transport
→ fresh referenced Issue/PR/head/review-lineage verification when REUSE is claimed
→ planner `TaskReleaseProposal/v1` semantic candidate
→ retained R151 standing exclusions
→ retained R150/R149 preflight
→ deterministic R151-compatible `DigestedSignalOpportunity/v1`

R153 only returns evidence decisions. It creates no Signal, Issue, Task, Route, Work Claim or worker slot and grants no execution, domain-write, W3 or merge authority.

## Review remediation incorporated

Independent review `5039041547` on prior head `e70bbf6bf7cd17c43a21d9dbb382e0c12b02bf7b` identified three P1s and one P2. The remediation is bounded inside the same R153 implementation surface.

### Trusted owner reconciliation provenance

Public GitHub text is evidence, not authority merely because R137 fetched it.

An authority-bearing reconciliation record now requires GitHub-computed owner provenance:
- repository owner, or
- `OWNER` / `MEMBER` / `COLLABORATOR` association through the already-used `chatgpt-codex-connector` app.

Untrusted matching text fails closed. A later untrusted comment cannot override a trusted record. Generic records must bind `reconciliation_issue` to the exact container Issue. The legacy AI Film handoff must bind its `existing_issue` to that same container.

No new actor registry is introduced. The trust evidence is GitHub metadata on the existing R137 transport plus the R145 owner repository binding.

### Fresh current-work verification

`REUSE_EXISTING_WORK` is not accepted from stale handoff text. R153 fresh-reads:
- referenced owner Issue and requires it open;
- referenced owner PR and requires it open/unmerged;
- exact PR head and requires equality with `existing_exact_head`;
- PR base/main binding and owner main;
- owner review queue lineage when the reconciliation record declares a review queue/state.

Closed work, moved head, base drift, stale review ticket or changed review state becomes `NEEDS_REVALIDATION`.

### S0C projection integrity

R153 does not rebuild or mutate S0C during materialization. Missing projection fails closed.

For an existing projection it uses the retained canonical S0C reducer itself as a read-only replay and proves:
- stable input revision across read/replay;
- watermark/history equality;
- reducer-version equality;
- stored projection core equals canonical replay;
- stored checksum equals the canonical replay checksum.

R153 does not copy reducer semantics and Git transport never becomes Signal truth.

### Caller ranking fields are non-authoritative hints

The legacy draft shape still accepts:
- `priority_class`
- `user_value_score`
- `materiality_score`
- `dependency_readiness_score`
- `age_cycles`
- `estimated_cost_score`

They are compatibility hints only and are not copied into an authority-bearing opportunity. R153 emits one fixed neutral ranking vector:

```yaml
priority_class: P3_BOUNDED_IMPROVEMENT
user_value_score: 50
materiality_score: 50
dependency_readiness_score: 100
age_cycles: 0
estimated_cost_score: 50
```

Therefore score inflation cannot reorder autonomous R153 opportunities. R151 remains the only retained selection/release authority. A future governed ranking policy may replace the neutral vector, but R153 does not invent one.

## Owner reconciliation forms

### `DURABLE_SIGNAL_OWNER_DOMAIN_REUSE_HANDOFF/v1`

Compatibility form for the first AI Film production dogfood. It requires exact Signal ID, owner project/domain binding, current owner main, exact existing Issue/PR/head and source proof. If review queue/state is declared, current queue lineage must match it.

### `SIGNAL_OWNER_RECONCILIATION/v1`

Generic exact-Signal form. It requires:
- exact `signal_id`;
- exact R145 owner domain;
- exact current owner main;
- exact `reconciliation_issue` binding;
- disposition in `REUSE_EXISTING_WORK`, `ALREADY_SATISFIED`, `GAP_PROVEN`, `NEEDS_REVALIDATION`.

`GAP_PROVEN` requires `dependency_ready: true`, no conflicting work refs and an open reconciliation Issue. `ALREADY_SATISFIED` requires the reconciliation Issue closed. REUSE additionally requires fresh referenced work verification.

No exact trusted record means `NEEDS_REVALIDATION`; semantic similarity never guesses NEW or DUPLICATE.

## Fail-closed invariants

- exact canonical `DurableSignalLedger` instance required;
- transport/replay artifacts alone cannot substitute for S0C truth;
- missing/tampered/stale S0C projection cannot materialize;
- non-`NOT_STARTED`, conflicted, superseded, rejected, closed or epistemically unknown Signals cannot materialize;
- unresolved R145 owner authority cannot materialize;
- caller cannot redefine owner main/domain or Signal desired effect;
- arbitrary/untrusted owner comments cannot mint reconciliation truth;
- stale referenced owner work cannot yield REUSE;
- cross-domain auto-materialization is forbidden in R153;
- R151 production/secrets/permissions/trading/destructive exclusions remain inherited;
- R150 must return a releaseable exact-current-state disposition.

## Scope

Only these five files belong to the R153 PR:

1. `coordination/CONTROL-TOWER/signal_opportunity_materializer.py`
2. `coordination/CONTROL-TOWER/tests/test_signal_opportunity_materializer.py`
3. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R153/PROJECT-PLAN.md`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R153/SIGNAL-OPPORTUNITY-MATERIALIZATION.schema.json`
5. `.github/workflows/program-control-tower-r153-signal-opportunity-materializer.yml`

No mutation to live `ACTIVE-*`, `ROUTES/**`, Work Claims, worker authority, S0C implementation, R145/R149/R150/R151/R152 semantics, W3, owner-domain production code, trading, production deploy, credentials or permissions.

## Stop gate

- exact-head Python 3.11 + 3.13 R153 adversarial suite;
- retained R152/R151/R150/R149 regressions;
- full Control Tower suite;
- Foundation / Phase 3 where triggered;
- exact five-file scope and authority-boundary checks;
- new exact-head `REVIEW_REQUEST/v1` through #453;
- independent other-window review;
- no self-review and no merge before governed ACCEPT.

Completion signal:

`R153_REMEDIATED_READY_FOR_INDEPENDENT_RE_REVIEW`
