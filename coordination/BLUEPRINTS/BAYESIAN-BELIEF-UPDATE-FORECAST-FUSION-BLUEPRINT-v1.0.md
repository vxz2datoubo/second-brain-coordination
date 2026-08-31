# DS-02 Bayesian Belief Update & Forecast Fusion Blueprint v1.0

## Status

`RESEARCH_ONLY / NO_TRADE / CONTRACT_VERIFIER_AND_EXECUTABLE_EVAL_ONLY`

Source: Issue #522. Current remediation snapshot: `SECOND-BRAIN-DS02-ISSUE522-REMEDIATION-003` (`issuecomment-5474354229`). Canonical base: `1a514fe839b1c47a14d7fad4a96e8c9fd2365338`.

This is a BELIEVE-layer **proposal contract plus deterministic verifier**. It does not authorize runtime, backtest, canonical belief production, capital allocation, brokerage, orders, account-fund access, or live trading.

## First principles

A probabilistic proposal is interpretable only when bound to a target, horizon, exchange/board/security identity, knowledge cutoff, point-in-time evidence, ex-ante prior provenance, likelihood assumptions, dependence provenance, rule/clause state, shrinkage state and numeric-integrity policy.

For compatible binary evidence the analytic reference is:

`logit(posterior) = logit(prior) + Σ log(BF_i)`

This algebra is not permission to multiply correlated evidence. Phase 1 has no canonical dependence authority and caller labels never prove independence.

## Phase-1 trust model

`BeliefPacket/v1` is `UNVALIDATED_PROPOSAL`, not canonical belief truth. It requires:

- `validation.authority_state = UNAVAILABLE_PHASE1`;
- `validation.packet_status = UNVALIDATED_PROPOSAL`;
- `validation.validated_computation_receipt = null`;
- `validation.canonical_belief_authorized = false`;
- all market/event/regime/epistemic/decision/risk/position/order/trade authority flags false.

Passing `belief_contract.py` means only that the proposal satisfies this bounded contract.

## Authority topology

```text
W2 market/replay ─┐
W5 event/evidence ├──> DS-02 proposal verifier ──> advisory-only downstream input
W13 participants ─┤
DS-11 regime ─────┤
#457 epistemic ───┘

DS-02 ─X─> BROKER / LIVE_ORDER / ACCOUNT_FUNDS
DS-02 ─X─> canonical upstream truth writeback
```

## Forecast, time and market-rule identity

A probability without target and horizon is invalid. Current single-security A-share identity includes target/version, six-digit symbol, exchange, compatible board, `A_SHARE_STOCK`, horizon, `as_of_time`, `knowledge_cutoff`, rule version, clause-state version and explicit used clause IDs.

Temporal ordering is mechanical:

`knowledge_cutoff <= as_of_time <= decision_time`

Evidence admission is stricter than a decision-time-only check:

`available_at <= knowledge_cutoff`

and therefore also `available_at <= decision_time`. Evidence that was known only after the declared knowledge cutoff cannot enter a historical proposal merely because the simulated decision happened later.

Schema constraints bind SSE/SZSE/BSE boards to the correct 2026 rule/state family. The verifier additionally checks the compatibility registry and produces `REVALIDATION_REQUIRED` when a referenced BSE clause remains deferred.

## Ex-ante prior discipline

Every prior carries ID/version, family/parameters, structured training-window start/end, regime scope, evidence digest and effective-from timestamp.

The verifier requires:

- training-window start <= end;
- training-window end <= knowledge cutoff;
- prior effective-from <= knowledge cutoff.

A prior tuned using information available only after the cutoff is `PRIOR_NOT_EX_ANTE` and rejected. This is provenance discipline, not a claim that any particular prior family is economically optimal.

## Evidence dependence provenance

Each evidence row carries source instance/family, neutral caller candidate-group label, ancestry refs, shared feed/feature/training/model lineage, revision provenance and `independence_status = UNVERIFIED`.

Rules:

1. copied/reposted/shared-lineage evidence triggers dependence collapse/revalidation;
2. relabeling a caller independence group cannot hide ancestry;
3. multiple apparently separate sources remain `INDEPENDENCE_UNVERIFIED` without separately governed dependence authority;
4. raw LLM confidence cannot mint likelihood authority.

## Posterior arithmetic and caller-shaped values

The verifier independently recomputes the analytic posterior from prior probability and cumulative log Bayes factor. A range-valid but inconsistent posterior is rejected. Even a mathematically consistent proposal remains non-canonical because Phase 1 has no validated computation receipt.

## Hierarchical shrinkage safety

The packet carries effective sample size, hierarchy level and hierarchical-prior identity/version. Numeric Integrity Registry defines a conservative **contract safety gate**, currently not an alpha parameter or empirical optimality claim:

- effective sample size below 20;
- posterior >= 0.90 or <= 0.10;
- result: `SMALL_SAMPLE_SHRINKAGE_REQUIRED / REVALIDATION_REQUIRED`.

This closes the binding “4 successes in 5 observations must not manufacture extreme certainty” requirement. Later empirical calibration of shrinkage strength is separately governed.

## Canonical content digest

`numeric_integrity.canonical_digest` is lower-case SHA-256 over sorted-key compact UTF-8 JSON of the complete packet with the digest field itself excluded. It protects packet-content integrity, not producer authenticity or canonical authority. Any content mutation without digest recomputation is `CANONICAL_DIGEST_MISMATCH` and rejected.

## Retraction and predictive contract

Belief/update history is append-only. Retraction appends invalidation/tombstone evidence and recomputes from surviving admitted evidence; deleting history is forbidden.

Predictive output preserves expected value, p05/p25/p50/p75/p95, positive probability, configured-loss probability and a distribution reference. High posterior never grants action authority.

## Executable adversarial contract

`DS02-ADVERSARIAL-EVALS-v1.0.yaml` now contains **29 executable attacks**. CI dynamically emits one unittest ID per case and executes schema/verifier/analytic behavior; label-presence-only checks are explicitly not evidence.

Coverage includes:

- repost/shared lineage and caller relabeling;
- posterior forgery and probability-range attacks;
- decision-time PIT, knowledge-cutoff leakage and revised data;
- ex-post prior effective date and training-window leakage;
- tiny-sample extreme posterior/shrinkage gate;
- exchange/rule substitution and BSE deferred clauses;
- target/feature drift;
- content-digest tampering;
- UNKNOWN/ABSTAIN, retraction and append-only history;
- market/event/regime/order authority escalation and no-action boundary.

## Validation path

1. Closed schema + deterministic cross-field verifier.
2. Analytic oracles.
3. 29 executable adversarial/metamorphic cases.
4. PIT + knowledge-cutoff + revision integrity.
5. Ex-ante prior + shrinkage safety.
6. Simulation-based calibration.
7. Inference diagnostics.
8. Prior/posterior predictive checks.
9. Proper-score calibration.
10. Purged/embargoed A-share OOS increment versus simpler baselines.
11. DS-10 research-overfitting audit.
12. Shadow-only validation.

Mathematical correctness and contract validity are necessary but never sufficient evidence of A-share alpha.

## Stop condition

This slice stops before runtime. Phase 2 requires independent acceptance of this exact head, canonical merge, fresh main, a new pre-write Phase-2 snapshot and valid execution capacity. Phase 3 A-share OOS remains separately governed. Live trading remains prohibited.
