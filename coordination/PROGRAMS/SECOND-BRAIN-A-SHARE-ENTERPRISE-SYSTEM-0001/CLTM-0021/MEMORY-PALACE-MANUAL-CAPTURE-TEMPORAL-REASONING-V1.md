# CLTM-0021 Memory Palace v1: Manual Capture + Temporal Conflict Reasoning

## 1. Owner goal

The owner wants a simple conversational write trigger: `采集记忆` (historical alias `数据采集` remains accepted). When the owner uses the trigger, the useful user content in the immediately relevant conversation context should become durable candidate memory, be provably retrievable later, preserve raw evidence and time semantics, and support temporal/constraint conflict discovery across old and new memories.

The primary success criterion is not merely storage. The system must be able to retrieve a relevant old memory later through lexical/semantic/time/graph cues and reason over derived absolute dates, including relative expressions such as `明天`.

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

`Conversation evidence -> manual capture -> temporal/event normalization -> candidate atoms -> conflict/unknown edges -> W3 MemoryStore -> hybrid retrieval -> temporal/constraint reasoning -> MemoryContextBundle -> assistant`

Raw evidence and current interpretation are separate. Historical episodes are append-only evidence; normalized events and current memory state are derived objects. Corrections use supersession and never rewrite old episodes.

## 3. Capture semantics

### 3.1 Trigger contract

Accepted owner triggers:
- `采集记忆`
- `数据采集`

Deterministic default scope:
1. If the trigger appears inside a substantive owner message, capture the owner-authored semantic content of that message excluding the trigger phrase.
2. If the message is trigger-only, capture the immediately preceding substantive owner message.
3. Assistant text may be referenced only as contextual evidence/analysis; assistant text cannot become owner memory.
4. If one source message contains multiple durable claims/events/plans/preferences/corrections, atomize them into separate candidate memories while preserving one shared source episode lineage.
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

## 5. Event and constraint model

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

Conflict detection must be conservative and typed:

### 5.1 Conflict classes
- `DIRECT_FACT_CONTRADICTION`: propositions cannot both be true for the same scope/time
- `SCHEDULE_HARD_CONFLICT`: known overlapping intervals or mutually exclusive commitments
- `SCHEDULE_POTENTIAL_CONFLICT`: same/overlapping date plus insufficient time/flexibility information
- `PREFERENCE_TENSION`: preferences point in incompatible directions but may coexist contextually
- `PLAN_SUPERSESSION_CANDIDATE`: newer user plan appears to replace an older plan but explicit correction is absent
- `UNKNOWN_CONSTRAINT`: evidence suggests a decision-relevant gap

Conflict records must include both atom IDs, derived event IDs, conflict type, evidence, confidence, unresolved/resolved status, and missing fields needed to resolve it.

No silent merge and no silent overwrite.

## 6. Retrieval / Memory Palace design

Current lexical retrieval is useful but insufficient. v1 retrieval becomes a hybrid orchestrator with four independent evidence channels:

1. **Lexical**: Chinese/English token/trigram/BM25 style term retrieval.
2. **Semantic**: embedding similarity over candidate statements/event summaries when an approved embedding provider is available. Semantic search is additive, never the sole source of truth.
3. **Temporal**: exact/nearby date and interval retrieval. Query expansion turns `明天` into an absolute time window before retrieval.
4. **Graph**: relation expansion over entities, events, conflicts, supersessions and provenance.

Ranking must preserve source channel scores and then apply deterministic boosts for:
- exact date overlap
- same actor/entity
- same project/scope
- explicit conflict edge
- correction/supersession relevance
- current validity

The result is a compact `MemoryContextBundle` containing:
- admitted atoms
- normalized events
- time relations
- conflicts
- unknowns
- provenance
- why each item was retrieved
- current-vs-historical status
- confidence and abstention gate.

## 7. Query behavior

### 7.1 Keyword recall
A query such as `睡觉`, `群运动`, `8月15日`, or related semantic wording should be able to retrieve the relevant captured memory under the correct user/project scope.

### 7.2 Temporal query expansion
A current utterance with `明天/后天/下周三/月底` must first resolve the expression against the current/utterance time and timezone, then search the resolved date window plus a bounded neighbor window when appropriate.

### 7.3 Multi-hop retrieval
If the current message says `明天我要去睡大觉`, retrieval may proceed:
`明天 -> 2026-08-15 -> events on 2026-08-15 -> prior group exercise plan -> constraint comparison`.

The final assistant response should distinguish:
- confirmed fact
- derived temporal fact
- potential conflict
- unknown/missing scheduling detail
- suggested clarification/action.

## 8. Four-layer knowledge mapping skill

For every important owner topic, the Memory Palace should maintain an explicit cognitive coverage map:

### A. `KNOWN_SAID`
Things the owner demonstrably knows and has explicitly said. Source-backed and retrievable.

### B. `KNOWN_UNSAID_INFERRED`
High-probability knowledge/constraints inferred from repeated behavior or context, but not explicitly stated. Must remain clearly labeled inference and never be treated as direct owner assertion.

### C. `UNKNOWN_BUT_ACCESSIBLE`
Concepts the owner has not demonstrated but can likely understand with a short bridge. Retrieval/teaching should connect these to known concepts.

### D. `UNKNOWN_REQUIRES_SCAFFOLDING`
Concepts requiring prerequisite layers, examples, analogy, progressive explanation or tooling. The system should store the prerequisite graph and teaching path, not merely label the owner as not knowing something.

This map is topic-specific and versioned. It must never become a global judgment of the person.

## 9. Research-derived design links

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

## 10. Storage strategy

Phase 1 remains SQLite/W3 because the accepted runtime already exists. Extend it additively with:
- normalized event table or event metadata
- temporal-expression records
- conflict/constraint records
- retrieval explanation records/tests
- FTS5/trigram option for improved lexical retrieval if migration tests prove safe

Do not jump to Neo4j/Postgres/vector DB solely because papers use graphs. Keep the logical graph contract independent of physical storage. Migrate only after benchmark evidence shows a need.

## 11. Manual capture receipt

A successful `采集记忆` operation must return a user-visible concise receipt containing only safe facts:
- capture status
- number of atoms/events persisted
- normalized date/time if any
- exact-recall proof = PASS/FAIL
- detected conflicts count/type
- whether clarification is needed
- candidate/formal authority state

Example:

`记忆采集成功：1 条计划记忆；“明天”已解析为 2026-08-15；精确召回 PASS；发现 1 个潜在日程冲突（同日已有群运动，具体时间未知）；已存为 candidate，未覆盖旧记忆。`

The receipt must never claim success unless durable write + post-write retrieval verification actually pass.

## 12. Retrieval-before-answer contract

When a current user turn has a material possibility of being affected by prior memory, query Memory Palace before answering. Do not retrieve everything. Build a bounded query plan from:
- entities
- user intent
- time expressions
- topic keywords
- active project/scope
- current/target time
- relation depth and budget.

The trust gate may return `ABSTAIN` when nothing reliable is found.

## 13. Required synthetic acceptance tests

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

## 14. Phase boundaries

### Phase A, epoch 107 implementation target
Synthetic-only implementation of:
- capture contract
- temporal normalization
- event representation
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

## 15. Security and authority

- Raw/private semantic content never goes to the public coordination repository.
- GitHub public repo may contain code, schemas, synthetic tests and aggregate receipts only.
- Credentials/tokens/API keys/private keys are never memory content and never committed.
- Candidate memory does not automatically become formal PROJECT/GLOBAL memory.
- Conflict detection proposes; it does not silently cancel plans or rewrite facts.
- High-risk actions remain owner-approved.
