# DS-02 Research Validation v1.0

## Evidence policy

Research evidence informs design constraints. It does **not** prove this system is calibrated, profitable, transferable to A-shares, suitable for live trading, or authorized to produce a canonical belief. In Phase 1, a schema-valid and verifier-valid packet is still an `UNVALIDATED_PROPOSAL`.

## Bayesian workflow evidence

### Prior and posterior predictive checks

Current PyMC guidance uses prior predictive checks to inspect prior implications before observing data and posterior predictive checks to compare posterior-generated data with observed structure.

**Engineering consequence:** sampler convergence is not model adequacy; predictive checks remain separate gates, and passing them does not grant trading or canonical-belief authority.

### MCMC diagnostics

Stan diagnostic guidance treats R-hat, effective sample size, divergences, tree-depth warnings and Monte Carlo error as computational-reliability evidence.

**Engineering consequence:** future sampling paths may abstain. A successful function return is not trustworthy inference by itself.

### PSIS-LOO

ArviZ documents PSIS-LOO as an estimate of expected pointwise predictive performance and exposes Pareto-k diagnostics.

**Engineering consequence:** model comparison may consume PSIS-LOO only with diagnostic provenance; it is never trading-action authority.

### Simulation-based calibration

SBC tests whether an inference implementation recovers calibrated posterior ranks in synthetic data drawn from the assumed generative model.

**Engineering consequence:** passing SBC tests inference under the simulator, not realism of the market model.

## Proper scoring and calibration

Proper scoring rules such as logarithmic score and Brier score provide principled evaluation of probabilistic forecasts. Evaluation must retain the complete forecast/outcome ledger, including failed trials and abstentions. Accuracy alone is insufficient.

## Dependence and forecast combination

Different labels do not imply independent information. Agents or models sharing an original source, feed, feature engineering, training data, model lineage or upstream evidence cannot be multiplied as independent measurements unless a separately governed dependence authority/model validates the relationship.

**Phase-1 machine consequence:**

- evidence explicitly carries `source_instance_id`, `ancestry_refs`, shared feed/feature/training/model lineage IDs;
- `candidate_independence_group_id` is neutral caller metadata, never authority;
- `dependence_authority_state = UNAVAILABLE_PHASE1`;
- `independence_status = UNVERIFIED`;
- copied/reposted/shared-lineage evidence triggers dependence collapse/revalidation;
- merely changing a display/group label cannot erase ancestry;
- multiple unresolved admitted sources remain `INDEPENDENCE_UNVERIFIED` rather than increasing certainty through naive multiplication.

This is intentionally conservative. The Phase-1 verifier detects known dependence and refuses to manufacture independence; it is not a general dependence-estimation runtime.

## Caller-shaped posterior and computation trust

A posterior value is not trusted merely because it lies in `[0,1]`. `belief_contract.py` independently recomputes the analytic log-odds update represented by `prior_probability + cumulative_log_bayes_factor` and rejects inconsistent caller-shaped values.

The stronger authority boundary is structural: `BeliefPacket/v1` cannot claim `VALID` or `VALIDATED` in Phase 1. It must carry:

- `packet_status = UNVALIDATED_PROPOSAL`;
- `authority_state = UNAVAILABLE_PHASE1`;
- `validated_computation_receipt = null`;
- `canonical_belief_authorized = false`.

Thus mathematical consistency is checked, but mathematical consistency alone never mints canonical belief truth.

## Regime/change evidence

Bayesian changepoint methods motivate explicit validity windows and structural-break handling, but DS-11 remains regime authority. DS-02 consumes regime/changepoint state and may return `REVALIDATION_REQUIRED`.

## 2026 A-share rule evidence

Official exchange publications provide a real structural-break case:

- SSE published its 2026 trading rules on 2026-04-24, effective 2026-07-06, superseding the 2023 revision and separately treating deferred provisions.
- SZSE published its 2026 trading rules on 2026-04-24, effective 2026-07-06, superseding the 2023 revision.
- BSE published revised rules on 2026-04-24 with general effect from 2026-07-06 while explicitly deferring specified clauses to later notice.

