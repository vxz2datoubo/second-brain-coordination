# DS-02 Research Validation v1.0

## Evidence policy

Research evidence constrains design. It does **not** prove calibration, profitability, A-share transferability, canonical-belief authority, or suitability for live trading. In Phase 1, even a schema-valid and verifier-valid packet is an `UNVALIDATED_PROPOSAL`.

## Bayesian workflow evidence

Prior predictive checks inspect prior implications before conditioning on observations; posterior predictive checks test whether posterior-generated data reproduce material observed structure. MCMC diagnostics such as R-hat, ESS and divergences address computational reliability, not economic adequacy. PSIS-LOO/Pareto-k support diagnosed predictive comparison, not trade authority. Simulation-based calibration tests inference under a specified simulator, not realism of the market model.

**Engineering consequence:** every future inference family needs its own diagnostic and predictive gates. Successful execution never alone produces trusted belief or trading authority.

## Proper scoring and calibration

Brier score, logarithmic score, reliability and calibration slope/intercept are forecast-quality evidence. Complete forecast/outcome history, failed trials and abstentions must be retained. Accuracy alone is insufficient.

## Ex-ante prior provenance

Issue #519 explicitly prohibits retrospective prior tuning masquerading as ex-ante knowledge. Phase-1 machine enforcement now requires a structured training window and regime scope, with both `training_window.end` and `prior.effective_from` no later than the packet `knowledge_cutoff`.

**Engineering consequence:** a mathematically plausible prior is rejected as `PRIOR_NOT_EX_ANTE` when its provenance uses knowledge unavailable at the declared cutoff. This is provenance control, not a claim that the chosen prior family is economically optimal.

## Point-in-time and knowledge-cutoff integrity

Decision-time PIT alone is not enough when a packet declares a stricter knowledge boundary. The machine contract now enforces:

`knowledge_cutoff <= as_of_time <= decision_time`

and admitted evidence must satisfy both:

`available_at <= knowledge_cutoff`

`available_at <= decision_time`.

Thus evidence that appears after the declared historical knowledge cutoff cannot leak into the proposal merely because it appears before a later simulated decision timestamp. Revised observations also retain revision identity plus superseded snapshot hashes.

## Dependence and forecast combination

Different labels do not imply independent information. Agents or models sharing an original source, feed, feature engineering, training data, model lineage or upstream evidence cannot be multiplied as independent measurements without a separately governed dependence authority/model.

Phase-1 machine consequences:

- evidence carries source-instance/ancestry/shared-lineage fields;
- `candidate_independence_group_id` is neutral metadata;
- `dependence_authority_state = UNAVAILABLE_PHASE1`;
- `independence_status = UNVERIFIED`;
- copied/reposted/shared-lineage evidence triggers dependence collapse/revalidation;
- multiple unresolved admitted sources remain `INDEPENDENCE_UNVERIFIED` rather than inflating confidence.

## Caller-shaped posterior and computation trust

`belief_contract.py` recomputes the analytic log-odds posterior represented by prior probability plus cumulative log Bayes factor and rejects inconsistent caller-shaped values. Structurally, Phase 1 cannot claim `VALID` or `VALIDATED`; the validated computation receipt is null and canonical-belief authority is false.

## Small-sample shrinkage safety

The binding design requires hierarchical shrinkage so tiny A-share samples cannot manufacture extreme certainty. Phase 1 therefore includes a conservative machine safety gate in the Numeric Integrity Registry: effective sample size below 20 combined with posterior >=0.90 or <=0.10 yields `SMALL_SAMPLE_SHRINKAGE_REQUIRED / REVALIDATION_REQUIRED`.

This threshold is explicitly a **contract safety gate**, not an alpha parameter, calibrated trading threshold, or claim of empirical optimality. Later empirical shrinkage strength requires separately governed validation.

## Canonical content integrity

