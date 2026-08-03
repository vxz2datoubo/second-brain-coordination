# BrainOps Local Agent, Service and Port Control Plane v1.0

Status: `PLAN_ONLY / DRAFT / NOT_ACTIVATED`

Owner: GPT architecture and review control plane

Target implementer: Codex after explicit route activation

Boundary: `LOCAL_FIRST / PUBLIC_SAFE_REPOSITORY_METADATA_ONLY / NO_TRADE / NO_REAL_ACCOUNT_ACTION`

> **Architecture update:** Read `BRAINOPS-CODEX-APP-FIRST-ACTIVATION-ADDENDUM-v1.1.md` together with this document. The integrated ChatGPT desktop application's Codex view is now the preferred user-facing execution and supervision surface. Codex CLI/SDK is a bounded, disabled-by-default fallback. Where this v1.0 document speaks of direct CLI dispatch as the normal path, the v1.1 addendum supersedes that interpretation.

## 1. Fundamental goal

Create one visible local operations console for the Second Brain ecosystem that can safely show, start, stop, restart, pause and diagnose:

- the Codex App route reconciler and task executor;
- the optional Codex CLI/SDK fallback executor;
- the GPT review-request watcher;
- Second Brain backend APIs, databases and retrieval workers;
- future MaiBot voice, microphone, speech-to-text, text-to-speech and terminal endpoints;
- native Windows processes;
- Windows Services;
- Docker Compose services;
- external endpoints that are monitored but not controlled.

The console must make automation visible and reversible. The user must always be able to see whether an executor is running, disable all automatic execution, disable one service, and inspect the latest action, logs, port, process identity and health result.

## 2. Non-goals for the first delivery

The first delivery must not:

- expose the console to the public network;
- place secrets, OAuth tokens or credentials in Git or SQLite;
- grant arbitrary shell execution from the browser;
- auto-merge pull requests;
- activate QQ while `execution_allowed: false`;
- run real trading, account, order or broker actions;
- replace existing task-route, lease, route-epoch, receipt or GPT review protocols;
- force ChatGPT/Codex or CLI fallback into a Windows system account that cannot access the user OAuth session;
- use simulated mouse/keyboard input, accessibility scraping or undocumented process injection to control the Codex App;
- install Docker, .NET SDK, databases or system services without an explicit capability report and approval gate.

## 3. Selected architecture

Use a split-host design rather than one oversized daemon.

### 3.1 BrainOps Console

A local ASP.NET Core application, preferably a Blazor Web App, serving only on `127.0.0.1` by default.

Responsibilities:

- web dashboard and control actions;
- service and port registry;
- current/desired-state reconciliation;
- audit records;
- health aggregation;
- adapter routing;
- real-time status updates through SignalR;
- read-only GitHub review/task state view;
- global automation kill switch.

Default management endpoint: `127.0.0.1:32100`, configurable and protected by a local secret generated outside Git.

### 3.2 BrainOps User Agent

A user-session process launched at login, initially through Windows Task Scheduler or a startup shortcut.

It coordinates components that require the user's profile, OAuth session or desktop-local files, especially:

- integrated ChatGPT desktop application / Codex view availability;
- Codex App Automation state and route reconciliation;
- optional Codex CLI/SDK fallback execution;
- QQ/QCLAW local client if a controllable interface is later discovered;
- MaiBot user-session microphone and audio-device processes;
- interactive tools that cannot run under `LocalSystem` or `LocalService`.

The user agent must not be silently converted into a system service.

### 3.3 BrainOps Host Service, optional later phase

A Windows Service implemented with .NET Worker Service for infrastructure that does not require interactive user credentials:

- Second Brain API hosts;
- databases or local queues;
- stable retrieval/indexing workers;
- system-level port and dependency monitoring;
- Docker Compose adapters;
- durable audit and health publication.

The Host Service and User Agent communicate through an authenticated local channel. Prefer Windows named pipes for privileged control. The browser only talks to the Console API on localhost.

### 3.4 Hybrid process adapters

Define one adapter interface and separate implementations:

1. `CodexDesktopHostAdapter`
2. `CodexAppAutomationAdapter`
3. `CodexCliFallbackAdapter`
4. `NativeProcessAdapter`
5. `WindowsServiceAdapter`
6. `DockerComposeAdapter`
7. `ExternalEndpointAdapter`
8. `ScheduledReconcilerAdapter`
9. future `MaiBotVoiceAdapter`

No adapter may accept arbitrary executable paths or shell strings from UI input. Executables, work directories and arguments come from an allowlisted service manifest committed to Git or a locally approved override.

