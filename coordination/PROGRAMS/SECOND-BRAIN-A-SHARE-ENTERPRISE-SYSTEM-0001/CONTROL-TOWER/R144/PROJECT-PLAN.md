# R144 PROJECT-PLAN — Control Tower GPT Engineering Worker First-Class Extension

## R2 provenance correction — authoritative

- canonical task_id: `CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144`
- route_epoch: `144`
- issue: `406`
- canonical activation executor recorded on main: `CODEX`
- **R1 actual implementation executor: `WORKBUDDY`**
- R1 WorkBuddy authority state: `NOT_CANONICALLY_RELEASED_FOR_R144 / CANDIDATE_IMPLEMENTATION_ONLY`
- **R2 corrective maintainer: `GPT_ARCHITECTURE_OWNER` under the user's explicit instruction to repair PR #408 directly**
- R2 authority semantics: `DRAFT_BRANCH_CORRECTIVE_MAINTENANCE / NOT_RETROACTIVE_WORKBUDDY_AUTHORIZATION / NOT_FIRST_CLASS_GPT_WORKER_LEASE / NOT_ACCEPTANCE_AUTHORITY`
- independent reviewer after R2: `SEPARATE_GPT_INDEPENDENT_REVIEWER`
- mode: `project_plan`
- canonical main at R1 preflight: `97a067037c9812deabc4da8e2e0450a7ffbf8300`
- implementation branch: `codex/r144-control-tower-gpt-worker-first-class`

> **Correction to the R1 plan:** the earlier statement `executor: CODEX（R144 真实执行器为 Codex）` was factually wrong. The user later confirmed that WorkBuddy actually produced the R1 implementation. Canonical Control Tower state had authorized CODEX while WorkBuddy remained paused/non-executable, so R2 preserves R1 code only as candidate implementation and does not fabricate retroactive WorkBuddy authority. Git commit author/committer identity is repository provenance, not automatic execution authority.

> 本计划基于真实仓库 inventory，不按 Issue 文本猜测架构。所有路径/字段名以当前 canonical main 为准。

---

## 一、真实仓库 inventory（G0）

### 1. AGENT_FILES

`coordination/CONTROL-TOWER/control_tower.py` 顶层常量：

```python
AGENT_FILES = {
    "CODEX":     "coordination/ACTIVE-CODEX-TASK.yaml",
    "QCLAW":     "coordination/ACTIVE-QCLAW-TASK.yaml",
    "WORKBUDDY": "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
}
```

当前仅三个单例 Agent。`GPT_ENGINEERING_WORKER` 不在其中 → 这是 R143/#405 被 executor identity gate 挡下的根因。

### 2. normalize_route / RouteSnapshot / route fingerprints

`control_tower.py`：

- `RouteSnapshot`（frozen dataclass）字段：`agent, task_id, route_epoch, issue, pr, branch, status, execution_allowed, completion_signal, fingerprint`。
- `normalize_route(agent, route)` 用 `_first()` 归一化别名键（`task_id/active_task_id`、`route_epoch/epoch`、`issue/active_issue`、`pr/implementation_pr/active_pull_request/pull_request/pr`、`branch/implementation_branch/planned_branch/frozen_branch/branch`），再对归一化 dict 做 sha256 → `fingerprint`。
- `route_witness(route)` = `asdict(route)`；`verify_route_witness(expected, current)` 只比较 fingerprint。

### 3. lane_claims

`coordination/CONTROL-TOWER/lane_claims.py`：

- `CLAIMS_FILE = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"`。
- 四种 claim 状态：`ACTIVE_IMPLEMENTATION` / `RESERVED_IMPLEMENTATION_NON_EXECUTABLE` / `HELD_PROPOSAL_ONLY` / `CLOSED_NO_ACTIVE_IMPLEMENTATION`。
- `validate_claims(root)` 从 `AGENT_FILES` 构建 `routes`，`_validate_bound_implementation_claim` 要求 `claim.execution_agent ∈ routes`，否则 `*_AGENT_INVALID`。
- 绑定漂移比较字段：`task_id / route_epoch / issue / pr / branch`（`_binding_drift` / `_binding_actual`）。
- 成对碰撞用 `classify_collision`（O0–O4）作用于 **lane** 级别。

### 4. authorization_witness

`coordination/CONTROL-TOWER/authorization_witness.py`：

- `authorization_witness(root, lane_id)` 从 `AGENT_FILES` 构建 `all_routes`，fingerprint 覆盖 lane、claim、all_claims、all_lanes、all_routes、release/capacity policy、overlap、release gate。
- `verify_authorization_witness` 比较 `authorization_fingerprint`。

