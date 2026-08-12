# WPDCR / PDER - CLTM-0021 private candidate ingestion epoch 81

agent_id: CODEX

planned difficulty: D3

actual difficulty: D3

## Observable evidence

- D0: verified canonical main fd9a3e12c36017de6f1db358e7fc8cc262fbb455, ACTIVE epoch-81 route and Issue #231 before implementation.
- D1: added one local-only Candidate v2 boundary, classified source metadata and public-safe synthetic adversarial tests.
- D2: preserved the existing ConversationEpisode -> LearningPacket -> MemoryStore -> QueryPlan -> ContextBundle path; no second storage, retrieval, vector, graph or temporal authority was introduced.
- D3: private-local admission required user/project/time/provenance and redacted receipts; secret, prompt-injection, assistant-role, malformed schema and wrong-scope attempts fail closed.
- D4: no formal PROJECT/GLOBAL write, real-private public publication, E48 live integration, private repo, production MCP/Gateway or trading action was attempted.

## Hardest part and negative result

The hardest boundary is permitting a local candidate body in the existing candidate store without making the public code path a disclosure channel. The chosen design keeps the packet and ContextBundle local, while the CLI exposes only public receipt hashes, counts, timestamp and status.

An initial synthetic test exposed that a second validation pass had omitted the schema version. This was corrected before the passing focused and full regression runs. LOCAL_EXECUTION_ISSUES = NONE_OBSERVED; the failed assertion was a normal implementation defect, not an environment execution issue.

## R2 remediation evidence

The R1 audit found five structural blockers. R2 separates the layered DailyMemoryCandidate-v2 package from the inner W3PrivateCandidateEnvelope-v1; maps coverage, all source episodes, candidate provenance, derived projection and upstream validation; admits only validated user-memory candidates; proves the exact imported atom is recalled; and confines input/store placement to an explicit private data root.

The sensitivity gate is now driven by Daily-v2 VALIDATION plus candidate sensitivity class, with structural token/PEM checks retained as defense in depth. Public synthetic tests reject password, API-key, token, cookie, session, MFA, recovery, payment, bank and broker credential classifications without storing representative secret values.

## Dependency and next gate

The real canary remains prohibited pending GPT R2 acceptance. When later authorized, the source state machine requires both CLTM_PRIVATE_DATA_ROOT and CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH, reports absent/unreadable as PRIVATE_SOURCE_BINDING_WAITING, reports malformed as REJECTED, and never emits a private path. All formal/private/live gates remain locked.
