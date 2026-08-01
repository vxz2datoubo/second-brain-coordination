# BrainOps Local Agent, Service and Port Control Plane v1.0

Status: `PLAN_ONLY / DRAFT / NOT_ACTIVATED`

Owner: GPT architecture and review control plane

Target implementer: Codex after explicit route activation

Boundary: `LOCAL_FIRST / PUBLIC_SAFE_REPOSITORY_METADATA_ONLY / NO_TRADE / NO_REAL_ACCOUNT_ACTION`

## 1. Fundamental goal

Create one visible local operations console for the Second Brain ecosystem that can safely show, start, stop, restart, pause and diagnose:

- the Codex route reconciler and task executor;
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
- force Codex into a Windows system account that cannot access the user OAuth session;
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

It owns processes that require the user's profile, OAuth session or desktop-local files, especially:

- Codex CLI `codex exec`;
- Codex OAuth-authenticated task sessions;
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

1. `NativeProcessAdapter`
2. `WindowsServiceAdapter`
3. `DockerComposeAdapter`
4. `ExternalEndpointAdapter`
5. `CodexExecutorAdapter`
6. `ScheduledReconcilerAdapter`
7. future `MaiBotVoiceAdapter`

No adapter may accept arbitrary executable paths or shell strings from UI input. Executables, work directories and arguments come from an allowlisted service manifest committed to Git or a locally approved override.

## 4. Core control model

The system is a reconciliation controller.

For each registered component it stores:

- `desired_state`: STOPPED, RUNNING, PAUSED, DISABLED;
- `observed_state`: UNKNOWN, STARTING, HEALTHY, DEGRADED, UNHEALTHY, STOPPING, STOPPED, BLOCKED;
- generation and fencing token;
- owning adapter;
- process/service/container identity;
- configured and observed ports;
- health checks;
- dependency graph;
- restart policy;
- last transition and actor;
- current lease or task route when applicable.

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

On Windows, supervised native process trees should be placed in a Windows Job Object when compatible. Closing or terminating the job must terminate the complete managed process group and prevent orphaned Codex, Python, Node or audio subprocesses.

Required lifecycle:

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

The Codex executor remains user-session hosted.

### 7.1 Review intake

GitHub events create a structured GPT review request. A scheduled anti-entropy scan detects missed requests.

### 7.2 GPT review result

GPT publishes a review decision plus a new task route and activation manifest. The activation manifest must contain an idempotency key, route epoch, reviewed base, target agent, execution permission, user-approval requirement and safety boundary.

### 7.3 Local dispatch

The BrainOps User Agent checks every 30 minutes and may also accept a local event signal. It dispatches only when all gates pass:

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
- global and per-service automation switches are enabled.

Codex must run non-interactively with structured JSONL output. The controller records the Codex session ID so a permitted resume can use the exact prior session rather than an unrelated `--last` session.

### 7.4 Immediate stop

The dashboard must provide:

- `Pause new dispatches`;
- `Stop after current safe checkpoint`;
- `Terminate current executor`;
- `Disable automatic execution`;
- `Emergency stop all managed user processes`.

Emergency stop is always local and must not require GitHub availability.

## 8. Dashboard requirements

The first useful dashboard should show:

### Summary cards

- global automation enabled/disabled;
- Codex executor state;
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
- PID/service/container ID;
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
- process tree;
- port ownership;
- action/audit history;
- exact command hash, with secrets redacted;
- GitHub task/review anchors for agent services.

## 9. Persistence and observability

Use SQLite for:

- service registry;
- desired/observed state snapshots;
- audit records;
- leases and fencing generations;
- port allocations;
- health history summaries.

Do not store raw secrets.

Use structured JSON logs per managed service. The first version may keep local rolling files; later versions may export metrics, traces and logs through OpenTelemetry.

SignalR pushes current state to the dashboard. Polling remains as a fallback so the UI can recover after reconnect.

## 10. Security model

- Bind Console and control APIs to loopback only.
- Generate a local management token outside the repository.
- Require anti-CSRF protections for state-changing browser requests.
- Separate read-only status endpoints from mutating control endpoints.
- Never expose arbitrary command execution.
- Allowlist executable path, working directory, argument template and environment-variable names.
- Redact token-like values before logs are written.
- Codex uses the narrowest permission profile that can complete the active task.
- Deny reads of `.env`, credential stores and unrelated directories unless an explicit route grants them.
- Network destinations are deny-by-default and allowlisted per adapter/task.
- All start/stop/restart/configuration actions generate an audit record.
- Use generation/fencing tokens so stale controllers or executors cannot update new state.
- Automatic retries are bounded and use idempotency keys.
- Repeated failures open a circuit breaker and require manual reset.

