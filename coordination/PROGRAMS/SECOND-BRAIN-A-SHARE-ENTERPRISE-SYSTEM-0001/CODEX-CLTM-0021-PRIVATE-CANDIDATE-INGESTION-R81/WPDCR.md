# WPDCR / PDER - CLTM-0021 private candidate ingestion epoch 81

agent_id: CODEX

planned difficulty: D3

actual difficulty: D3

## Observable evidence

- D0: verified ACTIVE epoch-81 route and canonical main; R4 observed `3328498b367e958b155254c3df2f3be6dcbbbe5c` as an E48-only successor while preserving this branch without rebase.
- D1: added one local-only Candidate v2 boundary, classified source metadata and public-safe synthetic adversarial tests.
- D2: preserved the existing ConversationEpisode -> LearningPacket -> MemoryStore -> QueryPlan -> ContextBundle path; no second storage, retrieval, vector, graph or temporal authority was introduced.
- D3: private-local admission required user/project/time/provenance and redacted receipts; secret, prompt-injection, assistant-role, malformed schema and wrong-scope attempts fail closed.
- D4: no formal PROJECT/GLOBAL write, real-private public publication, E48 live integration, private repo, production MCP/Gateway or trading action was attempted.

## Hardest part and negative result

The hardest boundary is permitting a local candidate body in the existing candidate store without making the public code path a disclosure channel. The chosen design keeps the packet and ContextBundle local, while the CLI exposes only public receipt hashes, counts, timestamp and status.

An initial synthetic test exposed that a second validation pass had omitted the schema version. This was corrected before the passing focused and full regression runs. LOCAL_EXECUTION_ISSUES = NONE_OBSERVED; the failed assertion was a normal implementation defect, not an environment execution issue.

## R5 remediation evidence

R5 adds a genuine single transaction around all accepted packets in one Daily package at the existing `MemoryStore` authority. Before it enters that boundary, correction identity resolution explicitly rejects an already-superseded target and duplicate target claims within the same package. The adversarial lifecycle test adds an ordinary candidate before the invalid correction and proves the complete store statistics are unchanged; it also proves two corrections to one open target are rejected with zero new store state.

Missing `valid_from` or `recorded_at` is no longer inferred from package episode zero. The normalizer accepts a missing temporal value only when that candidate's own supporting episode set yields exactly one canonical instant; otherwise it fails closed. A distinct producer candidate ID with the same canonical atom is preserved as a sorted set of content-hash aliases in existing W3 conversation metadata. The original primary hash remains stable, provenance exposes only the alias hashes, and a subsequent correction resolves either alias under the existing user/project/time gate.

No real private canary was run. R5 is synthetic/public-safe adversarial hardening only; all formal/private/live gates remain locked pending GPT review.

## R4 remediation evidence

The R3 audit found five remaining structural blockers. R4 makes DailyMemoryCandidateTransport-v1 the explicit strict machine contract and treats DailyMemoryCandidate-v2 as a human-report input that needs tolerant normalization. The normalizer accepts current producer alternatives such as lower-case coverage, actor/speaker and source-ref/provenance variants, optional candidate timing/sensitivity fields and validation/rejection layouts while retaining partial/unknown coverage and included/excluded-source semantics.

Producer-known candidate IDs are persisted only as a content hash in existing conversation metadata. A later correction uses `replaces_candidate_id`; the local bridge resolves the unique earlier W3 atom under user/project/time scope before any packet write. All correction targets and packets are preflighted before the first mutation, so a valid candidate followed by an unresolved correction leaves no partial state.

Episode valid-time is timezone-normalized, provenance quality is retained, and candidate confidence maps explicitly (HIGH/MEDIUM/LOW to 0.9/0.6/0.3) before traversing the existing packet/store/ContextBundle provenance surface. Raw source pointers and conversation text remain absent.

The sensitivity gate is now driven by Daily-v2 VALIDATION plus candidate sensitivity class, with structural token/PEM checks retained as defense in depth. Public synthetic tests reject password, API-key, token, cookie, session, MFA, recovery, payment, bank and broker credential classifications without storing representative secret values.

## Dependency and next gate

The real canary remains prohibited pending GPT R4 acceptance. When later authorized, the source state machine requires both CLTM_PRIVATE_DATA_ROOT and CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH, reports absent/unreadable as PRIVATE_SOURCE_BINDING_WAITING, reports malformed as REJECTED, and never emits a private path. All formal/private/live gates remain locked.

## Local execution issue

LEIP-UNICODE-001 occurred once while a read-only GitHub review-thread helper used the Windows GBK default to decode UTF-8 review text. Re-running the same read with PYTHONUTF8=1 succeeded. The independent occurrence was recorded in the canonical LOCAL-EXECUTION-ISSUE-PATTERNS registry: root cause remains multiple possible encoding boundaries, and the process-local workaround is containment rather than a permanent family-wide fix.
