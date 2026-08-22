# E60 Adaptive Local Resource Policy

## Purpose and boundary

This policy keeps the desktop responsive when Codex, WorkBuddy, a game, or a
video editor may be active. It is intentionally an admission and containment
policy, not an instruction to minimize all local work. E60 remains
`research_only / NO_TRADE`; this policy does not inspect accounts, credentials,
market data, private configuration, or unrelated process command lines.

The controller starts in `FOREGROUND_PRIORITY`. It never assumes that an
unknown foreground state is idle. It can therefore run a tiny deterministic
lifecycle canary while an interactive application is present, but it cannot
promote the task to a batch profile without positive low-load evidence.

## Profiles

| Property | `FOREGROUND_PRIORITY` default | `IDLE_BATCH` conditional |
|---|---:|---:|
| Per-agent policy cap | 2 owned Python processes | 3 owned Python processes |
| Project hard cap | 4 owned Python processes | 6 owned Python processes |
| CPU-bound workers | 1 | 2 |
| Nested parallelism | forbidden | forbidden |
| Heavy local stage | one serial stage | one serial stage |
| E60 lifecycle canary | one root plus one grandchild | one root plus one grandchild |

`IDLE_BATCH` is admitted only after three successive samples with all of:

- `foreground_contention=false` explicitly supplied by the caller;
- no user-reported stutter and no unexpected task-owned process growth;
- CPU at or below 20 percent;
- at least 12 GiB available RAM.

The runtime does not classify applications by executable name to guess whether
the user is gaming or editing. Unknown foreground state remains in
`FOREGROUND_PRIORITY`.

## Immediate safety actions

| Observation | Action |
|---|---|
| Foreground contention | demote to `FOREGROUND_PRIORITY`; tiny canary may continue only if other gates are healthy |
| User-reported stutter or unexpected owned-process growth | stop new spawns and fail closed |
| RAM below 10 GiB | stop new spawns |
| RAM below 8 GiB | hard fail closed |
| CPU at or above 35 percent for 3 seconds | stop new spawns and back off |
| CPU above 40 percent for 5 seconds | hard fail closed |

The Issue #194 batch target allowed a wider 40–45 percent operating band. The
later E60 local-safety override requires fail-closed above 40 percent for five
seconds. This task applies the stricter rule; remote CI, rather than local
fan-out, supplies heavy capacity.

## Workload routing

Only `LIFECYCLE_CANARY` can be launched locally by this E60 controller. Local
`HEAVY_MATRIX` and `HIGH_CONCURRENCY_VALIDATION` are denied with
`REMOTE_CI_REQUIRED_FOR_HEAVY_OR_FANOUT_WORKLOAD`. GitHub Actions remains the
preferred execution surface for those workloads. Every local stage must end
with an ownership-scoped postflight process count of zero.

## Evidence and limits

The controller records a profile decision in each local execution receipt. Its
tests use synthetic samples only; they do not create CPU or RAM stress on the
user's desktop. The controller can govern only E60-owned descendants admitted
through its lease. It cannot safely terminate unrelated processes or establish
system-wide ownership for another agent that bypasses this route.