## 11. Service manifest sketch

```yaml
schema_version: "1.0"
service_id: "codex.route-reconciler"
display_name: "Codex Route Reconciler"
adapter: "codex_executor"
run_context: "USER_SESSION"
auto_start: true
automation_default: false
executable:
  path: "codex"
  working_directory: "F:/aidanao"
  arguments_template: ["exec", "--json", "--cd", "{worktree}", "-"]
permissions_profile: "brainops-codex-workspace"
ports: []
health:
  type: "heartbeat_file"
  timeout_seconds: 90
restart_policy:
  mode: "on_failure"
  max_retries: 2
  backoff_seconds: [10, 60]
safety:
  arbitrary_arguments_forbidden: true
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

Containerize stable infrastructure when useful, such as databases, queues, vector stores and isolated APIs. Keep Codex and audio-device processes native unless capability evidence proves containers are appropriate.

The Docker adapter should support Compose profiles, dependency health, restart and stop. Docker is optional: absence of Docker must not block the native-process MVP.

## 14. Delivery phases

### P0: discovery and architecture

- inventory operating system, .NET SDK, Codex CLI, Docker, repository and current local processes;
- identify credential/session constraints;
- write ADRs and threat model;
- produce service/port manifest schemas;
- no installation and no process control.

### P1: read-only console

- ASP.NET Core/Blazor skeleton;
- SQLite registry;
- process, Windows Service, port and Docker discovery;
- dashboard and logs;
- no start/stop actions.

### P2: bounded manual control

- allowlisted start/stop/restart;
- Job Object process supervision;
- dependency and health checks;
- local audit log;
- global kill switch;
- automation remains disabled.

### P3: Codex route reconciler shadow mode

- 30-minute route scan;
- validate and report what would execute;
- no Codex dispatch;
- exercise READY, BLOCKED, PAUSED, stale epoch and duplicate cases.

### P4: Codex manual dispatch

- dashboard button performs the same gates and launches one Codex task;
- JSONL event capture and session identity;
- pause/terminate controls;
- no unattended automatic dispatch.

### P5: bounded automatic dispatch

- enable per-service and global switches;
- event plus 30-minute anti-entropy scan;
- lease/fencing/idempotency/circuit breaker;
- automatic dispatch only for routes explicitly permitting it.

### P6: optional Windows Host Service and MaiBot adapters

- system infrastructure service;
- named-pipe bridge to user agent;
- Docker profiles;
- voice pipeline components;
- OpenTelemetry export.

## 15. Mandatory tests

- schema validation and duplicate-key rejection;
- path traversal and executable substitution rejection;
- arbitrary argument injection rejection;
- public bind rejection;
- port collision and release tests;
- process-tree stop and orphan detection;
- restart-loop circuit breaker;
- stale route-epoch fencing;
- duplicate activation idempotency;
- concurrent controller/lease race tests;
- READY/BLOCKED/PAUSED/disabled route tests;
- QQ `execution_allowed: false` never dispatches;
- corrupted GitHub response and offline behavior;
- UI reconnect and state resynchronization;
- secret redaction tests;
- shutdown while a Codex child process is active;
- database migration, backup and rollback tests.

## 16. Acceptance boundary for the first implementation route

The first activated Codex route should deliver P0 plus a minimal P1 read-only prototype only. It must not install a Windows Service, enable automatic dispatch or control real project processes. GPT reviews the architecture, threat model, schemas, capability probes and read-only dashboard before any mutating adapter is released.

## 17. Known unknowns

- exact installed .NET SDK version;
- whether Codex user OAuth can be used safely by a scheduled user-session process;
- whether the local Codex build exposes a stable app-server interface suitable for later integration;
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

- OpenAI Codex CLI, non-interactive execution, permissions, App Server, MCP Server and GitHub Action;
- Microsoft .NET Worker Services, ASP.NET Core Windows Service hosting, Health Checks, SignalR and Windows Job Objects;
- GitHub Actions events, schedules, concurrency and repository dispatch;
- Docker Compose profiles, health dependencies and restart behavior;
- OpenTelemetry .NET logs, metrics and traces;
- EF Core SQLite provider.
