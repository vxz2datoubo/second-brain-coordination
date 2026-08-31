# DS-02 Bayesian Belief Update & Forecast Fusion Blueprint v1.0

## Status

`RESEARCH_ONLY / NO_TRADE / CONTRACT_VERIFIER_AND_EXECUTABLE_EVAL_ONLY`

Source: Issue #522. Current remediation snapshot: `SECOND-BRAIN-DS02-ISSUE522-REMEDIATION-002` (`issuecomment-5473796264`). Canonical base observed at remediation: `1a514fe839b1c47a14d7fad4a96e8c9fd2365338`.

This is a BELIEVE-layer **proposal contract plus deterministic verifier**. It does not authorize runtime, backtest, canonical belief production, capital allocation, brokerage, order creation, or live trading.

## First principles

The unit of truth is not model confidence. A probabilistic proposal is interpretable only when bound to a target, horizon, exchange/board/security identity, knowledge cutoff, point-in-time evidence, prior version, likelihood assumptions, dependence provenance, rule/clause activation state and numerical policy.

For compatible binary evidence, the analytic reference is:

`logit(posterior) = logit(prior) + Σ log(BF_i)`

This algebra is not permission to sum correlated evidence. Evidence multiplication requires dependence authority that Phase 1 explicitly does not possess. Caller-selected independence labels are never proof of conditional independence.

## Phase-1 trust model

`BeliefPacket/v1` is currently `UNVALIDATED_PROPOSAL`, not canonical belief truth.

The packet must contain:

- `validation.authority_state = UNAVAILABLE_PHASE1`;
- `validation.packet_status = UNVALIDATED_PROPOSAL`;
- `validation.validated_computation_receipt = null`;
- `validation.canonical_belief_authorized = false`;
- all market/event/regime/epistemic/decision/risk/position/order/trade authority flags false.

`belief_contract.py` performs deterministic structural and cross-field checks. Passing it means only that a proposal satisfies the Phase-1 contract. It does **not** mint a trusted posterior.

## Authority topology

```text
W2 market/replay ─┐
W5 event/evidence ├──> DS-02 proposal verifier ──> advisory-only downstream input
W13 participants ─┤
DS-11 regime ─────┤
#457 epistemic ───┘

DS-02 ─X─> BROKER
DS-02 ─X─> LIVE_ORDER
DS-02 ─X─> ACCOUNT_FUNDS
DS-02 ─X─> canonical upstream truth writeback
```

DS-02 cannot rewrite upstream canonical evidence, mint source independence, mint a regime, choose an action, size capital, or execute.

## Forecast and market-rule identity

A probability without target and horizon is invalid. For the current single-security A-share contract, minimum identity includes:

- `target_id` and `target_definition_version`;
- six-digit `symbol_or_universe`;
- `exchange` (`SSE`, `SZSE`, `BSE`);
- `board` (`MAIN`, `STAR`, `CHINEXT`, `BSE` as compatible with exchange);
- `security_type = A_SHARE_STOCK`;
- `forecast_horizon`;
- `as_of_time` and `knowledge_cutoff`;
- `market_rule_version`;
- `market_rule_clause_state_version`;
- explicit `rule_clause_ids` used by the proposal.

Schema constraints bind exchange/board to the correct 2026 rule/state family. The deterministic verifier additionally checks the machine rule-compatibility registry and blocks deferred BSE clause use with `REVALIDATION_REQUIRED`.

## Prior discipline

Every prior records ID/version, family/parameters, training window, evidence digest and effective-from time. A prior tuned after seeing the target outcome cannot be relabeled ex-ante. Future runtime authority must bind prior provenance more strongly than caller text.

## Evidence admission and dependence provenance

Each evidence item carries point-in-time and revision provenance plus a dependence envelope:

- `source_instance_id` and `source_family_id`;
- neutral `candidate_independence_group_id`;
- `ancestry_refs`;
- shared feed group IDs;
- shared feature group IDs;
- shared training-data group IDs;
- shared model-lineage IDs;
- `dependence_authority_state = UNAVAILABLE_PHASE1`;
- `independence_status = UNVERIFIED`.

Admission/verifier rules include:

1. `available_at <= decision_time`;
2. revised data must preserve superseded snapshot lineage;
3. repost ancestry and shared source/feed/feature/training/model lineage trigger dependence collapse/revalidation;
4. changing a caller independence label cannot hide lineage overlap;
5. multiple apparently separate admitted sources remain unverified when no canonical dependence authority exists;
6. raw LLM confidence is not probability or likelihood authority.

## Update arithmetic and caller-shaped posterior defense

The contract carries proposal values for prior probability, cumulative log-Bayes factor and posterior probability. The deterministic verifier recomputes the analytic posterior and rejects a range-valid but mathematically inconsistent value.

Example attack intentionally rejected:

`prior = 0.1`, `cumulative_log_bayes_factor = 0`, `posterior = 0.999999`.

Even a mathematically consistent proposal remains non-canonical in Phase 1 because no validated computation receipt exists.

## Reference update families

Phase 1 retains three analytic sanity families:

- Beta-Binomial;
- Normal-Normal with known observation variance;
- log-odds/log-Bayes-factor composition.

More complex hierarchical logistic, MCMC, state-space and particle paths remain future candidates and must satisfy separate governance and diagnostics.

### Retraction

The belief/update history is append-only by contract. Retraction must append invalidation/tombstone evidence and recompute from surviving admitted evidence. Under additive log-Bayes-factor assumptions, removing a factor must reproduce fresh recomputation without that factor. Deleting historical updates to hide a retraction is an adversarial failure.

## Posterior predictive, not scalar-only probability

Predictive output preserves expected value, p05/p25/p50/p75/p95, probability positive, probability below configured loss threshold, distribution reference and UNKNOWN mass. A high posterior never grants action authority, especially when predictive downside remains severe.

## Diagnostics and abstention

Future sampling paths may surface R-hat, ESS, divergences, prior/posterior predictive checks, calibration status and PSIS-LOO/Pareto-k. `UNKNOWN`, `ABSTAIN`, and `REVALIDATION_REQUIRED` are first-class states. Calibration failure cannot be silently upgraded to confidence.

## Executable adversarial contract

`DS02-ADVERSARIAL-EVALS-v1.0.yaml` contains exactly 24 mandatory attack fixtures. CI dynamically emits one unittest test ID per case and executes the actual schema/verifier or analytic invariant. Merely checking that an expected label exists is explicitly forbidden as evidence.

Mandatory attack families include copied/reposted evidence, shared feed/features/training lineage, caller posterior forgery, point-in-time/revision leakage, exchange/rule substitution, BSE deferred clauses, authority escalation, unknown/abstain, retraction recomputation, append-only violation and direct execution edges.

## A-share structural breaks

SSE, SZSE and BSE 2026 rules form real structural-break boundaries. Historical likelihoods are not silently pooled across incompatible rule eras. BSE rule publication/effective version and clause activation state are separate identities because specified provisions may remain deferred.

## Validation path

1. Closed schema + deterministic cross-field verifier.
2. Analytic oracles.
3. Executable adversarial/metamorphic properties.
4. Point-in-time/revision fixtures.
5. Simulation-based calibration.
6. Inference diagnostics.
7. Prior/posterior predictive checks.
8. Proper-score calibration.
9. Purged/embargoed A-share OOS increment versus simpler baselines.
10. DS-10 research-overfitting audit.
11. Shadow-only validation.

Mathematical correctness and contract validity are necessary but never sufficient evidence of A-share alpha.

## Stop condition

This slice stops before runtime. Phase 2 requires independent acceptance of the remediated exact head, canonical merge, fresh main, a new pre-write Phase-2 snapshot, and a valid execution slot. Phase 3 A-share OOS remains separately governed. Live trading remains prohibited.
