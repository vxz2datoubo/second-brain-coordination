# Work Process, Discoveries, Coordination and Risk Report

## Scope and actual profile

- `task_id`: `CODEX-BRAINOPS-APP-FIRST-AUTOMATIC-REVIEW-EXECUTION-CONTROL-PLANE-0030-E35`
- `agent_id`: `CODEX`
- Requested model/profile: `gpt-5.6-sol`, maximum reasoning, X4.
- Actual model/profile evidence exposed to this task: `ACCESS_NOT_EXPOSED`.
- Boundary retained: `LOCAL_FIRST / APP_FIRST / READ_ONLY_AND_SHADOW_ONLY / PUBLIC_SAFE / NO_TRADE`.

## Discovery and difficulty

The main architectural difficulty is that the desired user experience is
App-first automation, while local proof of App Automations, schedules, review
queue semantics and an external activation contract was unavailable. Treating
the desktop package or an executable name as proof would create a false control
path. P0 therefore records those facts as `UNKNOWN` and keeps the App-first
ownership type as a policy-level preference only.

A `dotnet` command was discoverable, but P0 did not obtain a usable SDK listing.
Instead of introducing a partially supported runtime, P1 uses a standard-library
Python equivalent. This preserves the required loopback/read-only controls and
matches the repository's current implementation substrate.

## Negative and unexpected findings

- The existing SuperBrain port `8766` was listening during P0. It is protected
  and was not touched.
- Candidate port `32100` was not listening at that observation time, but that is
  not a reservation or an approval to use it.
- The first web-test fixture attempted to use port `0`, which the production
  manifest correctly rejects. The fixture was corrected to request a temporary
  loopback port before construction; the production validation was not relaxed.
- Fetching the official Codex manual helper returned HTTP 403. This is logged as
  unavailable documentation evidence, not as an absence claim about the App.

## Improvement opportunities

1. Add an independently auditable manual capability observation protocol for
   App Automations without collecting session material.
2. Attach the source event watcher to a read-only GitHub reader only after a
   separate transport/authorization route is active.
3. Add a dedicated lifecycle route for an allowlisted, human-approved service
   executor; never reuse this read-only console as an executor.

## Coordination required

GPT must perform the requested second pass. A later route needs user approval
and an official/local App capability record before making the automation switch
anything other than a disabled visual control.