**Engineering consequence:** exchange, board and security type are explicit machine identity. `market_rule_version` and `market_rule_clause_state_version` are separately bound. Cross-exchange substitution is schema-invalid, while use of a rule clause marked deferred in the compatibility registry produces `REVALIDATION_REQUIRED`.

These rule sources do **not** prove predictive alpha, likelihood transfer, execution performance, or economic value.

## Point-in-time and revision provenance

Historical evaluation admits evidence only when `available_at <= decision_time`. Revised observations retain their own revision identity plus the hashes they supersede. A restatement cannot silently replace the point-in-time snapshot used by an earlier decision.

## Executable adversarial evidence

The 24-case adversarial pack is not a checklist. Each fixture is expanded into its own unittest test ID and executes an actual schema/verifier/analytic attack. The CI contract explicitly rejects label-presence-only testing as acceptance evidence.

Mandatory executable families include:

- repost ancestry and shared feed/feature/training/model lineage;
- uncalibrated confidence;
- mathematically inconsistent caller posterior;
- future evidence and revision laundering;
- target/feature version breaks;
- SSE/SZSE substitution and BSE deferred clause use;
- retraction recomputation and append-only deletion attack;
- UNKNOWN/ABSTAIN;
- no-action authority under high posterior;
- missing horizon/out-of-range probability/UI-authority attacks;
- authority escalation to market/event/regime/order surfaces.

## Validation ladder

| Gate | Question | Minimum evidence | Fail-closed state |
| --- | --- | --- | --- |
| V0 | Is the packet structurally/cross-field valid? | closed schema + deterministic verifier | REJECTED |
| V1 | Is closed-form math correct? | Beta-Binomial + Normal-Normal + log-BF oracles | INVALID_MODEL |
| V2 | Are mandatory adversarial/metamorphic properties preserved? | 24 executable fixtures + sequential/batch/retraction checks | REJECTED/REVALIDATION_REQUIRED |
| V3 | Is evidence point-in-time and revision-bound? | timestamp/revision fixtures | PIT_VIOLATION |
| V4 | Is inference calibrated under assumed simulator? | SBC | INFERENCE_INVALID |
| V5 | Is numerical inference reliable? | R-hat/ESS/divergence/MC-error gates | ABSTAIN |
| V6 | Can the model generate material observed structure? | prior/posterior predictive checks | MODEL_MISFIT |
| V7 | Are forecasts calibrated OOS? | Brier/log score/reliability | UNCALIBRATED |
| V8 | Does DS-02 add A-share economic information? | purged walk-forward + embargo + lockbox + costs | NO_INCREMENT |
| V9 | Is discovery robust to multiplicity? | DS-10 audit | OVERFIT_RISK |
| V10 | Does shadow behavior remain stable? | drift/abstention/reproducibility ledger | REVALIDATION_REQUIRED |

## Explicit non-claims

This contract does not claim:

1. Bayesian methods dominate frequentist methods in A-share forecasting.
2. A proposal posterior is automatically calibrated or canonical.
3. Passing the Phase-1 verifier proves independence.
4. Calibration implies positive expected value.
5. Positive expected value implies a position should be taken.
6. MCMC convergence proves model adequacy.
7. PSIS-LOO proves future market performance.
8. Official exchange rules imply an edge.
9. Mathematically valid composition proves conditional independence.
10. Larger models beat simple base-rate or regularized-logistic baselines.
11. Anything in this slice authorizes runtime, capital, orders, broker access, account-fund access, or trades.

## Future A-share comparison baseline

Phase 3 must compare at least:

- B0 empirical base rate;
- B1 simple regularized logistic/frequentist baseline;
- B2 pre-DS-02 rule/skill baseline;
- B3 existing ensemble;
- B4 existing ensemble + DS-02.

Evaluation is horizon-specific and split by market/rule/regime eras. Claimed improvements must survive realistic costs and DS-10 multiple-testing controls.
