# System Discovery and Opportunity Report

`agent_id: CODEX`

`task_id: CODEX-W12-D0-PR66-REBASE-W13-PMN-AMED-ABSORPTION-0013B-R3`

`boundary: research_only / NO_TRADE`

## Task-Level Findings

1. The 40 local W12 D0 files were byte-for-byte identical to the 40 files on
   PR #66 before R3 edits. The apparent untracked state was stale local Git
   history, not evidence loss.
2. Normal Git HTTPS fetch failed with connection reset while GitHub API remained
   available. API health and Git transport health are different operational facts.
3. No latest-main file invalidated the original W12 D0 evidence. The required
   change is a bounded post-D0 governance absorption, not a full audit restart.
4. During publication preflight, `main` advanced by five commits and registered
   module 0018, A-share house-edge-inspired survival and operating control. The
   preflight stopped the stale-base publication. Module 0018 is retained from
   latest `main`, classified as `REGISTERED_CANDIDATE / CONTRACTED_NOT_IMPLEMENTED_NOT_BACKTESTED / NO_TRADE`, and is not absorbed into this route because R3 is explicitly limited to W13, PMN and AMED.

## Module Findings

### W13

W13 is an evidence compiler and research bulletin, not an identity oracle. Its
current repository status is registered planning only. Participant activity,
identity, direction and amount remain separate. Northbound activity, brokerage
seats, ETF flows and market signatures cannot be silently promoted to exact
actor identity or amount.

### PMN

PMN is an expectation-aware interpretation layer on the existing W5/W2 systems
of record. Recurrence is not an official calendar; pre-event movement is not
proof of a leak; a surprise is undefined without a frozen expectation; and a
single asset move is not a complete causal explanation.

### AMED

AMED governs task intent, evidence, exploration and review. It is not a business
scheduler or a second evidence/learning runtime. Receipt completeness improves
auditability, but only independent GPT sampling can establish receipt quality.

## Cross-Module Findings

- W13 and PMN both consume W12 probability and DS-10 validation. Neither may
  own or mutate the shared probability authority.
- W13 participant hypotheses may inform PMN context, and PMN event context may
  inform W13 alternatives, but correlated evidence must not vote twice.
- W7 retains validation and final hard-risk authority; W10 freezes the decision
  episode; W11 alone allocates capital; OMS alone owns order state.

## Enterprise Opportunities

### Opportunity 1: Repository Publication Preflight

Disposition: `C_PROPOSAL_ONLY`.

Define a reusable exact-parent publication check for environments where REST is
reachable but Git transport is not. It should verify parent SHA, base tree,
artifact count, file hashes, merge parents, branch ref and post-publication diff.

### Opportunity 2: Shared Evidence-Cluster Contract

Disposition: `C_PROPOSAL_ONLY`.

During Issue #67 and #68 D0 planning, define how W13 and PMN reference one
canonical evidence cluster and one probability estimate. This prevents a news
article, market move and participant proxy derived from the same event from
being counted as three independent signals.

No new Skill candidate, source, interface or runtime is registered here. Both
opportunities require GPT disposition and remain outside the current task.
