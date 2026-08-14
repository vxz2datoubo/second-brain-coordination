# AMED Research Ledger - R112 P1

agent_id: CODEX

## Reuse decision

The existing W3 LearningPacket to MemoryStore to QueryPlan to ContextBundle path is sufficient for synthetic knowledge capture. A second store, graph redesign, embedding provider, QCLAW runtime dependency, or production bridge would duplicate authority or exceed P1.

## Research findings

- Generic atom identity cannot satisfy user/project/privacy separation. P1 therefore has a distinct knowledge-proposition-domain-v1 identity, while source episodes remain separate immutable provenance.
- Packet-backed provenance is the durable evidence surface. The atom keeps a union of privacy-minimized source episodes; packet_atoms preserves every importing packet.
- Query admission occurs before ranking. KnowledgeAtom rejects missing user, project, privacy domain, timezone-aware valid time, provenance, lifecycle, or freshness conditions.
- The existing MemoryStore transaction is the appropriate all-or-none write boundary after full preflight.

## Negative findings / rejected alternatives

- No private Daily-v2 source was read; it is not required and remains locked.
- No P2 graph, P3 associative recall, P4 lifecycle feedback, or P5 production API was added.
- A private-domain synthetic aggregate view was not introduced merely to test cross-domain voting. Private domains are fail-closed in P1; a later authorized aggregate needs its own governed equivalence policy.
