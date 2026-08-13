# CLTM-0021 Memory Palace v1: Manual Capture + Temporal Conflict Reasoning

## 1. Owner goal

The owner wants a simple conversational write trigger: `采集记忆` (historical alias `数据采集` remains accepted). When the owner uses the trigger, the useful user content in the immediately relevant conversation context should become durable candidate memory, be provably retrievable later, preserve raw evidence and time semantics, and support temporal/constraint conflict discovery across old and new memories.

The primary success criterion is not merely storage. The system must be able to retrieve a relevant old memory later through lexical/semantic/time/graph cues and reason over derived absolute dates, including relative expressions such as `明天`.

The owner additionally requires every atomic memory to have a temporal lifecycle. Old memories must remain historically recoverable, but their current decision weight must decline or be removed when they become stale, superseded, revoked, contradicted, or no longer applicable. This is especially important for market/trading memories where observations can age rapidly.

Owner evaluations are first-class memories. Statements such as `这个东西很好/不好`, `我觉得这个事件是假的`, `我觉得这个来源有偏见`, `我不信这个观点`, or `我现在更认可这个方法` must be stored as time-bound, source-backed owner stances linked to their target objects. They must never be silently converted into objective facts.

Example acceptance story:
- on 2026-08-14 Asia/Shanghai the owner says: `明天我要去睡大觉。采集记忆`
- the source utterance must remain preserved as evidence
- `明天` must be normalized relative to the utterance time/date to 2026-08-15, without rewriting the historical utterance
- if an earlier memory says that 2026-08-15 has a group exercise/activity, retrieval must surface both memories
- the system must not automatically assert a hard contradiction merely because the calendar date is the same; if time ranges or exclusivity are unknown, classify it as a potential schedule/commitment conflict and expose the missing information
- if overlap/exclusivity is known, a hard conflict may be emitted
- the assistant should explain the conflict and evidence, not silently overwrite either memory.

## 2. Architectural principle

Use a write-manage-read memory loop:

`Conversation evidence -> manual capture -> temporal/event/stance normalization -> candidate atoms -> relations/conflicts/unknowns -> W3 MemoryStore -> hybrid retrieval -> temporal/constraint/stance reasoning -> MemoryContextBundle -> assistant`

Raw evidence and current interpretation are separate. Historical episodes are append-only evidence; normalized events, evaluations, and current memory state are derived objects. Corrections use supersession and never rewrite old episodes.

GitHub/private durable storage is the long-term archive and provenance authority. The retrieval index may be local/rebuildable. GPT is the reasoning layer: Memory Palace retrieves evidence and structured clues; GPT performs the final contextual reasoning.

## 3. Capture semantics

### 3.1 Trigger contract

Accepted owner triggers:
- `采集记忆`
- `数据采集`

Deterministic default scope:
1. If the trigger appears inside a substantive owner message, capture the owner-authored semantic content of that message excluding the trigger phrase.
2. If the message is trigger-only, capture the immediately preceding substantive owner message.
3. Assistant text may be referenced only as contextual evidence/analysis; assistant text cannot become owner memory.
4. If one source message contains multiple durable claims/events/plans/preferences/corrections/evaluations, atomize them into separate candidate memories while preserving one shared source episode lineage.
5. Secret credentials, tokens, private keys and explicit SECRET_CREDENTIAL content fail closed.

### 3.2 Memory classes needed for v1

Keep existing roles and extend the semantic layer, not raw evidence:
- USER_ASSERTION
- USER_PREFERENCE
- USER_DECISION
- USER_CORRECTION
- USER_PLAN (new derived semantic type)
- USER_GOAL (new derived semantic type)
- USER_COMMITMENT (new derived semantic type)
- USER_EVENT_REPORT (new derived semantic type)
- USER_EVALUATION (new derived semantic type)
- USER_CREDIBILITY_JUDGMENT (new derived semantic type)
- USER_BIAS_JUDGMENT (new derived semantic type)

All automatic interpretation remains candidate authority unless separately promoted.

## 4. Temporal model

Every temporal memory must preserve both the linguistic expression and normalized interpretation.

Minimum fields:
- `recorded_at`: when the user said it, timezone-aware
- `recorded_timezone`: source timezone/assumption used for normalization
- `original_time_expression`: e.g. `明天`
- `anchor_time`: utterance time used to resolve the expression
- `resolved_start`
- `resolved_end` if known
- `resolution_granularity`: instant|hour|day|range|unknown
- `resolution_method`: deterministic_rule|model_assisted|user_explicit|unknown
- `temporal_confidence`
- existing bitemporal `valid_from`, `valid_to`, `recorded_at/updated_at`

