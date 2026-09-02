# W12 D0-D6 Project Plan

## Fixed Architecture

```text
W2 market facts + official RuleSnapshot
  -> W10 task/world context
  -> DS-01 DecisionFrame
  -> DS-02 shared ProbabilityEstimate
  -> DS-10 ResearchAuditReport
  -> W10 DecisionEpisode
  -> W11 NetEV/allocation (read only)
  -> candidate LearningPacket
  -> PR #57 canonical memory
  -> PR #58 gateway after its independent acceptance gate
```

At every phase the system remains `research_only / NO_TRADE`.

## D0: Reality Freeze

- **Input:** latest main, Issue #63, forecast, PR #57/#58/#64/#65/#8/#34, accessible local blueprints/code/skills/tests and official rules.
- **Output:** reality and maturity matrices, ownership freeze, rule matrix, findings, D0-D6 plan, feedback and handoff.
- **Acceptance:** every material claim has evidence class; no child runtime changes; at most three P0 slices.
- **Rollback:** remove the isolated D0 branch/worktree; shared root and protected files remain byte-unchanged.
- **Owner/reviewer:** Codex / GPT.

## D1: Gap Compiler and Maturity Registry

- **Input:** D0 matrices and W12 machine registry.
- **Implementation:** deterministic scanner for blueprint terms, skill IDs, contracts, owners, runtime references, tests and maturity; emit orphan, ghost, duplicate and stale findings.
- **Interfaces:** `SkillManifest`, `EvidenceReference`, `MaturityRecord`, `GapFinding`, `OwnershipBoundary`, deterministic `GapReport`.
- **Acceptance:** stable output hash; golden cases detect all mandatory finding types; no repository mutation outside W12 governance artifacts.
- **Protected backwrite:** separate authorized local task using preimage hashes, additive patch, reverse patch and postimage hashes.
- **Rollback:** delete generated registry version and restore prior immutable registry snapshot.

## D2: DS-01 Decision Framing

- **Input:** W10 context, evidence IDs, user goal, allowed alternatives and A-share `RuleSnapshotRef`.
- **Output:** versioned `DecisionFrame` candidate object.
- **Acceptance:** schema round-trip, missing-goal/constraint/observability tests, correlation-vs-causation guard, UNKNOWN preservation and no-order test.
- **Compatibility:** attach to W10 DecisionEpisode by reference; do not fork it.
- **Rollback:** unregister candidate skill and retain rejected frame artifacts for audit.

## D3: DS-02 Bayesian Belief and Forecast Fusion

- **Input:** DecisionFrame, priors, evidence likelihood claims, provenance, correlation groups and calibration history.
- **Output:** the shared versioned `ProbabilityEstimate`, with an immutable fusion contribution ledger, unknown mass and abstention. W10 references and freezes its ID/hash; it does not copy or mutate the estimate.
- **Acceptance:** conjugate and numerical fixtures, duplicate-source suppression, interval/UNKNOWN behavior, Brier/log-loss, coverage and calibration tests.
- **Compatibility:** emit a ForecastRecord-compatible projection; W11 consumes read-only and no sizing occurs until the calibration gate passes.
- **Rollback:** freeze model version and restore prior registered weight/calibration snapshot; never erase failed forecasts.

## D4: DS-10 Research Overfitting Audit

- **Input:** immutable experiment family ledger, failed and successful variants, point-in-time datasets and validation results.
- **Output:** `ResearchAuditReport` and promotion-block decision.
- **Acceptance:** leakage, purge/embargo, walk-forward, trial-family, failure-retention, PBO/DSR applicability and false-promotion tests.
- **Compatibility:** invoke W7 validation evidence; do not replace W7 hard gates.
- **Rollback:** freeze audit version and preserve all historic audit decisions.

## D5: Cross-System Integration

- **Input:** accepted D2-D4 contracts plus PR #57 and, only after acceptance, PR #58 gateway contracts.
- **Output:** candidate `LearningPacket` and retrievable `ContextBundle` carrying frame, belief, audit, conflicts and UNKNOWNs.
- **Acceptance:** deterministic round-trip, provenance, conflict propagation, revocation, access-policy and no-credential tests.
- **Dependency:** PR #58's unchanged independent 100+ QCLAW evaluation must be accepted before gateway integration.
- **Rollback:** use canonical snapshot/revocation mechanisms; W12 stores no independent canonical state.

## D6: Adversarial and Shadow Validation

- **Input:** synthetic cases, historical point-in-time A-share slices, rule-version transitions and approved shadow observations.
- **Output:** calibration report, failure taxonomy, maturity decision and SelfEvolution candidate packet.
- **Acceptance:** cross-period replication, drift/regime breakdown, abstention quality, counterexamples and no-trade isolation.
- **Promotion:** only sequential state transitions are allowed; `VALIDATED_RESEARCH_CAPABILITY` never grants production or order authority.
- **Rollback:** freeze or retire the candidate skill while retaining its evidence and failure history.

## Sequencing

- D0 and the external PR #58 adversarial evidence lane may run in parallel because D0 is read-only planning.
- D1 waits for D0 acceptance.
- D2, D3 and D4 are serial for contract integrity; test fixture research may be prepared in parallel without runtime code.
- D5 waits for D2-D4 and the PR #58 external gate.
- D6 waits for D5 deterministic integration.
- GPT creates or activates one child task at a time; no automatic issue explosion.

## Stop Conditions

- Any proposal requires a second memory, risk, portfolio, market, OMS or execution authority.
- An official rule source, effective date or instrument applicability is missing.
- Test or validation evidence is claimed without an actual command and exit code.
- A local write would touch another agent's uncommitted work or protected files outside an approved patch task.
- Credentials, broker/account data, service lifecycle or trading execution becomes necessary.
