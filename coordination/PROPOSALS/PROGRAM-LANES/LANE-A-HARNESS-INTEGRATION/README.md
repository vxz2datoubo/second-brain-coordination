# Lane A · Harness × Cognitive OS Integration · Proposal Workspace

Status: `ACTIVE_ARCHITECTURE_DESIGN / PROPOSAL_ONLY / NO_RUNTIME_AUTHORIZATION`

Owner: `USER`  
Architecture owner: `GPT`

This directory is the only durable write surface reserved for Lane A while it remains proposal-only. The user has explicitly started architecture design after Control Tower foundation PR #311 merged. This release permits architecture/research artifacts **only**. It does **not** authorize edits to W3/W8/W9/W10 runtime, Agent ACTIVE routes, domain canonical authorities, private sources, production gateways, permissions, or trading.

## Current H0 architecture package

1. `COGNITIVE-OPERATING-SYSTEM-ARCHITECTURE-BLUEPRINT.md`
   - master architecture for intelligent retrieval → problem framing → method discovery → evidence acquisition → independent challenge → adjudication → decision/risk gate → outcome observation → reflection → second-order learning → correction → skill evolution.
   - defines Signal Tower, DecisionEpisode, Effective Challenge, Trace/Handoff, failure taxonomy, learning loops, #312/#308 integration, and H0-H8 rollout.

2. `DEPARTMENT-CONTRACT-GRAPH.yaml`
   - machine-readable department/authority/relationship graph.
   - declares inputs, outputs, review/challenge/verify/veto/return/escalation paths and validator invariants.

3. `ADAPTER-BOUNDARY.yaml`
   - freezes authority boundaries between W3, #312, #310, W7, W2-W13, Signal Tower and Harness.
   - defines candidate stable interfaces and requires Adapter-first integration.
   - Harness source/repository/release identity is `REVERIFY_BEFORE_IMPLEMENTATION`.

4. `EVAL-PLAN.md`
   - memory, method discovery, challenge, tool verification, trace, second-order learning, organization graph, Harness PoC, resource governance and #308 A-share shadow evaluation.
   - includes A/B, ablation, negative and counterfactual tests.

5. `HARNESS-POC-CONTRACT.md`
   - future public-safe synthetic PoC only.
   - proves authority isolation, Primary/Challenger isolation, native trace linkage, bounded retry/cancel/failure and resource closure.

6. `IMPLEMENTATION-CLAIM-CANDIDATE.yaml`
   - future implementation Work Claim candidate only.
   - no runtime route exists yet.

7. `RESEARCH-EVIDENCE-LEDGER.md`
   - evidence mapping for ReAct, Reflexion, Self-Refine, CRITIC, Voyager, MemGPT, LongMemEval, LoCoMo, A-MEM, multi-agent/judge failure research, OpenTelemetry, Temporal, TLA+, NIST and Codex App Server.
   - research is reference evidence, not product truth.

## Frozen architecture authorities

- `W3 / Second Brain` = canonical knowledge, memory, provenance, conflict/unknown and lifecycle authority.
- `#312` = ProblemSignature / Method Discovery / Meta-Reasoning / Effective Challenge method layer.
- `Signal Tower` = single user mission intake, decomposition, dispatch proposal and result aggregation.
- `#310 Control Tower` = route / Work Claim / WIP / overlap / authorization governance; **not** task router.
- `Harness` = runtime/orchestration/session/workflow/subagent/tool/trace capability; **not** a second brain or truth authority.
- `W2-W13` = domain authorities; `W7` retains final risk veto.
- `#308` = first A-share consumer; it must not create a second Method Router, W3, feedback runtime or evidence truth.

## Proposal-only rules

Allowed:
- architecture contracts;
- interface/authority maps;
- evaluation and falsification plans;
- research/evidence ledgers;
- future Work Claim candidates;
- rollback and migration design.

Forbidden:
- runtime/source edits outside this directory;
- new executable Codex/QCLAW/WorkBuddy route;
- direct binding to mutable W3 internals;
- replacement of GitHub/W3/W7/W12/Control Tower authority;
- private data access or copy;
- production scheduler/MCP/Gateway;
- permission/visibility changes;
- account/order/fund/trading actions;
- automatic Formal Skill promotion;
- automatic Harness upstream upgrade.

## H0 next gates

Before any implementation route:

1. complete Authority + Interface + Department relationship compatibility review;
2. validate DecisionEpisode / FormalHandoff / MissionGraph machine contracts;
3. define Organization Graph Validator and critical state-machine model checks;
4. produce #312 REUSE/EXTEND/WRAP/MOVE-BEHIND-INTERFACE matrix;
5. produce #308 consumer dependency mapping;
6. independently reverify Harness canonical source/repository/tag/commit/license/public service surface;
7. perform fresh Control Tower O0-O4 / WIP / Work Claim scan;
8. issue explicit GPT implementation release only if H0 passes.

**H0 architecture work may continue now. Runtime implementation remains locked.**