Relative-time normalization must be deterministic when possible. `明天` on 2026-08-14 Asia/Shanghai resolves to calendar date 2026-08-15 Asia/Shanghai. The normalized value is derived metadata, never a replacement for raw utterance evidence.

Represent event-to-event relations with a small interoperable vocabulary inspired by ISO-TimeML / interval reasoning:
- BEFORE
- AFTER
- OVERLAPS
- SIMULTANEOUS
- CONTAINS
- DURING
- SAME_DAY
- UNKNOWN_TEMPORAL_RELATION

## 5. Temporal lifecycle and current decision value

Time affects at least three different things and they must not be collapsed into one timestamp:

1. **Evidence time**: when the statement/event was recorded (`recorded_at`).
2. **Validity time**: when the proposition/plan/evaluation applies (`valid_from`, `valid_to`).
3. **Freshness/revalidation time**: whether the memory should still influence a current answer (`last_verified_at`, `freshness_profile`, `revalidation_required`).

### 5.1 Lifecycle states

Use existing truth/lifecycle states where possible and preserve historical accessibility:
- `candidate`: currently usable candidate memory
- `approved`: higher-authority memory when separately approved
- `conflict`: unresolved competing evidence/interpretation
- `superseded`: replaced for CURRENT use but still historically retrievable
- `stale`: not sufficiently fresh for current use without revalidation
- `revoked`: explicitly invalidated/withdrawn
- `unknown`: unresolved knowledge gap

Do not delete old memory merely because it aged. Aging changes retrieval/ranking/admission, not historical evidence.

### 5.2 Freshness profile

Each memory atom/event/evaluation may carry:
- `freshness_class`: TRANSIENT | SHORT_CYCLE | MEDIUM_CYCLE | STRUCTURAL | UNKNOWN
- `last_verified_at`
- `revalidation_required`: true/false
- `revalidation_reason`
- `decay_policy_id`
- `freshness_score` as a derived runtime value, never permanent objective truth

No universal fixed half-life is allowed. Freshness policy is domain- and memory-type-specific and must be validated before becoming a formal rule.

Examples:
- intraday price/flow/market-rumor observation: often TRANSIENT or SHORT_CYCLE
- quarterly company operating fact: MEDIUM_CYCLE
- a user's stable learning preference: STRUCTURAL unless corrected
- historical event evidence: may be permanently historically valid even when low current-action relevance.

### 5.3 Market/trading memory rule

For market/trading use, retrieval must separate:
- `historical_similarity`: this happened before
- `current_validity`: the old fact still applies now
- `current_relevance`: it may matter to the present setup
- `revalidation_status`: current data confirms/weakens/refutes it

An old bullish clue must never receive current decision weight merely because it is semantically similar to today's stock. Current price, business state, policy, market regime and new evidence can make it stale or superseded.

A retrieval scorer may use time decay as one factor, but must not mechanically suppress durable structural knowledge or promote fresh low-quality evidence above verified structural memory. Current validity, evidence quality, domain horizon and explicit supersession/revocation dominate naive recency.

### 5.4 Memory evolution chain

Support append-preserving relations such as:
- UPDATES
- REFINES
- SUPERSEDES
- CORRECTION
- REVOKES
- CONFIRMS
- WEAKENS
- CONTRADICTS
- REVALIDATES
- RESOLVES_UNKNOWN

For CURRENT answers, retrieve the current lineage head plus relevant predecessor context when needed. For HISTORICAL questions, reconstruct the state valid at the requested time.

## 6. Owner evaluation / stance memory

Owner judgments are first-class, queryable, time-bound memory objects linked to the evaluated target.

A normalized stance record should include:
- `stance_id`
- `holder = owner`
- `target_type`: EVENT | CLAIM | SOURCE | PERSON | COMPANY | PRODUCT | METHOD | STRATEGY | ARTICLE | MODEL_OUTPUT | OTHER
- `target_id` or stable target reference
- `target_label`
- `evaluation_type`: QUALITY | LIKE_DISLIKE | GOOD_BAD | TRUST | CREDIBILITY | AUTHENTICITY | BIAS | RISK | USEFULNESS | ACCURACY | PREFERENCE | OTHER
- `stance`: POSITIVE | NEGATIVE | MIXED | SKEPTICAL | SUPPORTS | OPPOSES | BELIEVES_TRUE | BELIEVES_FALSE | BIASED | UNBIASED | UNKNOWN
- `strength`: optional bounded value/category
- `confidence`
- `basis`: explicit evidence/reason if stated, otherwise UNKNOWN
- `recorded_at`
- `valid_from`, `valid_to`
- `freshness_profile`
- `source_episode_ids`
- `superseded_by` / relation lineage

