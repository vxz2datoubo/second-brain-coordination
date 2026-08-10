---
name: brainops-control-plane
description: Design, review, implement or operate the local Second Brain control plane for Codex App/CLI and QQ task reconciliation, background processes, Windows services, Docker services, ports, health checks, logs, kill switches and future MaiBot voice endpoints. Prefer the integrated ChatGPT desktop application's Codex view as the user-facing execution and supervision surface; keep CLI/SDK as a bounded fallback. Trigger for local executor automation, service dashboards, port conflicts, start/stop management, route polling, agent dispatch, observability and operational safety. Do not use to grant trading authority or bypass active task routes.
---

# BrainOps Control Plane Skill

## Purpose

Use this skill to turn loosely described local automation needs into one safe and visible operations model for the Second Brain ecosystem.

The skill covers:

- agent review and execution handoffs;
- Codex App-first activation and supervision;
- Codex CLI/SDK fallback execution;
- background process supervision;
- user-session versus system-service separation;
- service and port registration;
- health and readiness checks;
- start, stop, restart, pause and emergency-stop behavior;
- audit logs and observability;
- future MaiBot voice/audio endpoints;
- GitHub route reconciliation.

It does not grant permission to execute a task. Canonical route files, route epochs, leases, activation manifests and user gates remain authoritative.

## Fundamental principles

1. Visibility before autonomy.
2. Reversible local control before unattended execution.
3. Desired state and observed state are separate facts.
4. Event triggers require periodic reconciliation because messages can be delayed, duplicated or lost.
5. Every mutating operation is idempotent, fenced and audited.
6. Prefer the integrated ChatGPT desktop application's Codex view for normal user-visible task execution and supervision.
7. Retain Codex CLI/SDK as a disabled-by-default fallback when App-native Automations or official App triggers cannot satisfy the reliability contract.
8. Never automate the Codex App through simulated UI input, accessibility scraping or undocumented process injection.
9. User-authenticated agents run in the user session unless evidence supports another host.
10. System infrastructure may run as a Windows Service only when it does not depend on interactive user credentials.
11. Ports are named resources with ownership, exposure and health, not anonymous integers.
12. No arbitrary shell execution from the management UI.
13. Unknown capabilities remain UNKNOWN until probed.

## Required context collection

Before proposing or implementing changes, collect and classify:

- operating system and execution account;
- repository and active route;
- installed ChatGPT desktop app version;
- presence of the ChatGPT/Codex global switcher and Codex view;
- Codex App Automation availability, cadence, thread continuation and review queue behavior;
- documented App trigger/deep-link/API availability;
- installed runtimes and tools;
- Codex CLI version, auth state and supported commands without reading secrets;
- existing Second Brain processes, services and ports;
- Docker availability;
- expected MaiBot components;
- user approval boundaries;
- whether the requested operation is read-only, manual-control or automatic-control.

Use the four-state capability vocabulary:

- `SUPPORTED`
- `UNSUPPORTED`
- `UNKNOWN`
- `BLOCKED`

Do not infer `SUPPORTED` from documentation alone. Local capability evidence is required.

## Architecture mapping workflow

### Step 1: identify the control subject

Classify each component as one of:

- Codex desktop host/view;
- Codex App Automation;
- Codex CLI/SDK fallback;
- user-session agent;
- native background process;
- Windows Service;
- Docker Compose service;
- external monitored endpoint;
- audio/voice stage;
- scheduled reconciler.

### Step 2: separate control plane and data plane

Control plane:

- registry;
- desired state;
- leases/fencing;
- start/stop policy;
- health aggregation;
- audit;
- UI;
- task-route interpretation.

Data plane:

- Codex App task execution;
- bounded Codex CLI fallback execution;
- Second Brain APIs and workers;
- databases and retrieval;
- MaiBot STT/TTS/dialogue/audio processes;
- project-specific workloads.

The control plane must never silently become a data-processing monolith.

