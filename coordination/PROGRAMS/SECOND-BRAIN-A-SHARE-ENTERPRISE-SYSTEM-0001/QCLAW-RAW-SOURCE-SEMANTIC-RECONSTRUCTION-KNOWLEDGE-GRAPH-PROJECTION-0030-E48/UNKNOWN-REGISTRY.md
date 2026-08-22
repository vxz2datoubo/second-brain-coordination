# UNKNOWN-REGISTRY — E48

> Per AMED-ENTERPRISE-POLICY-v1.0 and E48 hard-boundary rules, every
> UNKNOWN surfaced during E48 execution is logged here for GPT
> secondary review. Each entry is CANDIDATE_ONLY and does not become
> authority.

| ID | Category | Statement | Source | Why unknown | Proposed next step |
|----|----------|-----------|--------|-------------|--------------------|
| UNK-E48-001 | governance | Should E48 branch rebase onto canonical main `f8dfc72` before merge? | RTCE hard rule "no rebase/force/amend of plan commit" conflicts with merge-base freshness | Plan commit `e6e375c` was authored before `f8dfc72` (E61 authority routing); main advanced by one commit | GPT review decides whether to accept rebased PR or leave as-is |
| UNK-E48-002 | integration | E47 stub in `tests/_e47_stub.py` is a hand-written reproduction of E47 schema | E47 lives in PR #207 head, not yet merged into main | We cannot import the live E47 module until PR #207 merges | When PR #207 merges, replace `_e47_stub.py` with `import qclaw_e47_digest` |
| UNK-E48-003 | visualization | vis-network CDN pin vs. vendored offline copy | Dependency audit recommends pinning; offline operation requires vendoring | CDN requires network at *view time*; E48 only constraint is on task runtime | Codex or WorkBuddy may add `vendor/vis-network/` later if requested |
| UNK-E48-004 | coverage | Python 3.11 test pass is not verified locally | Only Python 3.13 is installed | The contract requires both 3.11 and 3.13 pass | Codex CI or WorkBuddy to run on 3.11 |
| UNK-E48-005 | baseline drift | One main commit between E48 base and current main | `f8dfc72` adds an E61 authority routing decision | E48's E61 digest bundle is a *content* addition, not a new authority, but the contract requires GPT clarification | GPT review |
| UNK-E48-006 | cross-sentence relation | "if-volume-then-price" mechanism is captured as 2-3 atoms; whether the L1 should also produce a cross-sentence `Relation` is open | Currently relations live in L2 only; L1 only carries edits | Could overload L1 OR keep relations strictly in L2 | Discussed in plan; recommend keep L2-only, monitor Codex/W3 feedback |

## Resolution rules

- No UNKNOWN may be silently resolved in autonomous mode.
- Every UNKNOWN closure requires either an explicit GPT decision OR a
  new task ticket with a new ACTIVE-* lease.
- This registry is the source of truth; chat history is not.