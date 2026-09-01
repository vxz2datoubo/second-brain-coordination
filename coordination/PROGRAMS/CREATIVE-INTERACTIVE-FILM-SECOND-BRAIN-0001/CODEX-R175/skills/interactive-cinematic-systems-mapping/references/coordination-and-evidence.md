# Coordination and evidence

## Systems of record and writers

| Surface | Source of record | Primary writer | Other consumers |
| --- | --- | --- | --- |
| product approval | canonical Issue/decision | USER or delegated integrator | all agents |
| script packages | approved versioned content catalog | governed content owner | runtime, director |
| player facts | append-only campaign ledger | runtime single writer | replay, drama, director |
| narrative proposal | proposal store | model gateway/simulator | validator only |
| director output | deterministic compilation | director compiler | offline/provider adapter |
| private asset bytes | local private asset store | WorkBuddy/operator adapter | authorized media adapter |
| asset references | campaign continuity ledger | governed runtime | director/media |
| knowledge lessons | review-candidate store | runtime/correction flow | human reviewer |
| execution evidence | exact-head receipts | executor/CI | reviewer |

## Agent allocation

- **Codex:** architecture, stable contracts, core state semantics, director
  compiler, failure behavior, focused tests, and repair of core findings.
- **WorkBuddy:** clean reproduction, Windows/private-environment facts,
  recovery/concurrency/storage/soak matrices, operator tooling, and explicitly
  routed D0/D1 isolated implementation.
- **GPT integrator/reviewer:** governed route publication, stage-level
  cross-module review, integration, and merge recommendation after user trigger.
- **User:** product direction, budget, provider credentials, real-user intake,
  content boundary, publication, deployment, and final merge authority.

## Evidence tiers

- `E0_RECORDED`: request, document, branch, observation, or hypothesis exists.
- `E1_DETERMINISTIC`: committed input passes a deterministic local check.
- `E2_CLEAN_REPRODUCED`: exact committed artifact reproduces in a clean clone.
- `E3_INDEPENDENTLY_ATTESTED`: a genuinely uninvolved reviewer verifies the
  exact candidate and records the result.

Executor clean reproduction is E2, not E3. A vendor specification proves only
what that document claims at the observed version/time.

## Candidate-branch rule

An unmerged branch may be used as source-selected evidence only when its exact
head, divergence, paths used, limitations, and import method are recorded.
Do not blind cherry-pick a branch whose base predates the current governance
main. Mechanically port bounded contracts or implementation into a newly
authorized branch, then rerun current policy, scope, and lifecycle tests.

## Closeout

Normal Codex/WorkBuddy loops do not require GPT review. When the user says
`同步`, `收尾`, or `做交接`, freeze an exact head and provide one consolidated
packet: base/head, commits, contract changes, cards/metrics changed, test matrix,
normal and negative lifecycle paths, WorkBuddy findings, known risks, rollback,
and one next stage. Never self-review, Ready, accept, or merge.