### 6.1 Epistemic separation rule

The following are different memories and must never be collapsed:

- Objective claim candidate: `事件 X 是假的`
- Owner stance: `用户认为事件 X 是假的`
- Source-quality judgment: `用户认为来源 Y 有偏见`

Unless independently verified, an owner disbelief judgment must not turn the target claim into a false fact. The memory system should preserve both the target proposition and the owner's stance toward it.

### 6.2 Evaluation relations

Use explicit graph relations such as:
- EVALUATES
- APPROVES
- DISAPPROVES
- TRUSTS
- DISTRUSTS
- BELIEVES
- DISBELIEVES
- FLAGS_BIAS
- QUESTIONS_CREDIBILITY
- PREFERS_OVER

Later changes in owner opinion are new stance events linked with UPDATES/REFINES/SUPERSEDES; never rewrite the earlier stance.

### 6.3 Retrieval behavior for evaluations

When a retrieved target has an owner stance, the MemoryContextBundle should expose it separately:
- target fact/event
- owner's historical/current evaluation
- evaluation time
- evaluation confidence/basis
- whether a newer evaluation supersedes it

Example assistant reasoning input:

`Event/source X is currently relevant. Owner evaluated X as low credibility on 2026-06-01 because of reason R. A later 2026-07-20 stance upgraded credibility after evidence E. Current stance lineage head = 2026-07-20.`

GPT may use this as personalized reasoning context but should still distinguish user preference/judgment from independently verified truth.

## 7. Event and constraint model

A memory such as `明天我要去睡大觉` should create a candidate event/plan object with:
- actor/entity
- action/activity
- target date/range
- location if stated
- participants if stated
- commitment strength: idea|plan|commitment|fact
- flexibility: fixed|flexible|unknown
- exclusivity/resource constraints if known
- provenance atom ids
- temporal lifecycle/freshness profile where relevant

Conflict detection must be conservative and typed:

### 7.1 Conflict classes
- `DIRECT_FACT_CONTRADICTION`: propositions cannot both be true for the same scope/time
- `SCHEDULE_HARD_CONFLICT`: known overlapping intervals or mutually exclusive commitments
- `SCHEDULE_POTENTIAL_CONFLICT`: same/overlapping date plus insufficient time/flexibility information
- `PREFERENCE_TENSION`: preferences point in incompatible directions but may coexist contextually
- `PLAN_SUPERSESSION_CANDIDATE`: newer user plan appears to replace an older plan but explicit correction is absent
- `STANCE_CONFLICT`: owner evaluations of the same target differ materially across time/context
- `SOURCE_CREDIBILITY_CONFLICT`: competing source credibility judgments/evidence
- `UNKNOWN_CONSTRAINT`: evidence suggests a decision-relevant gap

Conflict records must include both atom IDs, derived event/stance IDs, conflict type, evidence, confidence, unresolved/resolved status, and missing fields needed to resolve it.

No silent merge and no silent overwrite.

## 8. Retrieval / Memory Palace design

Current lexical retrieval is useful but insufficient. v1 retrieval becomes a hybrid orchestrator with four independent evidence channels:

1. **Lexical**: Chinese/English token/trigram/BM25 style term retrieval.
2. **Semantic**: embedding similarity over candidate statements/event/stance summaries when an approved embedding provider is available. Semantic search is additive, never the sole source of truth.
3. **Temporal**: exact/nearby date and interval retrieval. Query expansion turns `明天` into an absolute time window before retrieval; lifecycle/freshness is separately evaluated.
4. **Graph**: relation expansion over entities, events, stances, conflicts, supersessions and provenance.

Ranking must preserve source channel scores and then apply deterministic boosts/penalties for:
- exact date overlap
- same actor/entity/target
- same project/scope
- explicit conflict edge
- correction/supersession relevance
- current validity
- freshness profile and revalidation status
- owner stance relevance
- evidence quality

The result is a compact `MemoryContextBundle` containing:
- admitted atoms
- normalized events
- owner stances/evaluations
- time relations
- lifecycle/freshness status
- conflicts
- unknowns
- provenance
- why each item was retrieved
- current-vs-historical status
- confidence and abstention gate.

