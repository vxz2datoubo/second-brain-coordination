# WPDCR / PDER - CLTM-0021 private candidate ingestion epoch 81

agent_id: CODEX

planned difficulty: D3

actual difficulty: D3

## Observable evidence

- D0: verified ACTIVE epoch-81 route and canonical main; R3 observed `6d29d1a3931dd4a7065e6fa3422f560737afa45b` as an E48-only successor while preserving this branch without rebase.
- D1: added one local-only Candidate v2 boundary, classified source metadata and public-safe synthetic adversarial tests.
- D2: preserved the existing ConversationEpisode -> LearningPacket -> MemoryStore -> QueryPlan -> ContextBundle path; no second storage, retrieval, vector, graph or temporal authority was introduced.
- D3: private-local admission required user/project/time/provenance and redacted receipts; secret, prompt-injection, assistant-role, malformed schema and wrong-scope attempts fail closed.
- D4: no formal PROJECT/GLOBAL write, real-private public publication, E48 live integration, private repo, production MCP/Gateway or trading action was attempted.

## Hardest part and negative result

The hardest boundary is permitting a local candidate body in the existing candidate store without making the public code path a disclosure channel. The chosen design keeps the packet and ContextBundle local, while the CLI exposes only public receipt hashes, counts, timestamp and status.

An initial synthetic test exposed that a second validation pass had omitted the schema version. This was corrected before the passing focused and full regression runs. LOCAL_EXECUTION_ISSUES = NONE_OBSERVED; the failed assertion was a normal implementation defect, not an environment execution issue.

## R3 remediation evidence

The R2 audit found five remaining structural blockers. R3 separates the enabled human-readable DailyMemoryCandidate-v2 report from a versioned DailyMemoryCandidateTransport-v1 serializer and the inner W3PrivateCandidateEnvelope-v1. The transport carries partial coverage plus included/excluded-source semantics, actor/provenance fields, candidate disposition and sensitivity. Accepted out-of-scope candidates become explicit non-import records; a zero-eligible day produces a safe no-op receipt.

USER_CORRECTION now calls the canonical append-preserving correction builder, producing a supersedes relation that closes the prior candidate for CURRENT while retaining it for valid HISTORICAL recall. The existing provenance surface now projects each source episode's opaque ID, manifest, pointer hash and recorded instant, never a raw pointer or conversation body. Receipts aggregate actual IMPORTED and IDEMPOTENT_DUPLICATE outcomes across packets instead of claiming IMPORTED unconditionally.

The sensitivity gate is now driven by Daily-v2 VALIDATION plus candidate sensitivity class, with structural token/PEM checks retained as defense in depth. Public synthetic tests reject password, API-key, token, cookie, session, MFA, recovery, payment, bank and broker credential classifications without storing representative secret values.

## Dependency and next gate

The real canary remains prohibited pending GPT R3 acceptance. When later authorized, the source state machine requires both CLTM_PRIVATE_DATA_ROOT and CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH, reports absent/unreadable as PRIVATE_SOURCE_BINDING_WAITING, reports malformed as REJECTED, and never emits a private path. All formal/private/live gates remain locked.

## Local execution issue

LEIP-UNICODE-001 occurred once while a read-only GitHub review-thread helper used the Windows GBK default to decode UTF-8 review text. Re-running the same read with PYTHONUTF8=1 succeeded. This was limited to local subprocess decoding; no repository object, private source or remote state was altered. The reversible workaround is process-local and can be removed by unsetting that environment variable.
