---
name: brainops-control-plane
description: Design, review, implement or operate the local Second Brain control plane for Codex/QQ task reconciliation, background processes, Windows services, Docker services, ports, health checks, logs, kill switches and future MaiBot voice endpoints. Trigger for local executor automation, service dashboards, port conflicts, start/stop management, route polling, agent dispatch, observability and operational safety. Do not use to grant trading authority or bypass active task routes.
---

# BrainOps Control Plane Skill

## Purpose

Use this skill to turn loosely described local automation needs into one safe and visible operations model for the Second Brain ecosystem.

The skill covers:

- agent review and execution handoffs;
- background process supervision;
- user-session versus system-service separation;
- service and port registration;
- health and readiness checks;
- start, stop, restart, pause and emergency-stop behavior;
- audit logs and observability;
- future MaiBot voice/audio endpoints;
- GitHub route reconciliation and Codex non-interactive execution.

It does not grant permission to execute a task. Canonical route files, route epochs, leases, activation manifests and user gates remain authoritative.

## Fundamental principles

1. Visibility before autonomy.
2. Reversible local control before unattended execution.
3. Desired state and observed state are separate facts.
4. Event triggers require periodic reconciliation because messages can be delayed, duplicated or lost.
5. Every mutating operation is idempotent, fenced and audited.
6. User-authenticated agents run in the user session unless evidence supports another host.
7. System infrastructure may run as a Windows Service only when it does not depend on interactive user credentials.
8. Ports are named resources with ownership, exposure and health, not anonymous integers.
9. No arbitrary shell execution from the management UI.
10. Unknown capabilities remain UNKNOWN until probed.

## Required context collection

Before proposing or implementing changes, collect and classify:

- operating system and execution account;
- repository and active route;
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

- Codex task execution;
- Second Brain APIs and workers;
- databases and retrieval;
- MaiBot STT/TTS/dialogue/audio processes;
- project-specific workloads.

The control plane must never silently become a data-processing monolith.

### Step 3: select the host

Use a user-session host when the component requires:

- ChatGPT/Codex OAuth;
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

### Step 4: define the service manifest

A service manifest must include:

- stable service ID;
- display name;
- adapter;
- run context;
- executable or service/container identity;
- allowlisted working directory and argument template;
- desired start policy;
- dependencies;
- ports/pipes;
- health and readiness checks;
- restart/circuit-breaker policy;
- logs;
- secret handling;
- safety boundary.

Reject manifests that contain secrets, traversal paths, arbitrary commands, public management binds or unbounded retry loops.

### Step 5: define the port contract

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

### Step 6: define state and lifecycle

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

Transitions must be explicit, time-bounded and audited.

### Step 7: define process-tree containment

For native Windows processes, prefer verified whole-process-tree supervision such as Job Objects. A stop action must confirm that children and owned ports were released. Graceful shutdown occurs before forced termination.

### Step 8: add health and observability

Distinguish:

- liveness: process can respond;
- readiness: component can accept work;
- dependency health;
- task/route health;
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
12. Codex executor service is enabled.

On any mismatch, return `DO_NOT_EXECUTE` with a machine reason.

Use exact Codex session IDs for resume. Do not resume an unrelated session through an ambiguous latest-session shortcut.

Codex output should be structured JSONL when automated. Persist only safe event summaries and the exact session identity.

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
- stop after safe checkpoint;
- terminate current managed process;
- emergency stop all managed processes;
- per-service enable/disable;
- logs and health details.

Always show:

- desired and observed state;
- PID/service/container identity;
- ports;
- current task/lease;
- uptime and restart count;
- last action and error;
- last GitHub sync;
- controller version and configuration generation.

Mutating controls must explain why they are disabled in read-only or shadow phases.

## Rollout policy

Use this sequence:

1. P0 capability discovery and threat model.
2. P1 read-only dashboard.
3. P2 bounded manual start/stop.
4. P3 shadow route reconciliation.
5. P4 manual Codex dispatch.
6. P5 bounded automatic dispatch.
7. P6 optional system service, Docker and MaiBot voice adapters.

Never jump directly from design to unattended execution.

## Failure and safety patterns

Implement and test:

- idempotency keys;
- route-epoch fencing;
- leases with expiry;
- bounded retries with backoff;
- circuit breakers;
- dead-letter/block queues;
- audit events;
- offline-safe behavior;
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
- rejected alternatives and why;
- known/unknown capability map;
- component and port map;
- security boundaries;
- phased rollout;
- acceptance gates;
- exact Codex task wording when implementation is needed.

When this skill is used for implementation, obey the active task route and stop at its acceptance gate.

## Canonical local blueprint

Read and follow:

`coordination/BLUEPRINTS/BRAINOPS-LOCAL-AGENT-SERVICE-AND-PORT-CONTROL-PLANE-v1.0.md`
