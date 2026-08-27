# R154 — Trusted Signal Opportunity Ranking Evidence

Issue: #467

Base canonical main: `d63838f5ef4037b1f3040046bf8111ea509ec1a8`

## Why this exists

R153 closed the unsafe caller-ranking seam by replacing all caller scores with one fixed neutral vector. That was the correct fail-closed remediation, but it means multiple legitimate materialized Signals cannot be meaningfully ordered from trusted evidence.

R154 replaces only that temporary neutral vector. It does **not** replace R151. R151 remains the sole canonical idle-opportunity selection/release authority.

## Canonical flow

`S0C canonical replay-proven Signal origin`
→ `R153 trusted owner reconciliation / GAP_PROVEN`
→ `R149-shaped TaskReleaseProposal change surface`
→ `R154 TrustedSignalOpportunityRankingEvidence/v1`
→ rank vector embedded into the R153 opportunity
→ retained R150/R149 preflight
→ retained R151 selection/release.

R154 is a rebuildable evidence derivation layer. It creates no durable truth and grants no execution or mutation authority.

## V1 policy

R154 uses only mechanically grounded facts. Unknown value stays neutral instead of being guessed from prose.

### Priority

V1 always emits `P3_BOUNDED_IMPROVEMENT`. There is not yet a canonical research-priority classifier that can safely distinguish P3 from P4. Signal kind is preserved as provenance but is not treated as a research classifier.

### User value

V1 emits neutral `50`. No existing canonical user-value authority was found. User/model adjectives such as `urgent`, `critical`, or `high value` never alter this field.

### Signal materiality

Canonical S0C intake route materiality is distinct from R149 task materiality.

- `LOW -> 25`
- `MATERIAL -> 50`
- missing canonical route materiality -> neutral `50`
- `HIGH_RISK` -> not idle-rankable / fail closed
- any other present value -> fail closed

### Dependency readiness

Only R153's trusted owner reconciliation can supply readiness. `dependency_ready is True -> 100`; anything else fails closed.

### Starvation age

`age_cycles = min(20, ledger_watermark - origin_ledger_offset)` using the same replay-proven S0C history/projection already consumed by R153. Caller time or age claims are not inputs.

The cap matches the retained R151 rank-key starvation cap.

### Cost proxy

R154 does not claim wall-clock cost. It computes `CHANGE_SURFACE_BREADTH_PROXY_V1`, capped at 100:

- write path: 15 each
- read path: 5 each
- interface: 10 each
- read domain: 5 each
- write domain: 15 each
- authority claim: 20 each

Inputs are unique bounded R149 change-surface elements. Free text, token estimates and model cost guesses are ignored.

The accepted R153 fixture intentionally remains `P3 / 50 / 50 / 100 / 0 / 50`, so this successor does not break the prior accepted baseline merely by being integrated.

## Trust / authority boundary

R154 output carries:
- policy version;
- exact Signal ref;
- S0C proof/evidence refs;
- rank vector;
- per-feature provenance;
- cost-surface digest;
- deterministic ranking digest;
- all authority flags false.

It must never:
- select a winning opportunity;
- release a Task;
- create Issue/Route/Claim/worker slot;
- mutate S0C;
- grant execution/domain/W3/merge authority;
- use embeddings/fuzzy/NLP urgency classification as ranking authority.

## Integration rule

R153 remains the only canonical materializer from S0C + owner gap into a R151 opportunity. It must call R154 only with facts already proven by its canonical S0C replay and trusted owner reconciliation. Caller ranking fields remain compatibility hints and never enter R154.

R154 evidence is rebuildable; `r154://ranking/<digest>` in opportunity evidence binds the emitted numeric vector to the deterministic policy without creating another store.

## Scope

Six files only:

1. `coordination/CONTROL-TOWER/signal_opportunity_ranking.py`
2. `coordination/CONTROL-TOWER/tests/test_signal_opportunity_ranking.py`
3. `coordination/CONTROL-TOWER/signal_opportunity_materializer.py`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R154/PROJECT-PLAN.md`
5. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R154/TRUSTED-SIGNAL-OPPORTUNITY-RANKING.schema.json`
6. `.github/workflows/program-control-tower-r154-signal-opportunity-ranking.yml`

No changes to R151/R150/R149/R152 authority semantics, S0C implementation, R145, live routes/claims/worker slots, W3, trading, credentials, permissions or production deployment.

## Stop gate

- exact-head Python 3.11 + 3.13;
- R154 adversarial tests;
- retained R153/R152/R151/R150/R149;
- full Control Tower;
- Foundation / Phase 3 where triggered;
- exact six-file scope and authority checks;
- independent exact-head review through #453;
- no self-review and no merge before governed ACCEPT.

Completion signal:

`R154_TRUSTED_SIGNAL_OPPORTUNITY_RANKING_EVIDENCE_READY_FOR_INDEPENDENT_REVIEW`