## 4. Core control model

The system is a reconciliation controller.

For each registered component it stores:

- `desired_state`: STOPPED, RUNNING, PAUSED, DISABLED;
- `observed_state`: UNKNOWN, STARTING, HEALTHY, DEGRADED, UNHEALTHY, STOPPING, STOPPED, BLOCKED;
- generation and fencing token;
- owning adapter;
- App automation/thread identity or process/service/container identity;
- configured and observed ports;
- health checks;
- dependency graph;
- restart policy;
- last transition and actor;
- current lease or task route when applicable;
- dispatch owner: APP_AUTOMATION, CLI_FALLBACK, MANUAL_APP or NONE.

The controller repeatedly compares desired and observed state. It performs only the smallest authorized transition and records every action.

## 5. Port management model

A port is not merely a number. Each port registration must include:

- logical name, such as `brainops.console`, `secondbrain.api`, `maibot.stt`, `maibot.tts`;
- protocol: HTTP, HTTPS, WebSocket, TCP, UDP, named pipe or stdio;
- bind address;
- configured port and observed port;
- exposure class: LOOPBACK_ONLY, LAN_APPROVAL_REQUIRED, PUBLIC_FORBIDDEN;
- owning service;
- health-probe type;
- dependency and consumer list;
- allocation policy: FIXED, RANGE, OS_ASSIGNED;
- collision policy;
- enabled/disabled state;
- last successful probe and error.

Default policy:

- all management and agent-control ports bind to `127.0.0.1`;
- no `0.0.0.0` binding without a user-approved route;
- console port defaults to 32100;
- voice and model services use named logical ports and configurable ranges;
- the controller performs an actual bind/listen capability probe before starting a service;
- port conflicts fail closed and display the occupying PID/process where safely available;
- changing a port creates an auditable configuration generation, not an in-place hidden mutation.

## 6. Process supervision

On Windows, supervised native process trees should be placed in a Windows Job Object when compatible. Closing or terminating the job must terminate the complete managed process group and prevent orphaned CLI, Python, Node or audio subprocesses.

The integrated ChatGPT desktop application is external user software by default. BrainOps must not treat the entire application as a disposable child process or kill it merely to stop one task, except through an explicit user-confirmed emergency action.

Required lifecycle for managed native processes:

1. validate manifest and permissions;
2. validate dependency health;
3. reserve/check ports;
4. create process suspended when required;
5. associate process with Job Object;
6. start and capture stdout/stderr as structured streams;
7. publish PID, start time and command hash;
8. perform readiness probe;
9. on stop, request graceful termination first;
10. after timeout, terminate the Job Object;
11. confirm ports and process tree are released.

## 7. Codex automation path

The preferred Codex executor is App-native and user-session hosted. CLI/SDK remains a bounded fallback.

### 7.1 Review intake

GitHub events create a structured GPT review request. A scheduled anti-entropy scan detects missed requests.

### 7.2 GPT review result

GPT publishes a review decision plus a new task route and activation manifest. The activation manifest must contain an idempotency key, route epoch, reviewed base, target agent, execution permission, user-approval requirement and safety boundary.

### 7.3 App-first local dispatch

Prefer one dedicated Codex App Automation/reconciler thread that checks the canonical route on a supported schedule, ideally every 30 minutes after local verification.

It may dispatch only when all gates pass:

- target agent is CODEX;
- route status is READY;
- `execution_allowed: true`;
- `automatic_dispatch_allowed: true`;
- blocked list is empty;
- route epoch is greater than the last claimed epoch;
- PR head equals reviewed/base head;
- activation manifest is internally consistent;
- no live lease exists;
- user approval is not required;
- global and per-service automation switches are enabled;
- runner-owner fencing grants ownership to APP_AUTOMATION.

The App path must expose task/thread identity, approvals, review queue state, last/next automation run and usage-limit/attention state.

### 7.4 CLI/SDK fallback

CLI/SDK may be enabled only when an App limitation is evidenced and a separate gate permits it. It uses the same lease, fencing, route and idempotency contract and cannot run concurrently with the App owner.

When automated, CLI output must be structured JSONL. The controller records the exact session ID so a permitted resume uses the same session rather than an unrelated latest-session shortcut.

### 7.5 Immediate stop

The dashboard must provide:

- `Pause new dispatches`;
- `Pause App reconciliation`;
- `Stop after current safe checkpoint`;
- `Terminate current managed fallback executor`;
- `Disable automatic execution`;
- `Emergency stop all managed user processes`.

