# Decision Log

## D-001: Extend Phase 3 In Place

- status: ACCEPTED
- decision: P4 code will be added to the existing `integrated_offline_memory` package and existing `MemoryStore`, `QueryPlan`, `ContextAssembler`, and `ContextBundle` will be extended.
- reason: Issue #38 prohibits a second runtime.
- rejected alternative: a separate P4 store or gateway database.

## D-002: Public Repository Holds No Private Bodies

- status: ACCEPTED
- decision: local source probes may emit only manifest identifiers, hashes, counts, semantic bundle hashes, access decisions, and aggregate query outcomes.
- reason: private bodies require a local or authenticated private transport.

## D-003: KnowledgeQuery Is an External Request Contract

- status: ACCEPTED
- decision: `KnowledgeQuery` will deterministically compile into the existing `QueryPlan`; it will not implement its own search logic.
- reason: preserve one query runtime.

## D-004: Unknown License Cannot Activate

- status: ACCEPTED
- decision: unknown, undeclared, conflicting, or prohibited license evidence returns `WAITING_LOCAL_EVIDENCE` or `DENIED` and cannot open a source.
- reason: prevent Phase 3 unknown-license regression.

## D-005: Current Queries Exclude Superseded by Default

- status: ACCEPTED
- decision: current queries exclude superseded atoms; explicit historical queries may include them and must label them historical.
- reason: Issue #38 requires current/history separation without destroying history.

## D-006: Consolidate Duplicate Semantic Blocks

- status: ACCEPTED
- decision: identical normalized source blocks produce one content-addressed atom with all document references retained.
- reason: the authorized local probe exposed repeated semantic blocks; preserving each as a separate atom would cause duplicate inflation and invalid packet identities.

## D-007: Compile Evidence Before Any Answer Surface

- status: ACCEPTED
- decision: `AnswerEvidenceCompiler` consumes the existing `ContextBundle` and emits evidence selection reasons, conflicts, UNKNOWNs, omissions, conditions, and abstention; it does not generate prose.
- reason: a fluent answer is not an acceptable substitute for traceable evidence, and Issue #38 requires one canonical query runtime.

## D-008: Conflict Counterparts Are Query Context

- status: ACCEPTED
- decision: when conflict reporting is enabled, eligible counterpart atoms are added through `ContextAssembler` before budget selection and are explicitly labelled in the evidence package.
- reason: returning a conflict record without the available opposing atom would hide material evidence.

## D-009: Correction Does Not Imply Supersession

- status: ACCEPTED
- decision: `CORRECTION` creates a candidate correction plus an unresolved conflict; only explicit `SUPERSEDES` removes the target from the current view.
- reason: user feedback must not silently rewrite history or promote a candidate correction into authority.

## D-010: Feedback Is Previewed Before Mutation

- status: ACCEPTED
- decision: all seven feedback classes produce a deterministic candidate preview; commit validates the preview hash, imports through the existing LearningPacket path, records retrieval impact by IDs, and remains snapshot-recoverable.
- reason: the user must be able to inspect, repeat, or roll back learning effects without a hidden write path.

## D-011: Do Not Self-Certify the Independent Benchmark

- status: ACCEPTED
- decision: local 2,000-atom and recovery gates may complete, but the phase remains PARTIAL until the QCLAW 100+ query package is fetched and executed unchanged.
- reason: replacing an independent evaluation with Codex-authored answer keys would violate Issue #38's anti-self-certification boundary.