## 9. Query behavior

### 9.1 Keyword recall
A query such as `睡觉`, `群运动`, `8月15日`, `我以前为什么不信这个消息`, `我当时怎么看这家公司`, or related semantic wording should be able to retrieve the relevant captured memory under the correct user/project scope.

### 9.2 Temporal query expansion
A current utterance with `明天/后天/下周三/月底` must first resolve the expression against the current/utterance time and timezone, then search the resolved date window plus a bounded neighbor window when appropriate.

### 9.3 Multi-hop retrieval
If the current message says `明天我要去睡大觉`, retrieval may proceed:
`明天 -> 2026-08-15 -> events on 2026-08-15 -> prior group exercise plan -> constraint comparison`.

If the current message asks `这个消息可靠吗`, retrieval may proceed:
`消息/来源 -> owner prior credibility judgments -> newer superseding stance -> related evidence/conflicts -> current retrieval bundle`.

The final assistant response should distinguish:
- confirmed fact
- derived temporal fact
- owner evaluation/stance
- current vs historical stance
- stale/superseded evidence
- potential conflict
- unknown/missing detail
- suggested clarification/action.

## 10. Four-layer knowledge mapping skill

For every important owner topic, the Memory Palace should maintain an explicit cognitive coverage map:

### A. `KNOWN_SAID`
Things the owner demonstrably knows and has explicitly said. Source-backed and retrievable.

### B. `KNOWN_UNSAID_INFERRED`
High-probability knowledge/constraints inferred from repeated behavior or context, but not explicitly stated. Must remain clearly labeled inference and never be treated as direct owner assertion.

### C. `UNKNOWN_BUT_ACCESSIBLE`
Concepts the owner has not demonstrated but can likely understand with a short bridge. Retrieval/teaching should connect these to known concepts.

### D. `UNKNOWN_REQUIRES_SCAFFOLDING`
Concepts requiring prerequisite layers, examples, analogy, progressive explanation or tooling. The system should store the prerequisite graph and teaching path, not merely label the owner as not knowing something.

This map is topic-specific, time-versioned and evidence-backed. It must never become a global judgment of the person.

## 11. Research-derived design links

The design intentionally incorporates ideas from:
- MemGPT: hierarchical/virtual context and explicit memory management for multi-session chat.
- Generative Agents: complete experience record + reflection + dynamic retrieval for planning.
- LongMemEval: information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention; session decomposition and time-aware query expansion.
- LoCoMo: very long-horizon temporal/causal conversational evaluation.
- HippoRAG: graph-mediated associative retrieval / multi-hop recall.
- Zep/Graphiti: temporally aware knowledge graphs that preserve historical relationships.
- APEX-MEM (ACL 2026): append-only event memory + property graph + retrieval-time conflict/evolution resolution.
- SUTime / ISO-TimeML: explicit temporal-expression normalization and event/time relation representation.
- structured temporal-relation extraction literature: globally consistent event temporal graphs and conflict correction.
- HaluMem: evaluate extraction, update and QA separately because memory hallucinations can accumulate upstream.

These are design inspirations, not authority overrides. Local acceptance tests remain the promotion gate.

## 12. Storage strategy

Phase 1 remains SQLite/W3 because the accepted runtime already exists. Extend it additively with:
- normalized event table or event metadata
- temporal-expression records
- temporal lifecycle/freshness metadata
- owner stance/evaluation records
- conflict/constraint records
- retrieval explanation records/tests
- FTS5/trigram option for improved lexical retrieval if migration tests prove safe

Do not jump to Neo4j/Postgres/vector DB solely because papers use graphs. Keep the logical graph contract independent of physical storage. Migrate only after benchmark evidence shows a need.

## 13. Manual capture receipt

A successful `采集记忆` operation must return a user-visible concise receipt containing only safe facts:
- capture status
- number of atoms/events/evaluations persisted
- normalized date/time if any
- exact-recall proof = PASS/FAIL
- detected conflicts count/type
- stale/supersession actions created, if any
- whether clarification/revalidation is needed
- candidate/formal authority state

Example:

`记忆采集成功：1 条计划记忆；“明天”已解析为 2026-08-15；精确召回 PASS；发现 1 个潜在日程冲突（同日已有群运动，具体时间未知）；已存为 candidate，未覆盖旧记忆。`

Evaluation example:

