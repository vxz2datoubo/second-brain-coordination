# H0 Architecture Compatibility Review

Status: `PROVISIONAL_PASS_FOR_CONTINUED_H0_DESIGN / IMPLEMENTATION_NOT_RELEASED`

Reviewed scope:
- frozen Second Brain Foundation (#282/#335);
- Issue #312 Method Discovery / Meta-Reasoning / Effective Challenge;
- Issue #308 A-share evidence-first remediation;
- Signal Tower;
- Control Tower #310;
- Harness upstream snapshot + Adapter boundary;
- DecisionEpisode / MissionGraph / Claim / Handoff contracts;
- Effective Challenge;
- Outcome learning / skill evolution;
- Department Contract Graph / Organization Graph Validator;
- implementation dependency DAG.

## 1. Executive verdict

The proposed architecture is **structurally compatible** with the frozen Second-Brain foundation and preserves the high-value requirements from #312 and #308 without creating a second W3, second Method Router, second feedback runtime, second evidence truth, or second Control Tower.

Current verdict is not H0 final acceptance because several **bounded implementation-gate debts** remain. None requires reopening the Second-Brain foundation today.

Provisional disposition:

`CONTINUE_H0_DESIGN / NO_RUNTIME_ROUTE`

---

## 2. Authority review

### PASS — W3 ownership

W3 remains the sole durable knowledge/memory/provenance/lifecycle authority. Harness session logs and runtime context are explicitly non-authoritative for long-term knowledge.

### PASS — Method ownership

#312 owns ProblemSignature / Method Selection / Challenge policy selection. Durable method knowledge stays in W3 and is consumed through a bounded projection.

### PASS — Mission vs authorization separation

Signal Tower owns user Mission intake/decomposition/result aggregation. Control Tower owns execution authorization/WIP/collision. Harness only executes an already-authorized workflow.

### PASS — Risk veto

W7 final veto cannot be overridden by Adjudicator, Agent majority, Signal Tower or Harness.

### PASS — A-share domain separation

#308 consumes W2/W5/W6/W13/W12/W7 and shared cognition. It does not become a separate truth or learning authority.

---

## 3. Cognitive-loop review

The architecture now distinguishes:

1. retrieval;
2. problem structuralization;
3. user/system capability mapping;
4. method discovery;
5. prerequisite and regime validation;
6. evidence acquisition;
7. Primary generation;
8. Independent Challenge;
9. tool/source verification;
10. adjudication;
11. domain validation;
12. W12 decision science / stopping;
13. W7 final veto;
14. user output/action proposal;
15. outcome observation;
16. failure localization;
17. reflection candidate;
18. reflection verification;
19. method/tool/source/challenge credit;
20. candidate updates;
21. regression mining;
22. cross-context revalidation;
23. skill promotion/degradation/retirement;
24. next-episode reuse.

This satisfies the intended distinction between **thinking again** and **actually learning from validated consequences**.

---

## 4. Independent Challenge review

### PASS — topology

Producer/Challenger/Verifier/Adjudicator are role templates, not permanent independent authorities.

### PASS — anti-conformity

C2-C4 requires independent pass provenance before reveal.

### PASS — external evidence

Verifier is tool/source grounded and separate from generative challenge.

### PASS — no infinite debate

W12 value-of-information / budget / ABSTAIN and retry limits terminate loops.

### BOUNDED DEBT — independence implementation proof

Architecture specifies isolated sessions/context, but H2/H3 must prove provider-level isolation and no accidental conclusion leakage.

Classification: `P1 IMPLEMENTATION_TEST_REQUIRED`, not architecture blocker.

---

## 5. Learning review

### PASS — no one-shot promotion

Reflection, learning and promotion are separate stages.

### PASS — outcome is not method quality

MethodCredit separates ex-ante selection, execution, evidence, outcome and calibration quality. This prevents lucky profit from automatically validating a bad method and unlucky loss from automatically invalidating a sound method.

### PASS — system can learn architecture/process failures

Coordination/authority/trace/resource errors create EngineeringLearningCandidate and regression cases, rather than contaminating domain knowledge.

### BOUNDED DEBT — formal promotion runtime

The final executable Formal Skill promotion mechanism remains a future governed capability. Current architecture intentionally keeps it outside Harness/W3 automatic execution.

Classification: `P2 SUCCESSOR_CAPABILITY`, not H0 blocker.

---

## 6. Harness compatibility review

### PASS — canonical identity

Canonical upstream was independently re-identified as `deepseek-ai/deepseek-harness`.

Verified design snapshot:
- exact master SHA: `47f943859bef60e4160492346772ded9b24f765a`;
- package family/root version: `0.1.0-rc.5`;
- MIT license;
- official architecture: Cordis / everything-is-plugin / Service Definition-Provider-Consumer seams;
- official package inventory exposes stable product API families for sessions, skills, subagents, workflows, jobs, guards, bundles, SDK, interaction and related capabilities.

### PASS — Adapter-first fit

Official Harness architecture itself recommends extension plugins depend on Service Definitions, not concrete providers. This matches our Adapter boundary.

### RISK — developer preview

Official README warns compatibility-breaking changes are expected.

Mitigation:
- exact SHA/version pin;
- Adapter isolation;
- generated service contract snapshot;
- latest-upstream radar only;
- no auto-upgrade;
- rollback and compatibility tests.

### BOUNDED DEBT — runtime smoke

Clean install/pack/smoke on the target environment has not been performed in H0 proposal mode.

Classification: `P0 BEFORE H2 RUNTIME BINDING`, but **not a blocker to continued H0 architecture design**.

---

## 7. Control-plane review

### FINDING H0-CT-001 — stale aggregate/control projections

Current canonical `ACTIVE-PROGRAM-LANES.yaml` and `LANE-WORK-CLAIMS.yaml` still describe older Lane C / R120-era state even though Second Brain advanced through P2.4B and Foundation Closure. `ACTIVE-CODEX-TASK.yaml` also still contains the completed R132 route projection.

This confirms the already-known rule: latest execution truth must be reconciled and stale projections cannot authorize work.

Impact:
- does not invalidate proposal-only H0 writes because they are isolated in Lane A;
- **blocks any new executable H1/H2 route until Control Tower current-state reconciliation is refreshed**.

Classification: `P0 IMPLEMENTATION_RELEASE_BLOCKER / NOT H0 DESIGN BLOCKER`.

Required action before runtime:
1. refresh current observed lane state;
2. retire/neutralize stale R132 authorization projection;
3. update Work Claims to reflect Second-Brain Foundation closure and Lane A proposal status;
4. run fresh O0-O4/WIP scan;
5. issue fresh durable authorization witness.

---

## 8. Second-Brain bounded gaps

### R120-W01 context-only endpoint

Disposition: `BOUNDED_ADAPTER_CONCERN`.

Rule: Harness/Signal Tower may not solve it by importing W3 internals. If required by a real consumer, define a narrow successor interface and regression tests.

### R122 unknown binding

Disposition: `BOUNDED_SUCCESSOR_INTERFACE`.

Unknown preservation already exists conceptually; if cross-component binding needs stronger contract semantics, add a narrow versioned interface rather than reopen broad W3 architecture.

### FeedbackLifecycle/v1

Disposition: `SUCCESSOR_INTERFACE_CANDIDATE`.

The semantic actions exist in the frozen knowledge reconciliation lifecycle. A clean cross-component feedback API still needs a later bounded implementation contract.

None currently requires P2.5.

---

## 9. #312 compatibility verdict

`COMPATIBLE_WITH_ARCHITECTURAL_REASSIGNMENT`

No high-value #312 requirement was dropped. Requirements were assigned to correct owners:
- Method knowledge → W3;
- method routing → #312;
- challenge execution → Harness role workflow;
- evidence verification → verifier/domain tools;
- stopping → W12;
- final veto → W7;
- outcome credit → W9;
- Formal Skill authority → existing governance.

---

## 10. #308 compatibility verdict

`COMPATIBLE_AS_FIRST_DOMAIN_CONSUMER`

#308 retains:
- mandatory event coverage;
- PIT anomaly backfill;
- evidence language contract;
- Data Grade gates;
- H1-H5 competing hypotheses;
- counterargument/negative control/cross-sectional comparison;
- unresolved/unknown outputs;
- feedback into shared W9/W3 learning.

It does not own the shared cognition runtime.

---

## 11. H0 remaining work

Before final H0 verdict:

1. run a machine-oriented static validation pass over all proposal schemas/graph references;
2. complete architecture findings list from Organization Graph Validator spec;
3. reconcile any missing department relationships or duplicate conceptual roles;
4. freeze minimal MethodMemory / SkillManifest projection contracts;
5. freeze Trace Ledger event contract and privacy policy;
6. update Draft PR manifest/index;
7. perform a fresh Control Tower proposal-only O0-O4 scan against current main;
8. produce final GPT H0 verdict.

Until then:

`NO HARNESS RUNTIME IMPLEMENTATION ROUTE`.