`numeric_integrity.canonical_digest` is deterministic lower-case SHA-256 over sorted-key compact UTF-8 JSON of the packet excluding the digest field itself. A content mutation without a matching recomputation is rejected. The digest proves content consistency only; it does not authenticate the producer or mint canonical belief authority.

## Regime/change evidence

Bayesian changepoint methods motivate explicit validity windows and structural-break handling, but DS-11 remains regime authority. DS-02 consumes regime/changepoint state and may return `REVALIDATION_REQUIRED`.

## 2026 A-share rule evidence

Official exchange publications provide a structural-break case: SSE, SZSE and BSE published 2026 rule revisions with July 6, 2026 effective changes, and BSE separately deferred specified provisions. Therefore exchange, board, security type, rule version and clause activation state are separately bound. Cross-exchange substitution is schema-invalid and use of a registered deferred BSE clause revalidates.

These sources do not prove predictive alpha, likelihood transfer, execution performance, or economic value.

## Executable adversarial evidence

The adversarial pack now contains **29 executable cases**, each expanded to an individual unittest ID. Label-presence-only testing is explicitly rejected as evidence.

Attack families include:

- repost/shared feed/feature/training/model lineage and caller relabeling;
- raw confidence and mathematically inconsistent caller posterior;
- tiny-sample extreme posterior without acceptable shrinkage state;
- future decision-time evidence, post-knowledge-cutoff evidence and invalid temporal ordering;
- ex-post prior effective date and training-window leakage;
- revised-data lineage failure;
- target/feature identity drift;
- SSE/SZSE substitution and BSE deferred clause use;
- canonical content-digest tampering;
- retraction recomputation and append-only deletion;
- UNKNOWN/ABSTAIN and no-action behavior;
- market/event/regime/order authority escalation.

## Validation ladder

| Gate | Question | Minimum evidence | Fail-closed state |
| --- | --- | --- | --- |
| V0 | Is packet structure/cross-field logic valid? | closed schema + verifier | REJECTED |
| V1 | Is closed-form math correct? | Beta-Binomial + Normal-Normal + log-BF oracles | INVALID_MODEL |
| V2 | Are mandatory attacks executable? | 29 per-case fixtures | REJECTED / REVALIDATION_REQUIRED |
| V3 | Is information truly point-in-time? | decision/cutoff/revision fixtures | PIT / CUTOFF violation |
| V4 | Is prior provenance ex-ante and tiny-sample certainty controlled? | structured prior + shrinkage gate | REJECTED / REVALIDATION_REQUIRED |
| V5 | Is inference calibrated under the assumed simulator? | SBC | INFERENCE_INVALID |
| V6 | Is numerical inference reliable? | R-hat/ESS/divergence gates | ABSTAIN |
| V7 | Can the model reproduce material structure? | prior/posterior predictive checks | MODEL_MISFIT |
| V8 | Are forecasts calibrated OOS? | Brier/log score/reliability | UNCALIBRATED |
| V9 | Does DS-02 add A-share economic information? | purged walk-forward + embargo + lockbox + costs | NO_INCREMENT |
| V10 | Is discovery robust to multiplicity? | DS-10 audit | OVERFIT_RISK |
| V11 | Does shadow behavior remain stable? | drift/abstention/reproducibility ledger | REVALIDATION_REQUIRED |

## Explicit non-claims

This contract does not claim Bayesian methods dominate frequentist methods; a proposal posterior is automatically calibrated/canonical; the Phase-1 verifier proves independence; the shrinkage thresholds are economically optimal; calibration implies positive EV; positive EV implies action; MCMC convergence proves model adequacy; PSIS-LOO proves future performance; official rules imply edge; content SHA-256 authenticates a producer; or anything here authorizes runtime, capital, broker, orders, account funds, or trades.

## Future A-share comparison baseline

Phase 3 must compare at least empirical base rate, regularized-logistic baseline, pre-DS-02 baseline, existing ensemble, and existing ensemble + DS-02. Evaluation remains horizon-specific and split by market/rule/regime eras with realistic costs and DS-10 multiple-testing controls.