`记忆采集成功：1 条来源可信度评价；你认为“来源 X 有偏见”，记录时间 2026-08-13；该判断保存为 owner stance，不等同于“来源 X 客观上有偏见”；精确召回 PASS。`

The receipt must never claim success unless durable write + post-write retrieval verification actually pass.

## 14. Retrieval-before-answer contract

When a current user turn has a material possibility of being affected by prior memory, query Memory Palace before answering. Do not retrieve everything. Build a bounded query plan from:
- entities/targets
- user intent
- time expressions
- topic keywords
- active project/scope
- current/target time
- relation depth and budget
- memory lifecycle/freshness
- relevant owner stance/evaluation types.

The trust gate may return `ABSTAIN` when nothing reliable is found or when all retrieved market-sensitive evidence is stale and unvalidated.

## 15. Required synthetic acceptance tests

1. trigger-in-message capture
2. trigger-only captures previous owner message
3. multiple atoms from one message while preserving one episode lineage
4. assistant content never becomes user assertion
5. secret credential fail-closed
6. duplicate trigger/replay idempotency
7. keyword Chinese retrieval after capture
8. semantic paraphrase retrieval when semantic provider enabled
9. `2026-08-14 + 明天 -> 2026-08-15 Asia/Shanghai`
10. exact date retrieval of prior 2026-08-15 event
11. same-day unknown-time pair -> `SCHEDULE_POTENTIAL_CONFLICT`, not hard conflict
12. overlapping fixed intervals -> `SCHEDULE_HARD_CONFLICT`
13. non-overlapping same-day intervals -> no hard conflict
14. later explicit correction -> append-preserving supersession
15. CURRENT retrieval excludes superseded atom while HISTORICAL can retrieve it at valid time
16. conflict remains linked to both evidence sources
17. post-write exact scoped recall PASS required before success receipt
18. retrieval explanation identifies lexical/temporal/graph channels
19. cognitive coverage map supports all four states and never promotes inference to explicit assertion
20. restart/persistence test proves captured memory survives process restart
21. owner negative/positive evaluation is stored as stance linked to target, not objective fact
22. `我觉得事件X是假的` produces owner BELIEVES_FALSE/DISBELIEVES stance without marking event X objectively false
23. `我觉得来源Y有偏见` produces BIAS/CREDIBILITY stance linked to source Y
24. later opposite evaluation creates a new stance and supersession/update chain without deleting the old stance
25. CURRENT stance retrieval returns the newest valid lineage head; HISTORICAL retrieval can reconstruct prior stance
26. stale market clue remains historically retrievable but is down-ranked/fail-gated for current trading use until revalidated
27. superseded/revoked market clue cannot re-enter CURRENT decision context solely through semantic similarity
28. structural durable memory is not blindly suppressed merely for being old
29. retrieval explanation exposes freshness/current-validity reason for admitting/down-ranking/abstaining
30. full relevant Phase-3 regression suite PASS
31. public_safety_scan PASS
32. git diff --check PASS

## 16. Phase boundaries

### Phase A, epoch 107 implementation target
Synthetic-only implementation of:
- capture contract
- temporal normalization
- temporal lifecycle/freshness contract
- event representation
- owner stance/evaluation representation
- conservative conflict detection
- hybrid lexical + temporal + graph retrieval and retrieval explanations
- four-state cognitive coverage mapping contract
- acceptance tests above

No real private capture is authorized in Phase A.

### Phase B, later owner-approved/live route
Connect the manual phrase `采集记忆` from a conversational surface to a write-capable memory tool/bridge and prove one real private capture + later retrieval. Preferred integration is a narrowly scoped MCP/app tool set such as:
- `memory.capture`
- `memory.search`
- `memory.recall_context`
- `memory.conflicts`

If the ChatGPT plan/surface does not support write-capable custom MCP actions, use a local companion/approved bridge rather than weakening privacy or publishing raw memory to the public coordination repository.

## 17. Security and authority

- Raw/private semantic content never goes to the public coordination repository.
- GitHub public repo may contain code, schemas, synthetic tests and aggregate receipts only.
- Credentials/tokens/API keys/private keys are never memory content and never committed.
- Candidate memory does not automatically become formal PROJECT/GLOBAL memory.
- Conflict detection proposes; it does not silently cancel plans or rewrite facts.
- Owner evaluations remain owner stances unless independently verified as facts.
- Staleness/decay changes current decision relevance; it never destroys historical evidence.
- High-risk actions remain owner-approved.