### 5. claim projection / Program Control Tower projection

- `coordination/CONTROL-TOWER/claim_projection.py`：渲染 `PROGRAM-CONTROL-TOWER.md` 内的 `CONTROL_TOWER_CLAIMS_AUTOGEN` 区。
- `control_tower.py` 的 `render_projection_block`：渲染 `CONTROL_TOWER_AUTOGEN` 区，其中 Agent routes 表硬编码 `("CODEX","QCLAW","WORKBUDDY")`。
- 两个 autogen 区都由 CI 校验确定性。

### 6. WIP / resource limits

`coordination/ACTIVE-PROGRAM-LANES.yaml` → `portfolio_capacity_policy`：

```yaml
program_lanes_may_coexist: 3
codex_active_execution_routes_max: 1
qclaw_active_execution_routes_max: 1
workbuddy_active_execution_routes_max: 1
gpt_engineering_worker_parallel_routes_allowed: true
local_heavy_stage_concurrency_max: 1
a_share_business_vertical_slices_max: 1
same_canonical_object_writers_max: 1
nested_parallelism: "FORBIDDEN"
```

`scan_repository` 中 `agent_limits` 只含 CODEX/QCLAW/WORKBUDDY 的 `*_active_execution_routes_max`；GPT worker 无上限键。

### 7. route lifecycle / closure / history semantics

- 可执行状态集合 `NON_EXECUTABLE_STATUSES`（PAUSED/BLOCKED/REVIEW/DONE/CANCELLED/…）。
- 单例 Agent 的历史完成态用 `ACTIVE-*.yaml` 中的 `DONE`/`DONE_HISTORICAL` tombstone 表示（R142、R60）。
- 关闭/释放语义集中在 `lane_claims` 的 `CLOSED_NO_ACTIVE_IMPLEMENTATION`（要求 `execution_agent: null` + 无 route binding + 无 surface + durable closure_receipt）。

### 8. existing GPT executor-substitution routes

- `coordination/ROUTES/GPT-ENGINEERING-WORKER-R60-EXECUTOR-SUBSTITUTION.yaml`
- `coordination/ROUTES/GPT-ENGINEERING-WORKER-R142-EXECUTOR-SUBSTITUTION.yaml`

均为 `CLOSED_HISTORY_ONLY / NON_EXECUTABLE` tombstone，记录历史 `GPT_ENGINEERING_WORKER` + `GPT-5.6 Sol` 替代 provenance。**R144 不得改写这些历史为“当时就是 first-class worker”**。

### 9. CODEX/QCLAW/WORKBUDDY backward compatibility

- 原有 36 个测试全绿；`control_tower check` / `lane_claims` / `claim_projection` / `authorization_witness` 全 PASS。
- 约束：对三个单例 Agent 的 `AGENT_FILES`、`normalize_route`、`RouteSnapshot`、fingerprint、claim 绑定逻辑不得改变语义。

### 10. current gpt_engineering_worker_parallel_routes_allowed policy

已确认 `true`。因此 canonical 设计**不得**是 `ACTIVE-GPT-ENGINEERING-WORKER-TASK.yaml` 这种会被后一个窗口覆盖的单例文件。Issue 文本的“canonical identity recommendation”已被架构决策 comment `5340334185` 显式否决单例、强制 multi-slot registry。

---

## 二、架构决策（已由 comment 5340334185 定稿）

- canonical agent type：`GPT_ENGINEERING_WORKER`（唯一，不新增 `GPT_WORKER_1/2` ontology）。
- canonical active source：`coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`（复数 + `worker_slots` 列表），支持多个有界 slot/lease。
- 编程1/编程2 = `worker_slot_id` provenance，不是新 agent 物种。
- 两 slot 仅在不重叠 surface + WIP/资源允许内共存；同对象/同 authority 碰撞 fail-closed；单 slot 不得静默覆盖另一 active slot；stale slot/route witness 使授权失效；closed/released slot 保留 provenance 但无执行 lease。

---

## 三、目标 schema

### 3.1 canonical registry（新文件）

`coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`：

```yaml
schema_version: "1.0"
registry_id: "ACTIVE-GPT-ENGINEERING-WORKERS-0001"
agent_type: "GPT_ENGINEERING_WORKER"
parallel_routes_allowed: true
worker_slots: []   # 每个元素为一个 worker slot / lease
```

