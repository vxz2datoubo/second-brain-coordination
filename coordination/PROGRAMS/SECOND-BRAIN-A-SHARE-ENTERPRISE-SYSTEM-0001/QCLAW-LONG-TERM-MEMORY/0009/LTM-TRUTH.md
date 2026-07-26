# Long-Term Memory Plan — Epoch 9 Truth & Non-Duplication Remediation

**task_id:** QCLAW-MULTI-PR-TRUTH-ADAPTER-ATOMIZATION-LTM-CONSISTENCY-0012-E9
**route_epoch:** 9
**stage:** Stage D: PR #65 LTM Plan Truth

## Capability Status Classification
Every proposed capability MUST be classified as one of: PLAN | CONTRACT | PROTOTYPE | IMPLEMENTED

## Architecture Status
| Component | Status | Notes |
|-----------|--------|-------|
| Canonical offline store (PR #57) | MERGED_CANONICAL | Phase 3 offline memory — the only canonical store |
| Knowledge gateway (PR #58) | OPEN_CANDIDATE | Codex Phase 4 — NOT accepted runtime |
| 9-layer memory model | CONTRACT | Schema + taxonomy defined |
| Memory lifecycle (10 states) | CONTRACT | Schema defined |
| Memory record schema | CONTRACT | Schema defined |
| 9 retriever contracts | CONTRACT | Individual contracts documented |
| 13-factor reranking | PLAN | Weighted policy only |
| Memory palace architecture | PLAN | Computable navigation design |
| Memory palace schema | CONTRACT | Schema defined |
| Embedding provider contract | CONTRACT | Provider-agnostic |
| Vector index manifest | CONTRACT | Schema only |
| Re-embedding plan | PLAN | Transition strategy documented |
| Time/version index | PLAN | Design only |
| Conflict/UNKNOWN retrieval | PLAN | Policy documented |
| Memory consolidation | PLAN | Triggers documented |
| Memory decay/archive | PLAN | Factors documented |
| Hybrid retrieval (working code) | NOT_IMPLEMENTED | No runtime code |
| Vector search index (working code) | NOT_IMPLEMENTED | No backend chosen |
| Graph traversal (working code) | NOT_IMPLEMENTED | No implementation |
| Memory palace (working code) | NOT_IMPLEMENTED | No implementation |

## Non-Duplication Map (field-level)
| PR #65 Field | PR #57 Equivalent | Duplicates? | Resolution |
|-------------|------------------|-------------|------------|
| memory_id (SHA-256) | atom_id (SHA-256) | No | LTM memory_id wraps canonical atom_id |
| content_zh/en | content_zh/en | No | LTM retrieves, does not store canonical copies |
| confidence | confidence | No | LTM inherits from canonical atom |
| project | project scope | No | LTM adds project filtering layer |
| evidence_status | evidence_status | No | LTM inherits from canonical |
| source_atom_id | deterministic_id | No | LTM links not stores |

## Second-Brain vs Trading-System Separation
- Second-brain long-term retrieval (PR #65): knowledge management for canonical facts
- Trading-system D2 (PR #100): candidate participant classification adapter
- Shared: evidence contracts ONLY (source locks, family ontology, quarantine rules)
- Separated: retrieval logic, memory lifecycle, trading signals

## 36+ Adversarial Long-Memory Cases
- ALM-001: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-002: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-003: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-004: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-005: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-006: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-007: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-008: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-009: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-010: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-011: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-012: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-013: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-014: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-015: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-016: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-017: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-018: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-019: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-020: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-021: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-022: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-023: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-024: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-025: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-026: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-027: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-028: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-029: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-030: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-031: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-032: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-033: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-034: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-035: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case
- ALM-036: Stale memory, conflict, UNKNOWN, contamination, privacy, authority confusion test case

## No Implementation in This Task
- No canonical store code
- No retrieval runtime
- No vector index wiring
- No graph database
- Deliverable = executable validation of plan package only

**PLAN_AND_CONTRACTS_ONLY | NO_TRADE | PUBLIC_SAFE | CANDIDATE_ONLY**