Emergency stop is always local and must not require GitHub availability. Terminating the entire ChatGPT desktop app is a separate explicit emergency action, not the normal task-stop path.

## 8. Dashboard requirements

The first useful dashboard should show:

### Summary cards

- global automation enabled/disabled;
- ChatGPT desktop/Codex host availability;
- Codex App Automation state, last/next run and thread identity;
- current dispatch owner;
- CLI fallback enabled/disabled and state;
- pending GPT review requests;
- active route epoch and task ID;
- number of healthy/degraded/unhealthy services;
- occupied/conflicted ports;
- last GitHub sync time;
- last controller action.

### Service table

Columns:

- name;
- type/adapter;
- desired state;
- observed health;
- automation/thread or PID/service/container identity;
- ports;
- uptime;
- restart count;
- current task or lease;
- last error;
- actions: start, stop, restart, pause, logs, details.

### Detail panel

- immutable service manifest;
- effective local configuration;
- dependencies;
- health history;
- recent structured logs;
- process tree where applicable;
- port ownership;
- action/audit history;
- exact command hash for fallback processes, with secrets redacted;
- GitHub task/review anchors for agent services.

## 9. Persistence and observability

Use SQLite for:

- service registry;
- desired/observed state snapshots;
- audit records;
- leases and fencing generations;
- port allocations;
- health history summaries;
- safe App automation/thread identifiers and fallback session identifiers.

Do not store raw secrets.

Use structured JSON logs per managed service. The first version may keep local rolling files; later versions may export metrics, traces and logs through OpenTelemetry.

SignalR pushes current state to the dashboard. Polling remains as a fallback so the UI can recover after reconnect.

## 10. Security model

- Bind Console and control APIs to loopback only.
- Generate a local management token outside the repository.
- Require anti-CSRF protections for state-changing browser requests.
- Separate read-only status endpoints from mutating control endpoints.
- Never expose arbitrary command execution.
- Never control Codex App with simulated UI or undocumented process hooks.
- Allowlist executable path, working directory, argument template and environment-variable names for native fallback runners.
- Redact token-like values before logs are written.
- Codex uses the narrowest permission profile that can complete the active task.
- Deny reads of `.env`, credential stores and unrelated directories unless an explicit route grants them.
- Network destinations are deny-by-default and allowlisted per adapter/task.
- All start/stop/restart/configuration actions generate an audit record.
- Use generation/fencing tokens so stale controllers or executors cannot update new state.
- Use runner-owner fencing to prevent App and CLI from claiming the same route.
- Automatic retries are bounded and use idempotency keys.
- Repeated failures open a circuit breaker and require manual reset.

## 11. Service manifest sketch

```yaml
schema_version: "1.1"
service_id: "codex.route-reconciler"
display_name: "Codex App Route Reconciler"
adapter: "codex_app_automation"
run_context: "USER_SESSION"
auto_start: true
automation_default: false
app:
  host: "chatgpt_desktop"
  view: "codex"
  automation_identity: "LOCAL_DISCOVERY_REQUIRED"
  thread_identity: "LOCAL_DISCOVERY_REQUIRED"
fallback:
  adapter: "codex_cli"
  enabled: false
  executable: "codex"
  working_directory: "F:/aidanao"
  arguments_template: ["exec", "--json", "--cd", "{worktree}", "-"]
permissions_profile: "brainops-codex-workspace"
ports: []
health:
  type: "app_automation_heartbeat"
  timeout_seconds: 2100
restart_policy:
  mode: "manual_or_app_native"
safety:
  arbitrary_arguments_forbidden: true
  ui_automation_forbidden: true
  concurrent_runner_forbidden: true
  public_binding_forbidden: true
  secrets_in_manifest_forbidden: true
```

## 12. MaiBot and voice expansion

Future voice services should be modeled as normal managed components, not special hard-coded buttons:

- microphone capture;
- voice activity detection;
- streaming transcription;
- dialogue/agent endpoint;
- text-to-speech;
- audio playback;
- terminal or websocket gateway.

The console must show the audio device, protocol, port/pipe, latency, buffer state and health. Voice components should support per-stage start/stop so one failing TTS process does not require shutting down the whole Second Brain.

## 13. Docker and native-process boundary

Containerize stable infrastructure when useful, such as databases, queues, vector stores and isolated APIs. Keep ChatGPT/Codex App and audio-device processes native. Keep CLI fallback native unless capability evidence proves another host is appropriate.

The Docker adapter should support Compose profiles, dependency health, restart and stop. Docker is optional: absence of Docker must not block the native-process MVP.

## 14. Delivery phases

### P0: discovery and architecture

