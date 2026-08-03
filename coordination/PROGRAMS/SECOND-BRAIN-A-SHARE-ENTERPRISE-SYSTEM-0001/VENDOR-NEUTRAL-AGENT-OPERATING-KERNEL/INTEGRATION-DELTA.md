# Integration Delta

> `agent_id: CODEX`
>
> `authority: CANDIDATE_DELTA_ONLY`
>
> `canonical_files_modified: false`

## Target

Primary parent:

`coordination/BLUEPRINTS/PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-BLUEPRINT-v1.0.md`

Shared owners:

- W1: route, AMED, approval, and authority source;
- W3: knowledge, evidence, conflict, UNKNOWN, and long-term memory;
- W8: Agent and capability orchestration;
- W10: TaskContext and DecisionEpisode;
- Phase 3: QueryPlan, ContextBundle, LearningPacket, candidate memory.

## Proposed Additions

### PEOS runtime

Insert a runtime protocol between TaskContext and output:

```text
AuthorityResolver
-> IntentCompiler
-> ContextAssembler
-> DeliberationController
-> CapabilityRouter
-> ExecutionAndRecovery
-> CompletionAuditor
```

This protocol is not a sixth cognitive model and owns no canonical data.

### Epistemic provenance

Add eight lanes:

`USER_ASSERTED`, `USER_ADOPTED`, `TOOL_OBSERVED`, `INFERRED`,
`HYPOTHESIS`, `DECISION`, `OUTCOME`, and `UNKNOWN`.

The lanes map to existing SourceRecord, EvidenceItem, KnowledgeAtom,
ForecastRecord, DecisionRecord, ReviewRecord, DecisionEpisode, and
LearningPacket objects through adapters.

### DecisionEpisode links

Add references to:

- AuthorityResolution;
- TaskIntent;
- ContextBundle hash;
- ToolRouteDecision;
- ExecutionCheckpoint;
- CompletionReceipt;
- ModelBehaviorProfile version.

### Evaluation

Add:

- vendor-preference leakage;
- provenance-lane confusion;
- inference-to-observation promotion;
- duplicate side effects;
- recovery-state drift;
- cross-model contract equivalence;
- unowned artifact mutation;
- requirement-evidence overclaim;
- canonical self-promotion.

## New Candidate Files

- `coordination/BLUEPRINTS/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-PROTOCOL-v1.0-CANDIDATE.md`
- `coordination/BLUEPRINTS/PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-AGENT-KERNEL-ADDENDUM-v1.0-CANDIDATE.md`
- `coordination/BLUEPRINTS/PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.5-CANDIDATE.md`
- `coordination/SKILLS/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-GOVERNANCE-SKILL-v1.0.yaml`

## Deferred Adapters

| Adapter | Status | Owner to confirm |
|---|---|---|
| W1 route to AuthorityResolution | NOT_IMPLEMENTED_YET | GPT/W1 |
| Phase 3 QueryPlan to ContextAssembler | NOT_IMPLEMENTED_YET | W3/Phase 3 |
| MemoryWriteProposal to LearningPacket | NOT_IMPLEMENTED_YET | W3/Phase 3 |
| W8 CapabilityRegistry to CapabilityDescriptor | NOT_IMPLEMENTED_YET | W8 |
| CompletionReceipt to W9/SelfEvolutionLog | NOT_IMPLEMENTED_YET | W9 |
| ModelBehaviorProfile evaluation | NOT_IMPLEMENTED_YET | GPT-assigned evaluator |

## Root AGENTS Pointer

No change is made in this candidate. After GPT approval, add only a short
pointer to the accepted protocol. Do not copy the runtime prompt or full
blueprint into `AGENTS.md`.

## Rollback

The candidate is additive. Close the Draft PR or revert its commits. Existing
canonical PEOS, integration index, memory, active route, and trading state are
unchanged.
