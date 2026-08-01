# BrainOps Codex App-First Activation Addendum v1.1

Status: `PLAN_ONLY / DRAFT / NOT_ACTIVATED`

Applies to:

- `BRAINOPS-LOCAL-AGENT-SERVICE-AND-PORT-CONTROL-PLANE-v1.0.md`
- `CODEX-BRAINOPS-LOCAL-CONTROL-PLANE-P0-P1-0001-AMED.yaml`
- `.agents/skills/brainops-control-plane/SKILL.md`

This addendum supersedes any interpretation that makes Codex CLI the preferred human-facing execution surface.

## 1. Verified product state

OpenAI's July 16, 2026 desktop update placed ChatGPT and Codex behind one global switcher in the same Windows/macOS desktop application.

This is a shared desktop shell, not a complete workflow merge:

- Codex remains a separate view;
- Codex history remains separate from ChatGPT history;
- Codex keeps its local repository, folder, terminal and developer-tool workflows;
- ChatGPT Voice can coordinate Work and Codex in the desktop application;
- Codex App Automations can run recurring tasks on a schedule and return results to a review queue;
- local automations depend on the computer being awake and the desktop application running;
- current official documentation does not expose a stable public local IPC/API for an external program to create or start a new Codex App thread on demand;
- cloud-trigger support for Codex App Automations has been described as future work, so it must not be assumed available locally.

## 2. Revised architecture decision

### Primary operator and execution surface

Use the integrated ChatGPT desktop application's **Codex view** as the preferred user-facing execution environment.

It owns:

- human-visible Codex task threads;
- project/folder context;
- approvals and questions;
- task progress, diffs, terminal output and test results;
- App-native Automations;
- review queue;
- remote/mobile supervision when supported;
- voice coordination when enabled.

### Primary unattended activation path

Prefer a Codex App Automation that periodically returns to one dedicated BrainOps reconciler thread, reads the canonical GitHub route and performs the route gates.

Desired cadence: every 30 minutes.

The local capability probe must verify whether the installed Codex view supports this exact cadence. Until verified, classify it as `UNKNOWN`, not `SUPPORTED`.

The automation must:

1. read canonical `ACTIVE-CODEX-TASK.yaml` and activation manifest;
2. compare route epoch and reviewed head;
3. respect global/per-agent automation switches;
4. claim a lease only when all gates pass;
5. begin or continue work inside the Codex App thread/worktree model;
6. return results to the App review queue;
7. remain silent when there is no new executable route;
8. fail closed when the App host is unavailable, usage-limited or paused.

### CLI/SDK role

Codex CLI is retained as a **machine execution fallback and compatibility backend**, not the preferred human-facing path.

Use CLI/SDK only when one of these conditions is true:

- App-native Automations cannot support the required schedule;
- immediate event-driven execution is required and no App trigger API exists;
- deterministic JSONL output or machine-readable health is required;
- the App cannot be kept awake/running reliably;
- a recovery path is needed after App failure;
- a future official App API delegates to the same Codex runtime.

The control plane must not use Windows UI automation, simulated mouse/keyboard input, accessibility scraping or undocumented process injection to operate the Codex App.

## 3. Hybrid runtime model

```text
GPT publishes reviewed route
        |
        +--> canonical GitHub control state
                    |
                    +--> Codex App Automation (preferred, 30-minute reconciliation)
                    |        |
                    |        +--> visible Codex thread / approvals / review queue
                    |
                    +--> CLI/SDK fallback runner (disabled by default)
                             |
                             +--> deterministic headless execution when explicitly permitted
```

The two runners share the same route, lease, fencing and idempotency contracts. They must never execute the same route concurrently.

## 4. BrainOps dashboard changes

The dashboard must distinguish:

- `Codex Desktop Host`: whether the integrated ChatGPT desktop application and Codex view are available;
- `Codex App Automation`: enabled, paused, last run, next run, thread identity, last result;
- `Codex App Active Task`: current visible task/thread and attention state;
- `Codex CLI Fallback`: installed, authenticated, disabled/enabled, active session;
- `Dispatch Owner`: APP_AUTOMATION, CLI_FALLBACK, MANUAL_APP, NONE;
- `Host Availability`: AWAKE, APP_RUNNING, APP_UNAVAILABLE, USAGE_LIMITED, UNKNOWN.

The desktop application is an external user application by default, not a child process owned by BrainOps. The normal controls are:

- pause BrainOps App automation;
- disable new task dispatch;
- request safe stop at checkpoint;
- open/show Codex view where supported;
- show instructions when direct App control is unsupported.

BrainOps must not terminate the entire ChatGPT desktop application merely to stop one task, except through an explicit user-confirmed emergency action.

## 5. P0 capability probes added

Codex must inspect and report without exposing credentials:

- installed ChatGPT desktop app version;
- presence of the ChatGPT/Codex global switcher;
- whether the Codex view is available on this account;
- whether App Automations are available;
- supported automation cadence and whether 30-minute recurrence is accepted;
- whether an automation can return to the same Codex thread;
- whether task results appear in a review queue;
- whether the App must remain open and the machine awake;
- whether a documented local trigger, deep link, URI scheme, app intent, command or API exists;
- whether remote/mobile access is available for this Windows host;
- whether voice coordination is available in Codex view;
- whether App and CLI share session history/configuration in the installed build;
- CLI fallback version, auth state and JSONL support.

Every item must be classified `SUPPORTED / UNSUPPORTED / UNKNOWN / BLOCKED` with observed evidence.

## 6. Revised rollout

### P0

Discover App, Automation and CLI capabilities. No task execution.

### P1

Read-only dashboard showing App host, automation, route and CLI fallback fixtures/observations.

### P2

Manual enable/disable of BrainOps reconciliation state. Do not automate UI interactions with Codex.

### P3

Codex App Automation shadow reconciler. It reads routes and reports `WOULD_DISPATCH / WOULD_BLOCK` only.

### P4

Manual App-first dispatch through a user-visible Codex thread, with CLI fallback still disabled.

### P5

Bounded App-native automatic dispatch. CLI fallback may be enabled only through a separate explicit gate.

### P6

Optional event-driven CLI/SDK or future official App-trigger integration.

## 7. Acceptance rule

The implementation must prefer the Codex App whenever it can meet the required reliability and safety contract.

It must not choose CLI merely because CLI is easier to script. It may choose CLI as fallback only after documenting the exact App limitation and preserving the App as the primary monitoring and interaction surface where possible.
