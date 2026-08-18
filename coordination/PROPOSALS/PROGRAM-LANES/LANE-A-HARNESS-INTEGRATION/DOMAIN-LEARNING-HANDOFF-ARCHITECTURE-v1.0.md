# Domain Learning Handoff Architecture v1.0

Status: `PROPOSED / NON_EXECUTABLE`

Parent issue: `#375`

Architecture owner: `GPT`

Initial domain: `vxz2datoubo/eustia-ai-film`

## 1. Mission

Connect the Global Signal Tower to domain-owned learning systems without turning the Signal Tower, Harness, or Second Brain into a second domain knowledge authority.

The user-facing target is deliberately simple:

```text
normal work / directing
→ user gives an excellent case, positive/negative verdict, correction, or real-generation feedback
→ universal intake preserves exact provenance
→ learning relevance + materiality are classified
→ a bounded DomainLearningHandoffPacket is routed to the owning domain
→ the domain accepts/rejects/interprets it under its own rules
→ domain-owned learning/eval/regression/writeback occurs when authorized
→ DomainLearningReceipt returns exact evidence
→ future similar work retrieves validated lessons/cases with scope + failure conditions
```

The first real domain is AI Film because it already owns a mature feedback engine, revision-series logic, C-DANCE 2.5 real-generation evidence, route index, maturity states and regression concepts.

## 2. Frozen authority invariants

1. **Signal != Task != Learning Object.** A user feedback event may be useful to a domain without becoming a durable backlog Signal or formal engineering task.
2. **Signal Tower owns intake/routing/materiality, not domain semantics.** It may preserve a user verdict and evidence, but it may not decide that an AI Film lesson is `scene_verified`, `project_verified`, `general_stable`, `needs_revalidation`, `conflicted` or `deprecated`.
3. **Domain truth stays in the domain repository.** AI Film canonical remains in `vxz2datoubo/eustia-ai-film`; Second Brain stores only routing/evidence references and compact cross-domain receipts.
4. **Cross-repo mutation is domain-owned.** R138 proves a bounded capability executed; it is not a domain writer. A future AI Film learning writer/adapter must be owned and governed by AI Film or use a domain-owned PR/workflow boundary.
5. **Learning evidence != outcome truth.** A valid receipt proves the domain processed a handoff under a known contract. It does not prove the inferred lesson is universally correct.
6. **One success never auto-promotes.** New reusable lessons default to candidate unless the domain's own maturity policy says otherwise.
7. **Corrections are append-only relationships.** Omission is not revocation. Refine/supersede/revoke/contradict relationships preserve history and provenance.
8. **Privacy is preserved by reference.** Raw private conversations, media, credentials and secrets never move into public GitHub. Opaque source/asset refs and public-safe summaries are used where needed.

## 3. Intake classes

The global layer may classify the *kind of incoming evidence* without deciding domain conclusions.

Minimum `feedback_kind` values:

- `EXPLICIT_EXCELLENT_CASE`
- `POSITIVE_USER_VERDICT`
- `NEGATIVE_USER_VERDICT`
- `REVISION_DELTA`
- `REAL_GENERATION_EVIDENCE`
- `USER_CORRECTION`
- `STABLE_PREFERENCE_CANDIDATE`
- `SYSTEM_DEFECT_CANDIDATE`
- `CONFLICT_OR_COUNTEREXAMPLE`
- `UNKNOWN_LEARNING_RELEVANCE`

These labels describe the source event, not its eventual domain maturity.

## 4. Persistence and materiality

Every relevant feedback event enters the intake/router path, but not every event becomes a Durable Signal.

### 4.1 Routine domain learning

Examples: “A版构图更好”, “这个动作没踩到窗扇”, “这条广告走秀提示词值得参考”.

Default routing:

`TRACE_ONLY / DOMAIN_WORKFLOW`

The domain may create/update a candidate learning object under its own authority. This avoids polluting the global backlog with thousands of ordinary creative revisions.

### 4.2 Durable learning Signal

Use `DURABLE_SIGNAL` when the event represents a durable desired system effect, e.g.:

- “以后所有优秀案例都应该自动学习并在相似场景召回”;
- a repeated failure reveals a cross-project learning-system defect;
- an unresolved conflict materially changes system behavior;
- a new domain capability/writer/eval infrastructure is required.

### 4.3 Formal task

A formal task is created only after Global Preflight + valid Global Reconciliation + Control Tower release. A feedback event does not become an engineering task merely because it was useful.

## 5. DomainLearningHandoffPacket

A packet is a compact, immutable transfer object. It does not contain a pre-decided AI Film lesson.

Required decision-relevant fields:

- `handoff_id`, `schema_version`, `idempotency_key`
- `source_trace_ref` and optional `source_signal_refs`
- `source_scope`, `source_ref`, `observed_at`
- `domain_id`, `domain_repository`, `domain_source_revision`
- `feedback_kind`, `user_intent`, `user_verdict`
- `work_item_id`, optional `revision_series_id`, `parent_revision`
- `model_or_tool`, `model_version`, `generation_mode`
- `prompt_or_input_evidence_refs`, `result_evidence_refs`, `asset_refs`
- `observed_effects`, `explicit_user_reason`
- `candidate_goal` (what should be learned or checked, not the lesson itself)
- `privacy_class`, `public_safe_summary`
- `confidence_of_source_interpretation`
- `requested_domain_action`: `CLASSIFY_ONLY | LEARNING_CANDIDATE | TARGETED_EVAL | REGRESSION_CANDIDATE | CORRECTION_RECONCILIATION`
- `materiality`, `risk_flags`, `unknowns`
- canonical digest over all trusted fields except self-digest.

Raw chain-of-thought is forbidden. Secrets/credentials are forbidden. Private conversation/media bodies are forbidden in public handoff payloads.

## 6. Domain-side interpretation

The owning domain must resolve the handoff against its own canonical rules.

For AI Film the initial authoritative reads include, at minimum:

- `PROJECT_INDEX.yaml`
- `08_系统学习/反馈反推与系统反哺引擎.md`
- `08_系统学习/C-DANCE2.5真实生成反馈库.md`
- `10_运行时/director_route_index.yaml`
- applicable `read_sets.yaml`, maturity/eval/regression definitions
- current work-item/continuity/character/space files only when the packet requires them.

The domain decides:

- which existing work item/revision/case/lesson the evidence belongs to;
- whether it is duplicate, refine, supersede, contradict, new candidate or not learning-worthy;
- maturity and version-binding;
- target canonical file(s);
- whether a targeted eval/regression is required;
- whether writeback is safe under existing local rules or needs a higher gate.

## 7. DomainLearningReceipt

A receipt is compact evidence, not a copied knowledge object.

Required fields:

- `receipt_id`, `handoff_id`, `handoff_digest`
- `domain_id`, exact domain source revision used
- `processor_capability_id`, `processor_code_identity`
- `decision`: `ACCEPTED | REJECTED | DUPLICATE | NEEDS_MORE_EVIDENCE | CONFLICT | NEEDS_HIGHER_GATE`
- `domain_classification`
- `affected_object_refs`
- `maturity_before`, `maturity_after` when applicable
- `writeback_status`: `NONE | CANDIDATE_RECORDED | DOMAIN_PR_OPENED | DOMAIN_COMMIT_VERIFIED | WAITING_GATE`
- exact write evidence when writeback occurs: repo/ref/commit/path/blob/content digest or governed domain PR identity
- `eval_refs`, `regression_refs`, `counterexample_refs`
- `unknowns`, `limitations`, `needs_revalidation`
- `process_compliance`, separate `outcome_quality`
- cleanup/resource evidence for executable processing
- canonical receipt digest.

The global layer may use this receipt to close or update the source Signal/trace, but it may not rewrite the domain learning object.

## 8. Two-stage domain writer model

To preserve the R138 trust boundary, domain learning writeback is split conceptually:

### Stage A: governed interpretation / dry-run

Read exact domain canonical state, resolve the handoff, produce a proposed learning delta and receipt candidate. No domain mutation.

### Stage B: domain-owned writer

A future separately governed AI Film adapter or domain-owned PR workflow applies only allowed low-risk learning deltas under AI Film's existing rules. It must:

- use exact expected domain head;
- use an explicit target-file/write-route allowlist;
- preserve Fetch → Edit → Commit/PR → Fetch Verify semantics;
- never auto-promote high-impact maturity or change core plot/character identity/topology/default assets without the domain's gate;
- emit exact post-write evidence back into `DomainLearningReceipt`.

Second Brain must never implement Stage B by directly editing arbitrary AI Film files through a generic cross-repo writer.

## 9. Retrieval and future weighting

The learning loop is incomplete unless validated knowledge is later recalled.

Future director retrieval must use structural matching, not raw textual similarity alone. Recommended retrieval keys:

- symptom / route IDs
- task class and ProblemSignature-like features
- scene function, shot scope, action/contact chain, spatial continuity
- model/tool/version and generation mode
- character/role/relationship constraints when relevant
- evidence maturity and health
- applicable/non-applicable contexts
- known failure conditions/counterexamples
- recency/version revalidation state.

Weighting rules:

