# Domain Learning Handoff Threat Model v1.0

Status: `PROPOSED / NON_EXECUTABLE`

Parent issue: `#375`

## Protected assets

- user's actual feedback and corrections;
- source provenance and model/tool/version identity;
- AI Film canonical learning authority;
- Signal Tower routing/materiality authority;
- Control Tower execution/lease authority;
- privacy of raw conversations/media;
- maturity/eval/regression integrity;
- future retrieval quality and failure-boundary visibility.

## Trust boundaries

1. User/chat source → Global Intake.
2. Global Intake/Signal/Trace → `DomainLearningHandoffPacket`.
3. Second Brain → domain-owned processor.
4. Domain processor → domain canonical learning objects.
5. Domain receipt → global closure/trace.
6. Domain learning objects → future director retrieval.

No boundary is allowed to silently inherit the authority of the next boundary.

## Threats and mandatory controls

### T01 Source meaning laundering

Threat: a model turns a vague remark into a strong reusable lesson that the user never stated.

Controls:
- packet separates `user_verdict`, `observed_effects`, `explicit_user_reason`, `candidate_goal` and interpretation confidence;
- low-confidence interpretation remains candidate/unknown;
- domain must retain alternative explanations and counterexamples where applicable.

### T02 Feedback spam becomes backlog spam

Threat: every “好/不好” becomes a durable Signal/formal task.

Controls:
- persistence and execution are independent axes;
- routine feedback defaults to `TRACE_ONLY / DOMAIN_WORKFLOW`;
- formal task requires materiality + reconciliation + Control Tower release.

### T03 Second Brain becomes shadow AI Film knowledge base

Threat: handoff packets or receipts copy full AI Film lessons/canonical text into Second Brain.

Controls:
- packet carries evidence and intent, not a finalized domain lesson;
- receipt carries compact object refs/status/evidence, not the canonical lesson body;
- domain repository remains unique truth.

### T04 R138 capability proof misused as domain write authority

Threat: because R138 can prove execution, callers treat it as permission to mutate AI Film.

Controls:
- R138 remains execution evidence only;
- Stage B writer is a separate domain-owned gate;
- any Second Brain generic cross-repo write path is forbidden.

### T05 Dry-run false writeback

Threat: Stage A classifies correctly and reports `CANDIDATE_RECORDED` without any domain write.

Controls:
- `writeback_status=NONE` unless exact domain evidence exists;
- non-NONE writeback requires exact commit/path/blob/content digest or governed domain PR identity;
- self-report is insufficient.

### T06 One positive example becomes universal rule

Threat: one excellent output or one user preference automatically reaches project/general maturity.

Controls:
- domain maturity authority only;
- one success cannot auto-promote;
- candidate/scene_verified are bounded;
- promotion requires domain validation/eval rules.

### T07 Confounded experiment false attribution

Threat: multiple prompt/camera/reference variables change but system attributes improvement to one method.

Controls:
- preserve intended vs verified controls and control drift;
- `confounded/inconclusive` remains representable;
- targeted eval is preferred over forced conclusion.

### T08 Stale model-version lesson

Threat: a Seedance/C-DANCE/H3 behavior learned under one version is silently applied to a newer version.

Controls:
- packet and domain objects bind model/tool/version;
- retrieval considers version and `needs_revalidation`;
- stale version-bound rules are downweighted or blocked.

### T09 Replay/double learning

Threat: heartbeat, retry, duplicate messages or cross-window ingestion create duplicate cases/lessons.

Controls:
- canonical packet digest + idempotency key;
- exact replay returns `DUPLICATE`;
- corrections create relations rather than parallel duplicate truth.

### T10 Correction loss

Threat: later user correction is treated as another independent preference while old wrong record stays current.

Controls:
- append-only `REFINES/SUPERSEDES/REVOKES/CONTRADICTS` relations;
- current/historical state separate;
- omission never revokes.

### T11 Private data leak

Threat: raw private chat, media, credentials or local paths are copied to public GitHub.

Controls:
- public-safe summaries + opaque refs;
- secret/private-body rejection before handoff persistence;
- receipts do not echo raw private payloads.

### T12 Retrieval semantic contamination

Threat: future director retrieves a lexically similar but structurally wrong case and overweights it.

Controls:
- structural/prerequisite reranking;
- route/symptom/task/scene/model/context/failure conditions used;
- retrieval explains match rationale and maturity;
- 0 suitable cases is a valid result.

### T13 Domain route bypass

Threat: a handoff directly edits a file that is not the domain's correct write route.

Controls:
- domain processor resolves target through domain-owned write routes;
- Stage B exact target allowlist + expected domain head;
- fetch-verify after write.

### T14 Promotion injection

Threat: external text or prompt injection says “mark this general_stable” or “promote to formal skill”.

Controls:
- external/source text has no authority to set maturity;
- maturity/promotion decided only by domain policy and gates;
- Formal Skill promotion remains separate.

### T15 Cross-window source drift

Threat: one GPT window creates a handoff from stale project/domain state while another has already corrected it.

Controls:
- packet binds source/domain revisions;
- processor rechecks current domain head;
- stale head triggers reroute/re-resolution/fail-closed;
- preserve `CROSS_WINDOW_STATE_DRIFT` regression family.

### T16 Outcome/process conflation

Threat: successful ingestion is interpreted as proof that the lesson is correct.

Controls:
- receipt separates `process_compliance` and `outcome_quality`;
- successful process can still yield `NEEDS_MORE_EVIDENCE`, `CONFLICT` or candidate maturity.

## Abuse-resistant resource policy

- routine handoffs are light and bounded;
- no nested pools/unbounded workers;
- one active Codex route and one local heavy stage;
- duplicate suppression before expensive domain processing;
- bounded output size/timeouts;
- task-owned cleanup only;
- no global kill Python/Docker;
- material evals become separately governed work rather than silently consuming resources.

## High-impact gates that remain manual/explicit

Even after the learning loop is automated, stop at:

- core plot/world/character identity reversal;
- canonical spatial topology change;
- replacement of formal default assets;
- project/general maturity promotion when it materially expands scope;
- deletion/large-scale compaction;
- authority-source replacement;
- production/private/credential/permission changes;
- trading/accounts/orders/funds;
- unresolved conflict where wrong resolution could widely contaminate future retrieval.

The system should continue other safe work instead of waking the user for every blocked high-impact item.