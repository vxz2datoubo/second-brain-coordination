# Lane A · Harness × Cognitive OS Integration · Proposal Workspace

Status: `ACTIVE_ARCHITECTURE_DESIGN / PROPOSAL_ONLY / NO_RUNTIME_AUTHORIZATION`

Owner: `USER`  
Architecture owner: `GPT`

This directory is the only durable write surface reserved for Lane A while it remains proposal-only. The user explicitly started H0 architecture design after the Control Tower foundation merged. This permits architecture/research artifacts only. It does **not** authorize W3/W2-W13 runtime changes, Agent routes, private/live/production access, permissions, Formal Skill promotion, or trading.

## H0 package index

### Master architecture

- `COGNITIVE-OPERATING-SYSTEM-ARCHITECTURE-BLUEPRINT.md`
  - intelligent retrieval → problem framing → method discovery → evidence → independent challenge → adjudication → risk gate → outcome → reflection → verified second-order learning → skill evolution.
- `H0-ARCHITECTURE-COMPATIBILITY-REVIEW.md`
  - first internal architecture audit, current bounded debts and implementation blockers.
- `IMPLEMENTATION-DEPENDENCY-DAG.yaml`
  - H0-H8 ordering, dependencies and resource semantics.

### Authority / organization

- `DEPARTMENT-CONTRACT-GRAPH.yaml`
  - machine-readable authority, inputs/outputs, review/challenge/verify/veto/return/feedback relationships.
- `ORGANIZATION-GRAPH-VALIDATOR-SPEC.yaml`
  - duplicate authority, orphan/dead-end, cycles, return paths, trace, privacy, resource, PIT, NO_TRADE checks plus formal-model candidates.
- `SIGNAL-TOWER-MISSION-ROUTER-CONTRACT.yaml`
  - single user Mission entry, 0/1/N work planning, Control Tower authorization boundary.

### Core cognitive contracts

- `COGNITIVE-OS-CONTRACT-SCHEMAS.yaml`
  - DecisionEpisode, ProblemSignature, Mission, MissionGraph, Claim, ChallengeCase, VerificationResult, Adjudication, FormalHandoff, OutcomeLearning and reproducibility fingerprint.
- `ISSUE-312-COMPATIBILITY-MATRIX.yaml`
  - maps #312 capabilities into REUSE / EXTEND / WRAP / SPLIT responsibilities without creating parallel authorities.
- `ISSUE-308-CONSUMER-DEPENDENCY-MAP.yaml`
  - #308 as first A-share evidence-first consumer, `research_only / NO_TRADE`.
- `LEARNING-EVOLUTION-LIFECYCLE.yaml`
  - observation → outcome match → localization → reflection candidate → reflection verification → credit → candidate updates → regression → cross-context revalidation → promotion/degradation/retirement.

### Harness integration

- `ADAPTER-BOUNDARY.yaml`
  - Adapter-first authority/interface boundary; domain code must not depend on concrete Harness providers.
- `HARNESS-UPSTREAM-IDENTITY-VERIFICATION.md`
  - canonical upstream independently reverified as `deepseek-ai/deepseek-harness`; design snapshot `47f943859bef60e4160492346772ded9b24f765a`, `0.1.0-rc.5`, MIT; runtime smoke still pending.
- `HARNESS-POC-CONTRACT.md`
  - future public-safe synthetic PoC: authority isolation, Primary/Challenger isolation, native trace, bounded retry/cancel/failure, resource closure.
- `IMPLEMENTATION-CLAIM-CANDIDATE.yaml`
  - future H1/H2 Work Claim candidate only; no execution route exists.

### Evidence / evaluation

- `EVAL-PLAN.md`
  - memory, method discovery, challenge, verification, trace, learning, organization, Harness, resources and A-share A/B/ablation/negative/counterfactual evaluation.
- `RESEARCH-EVIDENCE-LEDGER.md`
  - primary/official research mapping; research evidence is not product truth.

## Frozen authority topology

- `W3 / Second Brain` = canonical knowledge, memory, provenance, conflict/unknown and lifecycle authority.
- `#312` = ProblemSignature / Method Discovery / Meta-Reasoning / Challenge method layer.
- `Signal Tower` = user Mission intake, decomposition, dispatch proposal and result aggregation.
- `#310 Control Tower` = route / Work Claim / WIP / overlap / authorization governance; **not** task router.
- `Harness` = runtime/orchestration/session/workflow/subagent/tool/job/trace capability; **not** a second brain or truth authority.
- `W2-W13` = domain authorities; `W7` retains final risk veto.
- `W9` = outcome calibration, failure localization, MethodCredit/SkillHealth candidates.
- `#308` = first A-share consumer; no second W3/Method Router/feedback/evidence truth; `NO_TRADE`.

## Harness verification state

Identity and architecture surface: `PASS_FOR_H0_DESIGN`.

Verified snapshot:
- repo `deepseek-ai/deepseek-harness`;
- `master` SHA `47f943859bef60e4160492346772ded9b24f765a`;
- package family/root `0.1.0-rc.5`;
- MIT;
- official Cordis / everything-is-plugin / Service Definition-Provider-Consumer architecture.

Official project maturity remains developer preview with expected breaking changes, so exact pin + Adapter isolation + compatibility radar + no auto-upgrade remain mandatory.

Runtime install/pack/smoke: `PENDING / REQUIRED_BEFORE_H2`.

## Current H0 architecture audit

Provisional verdict:

`PROVISIONAL_PASS_FOR_CONTINUED_H0_DESIGN / IMPLEMENTATION_NOT_RELEASED`

Known implementation-release blocker:
- canonical Control Tower aggregate/work-claim/active-route projections still contain stale older Lane C/R132 state. Before H1/H2, refresh observed state, neutralize stale execution projection, run fresh O0-O4/WIP scan and create a fresh authorization witness.

Bounded successor concerns that do **not** reopen P2.5:
- R120-W01 context-only endpoint;
- R122 unknown binding;
- clean cross-component `FeedbackLifecycle/v1` API;
- executable Formal Skill promotion governance;
- Harness target-environment runtime smoke.

## Proposal-only rules

Allowed:
- architecture/contracts/interfaces;
- authority and relationship maps;
- evaluation/falsification;
- research/evidence ledgers;
- implementation claim candidates;
- migration/rollback design.

Forbidden:
- runtime/source edits outside this directory;
- executable Codex/QCLAW/WorkBuddy route;
- direct binding to W3 internals or concrete Harness providers;
- replacement of W3/#312/W7/Control Tower/domain authorities;
- private data access/copy;
- production scheduler/MCP/Gateway;
- permission/visibility changes;
- account/order/fund/trading action;
- automatic Formal Skill promotion;
- automatic Harness upgrade.

## Remaining H0 gates

1. machine/static validation of proposal schemas and graph references;
2. minimal MethodMemory + SkillManifest projection contracts;
3. Trace Ledger event/privacy contract;
4. final Organization Graph findings pass;
5. fresh Control Tower proposal/current-state O0-O4/WIP scan;
6. final GPT H0 compatibility verdict.

**H0 architecture may continue. No Harness runtime implementation route has been released.**