- inventory operating system, .NET SDK, ChatGPT desktop/Codex view, App Automations, Codex CLI fallback, Docker, repository and current local processes;
- identify App cadence, same-thread, review queue, host-awake and trigger/API constraints;
- identify credential/session constraints;
- write ADRs and threat model;
- produce service/port manifest schemas;
- no installation and no process control.

### P1: read-only console

- ASP.NET Core/Blazor skeleton;
- SQLite registry;
- App host/automation, process, Windows Service, port and Docker discovery;
- dashboard and logs;
- no start/stop actions.

### P2: bounded manual control

- allowlisted BrainOps state controls;
- no simulated App UI control;
- Job Object supervision for native fallback processes;
- dependency and health checks;
- local audit log;
- global kill switch design;
- automation remains disabled.

### P3: Codex App route reconciler shadow mode

- desired 30-minute route scan, subject to local capability proof;
- validate and report what would execute;
- no Codex App or CLI dispatch;
- exercise READY, BLOCKED, PAUSED, stale epoch and duplicate cases.

### P4: Codex manual App-first dispatch

- user-visible Codex thread performs the same gates and launches one task;
- App task/thread and review-queue identity capture;
- pause/attention controls;
- CLI fallback disabled;
- no unattended automatic dispatch.

### P5: bounded App-native automatic dispatch

- enable per-service and global switches;
- periodic anti-entropy scan;
- lease/fencing/idempotency/circuit breaker;
- automatic dispatch only for routes explicitly permitting it.

### P6: optional CLI/SDK event fallback, Windows Host Service and MaiBot adapters

- event-driven fallback only after separate approval;
- system infrastructure service;
- named-pipe bridge to user agent;
- Docker profiles;
- voice pipeline components;
- OpenTelemetry export.

## 15. Mandatory tests

- schema validation and duplicate-key rejection;
- path traversal and executable substitution rejection;
- arbitrary argument injection rejection;
- undocumented App UI automation rejection;
- public bind rejection;
- port collision and release tests;
- fallback process-tree stop and orphan detection;
- restart-loop circuit breaker;
- stale route-epoch fencing;
- duplicate activation idempotency;
- App/CLI runner-owner concurrency rejection;
- READY/BLOCKED/PAUSED/disabled route tests;
- App unavailable, closed, asleep and usage-limited behavior;
- QQ `execution_allowed: false` never dispatches;
- corrupted GitHub response and offline behavior;
- UI reconnect and state resynchronization;
- secret redaction tests;
- shutdown while a managed fallback process is active;
- database migration, backup and rollback tests.

## 16. Acceptance boundary for the first implementation route

The first activated Codex route should deliver P0 plus a minimal P1 read-only prototype only. It must not install a Windows Service, create an App Automation, enable automatic dispatch or control real project processes. GPT reviews the App/Automation/CLI capability evidence, architecture, threat model, schemas and read-only dashboard before any mutating adapter is released.

## 17. Known unknowns

- exact installed ChatGPT desktop app version;
- whether the ChatGPT/Codex global switcher and Codex view are available on this account;
- whether Codex App Automations support an exact 30-minute recurrence;
- whether an Automation can return to the same Codex thread and review queue;
- whether the local App exposes a documented trigger/deep link/API/App Intent;
- whether App and CLI share configuration/session history in the installed build;
- whether mobile/remote and voice coordination are available for this Windows host;
- exact installed .NET SDK version;
- whether Codex OAuth can be used safely by a scheduled user-session fallback process;
- whether the local Codex CLI build exposes a stable app-server interface suitable for later integration;
- QQ/QCLAW external trigger and status APIs;
- current Second Brain service inventory and port map;
- MaiBot voice stack, audio-device constraints and protocol choices;
- Docker Desktop availability and resource impact;
- whether local Windows elevated sandboxing is available;
- the safest installation/startup mechanism for the user agent;
- final UI packaging choice: browser-only, tray launcher or desktop wrapper.

Unknowns must remain explicit and be closed by capability evidence. They must not be guessed into `SUPPORTED`.

## 18. Reference families

Implementation research should prefer current official documentation for:

- OpenAI ChatGPT desktop app, Codex view, Codex App Automations, remote access, voice coordination, CLI/SDK fallback and permissions;
- Microsoft .NET Worker Services, ASP.NET Core Windows Service hosting, Health Checks, SignalR and Windows Job Objects;
- GitHub Actions events, schedules, concurrency and repository dispatch;
- Docker Compose profiles, health dependencies and restart behavior;
- OpenTelemetry .NET logs, metrics and traces;
- EF Core SQLite provider.
