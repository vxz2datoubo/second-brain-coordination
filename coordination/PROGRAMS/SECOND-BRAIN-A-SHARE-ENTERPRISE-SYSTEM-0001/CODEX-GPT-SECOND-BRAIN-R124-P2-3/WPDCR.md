# R124 P2.3 WPDCR

agent_id: CODEX

## Planned and actual difficulty

Planned difficulty was D3: move three candidate-discovery paths without changing the accepted R118-R123 policy boundary or inventing a ranking scheme. Actual difficulty was D3. The hardest part was preserving existing temporal and shared-lineage behavior while ensuring every candidate is admitted before it reaches deduplication and the budget.

## Observable evidence and negative results

Direct source inspection found the adapter-side `all_atoms`, relation and source-reference scans. The implementation moves them to `ContextAssembler`, where the existing caller-observability and admission checks already run before `_CandidateSet.consider`. Focused synthetic tests prove temporal retrieval, foreign-scope non-observability, no adapter second-path calls, multi-path deduplication and repeatability. No private source, real store, ingestion, canary, scheduler, formal write, E48/live path, production MCP/Gateway, permission action, trading action or merge was attempted.

One initially over-specific test expectation assumed a temporal seed would not also have a graph provenance marker. The focused test showed that self-lineage graph attribution is existing compatible behavior. The expectation was narrowed to the required temporal attribution and deterministic result, rather than changing production behavior.

## Discoveries and coordination

The candidate authority migration can preserve the frozen ranking policy: lexical and relation scores remain scored; temporal and provenance discovery are ordered supplemental candidates with no invented numeric weight. CODEX owns this synthetic/public-safe runtime slice. GPT owns review and any future change to ranking policy, deferred watchpoints, formal persistence or live/private authority.

## Postflight and next acceptance gate

The local adapter regression passed 98/98 and the integrated Phase-3 regression passed 279/279. The public-safety scanner passed 84 files with 0 issues; six YAML documents parsed; and `git diff --check` passed. Create an attributed additive commit; push the exact head and open a Draft PR; then require Python 3.11/3.13 exact-head CI and GPT review. LOCAL_EXECUTION_ISSUES = NONE_OBSERVED.