### Step 3: select the Codex runner

Use `APP_AUTOMATION` when the installed Codex view can satisfy schedule, project context, permissions, review queue and reliability requirements.

Use `MANUAL_APP` for user-approved visible execution before unattended dispatch is released.

Use `CLI_FALLBACK` only when:

- App Automations cannot support the required recurrence;
- immediate event-driven dispatch is required and no official App trigger exists;
- deterministic JSONL or machine-readable health is necessary;
- the App host cannot remain available reliably;
- recovery from an App failure is required;
- a future official App API delegates to a machine runner.

Record the selected dispatch owner and prevent concurrent App and CLI execution of the same route.

### Step 4: select the host

Use a user-session host when the component requires:

- ChatGPT/Codex OAuth;
- Codex desktop view;
- desktop audio devices;
- user profile files;
- interactive tools;
- desktop notifications.

Use a Windows Service when the component requires:

- boot-time availability;
- no interactive credentials;
- durable infrastructure behavior;
- system-managed recovery.

Use Docker when the component is isolated, stateless or infrastructure-oriented and Docker is already available. Docker absence must not block native MVP work.

### Step 5: define the service manifest

A service manifest must include:

- stable service ID;
- display name;
- adapter;
- run context;
- App automation/thread identity or executable/service/container identity;
- allowlisted working directory and argument template when applicable;
- desired start policy;
- dependencies;
- ports/pipes;
- health and readiness checks;
- restart/circuit-breaker policy;
- logs;
- secret handling;
- safety boundary.

Reject manifests that contain secrets, traversal paths, arbitrary commands, public management binds or unbounded retry loops.

### Step 6: define the port contract

For each endpoint record:

- logical name;
- protocol;
- address;
- port/range/pipe;
- exposure class;
- owner;
- consumers;
- probe;
- collision behavior;
- allocation generation.

Default management exposure is `LOOPBACK_ONLY`.

### Step 7: define state and lifecycle

Desired state:

- RUNNING
- STOPPED
- PAUSED
- DISABLED

Observed state:

- UNKNOWN
- STARTING
- HEALTHY
- DEGRADED
- UNHEALTHY
- STOPPING
- STOPPED
- BLOCKED

Codex-specific observed host states may include:

- APP_RUNNING
- APP_UNAVAILABLE
- AUTOMATION_ENABLED
- AUTOMATION_PAUSED
- USAGE_LIMITED
- USER_ATTENTION_REQUIRED
- CLI_FALLBACK_DISABLED

Transitions must be explicit, time-bounded and audited.

### Step 8: define process-tree containment

For managed native Windows processes, prefer verified whole-process-tree supervision such as Job Objects. A stop action must confirm that children and owned ports were released. Graceful shutdown occurs before forced termination.

The integrated ChatGPT desktop application is external user software by default. Do not treat the whole application as a child process or terminate it to stop one task without explicit user-confirmed emergency authority.

### Step 9: add health and observability

Distinguish:

- liveness: process or App host can respond;
- readiness: component can accept work;
- dependency health;
- task/route health;
- App automation health;
- usage-limit state;
- user-attention-required state.

Emit structured logs. Keep secret values redacted. Use real-time UI updates with polling/reconciliation fallback.

## Codex route reconciliation

A local Codex dispatcher may execute only after all gates pass:

1. target is CODEX;
2. route is READY;
3. `execution_allowed` is true;
4. `automatic_dispatch_allowed` is true for unattended dispatch;
5. blockers are empty;
6. route epoch is newer than the last claim;
7. reviewed/base head matches remote state;
8. activation manifest is consistent;
9. no valid lease exists;
10. no user approval is required;
11. global automation switch is enabled;
12. the chosen App Automation or fallback executor is enabled;
13. dispatch owner fencing prevents App and CLI from claiming the same route.

On any mismatch, return `DO_NOT_EXECUTE` with a machine reason.

