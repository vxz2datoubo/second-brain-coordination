# WorkBuddy Multi-Executor Readiness Reality Audit v1

Status: `CANDIDATE / OWNER-CARRIED READ-ONLY AUDIT / NO REPO WRITE AUTHORITY`

Source: Issue #627
Architecture snapshot: `SECOND-BRAIN-ISSUE627-MULTI-EXECUTOR-EPISTEMIC-NUMERIC-001` / `issuecomment-5592959662`

## Purpose

Measure the real local capacity and collision surfaces needed to run 3..N WorkBuddy engineering executors safely. This audit exists because logical executor capacity and physical concurrent load are different things.

This is **not** a successor execution Route, Claim, Lease or Reservation. It must not preempt or modify the currently active R175 WorkBuddy task and must not claim that historical R579 multi-slot code is canonical.

## Hard boundaries

- READ ONLY.
- Do not edit, create, delete, stage, commit, push, merge or reset repository files.
- Do not create a new branch/worktree in this audit; only inventory current layout and prove whether future worktrees are feasible.
- Do not stop, restart, install, upgrade or reconfigure services/packages/runtimes.
- Do not kill any process.
- Do not start Local Bridge, capture, browser automation, video generation, market-data provider session, trading/account/order API, or persistent daemon.
- Do not expose credentials, tokens, cookies, license keys, usernames/private paths or other reusable secrets in the report.
- Do not interrupt/reorder R175.
- Do not use Codex.
- Obey the ACTIVE local process/resource protocol. Audit commands themselves should remain lightweight.

## Fresh sources to read first

From remote current `main`, read at minimum:

1. `coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml`
2. `coordination/GOVERNANCE/EXECUTION-CARRIER-AND-CONCURRENCY-CONTRACT-v1.0.yaml`
3. `coordination/GOVERNANCE/AGENT-TASK-LEASE-AND-COMPLETION-FRESHNESS-PROTOCOL-v1.0.yaml`
4. `coordination/GOVERNANCE/LOCAL-EXECUTION-RESOURCE-BUDGET-AND-PROCESS-LIFECYCLE-PROTOCOL-v1.0.yaml`
5. `coordination/GOVERNANCE/LOCAL-WORKBUDDY-BRIDGE-CONTRACT-v1.0.yaml`
6. `coordination/GOVERNANCE/MULTI-GPT-N-WORKBUDDY-EXECUTOR-POOL-ARCHITECTURE-v1.0.yaml` from candidate branch `gpt/issue627-multi-executor-epistemic-map-v1`
7. Issue #627
8. historical Issue #579 and PR #590 review `pullrequestreview-5119201290`
9. current `coordination/ACTIVE-WORKBUDDY-TASK.yaml` only to prove it remains untouched.

## Audit matrix

### A. Host and process baseline

Record safe/non-secret facts:
- OS version/build;
- CPU model, physical cores, logical threads;
- total and currently available RAM;
- GPU model, VRAM and current utilization if observable without starting new services;
- baseline project-owned Python/process count;
- total Python processes with ownership classification where safely derivable;
- whether Windows Job Object/process-group controls are available to the current WB carrier;
- current shell/terminal/runtime identities.

Do not publish private full paths; hash/redact them where needed.

### B. WorkBuddy carrier inventory

For CLI Headless / CLI WebUI / Desktop, report:
- installed/available or not observed;
- version/build where visible;
- actual model selection controls;
- whether distinct simultaneous instances are mechanically possible;
- whether each instance can have a distinct local working directory/worktree;
- whether process PID/root ownership can be observed;
- whether cancel/timeout reliably tears down descendants;
- whether carrier has a stable per-instance identity suitable for `executor_id`;
- UNKNOWN where unverified.

Do not launch multiple heavy instances just to prove concurrency.

### C. Git/worktree feasibility

Read-only inventory:
- Git version;
- current repo path represented only by safe label/hash if private;
- `git worktree list --porcelain` summary;
- existing branches/worktrees and whether any are dirty;
- filesystem volume/free-space estimate;
- expected cost of 3, 4, 6 and 8 isolated worktrees based on repository size and shared-object behavior;
- any path-length/Windows locking/antivirus constraints observed.

Return a proposed deterministic naming convention, but do not create worktrees.

### D. Collision and exclusivity inventory

Identify resources that must be MUTEX, SEMAPHORE, READ_SHARED or can be independent:
- heavy local tests/mutation/provider runs;
- GPU-heavy inference/generation;
- browser interactive sessions;
- known local HTTP/TCP ports;
- Local Bridge port/config/process identity;
- TDX/TQ provider/service use without invoking them;
- writable caches/temp directories;
- Python virtualenv/package installation surface;
- Node/npm caches if material;
- database/sqlite/local state files;
- video/image generation carriers;
- any single-instance desktop application dependency.

For every item return `resource_id`, lock type, proposed capacity, evidence and confidence.

### E. Resource canary design only

Do not run the canary in this audit. Design a later bounded canary for:
- 3 LIGHT WB executors;
- 1 HEAVY + 2 LIGHT;
- 2 HEAVY (expected to be blocked under current policy unless policy changes);
- one executor crash/timeout;
- one stale lease holder;
- one worktree/path collision;
- one service-port collision;
- one GPU/browser exclusive-resource collision.

For each case specify expected scheduler decision and measurement needed.

### F. Parameter calibration candidates

Do not invent values. Return measured evidence and recommended candidate values for:
- `WB.LOGICAL_SLOT_CAPACITY_MAX`
- `WB.RUNNING_EXECUTOR_CAPACITY_DEFAULT`
- `WB.LEASE_HEARTBEAT_INTERVAL_SECONDS`
- `WB.LEASE_EXPIRY_SECONDS`
- `WB.LIGHT_TASK_CPU_TOKEN`
- `WB.LIGHT_TASK_RAM_GIB_TOKEN`
- `WB.BROWSER_SESSION_CAPACITY`
- `WB.GPU_HEAVY_CAPACITY`

Each recommendation must label itself `MEASURED`, `INFERRED`, or `UNKNOWN`, and must not override the active hard resource protocol.

## Required result schema

Return one report with:

```yaml
schema: WORKBUDDY_MULTI_EXECUTOR_REALITY_AUDIT_RESULT/v1
status: COMPLETE | PARTIAL | BLOCKED
observed_main: <sha>
architecture_issue: 627
architecture_snapshot: SECOND-BRAIN-ISSUE627-MULTI-EXECUTOR-EPISTEMIC-NUMERIC-001
repo_mutated: false
r175_mutated_or_preempted: false
process_or_service_mutation_performed: false
host_profile: {}
baseline_resources: {}
carrier_capabilities: []
worktree_feasibility: {}
resource_lock_inventory: []
collision_surfaces: []
calibration_candidates: []
canary_design: []
unknowns: []
risks: []
recommended_next_engineering_slice: {}
secret_value_exposure: false
```

## Success condition

The audit is successful when GPT can determine, from evidence rather than guesswork:
1. whether three simultaneous LIGHT WorkBuddy executors are physically safe on the present machine;
2. which resources serialize independently of executor count;
3. what local identity/heartbeat/process evidence can support future leases;
4. how many logical slots can be represented versus how many may RUN;
5. which parameters remain UNKNOWN and require a later canary;
6. how to create the clean R579 successor without changing R175.

Completion signal:
`WB_MULTI_EXECUTOR_READINESS_REALITY_AUDIT_READY_FOR_GPT_ARCHITECTURE_RECONCILIATION`
