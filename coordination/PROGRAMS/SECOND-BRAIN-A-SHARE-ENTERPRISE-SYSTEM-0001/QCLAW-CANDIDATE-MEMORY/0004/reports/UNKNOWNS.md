# UNKNOWNS — Candidate Memory Library v0.2

**Task ID:** QCLAW-CANDIDATE-MEMORY-LIBRARY-RETRIEVAL-0004
**Date:** 2026-07-21

## Open Technical Questions

1. **Codex PR #41 runtime access** — Cross-system tests (XT-001 through XT-006) are defined but cannot be run without access to Codex's replay module. Is Codex PR #41 merged or still in draft? If merged, what's the branch/commit to test against?

2. **Chinese tokenizer integration** — Issue #43 explicitly says "minimal deterministic Chinese word segmentation" for Work Package D. Current implementation does English-only keyword search via FTS5. Should a jieba/pkuseg tokenizer be integrated, or is the English baseline sufficient for Gate 0?

3. **File-based SQLite determinism** — Two-round build is deterministic on `:memory:` SQLite with same packets, but the SHA256 of the `.db` file itself will differ because SQLite writes metadata (WAL, page headers) non-deterministically. Is revision hash (snapshot manifest) sufficient, or does the `.db` file hash also need to match?

4. **`knowledge_status` vs `verification_status`** — Current schema has both fields. Are they truly independent, or should `verification_status` be folded into `knowledge_status`? The 4-axis independence design treats them as separate, but the boundary between "verified fact" (verification_status=VERIFIED) and "approved knowledge" (knowledge_status=VERIFIED) is fuzzy.

5. **Packet-level vs atom-level `gpt_access`** — USER-DIRECTIVE-v1.0 says `gpt_access = FULL_SEMANTIC_ACCESS` for all knowledge. The schema supports per-atom `gpt_access` overrides. Is this override capability actually needed, or does it add unnecessary complexity?

6. **Retrieval budget defaults** — Current `DEFAULT_BUDGET = 50`. Is this too generous for embedded context (token cost) or too restrictive for deep exploration? Should it be configurable per QueryPlan intent?

7. **Evidence quality propagation** — When a CORRECTION atom supersedes an existing atom, should the old atom's `evidence_quality` downgrade, or is the supersession chain sufficient?

## Open Governance Questions

8. **Authority promotion path** — All atoms are `CANDIDATE_ONLY`. What's the process for promoting to `APPROVED`? Manual review? Automated after N verifications? Only via explicit GPT approval?

9. **Memory library integration with live system** — The memory library is standalone. How does it integrate with:
   - QCLAW's live trading agents?
   - The 8766-port Second Brain?
   - MaiBot's InnnerBrain?
   - The knowledge digester pipeline?

10. **Knowledge deduplication across scopes** — An atom with scope="test" might be semantically identical to one with scope="trading". Current deduplication is exact-match only (same canonical_statement). Should scope-agnostic semantic dedup be implemented?

## Open Implementation Questions

11. **Auto-FTS indexing** — FTS terms are manually indexed via `index_atom_terms()`. Should the store auto-index on insert (SQLite trigger or Python middleware)?

12. **Serialization format** — ContextBundle currently produces JSON. Is this the right format for GPT consumption, or should it be Markdown/MDX for better readability in chat context?

13. **Performance at scale** — Tested with 8 atoms. How does the retrieval engine behave at 10K+ atoms? FTS5 scales well but relation expansion (1-hop neighbors) could produce O(n²) joins without indexing.
