# R153 — Durable Signal Opportunity Materializer

Issue: #465

Base main at engineering start: `450dc7ba20dcc8425d970f4f0657e28a833e4cee`

## Why this exists

Canonical R151 accepts `DigestedSignalOpportunity/v1`, ranks P3/P4 opportunities after trusted P0/P1/P2 reconciliation, and may mint bounded authorization. Canonical R152 safely applies such an authorization. The remaining seam is that the opportunity itself is still planner/caller supplied.

The first production dogfood exposed this clearly. Durable Signal `signal:r147-4a6244d5b465ca2ce8e9cdd26d870f60` is real S0C truth, but owner-domain AI Film already has Issue #16 / PR #17 doing materially overlapping runtime validation. A correct autonomous system must reuse/abstain, not print a duplicate Issue.

R153 makes that pre-R151 materialization machine-verifiable.

## Truth and authority model

R153 does not read Git transport JSON as Signal truth. It accepts only an exact instance of the canonical S0C `DurableSignalLedger` class and verifies its current projection watermark/input revision before recovering the effective Signal and semantic-origin envelope.

The planner may supply a `SignalOpportunityDraft/v1`, but may not redefine:
- Signal existence/effective state;
- Signal primary domain;
- desired effect;
- problem to solve;
- success condition;
- owner repository/current main;
- owner reconciliation disposition;
- R149/R150 release disposition.

Owner authority is resolved through retained R145 `DomainAuthorityResolver` with exact-read, semantic-authority and live freshness proofs.

Owner-domain overlap/satisfaction is not inferred by fuzzy text similarity. R153 reuses the retained R137 GitHub GET transport through a narrow adapter and requires an exact durable-Signal backlink in a structured owner-domain reconciliation record.

Supported owner record forms:

1. `DURABLE_SIGNAL_OWNER_DOMAIN_REUSE_HANDOFF/v1`
   - existing production dogfood handoff format;
   - exact `source_signal_id` + current owner main + open owner work → `REUSE_EXISTING_OWNER_WORK`.

2. `SIGNAL_OWNER_RECONCILIATION/v1`
   - exact `signal_id`;
   - exact R145 owner domain + owner main;
   - disposition is one of `REUSE_EXISTING_WORK`, `ALREADY_SATISFIED`, `GAP_PROVEN`, `NEEDS_REVALIDATION`;
   - `GAP_PROVEN` additionally requires `dependency_ready: true` and no `work_refs`.

No matching exact-signal record means `NEEDS_REVALIDATION`, never guessed NEW.

## Materialization flow

`canonical S0C ledger`
→ effective eligible NOT_STARTED Signal
→ semantic-origin fields from S0C history
→ R145 owner authority/freshness
→ current owner reconciliation Issue + comments through retained R137 transport
→ REUSE / SATISFIED / REVALIDATE, or `GAP_PROVEN`
→ planner `TaskReleaseProposal/v1` exact-binding checks
→ R151 standing risk exclusion
→ retained R150 (and transitively R149/R145/current Control Tower) preflight
→ exact R151-compatible `DigestedSignalOpportunity/v1`

R153 only returns a deterministic evidence decision. It creates no Signal/Task/Issue/Route/Claim/slot and grants no execution/domain/W3/merge authority.

## Fail-closed notes

- A dict/object with ledger-like methods is not S0C. Exact canonical `DurableSignalLedger` class identity is required.
- Transport/replay evidence alone cannot materialize.
- stale coordinator checkout, S0C projection, owner main or R145 binding cannot materialize.
- DONE/CANCELLED/SUPERSEDED/CONFLICTED/BLOCKED/non-NOT_STARTED and UNKNOWN/NEEDS_REVALIDATION Signals do not materialize.
- cross-domain auto-materialization is forbidden in this slice.
- semantic similarity without exact owner reconciliation evidence remains `NEEDS_REVALIDATION`.
- standing production/secrets/permission/trading/destructive exclusions remain inherited from R151.
- R150 must return a releaseable final disposition before an opportunity is emitted.

## Scope

Only these five files are allowed in the R153 implementation PR:

1. `coordination/CONTROL-TOWER/signal_opportunity_materializer.py`
2. `coordination/CONTROL-TOWER/tests/test_signal_opportunity_materializer.py`
3. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R153/PROJECT-PLAN.md`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R153/SIGNAL-OPPORTUNITY-MATERIALIZATION.schema.json`
5. `.github/workflows/program-control-tower-r153-signal-opportunity-materializer.yml`

No mutation to `coordination/ACTIVE-*`, `coordination/ROUTES/**`, `LANE-WORK-CLAIMS.yaml`, S0C implementation, W3, Signal runtime, owner-domain code, trading, production, credential or permission surfaces.

## Stop gate

- exact-head Python 3.11 + 3.13 R153 adversarial suite;
- retained R152/R151/R150/R149;
- full Control Tower suite;
- Foundation / Phase 3 where triggered;
- five-file scope and authority-boundary checks;
- independent exact-head review through #453;
- no self-review and no merge before governed ACCEPT.

Completion signal:

`R153_DURABLE_SIGNAL_OPPORTUNITY_MATERIALIZER_READY_FOR_INDEPENDENT_REVIEW`
