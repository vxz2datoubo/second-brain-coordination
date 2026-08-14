# R116 P2 current-state architecture map

agent_id: CODEX  
task: CODEX-GPT-SECOND-BRAIN-COGNITIVE-CLOSED-LOOP-FUSION-P2-UNIFIED-RETRIEVAL-CONTEXT-PLAN  
epoch: 116  
base: f07e2181aa67c2b588dedfef33c8bc40ee59b468

## Authoritative reuse surface

| Concern | Existing authoritative implementation | P2 planning conclusion |
| --- | --- | --- |
| Candidate persistence | `PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/memory_store.py`, `MemoryStore.import_learning_packets_atomic` | Retain this single W3 candidate store; P2 creates no second store or direct mutation path. |
| Packet admission | `learning_packet.py`, `build_learning_packet` and `verify_learning_packet` | All new context inputs remain packet-derived and verification-bound. |
| Conversation candidate | `conversation_memory.py`, `ConversationEpisode`, `build_conversation_candidate`, `build_conversation_correction` | Reuse user/project/privacy/time/claim-role metadata and correction lifecycle. |
| Knowledge candidate | `knowledge_reconciliation.py`, `KnowledgeEpisode`, `KnowledgeCandidate` | Reuse source-trust, passage binding, privacy-domain and knowledge provenance rules. |
| Base retrieval | `retrieval.py`, `QueryPlan`, `ContextAssembler.assemble`, `ContextBundle` | Evolve this one planner/assembler into the P2 authority.  Do not introduce a parallel resolver. |
| Graph/conflict/unknown access | `memory_store.py`, `relations_around`, `related_atom_ids`, `conflicts_for`, `unknowns_for`, `provenance_for_atom` | Reuse read APIs behind a common admission policy and deterministic budget. |
| Memory Palace adapter | `memory_palace.py`, `retrieve_memory_palace`, `normalize_temporal_expression` | Fold its lexical/temporal/graph/provenance channel behavior into P2 planner/assembler; delete or delegate the special adapter only in a later authorized runtime slice. |

## Current effective contracts

`QueryPlan` already carries `query_text`, project `scopes`, `atom_types`, `truth_states`, confidence/time bounds, `relation_depth`, `budget`, `intent` (`CURRENT` or `HISTORICAL`), `user_scope`, `privacy_domains`, explicit aggregate mode, and `valid_at`.  Its validation already fail-closes a user-scoped query without a user scope, historical intent without `valid_at`, and multi-domain use without the synthetic aggregate mode.

`ContextAssembler._allowed` executes generic visibility/status/scope/type/confidence/time filtering and then conversation or knowledge-specific admission before candidate ranking.  Conversation admission requires user scope, source class, permitted user claim role, provenance, valid time and current revalidation.  Knowledge admission requires compatible project/user/privacy scope, public-safe aggregate handling, provenance/identity/role validity and current revalidation.  `_trust_gate` abstains if nothing is eligible.

`ContextBundle` presently exposes plan identity, knowledge version, atoms, relations, conflicts, unknowns, source lineage, omitted budget count, context budget, semantic access state, trust gate and provenance.  `MemoryStore.provenance_for_atom` returns packet/content hashes, opaque manifest identifiers, redacted episode metadata and pointer hashes rather than raw pointers or source bodies.

## P2 gaps relative to the canonical route

1. Memory Palace performs a useful hybrid retrieval but has a separate response shape and directly adds temporal/provenance graph candidates after base assembly.  P2 must make every channel use one pre-ranking admission interface.
2. There is no single versioned `GPTSecondBrainContextBundle v1` that distinguishes evidence, conflicts, alternatives, unknowns, admission rejections and channel contributions under a common budget.
3. Current ranking is deterministic lexical score plus identifier ordering, but has no frozen cross-channel voting/dedup policy or structural-analogy boundary.
4. Source lineage is available per atom, but a compact bundle-level evidence/alternative/provenance adjacency explanation is not yet specified.
5. Current and historical behavior exists for conversation/knowledge but needs one frozen P2 lifecycle table covering every object family and no-resurrection assertions.

No runtime implementation is changed by this planning epoch.