1. `general_stable/project_verified` can outrank a merely similar candidate when prerequisites match.
2. `scene_verified` should upweight only within its bounded scene/problem family.
3. `candidate` may be suggested as an experiment, never silently treated as a rule.
4. `needs_revalidation/conflicted/deprecated` must be downweighted or blocked according to domain policy.
5. explicit user request to reuse an excellent case may strongly upweight that case for the current task, but still cannot override hard continuity/identity/safety constraints.
6. retrieval must expose *why* a case/lesson matched and its failure boundaries.

## 10. AI Film smoke cases

R139 must design replayable, non-destructive smoke tests using already-known project evidence.

### Smoke A: explicit excellent case

Existing user-approved high-end fashion runway case: black void + glossy black floor + hard key/secondary hard light + model walking toward camera while camera retreats + bold yellow 3D typography.

Expected dry-run result:

- classify input as `EXPLICIT_EXCELLENT_CASE`;
- find/route to the existing excellent-case/feedback learning area rather than duplicating a second global copy;
- return candidate/reuse metadata and future retrieval keys;
- no automatic universal promotion.

### Smoke B: C-DANCE 2.5 real feedback

Existing `CD25-KAIM-WINDOW-AB-20260815` evidence.

Expected dry-run result:

- preserve actual A/B prompts/result refs/user verdict;
- preserve confounding where the camera design was not truly controlled;
- route observed failures such as event order/contact binding/observable-knowledge/environment response to the existing real-generation evidence layer;
- avoid claiming SOAC superiority from a confounded comparison;
- produce targeted eval/regression candidates instead of a fake stable rule.

## 11. Idempotency and correction

`idempotency_key` must bind at least domain + source evidence identity + work item/revision + feedback semantics.

Rules:

- exact replay → `DUPLICATE`, no second learning object;
- same source with corrected user verdict → append correction/refinement relationship;
- stale domain revision → re-resolve or fail closed, never apply a precomputed delta blindly;
- conflicting evidence → preserve both sides and mark conflict/needs evaluation;
- packet omission never revokes prior domain knowledge.

## 12. Threat and false-green model

Block or flag:

- Signal Tower inventing a lesson not stated by user/evidence;
- a self-reported “learned” status without exact domain receipt;
- one executable success being relabeled as proof unrelated scans ran;
- second copy of AI Film knowledge stored in Second Brain;
- hidden promotion of a candidate after one positive verdict;
- stale model-version experience treated as current without revalidation;
- private raw conversation/media copied into public GitHub;
- duplicate/replayed packets creating duplicate learning objects;
- Stage A dry-run being misreported as Stage B writeback;
- domain writer exceeding exact target routes.

## 13. Resource policy

- single-worker default;
- no nested pools;
- one active Codex route / one local heavy stage;
- bounded outputs and timeouts;
- task-owned temp/process/cache only;
- no global Python/Docker kill;
- remote CI preferred for broad matrices;
- routine feedback intake should remain lightweight and not spawn engineering jobs unless materiality requires them.

## 14. Acceptance requirements for a future R139 implementation

At least these semantic scenarios must be tested:

1. explicit excellent case → correct AI Film handoff;
2. positive and negative verdicts remain distinguishable;
3. real-generation evidence preserves model/version/result refs;
4. routine feedback does not create a Durable Signal/formal task by default;
5. material system-learning request does create/associate a Durable Signal;
6. exact duplicate is suppressed;
7. user correction creates append-only correction relation;
8. stale domain head fails closed/re-resolves;
9. unknown domain capability remains UNKNOWN, not PASS;
10. Stage A dry-run cannot claim writeback;
11. Second Brain contains no duplicated AI Film lesson body;
12. AI Film domain classification/maturity remains domain-owned;
13. one success cannot auto-promote;
14. confounded A/B remains inconclusive;
15. receipt binds exact processor/domain revision;
16. private raw body cannot enter public handoff;
17. future retrieval returns applicability/failure conditions;
18. model-version `needs_revalidation` suppresses stale high weighting;
19. unrelated cognitive scan cannot be satisfied by a learning-ingestor proof;
20. any future Stage B writer must be separately authorized and domain-owned.

## 15. Implementation sequence

Recommended gated sequence:

1. **R139-A architecture/contract canonicalization**: this document + machine contract + threat model; no execution route.
2. **R139-B non-executable reservation** after fresh Global Reconciliation.
3. **R139-C Second Brain handoff/dry-run implementation**: packet/receipt schemas, router integration, replay/idempotency, read-only AI Film smoke; no AI Film write.
4. **AI Film domain-owned adapter stage** (separate gate/repository): implement a minimal domain learning processor/writer under AI Film's own governance.
5. **Cross-repo end-to-end smoke**: exact feedback → handoff → domain receipt → verified candidate writeback → future director retrieval.
6. **Promotion only after real repeated use**; production/private bridge remains separately gated.

This sequence preserves the user's desired automation while keeping authority boundaries mechanically visible and reversible.