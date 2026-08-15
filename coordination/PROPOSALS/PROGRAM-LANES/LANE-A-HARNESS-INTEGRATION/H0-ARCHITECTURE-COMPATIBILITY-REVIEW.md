# H0 Architecture Compatibility Review

Status: `STATIC_ARCHITECTURE_PASS_WITH_BOUNDED_DEBT / H0_FINAL_NOT_READY / IMPLEMENTATION_FAIL_CLOSED`

Reviewed scope:
- frozen Second Brain Foundation (#282/#335);
- Issue #312 Method Discovery / Meta-Reasoning / Effective Challenge;
- Issue #308 A-share evidence-first remediation;
- Signal Tower;
- Control Tower #310;
- Harness upstream snapshot + Adapter boundary;
- DecisionEpisode / MissionGraph / Claim / Handoff contracts;
- Effective Challenge;
- Outcome/correction/audit learning + skill evolution;
- MethodMemory / SkillManifest progressive disclosure;
- Trace Ledger / privacy;
- Department Contract Graph / Organization Graph Validator;
- H1/H2 implementation separation;
- implementation dependency DAG;
- current canonical control-plane reconciliation evidence.

## 1. Executive verdict

The proposed architecture is **structurally compatible** with the frozen Second-Brain foundation and preserves the high-value requirements from #312 and #308 without creating a second W3, second Method Router, second feedback runtime, second evidence truth, second Control Tower, or Harness-owned truth authority.

A cross-file H0 audit found real design defects and repaired them on the proposal branch. Current architecture-static verdict:

`PASS_WITH_BOUNDED_DEBT`

However H0 final acceptance is deliberately held:

`H0_FINAL_ACCEPTANCE = NOT_READY`

`H1/H2_IMPLEMENTATION_RELEASE = FAIL_CLOSED`

The remaining blocking reason is canonical Control Tower stale state, now independently reproduced by the existing Control Tower CI.

---

## 2. Authority review

### PASS — W3 ownership

W3 remains the sole durable knowledge/memory/provenance/lifecycle authority. Harness session logs/runtime context are runtime trace/context only.

### PASS — Method ownership

#312 owns ProblemSignature / Method Selection / Challenge policy selection. Durable MethodMemory stays in W3; Method Router consumes a projection. Formal Skill authority remains outside Harness.

### PASS — Mission vs authorization

Signal Tower owns Mission intake/decomposition/result aggregation. Control Tower owns executable route/Work Claim/WIP/collision/authorization. Harness only executes an already-authorized workflow.

### PASS — execution roles do not become authorities

`PRIMARY_PRODUCER` and `CHALLENGER` are explicit role templates with `authority_domain: NONE`.

### PASS — Risk veto

W7 final veto cannot be overridden by Adjudicator, Agent majority, Signal Tower, Harness, role template, or prose.

### PASS — A-share domain separation

#308 consumes shared cognitive services and W2/W5/W6/W13/W12/W7. It does not become a separate truth/method/learning authority and remains `NO_TRADE`.

---

## 3. Machine-contract review

### FIXED — design DSL vs executable schema ambiguity

The original contract file looked JSON-Schema-like but contained free-form semantic rules. That could have produced a shadow implementation where a report claims “schema validated” while important rules are still prose.

The contract is now explicitly:

`COGNITIVE_CONTRACT_DSL/v0.2`

H1 must:
- compile structural constraints to formal JSON Schema or justified equivalent;
- implement every named semantic invariant deterministically;
- attach positive/negative fixtures and stable error codes.

### FIXED — state ordering ambiguity

Removed semantic dependence on expressions such as `state >= EXECUTING`.

`DecisionEpisodeStateMachine_v1` now declares explicit states, forward transitions, terminal states, states requiring authorization/trace, and bounded `ReworkRequest/v1` transitions.

### FIXED — missing causal/PIT fields

ProblemSignature now has explicit:
- `competing_hypotheses_required`;
- `evidence_waiver_ref`;
- `pit_capability_ref`.

### FIXED — Challenge independence contract

ChallengeCase now stores `challenge_level`; C2-C4 deterministic invariant requires `independent_pass_ref`.

### BOUNDED DEBT — actual schema compiler/validator code

Not implemented in H0 by design. This is H1's primary deliverable.

Classification: `P1 H1_IMPLEMENTATION_GATE`, not a reason to reopen W3.

---

## 4. Organization / return-path review

### FIXED — implicit Primary Producer

Primary was previously conceptually present but missing as a formal graph node. It is now an explicit role template.

### FIXED — Challenger explicit role

Challenge coordinator and Challenger execution role are separated. The Challenge Mesh coordinates policy/requests; Challenger performs independent generation.

### FIXED — prose-only return arrows

Aliases such as:
- `SOURCE_CALLER`
- `DOMAIN_CALLER`
- `RESPONSIBLE_UPSTREAM`
- `PRODUCER_OR_EVIDENCE_VERIFIER`
- `PRODUCER_OR_SIGNAL_TOWER`

now have machine-resolvable rules and allowed target sets. Unknown/unresolvable aliases must fail closed.

### BOUNDED DEBT — executable graph validator

OGV-001..032 are specified, including role/alias resolution and route/work-claim consistency. H1 must implement deterministic offline checks.

---

## 5. Cognitive-loop review

The architecture distinctly represents:

1. retrieval;
2. ProblemSignature;
3. cognitive capability mapping;
4. MethodMemory / SkillManifest discovery;
5. prerequisite/regime/permission validation;
6. method selection 0..N / NO_METHOD / ABSTAIN;
7. evidence acquisition;
8. Primary generation;
9. independent Challenge;
10. tool/source Verification;
11. Adjudication;
12. domain validation;
13. W12 decision science / value-of-information stopping;
14. W7 final veto;
15. user output/action proposal;
16. outcome **or verified correction/audit** observation;
17. failure localization;
18. ReflectionCandidate;
19. reflection verification;
20. method/tool/source/challenge credit;
21. candidate updates;
22. regression mining;
23. cross-context/regime revalidation;
24. skill promotion/degradation/retirement;
25. next-episode reuse.

This preserves the central distinction:

> Reflection is not learning. Learning is not promotion.

---

## 6. Learning review

### FIXED — outcome-only learning assumption

OutcomeLearning no longer requires a real-world `outcome_ref` in every case. Verified user correction or audit finding can trigger a learning event while remaining evidence-bound.

### PASS — no one-shot promotion

OutcomeLearning/Reflection may create candidates only. Formal Skill transition remains a separate governance event after multi-stage revalidation.

### PASS — outcome != method quality

MethodCredit separates:
- ex-ante selection quality;
- execution quality;
- evidence quality;
- outcome quality;
- calibration quality;
- transfer quality.

Lucky success cannot automatically validate a bad method; unlucky outcome cannot automatically invalidate a sound decision.

### PASS — process failures can become engineering-learning candidates

Coordination/authority/trace/resource errors feed EngineeringLearningCandidate + RegressionCase rather than corrupting domain truth.

### BOUNDED DEBT — Formal Skill execution governance

A future governed runtime remains required. It is not owned by Harness and is not an H0 blocker.

---

## 7. MethodMemory / SkillManifest review

### PASS — single durable method authority

Durable MethodMemory remains W3-owned.

### PASS — progressive disclosure

- Level 0: compact catalog
- Level 1: preconditions/failure/regime manifest
- Level 2: selected method body
- Level 3: cases/failures/counterexamples only when validation requires

This prevents a growing skill library from turning every task into full-library context loading.

### PASS — structural retrieval beyond topic similarity

Method retrieval may use structure, failure modes, case analogy, regime, tool/data compatibility and cognitive bridge signals. Topic/embedding similarity alone is forbidden as selector.

---

## 8. Independent Challenge review

### PASS — topology

Primary Producer / Challenger / Evidence Verifier / Adjudicator are separate roles/services with no truth authority transfer.

### PASS — anti-conformity

C2-C4 requires blind/independent pass provenance before reveal.

### PASS — external evidence

Evidence Verifier is tool/source grounded and separate from generative disagreement.

### PASS — no infinite debate

W12 value-of-information, retry budgets, ReworkRequest and ABSTAIN/ESCALATE terminate loops.

### BOUNDED DEBT — provider-level isolation proof

H2/H3 must prove that actual runtime contexts do not accidentally leak Primary conclusions into the blind Challenger phase.

---

## 9. Trace / privacy review

### PASS — three-layer trace

- Native Raw Trace
- Cross-Agent Trace Ledger
- Formal Handoff (`*.handoff.json + *.analysis.md`)

`Raw once, reference everywhere` prevents duplicated giant traces.

### PASS — private chain-of-thought is not required

Auditability uses structured events, claims, tools, artifacts, evidence, transitions and provider-native public-safe events, not mandatory private chain-of-thought capture.

### PASS — privacy separation

Raw private prompt/source content is not generic telemetry by default. Secret values never enter fingerprints.

### BOUNDED DEBT — executable T0-T3 validators

Defined now, implemented/tested in H1/H2.

---

## 10. Harness compatibility review

### PASS — canonical identity / architecture surface

Verified H0 snapshot:
- repo `deepseek-ai/deepseek-harness`;
- exact SHA `47f943859bef60e4160492346772ded9b24f765a`;
- `0.1.0-rc.5`;
- MIT;
- official Cordis / everything-is-plugin / Service Definition-Provider-Consumer architecture.

### PASS — Adapter-first fit

Our boundary aligns with the upstream architectural principle that extension consumers depend on Service Definitions rather than concrete providers.

### RISK — developer preview

Breaking changes are expected.

Mitigation remains:
- exact pin;
- Adapter isolation;
- public service signature snapshot;
- latest-upstream compatibility radar;
- no auto-upgrade;
- rollback tests.

### H2 BLOCKER — runtime smoke

Clean install/pack/provider/target-environment/rollback smoke is intentionally not done in H0 and is mandatory before H2 runtime acceptance.

---

## 11. H1/H2 implementation separation

### FIXED — one oversized claim

H1 contract skeleton and H2 Harness PoC were initially in one heavy implementation candidate. They are now two independent future claims.

### H1

Contract-only synthetic skeleton:
- formal structural schemas/equivalent;
- semantic validators;
- state machines;
- graph validator;
- trace/handoff/fingerprint fixtures;
- public-safe deterministic tests.

H1 may **not** bind/install Harness as product runtime.

### H2

Harness Adapter PoC:
- separate fresh route/Work Claim;
- pinned runtime smoke;
- workflow/subagent/tool/retry/cancel/native trace;
- Primary/Challenger isolation;
- resource/rollback tests.

**H1 authorization/acceptance never implies H2 authorization.**

---

## 12. Control-plane review

### OPEN P0 — completed R132 still looks executable

`ACTIVE-CODEX-TASK.yaml` still projects R132 as `READY`, `execution_allowed: true`, `next_command: 读取任务`, despite merged PR #334 and completed Foundation Closure.

### OPEN P0 — Lane C Work Claim still R120

`LANE-WORK-CLAIMS.yaml` still binds the current heavy implementation lease to R120 / Issue #305 / PR #307.

### OPEN P0 — Program Lane registry stale

`ACTIVE-PROGRAM-LANES.yaml` still reports R120-era observed state and Lane A as PAUSED.

### Mechanical proof

Existing `Program Control Tower foundation` CI independently reproduced the drift:
- Python 3.11/3.13 targeted regressions PASS;
- 20/20 targeted tests PASS;
- reconciliation FAIL with `CT-R01-STALE-VIEW / PROGRAM_REGISTRY_ROUTE_DRIFT`;
- downstream Work Claim/witness stages skipped.

This is desired fail-closed behavior.

A bounded remediation candidate exists in:

`CONTROL-TOWER-STALE-STATE-REMEDIATION-CANDIDATE.yaml`

It is **not applied from Lane A**.

---

## 13. Second-Brain bounded gaps

### R120-W01 context-only endpoint

`BOUNDED_ADAPTER_CONCERN`

Do not expose W3 internals to solve it. Add a narrow successor interface only when a real consumer proves need.

### R122 unknown binding

`BOUNDED_SUCCESSOR_INTERFACE`

Keep fail-closed and add a narrow versioned successor if required.

### FeedbackLifecycle/v1

`SUCCESSOR_INTERFACE_CANDIDATE`

The semantics exist; a clean external adapter surface is future bounded work.

None justify P2.5.

---

## 14. #312 compatibility verdict

`COMPATIBLE_WITH_ARCHITECTURAL_REASSIGNMENT`

No material capability was dropped:
- Method knowledge → W3
- method routing → #312
- challenge runtime → role workflow/Harness later
- evidence verification → Verifier/domain tools
- stopping → W12
- final veto → W7
- outcome credit → W9
- Formal Skill authority → existing governance

---

## 15. #308 compatibility verdict

`COMPATIBLE_AS_FIRST_DOMAIN_CONSUMER`

Preserved:
- mandatory event coverage;
- PIT anomaly backfill;
- evidence language;
- Data Grade gates;
- H1-H5 competing hypotheses;
- strongest counterargument / negative controls / cross-sectional comparison;
- unresolved/unknown outputs;
- shared W9/W3 feedback;
- `NO_TRADE`.

---

## 16. Final H0 gate

The architecture itself is now sufficiently mature to wait at the final gate rather than expand horizontally.

H0 may receive final `ACCEPT` or `ACCEPT_WITH_BOUNDED_DEBT` only after:

1. stale completed R132 executable projection is neutralized;
2. Lane C Work Claim represents Foundation closed/no active heavy lease;
3. Lane A is reconciled as active proposal-only architecture design;
4. Lane B hold remains unchanged unless separately started;
5. Control Tower reconciliation PASS;
6. Work Claims PASS;
7. O0-O4 / WIP / heavy-resource checks PASS;
8. durable authorization witness round trip PASS for the cleaned state;
9. H0 static audit rerun shows no open P0 architecture/control blocker;
10. no new semantic loss from #312/#308/Foundation is introduced by cleanup.

Until then:

`H0_FINAL_ACCEPTANCE = NOT_READY`

`NO_H1_EXECUTABLE_ROUTE`

`NO_HARNESS_RUNTIME_IMPLEMENTATION_ROUTE`
