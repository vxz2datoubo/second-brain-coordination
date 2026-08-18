# H0 Architecture Compatibility Review

Status: `H0_ACCEPT_WITH_BOUNDED_DEBT / IMPLEMENTATION_NOT_AUTO_RELEASED`

Canonical main rechecked after Control Tower cleanup: `62a171944840a2f064e0c9a4936f7e0b0d081e68`.

Control Tower cleanup PR #337 merged after exact-head review. The reviewed cleanup head `ef564d91770e58c19e8ede7d80f1036464c7682f` passed workflow `31878478727` on Python 3.11 and 3.13 with 32/32 targeted regressions plus reconciliation, Work Claims, projection and durable witness round trip.

## Final H0 verdict

`ACCEPT_WITH_BOUNDED_DEBT`

The proposed Cognitive OS architecture is compatible with the frozen Second-Brain foundation and preserves the high-value requirements of #312 and #308 without creating a second W3, second Method Router, second feedback runtime, second evidence truth, second Control Tower or Harness-owned truth authority.

All H0 architecture/control-plane P0 gates now pass. Remaining work is assigned to later implementation gates and does not justify reopening P2.5/P2.6.

## Authority topology

- W3 / Second Brain: single durable knowledge, memory, provenance, conflict/unknown and lifecycle authority.
- #312: ProblemSignature, Method Discovery, Meta-Reasoning and challenge-policy selection.
- Signal Tower: single Mission intake, decomposition, dispatch proposal and user result aggregation.
- Control Tower #310: route, Work Claim, WIP, collision, commit-time freshness and execution authorization governance. It is not a task router.
- Harness: future runtime/session/workflow/subagent/tool/job/trace execution kernel behind our Adapter. It is not a truth authority.
- W2-W13: domain authorities; W7 retains final risk veto.
- W9: outcome/correction/audit learning, failure localization, MethodCredit and SkillHealth candidates.
- Primary Producer / Challenger / Evidence Verifier / Adjudicator: execution roles with no canonical truth authority.
- #308: first A-share consumer, `research_only / NO_TRADE`.

## Cognitive loop preserved

The H0 architecture distinctly models:

1. Mission intake;
2. ProblemSignature;
3. Second-Brain retrieval;
4. user/system cognitive capability mapping;
5. MethodMemory / SkillManifest discovery;
6. prerequisite, regime, permission and evidence checks;
7. method selection 0..N / NO_METHOD / ABSTAIN;
8. evidence acquisition;
9. Primary generation;
10. independent Challenge;
11. tool/source Verification;
12. Adjudication;
13. domain validation;
14. W12 decision science / value-of-information stopping;
15. W7 final veto;
16. output/action proposal;
17. outcome or verified correction/audit observation;
18. failure localization;
19. ReflectionCandidate;
20. reflection verification;
21. method/tool/source/challenge credit;
22. candidate updates;
23. regression mining;
24. cross-context/regime revalidation;
25. skill promotion/degradation/retirement;
26. next-episode recall and reuse.

The central invariant remains:

> Reflection is not learning. Learning is not promotion.

## Key design defects repaired during H0

- machine-looking DSL was separated from executable-schema semantics;
- state transitions no longer rely on ordinal prose comparisons;
- causal/PIT fields and invariants are explicit;
- ChallengeCase stores challenge level and independent-pass provenance;
- Primary Producer / Challenger are explicit roles;
- dynamic return aliases are machine-resolvable;
- Harness identity verification is separated from later runtime smoke;
- H1 contract skeleton and H2 Harness runtime PoC are separate future claims/routes;
- W9 remains owner of OutcomeLearning;
- completed R132 is a non-executable tombstone;
- Lane C has a first-class `CLOSED_NO_ACTIVE_IMPLEMENTATION` state;
- Program Lanes must declare dependencies/shared_interfaces and fail closed when the contract is malformed.

## Control-plane final state

Canonical main now confirms:

- R132: `DONE / execution_allowed=false / runtime_code_change_allowed=false / NO_ACTIVE_TASK`;
- Lane C: `CLOSED_NO_ACTIVE_IMPLEMENTATION`, no Agent, route, heavy resource or current work surface;
- Lane A: active proposal-only H0 architecture, no executable route/heavy lease;
- Lane B: still held until separately started.

