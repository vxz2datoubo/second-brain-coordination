# R114 P1 Semantic-Integrity Hardening WPDCR

agent_id: CODEX

## Plan, difficulty and evidence

R114 closes three review blockers in the existing synthetic P1 path. The critical design decision was to make absence of a directive conservative: a nonempty bounded comparison now means UNKNOWN unless it is explicitly classified, preventing an unnoticed near-duplicate from becoming a second proposition.

The second difficulty was evidence naming. The current deterministic index can prove non-exact lexical retrieval and relation-assisted reachability, but not semantic paraphrase. The receipt therefore records every atom's proof mode and keeps semantic success false. The third change moves source trust to each immutable source episode, with a conservative proposition aggregate retained after duplicate union and restart.

## Observable validation and negative evidence

Focused R114 tests: 14/14 PASS. Full Phase-3 regression: 260/260 PASS. The negative cases demonstrate no-directive near-duplicate abstention/zero mutation, missing non-equivalence proof denial, and both trusted-to-inert and inert-to-trusted duplicate orders. No private source or store was read.

An initial governance lookup referenced a historical non-existent protocol filename. It failed before mutation and was corrected by discovering the current canonical remote tree (R114-LOCAL-001). This is a contained lookup error, not a claimed permanent system fix.

## Boundaries, discovery and next gate

R114 deliberately does not add a semantic engine or lifecycle transition; these are P3 and P4 boundaries. Real private ingestion, formal PROJECT/GLOBAL promotion, scheduler, production bridge, QCLAW dependency, permissions, trading and merge remain locked. The next acceptance gate is exact-head GitHub Python 3.11/3.13 CI followed by GPT review of PR 290.
