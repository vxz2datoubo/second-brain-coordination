# R177 work process, difficulty, discovery and coordination report

`agent_id: CODEX`

## Work process

Fresh canonical governance was read from main, while implementation started in
a new standalone clone at the exact R176 technical-dependency head. The slice
implemented catalog serialization, atomic materialization, strict reload,
immutable enumeration/lookup/selection, a DirectorBrief/v2 binding, adversarial
tests, documentation, scope verification and single-suite exact-head CI.

## Difficulty

Planned and actual difficulty: **D2**. The hardest part was maintaining three
different invariants simultaneously: immutable content identity, crash-safe
persistence and no accidental session/director-job authority. Observable
evidence is the 51-test lifecycle and attack suite plus clean-clone replay.

## Changes from the initial method

The initial atomic temp-file design was strengthened before commit with an
exclusive lock because atomic replacement alone permits two concurrent creators
to race and replace the same immutable target. Exact duplicate packages and
untyped director inputs were also made explicit violations.

## Failed attempts and negative results

No test or implementation command failed in this slice. Filesystem read-only
attributes and a database were evaluated and rejected as unnecessary or
platform-coupled. No arbitrary catalog size threshold was invented without data.

## Discoveries and expansion

- Shared immutable scripts plus per-player delta ledgers are the correct future
  storage boundary for many users playing one script.
- A stale lock must remain UNKNOWN rather than be deleted by elapsed time alone.
- Target-hardware catalog limits need measured bytes, count, latency and memory.
- Full DirectorBrief/v2 compilation is the next architectural consumer but is
  outside this slice.

## Exact coordination

GPT R172 retains all PlayerCampaign, CreativeSession/v2, migration and save-slot
write authority. WorkBuddy #532 retains its ordered validation batch and paths.
PR #535 and the R176 branch were not modified. R177 remains stacked technical
evidence and inherits neither acceptance nor canonicality.

## Next gate

Create a Draft R177 PR, observe exact-head CI, and freeze it. It cannot become
Ready or merge until R176 is independently accepted and canonicalized, followed
by a separate R177 review request.
