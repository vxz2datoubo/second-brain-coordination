# QCLAW-P4-INDEPENDENT-ADVERSARIAL-EVIDENCE-0013A

## Independence Declaration

This adversarial query package was designed and built by QCLAW **without any
access to Codex's source code, test answers, runtime internals, or knowledge
store state.** No query was reverse-engineered from known Codex behavior.

**All expected answers are derived from QCLAW's own knowledge atomization
output** in the following directories:

- `QCLAW-KNOWLEDGE-ATOMIZATION/0008/` — architecture atoms
- `QCLAW-PEOS/0010/` — PEOS cognitive system atoms  
- `QCLAW-KELLY/0011/` — Kelly/Thorp position sizing atoms
- `QCLAW-DECISION-SCIENCE/0012/` — Decision science skill atoms

## Package Contents

**110 queries across 13 categories** targeting Issue #38 / PR #58:

| Category | Queries | Focus |
|---|---|---|
| AC-01 | 8 | Precise facts vs confusable near-matches |
| AC-02 | 8 | Negation, double negation, prohibition preservation |
| AC-03 | 8 | Missing premises, exceptions, conditional truth |
| AC-04 | 8 | Current vs historical versions, superseded content |
| AC-05 | 8 | Direct/implicit conflicts, boundary disputes |
| AC-06 | 10 | UNKNOWN recall, abstention precision |
| AC-07 | 8 | Forbidden recall (credential/financial values) |
| AC-08 | 8 | Source lineage, quality, cross-issue verification |
| AC-09 | 8 | Time/scope/type/state/confidence/language filters |
| AC-10 | 8 | 1-hop/2-hop/reverse/cycle dependency traversal |
| AC-11 | 10 | Mixed language, full-width, Unicode, synonyms |
| AC-12 | 8 | Budget overflow, conflict/UNKNOWN reservation |
| AC-13 | 8 | Credential induction, injection, authority escalation |

## Safety

- **PUBLIC_SAFE**: No credential values, API keys, tokens, private keys, or financial data
- **CANDIDATE_ONLY**: All atom references are candidate-quality (not authority/approved)
- **NO_TRADE**: No realtime market path, broker/account/order integration
- **No answer poisoning**: Expected/forbidden atom IDs are from QCLAW atoms, not Codex answers

## Usage (for Codex / PR #58)

1. Consume this package as-is — do NOT modify queries or answer keys
2. Execute all 110 queries against the Phase 4 gateway runtime
3. Record per-query results: pass/fail classification + actual atoms returned
4. Report mandatory metrics: overall %, conflict/UNKNOWN/forbidden recall rates
5. Do NOT delete failing queries or rewrite expected answers
6. Submit results for GPT independence review

## Non-Deliverables

- No runtime implementation (Codex maintains the single canonical runtime)
- No parallel database, fusion engine, or query planner
- No modification of Codex's branch or PR #58
- No claim of 100% coverage — this is an adversarial SAMPLE, not exhaustive

## AI_HANDOFF

See `AI_HANDOFF.yaml` for transition notes, UNKNOWNs encountered during design,
and recommendations for future expansion.
