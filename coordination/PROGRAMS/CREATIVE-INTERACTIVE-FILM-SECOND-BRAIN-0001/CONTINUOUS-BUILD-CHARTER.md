# Continuous Build Charter — Creative Runtime

agent_id: CODEX

## Operating change authorized by the user

This branch uses a **continuous build window**. CODEX keeps implementing,
testing, researching, and performing clean-environment reproduction until the
user explicitly says `收尾`, `停止`, or an equivalent close-out instruction.
Routine implementation checkpoints are safety records only; they do not create
a GPT review request and do not interrupt the build for a micro-review.

At close-out, CODEX freezes an exact head, completes a clean reproduction,
collects one consolidated evidence packet, and directly sends GPT a single
audit request. GPT remains a separate reviewer/integrator; CODEX does not
self-accept, mark ready, or merge its own work.

## Current branch

- branch: `codex/creative-runtime-continuous-build`
- baseline: `1a514fe839b1c47a14d7fad4a96e8c9fd2365338`
- working focus: coherent continuity/runtime validation, user-understanding
  mapping, knowledge provenance, deterministic quality metrics, and clean
  replay.

## Safety boundaries

- No credentials, provider calls, paid/external generation, public release,
  deployment, trade execution, or canonical knowledge-store write.
- No modification of frozen candidate PRs #493, #495, #502, #506, #508, #511,
  or #513.
- No force push, rebase, amend, reset, or history rewrite.
- External research is cited as a candidate design input, never imported as
  proprietary content or automatically promoted to knowledge.
- GitHub is the source of executable synthetic/runtime evidence. Any future
  customer intake runs locally in a separately approved, gitignored adapter;
  no customer record, media, cache, account, cookie, or credential may enter
  this branch.

## Verification cadence

1. Fast local tests after coherent code changes.
2. Full local standard-library suite at milestone checkpoints.
3. Fresh-clone / clean-worktree reproduction for major milestones and close-out.
4. One concentrated GPT independent review only after user-directed close-out.

GitHub additionally runs the same offline suite on the exact submitted commit
through `.github/workflows/creative-runtime-offline.yml` using Python 3.11 and
3.13. This is reproducibility evidence, not an approval to deploy or receive
customer data.

The reproducibility entry point is `python tools/verify_creative_runtime.py
--expected-head <frozen-SHA>`. It checks identity, the full creative test suite,
diff whitespace, a three-scene play-through, verified timeline/director input,
understanding-map drift gate, review-only knowledge derivation, and v1-to-v2
migration. Its JSON receipt is execution evidence, not self-acceptance.

## What the user should expect

The user does not need to approve each implementation detail. They only need
to intervene for a scope/risk decision, a true hard blocker, or when they want
the branch to enter the close-out audit phase.