当前 `worker_slots: []`（R144 自身不创建一个虚假的 GPT worker slot；**不得制造无法取得的 provenance**）。

### 3.2 worker slot 字段绑定（每个 active slot 至少机械绑定）

- `worker_slot_id`（稳定 slot/lease 身份）
- `executor_role`（= `GPT_ENGINEERING_WORKER`）
- `model_id`（如 `GPT-5.6 Sol`，缺失时显式 `UNKNOWN`）
- `task_id` / `route_epoch` / `issue` / `pr` / `branch`
- `status` / `execution_allowed`
- `write_paths` / `read_paths` / `interfaces` / `read_domains` / `write_domains`
- `authority_claims`
- `resource_class`
- `provenance`（历史 executor/model 保留）
- `reviewer_role` + `reviewer_separation`（执行身份 ≠ 验收 authority）
- `activation_state`（`ACTIVE`/`RESERVED`/`RELEASED`）
- `closure_state`（null 或 `RELEASED`）

禁止仅用“编程1/编程2”聊天窗口昵称作 authority identity。

### 3.3 Work Claim 扩展

GPT worker claim 需同时绑定：

```yaml
execution_agent: "GPT_ENGINEERING_WORKER"
worker_slot_id: "<exact slot/lease id>"
route_binding:
  worker_slot_id: "<同上的 exact slot id>"
  task_id / route_epoch / issue / pr / branch
```

不得只绑 Agent 类型，否则两个 GPT worker 会互相冒充同一 active route。

### 3.4 Authorization Witness 扩展

witness material 增加 `worker_slots`（全部 slot 归一化结果 + 各自 fingerprint），任何 slot/task/epoch/issue/pr/branch/execution_allowed/claim/peer-claim/policy/release 变化都会使 `authorization_fingerprint` 失效。

R2 进一步要求 registry 顶层 authority/policy material 也进入 witness，并暴露 `worker_registry_fingerprint`，避免 `worker_slots` 不变时顶层 policy 漂移仍被视为 fresh。

---

## 四、并发治理（fail-closed 规则）

| # | 场景 | 判定 |
|---|---|---|
| 1 | 两 GPT worker 写同一 canonical object | FAIL CLOSED（O3/O4） |
| 2 | 两 GPT worker claim 同一 authority | FAIL CLOSED（O4） |
| 3 | 同一 slot 被两个 active task 复用 | FAIL CLOSED（重复 slot_id） |
| 4 | 新 active slot 静默覆盖旧 active slot | FAIL CLOSED（重复 slot_id） |
| 5 | 两不同 slot 只读/完全非重叠 | WIP/资源允许内 PASS |
| 6 | 超过 GPT worker configured capacity | FAIL CLOSED |
| 7 | local heavy stage | 仍 max 1 |
| 8 | nested parallelism | 仍 FORBIDDEN |
| 9 | ACTIVE/RESERVED slot 无 exact Work Claim | FAIL CLOSED（R2） |
| 10 | slot 与 claim 的 surface/resource 漂移 | FAIL CLOSED（R2） |
| 11 | RESERVED + execution_allowed=true | FAIL CLOSED（R2） |
| 12 | malformed registry/slot 被静默过滤 | FAIL CLOSED（R2） |

容量键：在 `portfolio_capacity_policy` 新增 `gpt_engineering_worker_active_slots_max`（默认有界值，与 `parallel_routes_allowed: true` 一致）。

---

## 五、实现步骤（G2/G3）

1. 新增 `coordination/CONTROL-TOWER/worker_slots.py`：`WorkerSlot` dataclass、`normalize_worker_slot`、`load_worker_slots`、严格 registry validation、slot/claim 双向绑定与 fail-closed checks。
2. `control_tower.py`：`scan_repository` 纳入 worker slot 校验；`render_projection_block` 增加 “GPT Engineering Worker slots” 区；`AGENT_FILES` 不变。
3. `lane_claims.py`：`_validate_bound_implementation_claim` 支持 `GPT_ENGINEERING_WORKER` + `worker_slot_id` 精确绑定；绑定漂移比较加入 slot semantics。
4. `authorization_witness.py`：material 纳入 worker slots + worker registry fingerprint。
5. `claim_projection.py`：投影 worker slot 绑定。
6. `coordination/ACTIVE-PROGRAM-LANES.yaml`：新增 `gpt_engineering_worker_active_slots_max`（仅新 ontology）。
7. `coordination/PROGRAM-CONTROL-TOWER.md`：由 deterministic generator 重生成。
8. `.github/workflows/program-control-tower.yml`：trigger paths 增加新 registry（**命名核对：brief 写 `program-control-tower-foundation.yml`，真实仓库文件为 `program-control-tower.yml`（`name: Program Control Tower foundation`），以真实仓库为准，本计划如实记录此差异**）。
9. `coordination/CONTROL-TOWER/README.md`：补充 worker slot 模型说明。
10. `coordination/CONTROL-TOWER/tests/test_worker_slots.py`：A–W + R2 fail-closed 对抗测试。

