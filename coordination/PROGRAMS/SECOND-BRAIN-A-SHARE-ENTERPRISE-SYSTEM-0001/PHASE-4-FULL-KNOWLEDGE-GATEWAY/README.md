# Phase 4 Full Knowledge Gateway

- agent_id: `CODEX`
- task_id: `CODEX-P4-FULL-KNOWLEDGE-GATEWAY-0007`
- issue: `#38`
- status: `IN_PROGRESS`
- boundary: `research_only / NO_TRADE / local-first / credential-values-denied`

This phase extends the existing `integrated_offline_memory` package from Phase 3. It does not create another store, fusion engine, QueryPlan runtime, or ContextBundle runtime.

The public repository contains contracts, implementation, synthetic fixtures, aggregate receipts, hashes, and tests only. Authorized private knowledge bodies remain local. Credential values are denied from queries, packets, bundles, logs, errors, snapshots exported as evidence, and public artifacts.

## Canonical Flow

```text
KnowledgeSourceManifest
-> local read-only adapter
-> candidate LearningPacket
-> Phase 3 MemoryStore
-> QueryPlan
-> ContextBundle
-> AnswerEvidenceBundle
-> candidate feedback LearningPacket
-> snapshot / rollback / deterministic rebuild
```

## Recovery

Read `STATUS.yaml`, `PROGRESS-CHECKPOINT.yaml`, `DECISION-LOG.md`, and `UNKNOWN-REGISTRY.yaml`, refresh remote task state, then continue from the first incomplete checkpoint in `PROJECT-PLAN.yaml`.