Prefer a dedicated Codex App Automation/reconciler thread for periodic activation. Desired cadence may be 30 minutes, but the installed App must prove that cadence is supported.

Use exact App automation/thread identities and exact CLI session IDs for resume. Do not resume an unrelated session through an ambiguous latest-session shortcut.

When CLI fallback is used, output should be structured JSONL. Persist only safe event summaries and the exact session identity.

## Review-request reconciliation

Completion reports from Codex or QQ must become structured review requests with:

- source agent;
- task ID;
- route epoch;
- PR and branch;
- reviewed base;
- tested head;
- receipt head;
- completion signal;
- CI and archive evidence;
- idempotency key;
- requested review scope.

Use an event-driven route for low latency and a scheduled anti-entropy scan for missed events.

Duplicate requests are deduplicated by agent, task ID, route epoch and tested head.

## Dashboard design rules

Always make these controls visible:

- global automation enable/disable;
- pause new dispatches;
- pause Codex App reconciliation;
- stop after safe checkpoint;
- terminate current managed fallback process;
- emergency stop all managed processes;
- per-service enable/disable;
- logs and health details.

Always show:

- Codex desktop host availability;
- App Automation state, last run, next run and thread identity;
- desired and observed state;
- dispatch owner: APP_AUTOMATION, CLI_FALLBACK, MANUAL_APP or NONE;
- PID/service/container identity where applicable;
- ports;
- current task/lease;
- uptime and restart count;
- last action and error;
- last GitHub sync;
- controller version and configuration generation.

Mutating controls must explain why they are disabled in read-only or shadow phases.

## Rollout policy

Use this sequence:

1. P0 capability discovery and threat model, including Codex App/Automation probes.
2. P1 read-only dashboard.
3. P2 bounded manual control of BrainOps state, not UI automation.
4. P3 shadow Codex App route reconciliation.
5. P4 manual App-first Codex dispatch.
6. P5 bounded App-native automatic dispatch.
7. P6 optional CLI/SDK event fallback, system service, Docker and MaiBot voice adapters.

Never jump directly from design to unattended execution.

## Failure and safety patterns

Implement and test:

- idempotency keys;
- route-epoch fencing;
- runner-owner fencing between App and CLI;
- leases with expiry;
- bounded retries with backoff;
- circuit breakers;
- dead-letter/block queues;
- audit events;
- offline-safe behavior;
- App unavailable/closed/asleep behavior;
- usage-limit behavior;
- UI/state resynchronization;
- secret redaction;
- orphan-process detection;
- port-collision detection;
- dependency readiness;
- emergency local shutdown independent of GitHub.

## QQ/QCLAW rule

QQ aliases do not override canonical route state. If the canonical QQ route is paused, blocked, disabled or `execution_allowed: false`, the control plane must not dispatch it, even if an old completion signal or user-interface state suggests otherwise.

## MaiBot voice mapping

Treat the future voice chain as separate services:

- capture;
- VAD;
- STT;
- dialogue/agent;
- TTS;
- playback;
- websocket/terminal gateway.

Each stage gets its own health, latency, port or pipe, logs and start/stop state. Do not collapse all stages into one opaque process.

## Output requirements

When this skill is used for a design or review, return:

- the selected architecture;
- App-first versus CLI-fallback decision and evidence;
- rejected alternatives and why;
- known/unknown capability map;
- component and port map;
- security boundaries;
- phased rollout;
- acceptance gates;
- exact Codex task wording when implementation is needed.

When this skill is used for implementation, obey the active task route and stop at its acceptance gate.

## Canonical local blueprint

Read and follow both:

- `coordination/BLUEPRINTS/BRAINOPS-LOCAL-AGENT-SERVICE-AND-PORT-CONTROL-PLANE-v1.0.md`
- `coordination/BLUEPRINTS/BRAINOPS-CODEX-APP-FIRST-ACTIVATION-ADDENDUM-v1.1.md`