Control Tower validation on the cleanup merge candidate passed:

- Python 3.11: PASS
- Python 3.13: PASS
- 32/32 targeted regressions: PASS
- reconciliation: PASS
- Program Lane contract/dependencies/shared_interfaces: PASS
- Work Claims: PASS
- projection: PASS
- durable authorization witness round trip: PASS
- Codex route witness: `DONE / execution_allowed=false`
- pairwise current claims: A↔B O1 read/read, A↔C O0, B↔C O0
- proposal-only collision blockers: none.

## Harness compatibility

Verified H0 design snapshot:

- repo `deepseek-ai/deepseek-harness`;
- exact SHA `47f943859bef60e4160492346772ded9b24f765a`;
- package family/root `0.1.0-rc.5`;
- MIT;
- Cordis / everything-is-plugin / Service Definition-Provider-Consumer architecture.

Because upstream is a developer preview with expected breaking changes, hard rules remain:

- exact pin;
- Adapter isolation;
- domain code never depends on concrete Harness providers;
- latest upstream is radar/canary only;
- no auto-upgrade;
- rollback and compatibility tests required.

Pinned install/pack/provider/target-environment/rollback smoke remains a **hard P0 at H2**, not an H0 architecture blocker.

## #312 preservation

`COMPATIBLE_WITH_ARCHITECTURAL_REASSIGNMENT`

Preserved:
- four cognitive states;
- ProblemSignature;
- MethodMemory / SkillManifest progressive disclosure;
- discovery beyond topic similarity;
- 0..N / NO_METHOD / NO_SUITABLE_METHOD / ABSTAIN;
- bounded dynamic method composition;
- Effective Challenge;
- independent evidence audit;
- MethodCredit / SkillHealth;
- regression / regime / freshness;
- no one-shot Formal Skill promotion;
- Control Tower and resource gates.

## #308 preservation

`COMPATIBLE_AS_FIRST_DOMAIN_CONSUMER`

Preserved:
- mandatory event coverage;
- PIT anomaly backfill;
- evidence-language contract;
- Data Grade gates;
- H1-H5 competing hypotheses;
- strongest counterargument, negative controls and cross-sectional comparison;
- unresolved/unknown outputs;
- shared W9/W3 feedback;
- `NO_TRADE`.

## Cross-project AI Film direction

AI Film is intentionally modeled as a future **Domain Consumer**, not a permanent silo and not a second Cognitive OS.

Future shared services may include retrieval, DecisionEpisode, method discovery, reflection verification, regression, MethodCredit/SkillHealth, Trace/Handoff, Signal Tower/Control Tower integration and Harness runtime.

AI-film-specific authority remains in its own domain repository: screenplay, character, performance, spatial continuity, shots, cinematography, Seedance/H3/model-specific production knowledge, visual/video evidence and golden cases.

Cross-domain learning may promote only validated transferable abstractions. Domain-specific successful cases do not automatically become global rules.

## Bounded debt after H0

### H1
- compile/implement formal schemas or justified equivalent;
- deterministic semantic invariant validators;
- DecisionEpisode/MissionGraph/Rework state tests;
- Organization Graph validator;
- Trace/Handoff/fingerprint fixtures;
- critical model/state-machine checks.

H1 may not install or bind Harness as product runtime.

### H2
- pinned Harness install/pack/service-signature/provider smoke;
- workflow/subagent/tool/retry/cancel/native trace;
- provider-level Primary/Challenger isolation;
- resource and rollback tests;
- fresh route / Work Claim / O0-O4 / witness.

H2 remains separately blocked.

### Bounded successor interfaces
- R120-W01 context-only endpoint;
- R122 unknown binding;
- FeedbackLifecycle external adapter;
- future AI Film Domain Adapter.

These do not reopen broad W3 unless a real consumer demonstrates a contract defect or proven regression.

## What H0 acceptance means

H0 architecture design is sufficiently frozen for implementation planning.

It does **not** authorize:
- H1 execution automatically;
- any new Codex/QCLAW/WorkBuddy route;
- Harness runtime;
- H2;
- private/live/production access;
- permission changes;
- trading;
- automatic Formal Skill promotion.

The next possible executable step is a separate, fresh **H1 contract-only** route/Work Claim after GPT release and current Control Tower checks.
