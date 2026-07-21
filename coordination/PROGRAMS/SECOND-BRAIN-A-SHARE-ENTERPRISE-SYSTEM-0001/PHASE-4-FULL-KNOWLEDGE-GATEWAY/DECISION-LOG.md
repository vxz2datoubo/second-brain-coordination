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
