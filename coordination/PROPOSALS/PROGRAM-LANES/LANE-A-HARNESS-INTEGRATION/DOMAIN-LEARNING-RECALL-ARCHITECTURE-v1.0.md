# Domain Learning Recall Architecture v1.0

## Mission

R140 builds the read-only consumption half of the learning loop after R139 Stage-A handoff: a directing/problem context becomes a structured recall request, verified domain-owned learning objects are read at an exact domain revision, applicability and failure conditions are evaluated, and a bounded recall bundle/receipt is returned for downstream directing use.

This is a **Mission-sized vertical slice**, not a semantic search helper. It must complete request → authority resolution → structural matching → applicability/revalidation gating → evidence-bound bundle → real read-only replay → exact-head CI in one Codex task.

## Authority split

- **Signal Tower / Second Brain owns:** request provenance, query normalization, retrieval orchestration, exact-read evidence, ranking mechanics, abstention logic, trace/receipt identity.
- **AI Film owns:** canonical lesson/case bodies, maturity, applicability metadata, failure conditions, counterexamples, deprecation/conflict state, model/version compatibility and write routes.
- **Control Tower owns:** task release, write allowlist, lease, execution and merge gates.

Second Brain MUST NOT infer or overwrite missing AI Film authority fields as domain truth.

## Core contracts

### DomainLearningRecallRequest

Carries request_id, source_trace_ref, task/context identity, problem/symptom signatures, scene/work-item attributes, model/tool/version, constraints, requested evidence classes, target domain/revision, privacy class and budget.

### DomainLearningRecallBundle

Immutable evidence-bound result containing exact domain revision, matched canonical object refs, match dimensions, applicability state, failure-condition/counterexample hits, maturity/revalidation observations, bounded ranking evidence, abstentions/unknowns and exact read proofs. It contains refs/public-safe summaries, not a duplicate canonical lesson body.

### DomainLearningRecallReceipt

Records provider code identity, request/bundle digests, exact reads, result class (`RECALLED`, `ABSTAINED`, `NEEDS_REVALIDATION`, `CONFLICTED`, `UNSUPPORTED`), process compliance and limitations. Process compliance is not outcome truth.

## Retrieval policy

Ranking MUST be multi-axis and evidence constrained. Text similarity alone cannot establish applicability. At minimum evaluate:

1. problem/symptom signature;
2. scene/work-item class;
3. model/tool/version compatibility;
4. explicit constraints and production context;
5. domain maturity/state;
6. applicability and non-applicability declarations;
7. failure conditions and counterexamples;
8. needs_revalidation/conflicted/deprecated state;
9. provenance/evidence availability.

A strong semantic match with failed applicability gates must be downgraded or rejected.

## Required real replays

1. `AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY`: query for high-end fashion runway / black void / hard dual light / 3D typography. Resolve the domain-owned excellent case and preserve its bounded/prompt-only maturity semantics. No universal promotion.
2. `CD25-KAIM-WINDOW-AB-20260815`: query for the corresponding C-DANCE real-generation problem. Recall the canonical feedback while preserving `candidate` and `confounded_inconclusive`; never manufacture SOAC superiority.
3. Negative replay: a deliberately incompatible model/version or failure condition must abstain / mark `NEEDS_REVALIDATION`, demonstrating that nearest-text is not enough.

AI Film exact reference for R140 architecture: `44c383afd2207a97caf45b1b0da6ee1dece43a76`. It is read-only and must be rechecked before activation.

## M0→M6

- M0 fresh route/claim/lane/domain revision and authority scan.
- M1 request/bundle/receipt schemas and canonical digests.
- M2 structural retrieval + applicability/revalidation/abstention integration.
- M3 adversarial and retained regressions, including false-green tests.
- M4 three real/negative read-only replays with zero mutation.
- M5 exact-head Python 3.11/3.13 CI plus R136-R139 retained regressions/public-safety.
- M6 evidence, cleanup, rollback and completion signal.

## Hard locks

No AI Film/domain canonical write; no domain maturity decision; no lesson-body duplication; no Formal Skill promotion; no private raw body/media or secrets; no generic cross-repo writer; no production/permission/Harness/H2/H7/history rewrite/trading; no Codex merge authority.

## Completion

`R140_DOMAIN_LEARNING_RECALL_LOOP_READY_FOR_GPT_REVIEW`
