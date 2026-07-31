# Vendor-Neutral Agent Operating Kernel

> `agent_id: CODEX`
>
> `proposal_id: VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-PROPOSAL-0011`
>
> `status: IMPLEMENTED_CANDIDATE_PENDING_GPT_REVIEW`
>
> `boundary: research_only / NO_TRADE`

## Purpose

This package is a candidate runtime protocol for the existing Personal
Epistemic Cognitive Operating System (PEOS 0010). It gives different models and
agents the same machine-checkable semantics for:

- project authority;
- task intent;
- evidence and uncertainty;
- candidate memory writes;
- capability-based tool routing;
- interruption recovery;
- completion evidence;
- multi-agent handoff;
- model-specific behavior tuning.

It is not a second memory system, a second agent framework, a trading runtime,
or a new source of project authority.

## Source Boundary

The design was prompted by a publicly circulated 1511-line third-party capture
that claims to represent a model system prompt. Its authenticity and license
are not established. The raw capture is not included in this repository.

Only generic mechanisms were considered. Vendor identity, product promotion,
partner preference, proprietary tool names, political positioning, and
consumer-product persona text were excluded from the common kernel. Operational
integrity controls such as evidence truthfulness, explicit authority,
idempotency, rollback, auditability, and credential isolation remain because
they are engineering correctness requirements.

See:

- `PUBLIC-SOURCE-PROVENANCE.md`
- `SOURCE-ADAPTATION-MATRIX.yaml`
- `UNKNOWN-REGISTRY.yaml`

## Ownership

The candidate reuses existing project authority:

| Concern | Existing owner |
|---|---|
| Task route, AMED, approvals | W1 |
| Knowledge, evidence, conflict, UNKNOWN, long-term memory | W3 |
| Agent and capability orchestration | W8 |
| Task context and DecisionEpisode | W10 |
| QueryPlan, ContextBundle, LearningPacket candidate memory | Phase 3 |
| A-share facts, rules, validation, risk, execution | Existing domain owners |

The kernel only coordinates these owners through typed contracts.

## Contracts

1. `AuthorityResolution`
2. `TaskIntent`
3. `EpistemicClaim`
4. `MemoryWriteProposal`
5. `CapabilityDescriptor`
6. `ToolRouteDecision`
7. `ExecutionCheckpoint`
8. `CompletionReceipt`
9. `AgentHandoff`
10. `ModelBehaviorProfile`

All durable claims preserve one of eight provenance lanes:

`USER_ASSERTED`, `USER_ADOPTED`, `TOOL_OBSERVED`, `INFERRED`,
`HYPOTHESIS`, `DECISION`, `OUTCOME`, or `UNKNOWN`.

## Reference Runtime

The implementation is intentionally small and dependency-free. It demonstrates:

- deterministic authority resolution;
- deterministic provider-neutral routing;
- candidate-only memory proposals;
- immutable revisions with provenance;
- idempotent checkpoint recovery;
- requirement-to-evidence completion auditing.

It does not execute tools, write canonical memory, change project routes, start
services, or place orders.

## Run

From the repository root:

```powershell
python -B coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL/run_all_tests.py
```

The package does not require installation or third-party dependencies.

## Integration

Candidate blueprint integration is described in:

- `coordination/BLUEPRINTS/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-PROTOCOL-v1.0-CANDIDATE.md`
- `coordination/BLUEPRINTS/PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-AGENT-KERNEL-ADDENDUM-v1.0-CANDIDATE.md`
- `coordination/BLUEPRINTS/PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.5-CANDIDATE.md`

GPT must review ownership, non-duplication, authority precedence, and activation
before any candidate is promoted or referenced from canonical `AGENTS.md`.

## Non-Goals

- Reproducing or imitating a proprietary system prompt.
- Training or fine-tuning a model.
- Removing domain risk controls or production approvals.
- Giving a model permission to promote its own proposal.
- Treating a model profile as project authority.
- Storing credential values.
- Enabling real trading.
# E29 Extension Boundary

E29 adds candidate-only specifications for W1 Authority/Lease, W3 Phase 3
Epistemic Memory, and W8 Capability/Execution/Recovery adapters. It also adds
machine-readable K3 cross-model and K4 Shadow-0/1/2 gate definitions. All five
are `SPEC_ONLY_NOT_IMPLEMENTED` or `DISABLED_NOT_RUN`; no adapter, evaluation,
feature flag, live route, account, order, trade, or canonical memory write is
enabled by these files.

The E29 verifier freezes the discovered test-case manifest and checks exact
commit/tree identity when Git metadata is available. Archive execution remains
supported without Git metadata and is still required to be root-contained.
