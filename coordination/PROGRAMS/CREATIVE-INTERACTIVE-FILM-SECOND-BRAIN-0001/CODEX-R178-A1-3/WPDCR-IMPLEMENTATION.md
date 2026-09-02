# R178 work process, difficulty, discovery and coordination report

`agent_id: CODEX`

## Work process and difficulty

Fresh governance was read from canonical main and implementation used a new
task-owned standalone clone at the exact R177 dependency head. The D2 slice
added immutable DirectorBrief/v2 compiled content, stateless multi-script
selection and switching, full-field inspection, 10 lifecycle/attack tests,
documentation, scope tooling and one-suite CI. Total creative regression reached
61 tests.

## Failures and changes

One test exposed that a manual stale package hash escaped the director exception
boundary as a registry exception. The compiler now normalizes that rejection
while preserving its exact code. The first verification clone timed out and a
bad follow-up harness printed PASS despite earlier failures; that output was
discarded. A targeted fetch completed the clone and a fail-fast command reran
all 61 tests, scope and diff successfully.

## Discoveries and opportunities

- Pure switching avoids hidden shared state across users.
- Recomputed outer hashes do not establish truth; recompile-and-compare does.
- The player NarrativeState join and shot-policy compiler are future governed
  slices, not implicit extensions of content compilation.

## Coordination and next gate

GPT R172 player/session authority, WorkBuddy #532 and predecessor PRs #535/#537
were untouched. No director/media job authority exists. Create a stacked Draft
PR, run exact-head CI, then freeze it until the predecessor chain is independently
accepted and canonicalized.