---

## 六、adversarial test 映射（G4，A–W + R2）

| 用例 | 断言 |
|---|---|
| A | valid slot + exact active claim → PASS |
| B | active claim + execution_allowed=false slot → FAIL |
| C–G | stale task_id/route_epoch/issue/pr/branch → FAIL |
| H | stale slot/lease identity → FAIL |
| I | GPT worker 冒充 CODEX → FAIL / mechanically distinct |
| J | 两 slot 同 canonical write surface → FAIL |
| K | 两 slot 同 authority → FAIL |
| L | 两 slot 非重叠且 WIP 内 → PASS |
| M | 同一 slot double booked → FAIL |
| N | silent slot overwrite → FAIL |
| O–Q | route / peer claim / release policy 变化使 witness 失效 → FAIL |
| R | closed/released slot 有 execution lease → FAIL |
| S | closed slot 正确 tombstone → PASS |
| T/U/V | 既有 CODEX/QCLAW/WORKBUDDY route → 保留 PASS |
| W | projection generator 确定性/幂等 → PASS |
| R2-1 | `worker_slots` 非 list → FAIL CLOSED |
| R2-2 | slot 非 mapping → FAIL CLOSED |
| R2-3 | registry identity/schema 缺失 → FAIL CLOSED |
| R2-4 | registry/program parallel policy 漂移 → FAIL CLOSED |
| R2-5 | ACTIVE slot 无 Work Claim → FAIL CLOSED |
| R2-6 | slot/claim surface 漂移 → FAIL CLOSED |
| R2-7 | ACTIVE slot 缺 PR → FAIL CLOSED |
| R2-8 | RESERVED slot executable → FAIL CLOSED |
| R2-9 | 同 task 多 active slots 且 nested_parallelism forbidden → FAIL CLOSED |
| R2-10 | worker registry top-level policy change invalidates witness → FAIL |

---

## 七、允许修改路径（对齐任务第十四节）

- `coordination/CONTROL-TOWER/**`
- `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`（新）
- `coordination/ACTIVE-PROGRAM-LANES.yaml`（仅新 ontology）
- `coordination/PROGRAM-CONTROL-TOWER.md`（仅 deterministic generator）
- `.github/workflows/program-control-tower.yml`（仅覆盖新 Agent 测试；文件名以真实仓库为准）
- `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R144/**`（本计划 + 回执）

不越界。若发现需超范围 → STOP 报 SCOPE_EXPANSION_REQUIRED。

---

## 八、hard locks（不变）

NO_TRADE · NO_W2_RUNTIME · NO_W3_WRITE · NO_SIGNAL_TOWER_RUNTIME_WRITE · NO_PRODUCTION_OR_PRIVATE_DATA · NO_SECRET_OR_PERMISSION_EXPANSION · NO_FAIL_CLOSED_WEAKENING_FOR_R143 · NO_EXECUTOR_IMPERSONATION · NO_SELF_REVIEW · NO_SELF_MERGE · NO_REBASE_RESET_FORCE_PUSH_HISTORY_REWRITE。

R143/#405 保持冻结，R144 完成后不得自动恢复；须 R144 independently accepted+merged 后 fresh preflight。

---

## 九、R2 completion gate

R2 的完成条件不是“当前 GPT 窗口觉得修好了”。必须同时满足：

1. exact Draft PR head + fresh merge-ref parent1=current canonical main / parent2=exact head；
2. Python 3.11 + 3.13 Control Tower CI 双绿；
3. 全套旧测试 + R2 新 adversarial tests 全绿；
4. `errors=[]`、projection MATCH、claim projection MATCH、authorization witness fresh；
5. PR/Issue/plan provenance 明确区分：canonical CODEX activation、R1 actual WorkBuddy implementation、R2 GPT corrective maintenance；
6. current GPT modifier **不得 self-review / APPROVE / merge**；
7. 由另一独立 GPT reviewer 对 exact R2 head 做 acceptance decision。

R2 completion signal：`R144_R2_GPT_CORRECTIVE_PATCH_READY_FOR_INDEPENDENT_REVIEW`。