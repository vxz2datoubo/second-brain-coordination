# Lane A · Harness × Cognitive OS Integration · Proposal Workspace

Status: `H0_ARCHITECTURE_STATIC_PASS_WITH_CONTROL_PLANE_BLOCKERS / PROPOSAL_ONLY / NO_RUNTIME_AUTHORIZATION`

Owner: `USER`  
Architecture owner: `GPT`

This directory is the only durable write surface reserved for Lane A while it remains proposal-only. The user explicitly started H0 architecture design after the Control Tower foundation merged. This permits architecture/research artifacts only. It does **not** authorize W3/W2-W13 runtime changes, Agent routes, private/live/production access, permissions, Formal Skill promotion, or trading.

## Current verdict

- Architecture static review: `PASS_WITH_BOUNDED_DEBT`
- H0 final acceptance: `NOT_READY`
- H1/H2 implementation release: `FAIL_CLOSED`
- Reason: current canonical Control Tower projections are stale even though the H0 internal architecture defects found so far have been repaired or bounded.

Control Tower CI independently reproduced the blocker: 20 targeted regressions passed, then canonical reconciliation failed with `CT-R01-STALE-VIEW / PROGRAM_REGISTRY_ROUTE_DRIFT`. The failed gate is treated as positive fail-closed evidence, not as permission to weaken reconciliation.

## H0 package index

### Master architecture / audit

- `COGNITIVE-OPERATING-SYSTEM-ARCHITECTURE-BLUEPRINT.md`
  - intelligent retrieval → problem framing → method discovery → evidence → independent challenge → adjudication → risk gate → outcome/correction/audit → reflection verification → second-order learning → skill evolution.
- `H0-ARCHITECTURE-COMPATIBILITY-REVIEW.md`
  - architecture compatibility and bounded successor concerns.
- `H0-STATIC-CROSS-FILE-AUDIT.yaml`
  - 14 architecture/control findings; repaired internal defects and open control-plane blockers.
- `H0-VALIDATION-RECEIPT.md`
  - records exact PR head/Actions run and the Control Tower expected fail-closed result.
- `IMPLEMENTATION-DEPENDENCY-DAG.yaml`
  - H0-H8 ordering, dependencies and resource semantics.

### Authority / organization

- `DEPARTMENT-CONTRACT-GRAPH.yaml`
  - explicit departments + `PRIMARY_PRODUCER` / `CHALLENGER` role templates; machine-resolvable return aliases; authority, inputs/outputs, review/challenge/verify/veto/return/feedback relationships.
- `ORGANIZATION-GRAPH-VALIDATOR-SPEC.yaml`
  - OGV-001..032 covering authority, orphan/dead-end, cycles, return aliases, schema compilability, route/work-claim consistency, trace, privacy, resource, PIT, NO_TRADE, H1/H2 separation and formal-model candidates.
- `SIGNAL-TOWER-MISSION-ROUTER-CONTRACT.yaml`
  - single user Mission entry, 0/1/N work planning, Control Tower authorization boundary.

### Core cognitive contracts

- `COGNITIVE-OS-CONTRACT-SCHEMAS.yaml`
  - `COGNITIVE_CONTRACT_DSL/v0.2` with DecisionEpisode state machine, ProblemSignature, Mission, MissionGraph, Claim, ChallengeCase, VerificationResult, Adjudication, FormalHandoff, OutcomeLearning, ReworkRequest, named semantic invariants and reproducibility fingerprint.
  - H1 must compile structural rules to formal JSON Schema or equivalent and implement deterministic semantic validators.
- `METHOD-MEMORY-SKILL-MANIFEST-CONTRACT.yaml`
  - W3-owned MethodMemory + progressive SkillManifest projection; Level 0 catalog → Level 1 manifest → Level 2 selected method body → Level 3 cases/failures.
- `TRACE-LEDGER-PRIVACY-CONTRACT.yaml`
  - Native Raw Trace / Cross-Agent Ledger / Formal Handoff; raw once/reference everywhere; privacy classes and T0-T3 completeness.
- `LEARNING-EVOLUTION-LIFECYCLE.yaml`
  - observation → match → localization → reflection candidate → reflection verification → credit → candidate updates → regression → cross-context revalidation → promotion/degradation/retirement.
- `ISSUE-312-COMPATIBILITY-MATRIX.yaml`
  - #312 mapped to existing authorities without parallel W3/skill/feedback runtimes.
- `ISSUE-308-CONSUMER-DEPENDENCY-MAP.yaml`
  - #308 fixed as first A-share evidence-first consumer, `research_only / NO_TRADE`.

### Harness integration

- `ADAPTER-BOUNDARY.yaml`
  - Adapter-first boundary; upstream identity/surface verified for H0, runtime binding still blocked pending smoke + fresh governance.
- `HARNESS-UPSTREAM-IDENTITY-VERIFICATION.md`
  - canonical upstream `deepseek-ai/deepseek-harness`, design snapshot `47f943859bef60e4160492346772ded9b24f765a`, `0.1.0-rc.5`, MIT.
- `HARNESS-POC-CONTRACT.md`
  - future H2 public-safe synthetic PoC with authority isolation, independent contexts, native trace, bounded failure/resource behavior.
- `IMPLEMENTATION-CLAIM-CANDIDATE.yaml`
  - two separate future claims:
    - H1 contract-only synthetic skeleton, no Harness runtime binding;
    - H2 Harness Adapter PoC, separate fresh Work Claim/route required.

### Control-plane remediation

- `CONTROL-TOWER-STALE-STATE-REMEDIATION-CANDIDATE.yaml`
  - proposal only, not applied.
  - specifies safe semantic cleanup for stale R132 ACTIVE projection, stale R120 Lane C Work Claim, stale Program Lane registry, Lane A proposal-only status and Lane B hold preservation.
  - canonical Control Tower files must be changed only through separately authorized governance work.

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
- `W9` = outcome/correction/audit learning, failure localization, MethodCredit/SkillHealth candidates.
- `PRIMARY_PRODUCER` / `CHALLENGER` = ephemeral execution roles, never canonical authorities.
- `#308` = first A-share consumer; no second W3/Method Router/feedback/evidence truth; `NO_TRADE`.

## Current open blockers

Before H0 can receive final acceptance, canonical governance must reconcile:

1. `ACTIVE-CODEX-TASK.yaml` still exposes completed R132 as `READY / execution_allowed=true / next_command=读取任务` even though PR #334 merged and Foundation Closure is complete.
2. `CONTROL-TOWER/LANE-WORK-CLAIMS.yaml` still binds Lane C to R120 / Issue #305 / PR #307 heavy implementation.
3. `ACTIVE-PROGRAM-LANES.yaml` still reflects R120-era observed state and Lane A as PAUSED.

No H1/H2 implementation route may be released while these remain unresolved.

## Proposal-only rules

Allowed:
- architecture/contracts/interfaces;
- authority and relationship maps;
- evaluation/falsification;
- research/evidence ledgers;
- future implementation-task drafts and claim candidates;
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
- automatic Harness upgrade;
- weakening Control Tower checks merely to make PR CI green.

## Next gate sequence

1. prepare H1 task/acceptance contract as **inactive draft only**;
2. separately authorize and apply bounded Control Tower stale-state cleanup;
3. rerun current Control Tower reconciliation / Work Claims / O0-O4 / WIP / witness checks;
4. rerun H0 static audit against cleaned current state;
5. issue final GPT H0 compatibility verdict;
6. only then publish a separate H1 executable route;
7. H1 acceptance still does not authorize H2.

**No Harness runtime implementation route has been released.**
