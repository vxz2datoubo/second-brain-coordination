## R144 — GPT Engineering Worker First-Class Control Tower Extension

- task_id: `CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144`
- route_epoch: `144`
- issue: `#406`
- executor: `CODEX`（R144 真实执行器为 Codex）
- reviewer: `GPT_INDEPENDENT_REVIEWER`
- mode: `project_plan`
- base: `97a067037c9812deabc4da8e2e0450a7ffbf8300`（fresh canonical main，未漂移）

### 目标

把 `GPT_ENGINEERING_WORKER` 正式纳入 Control Tower 一等执行身份。**不**新增 `GPT_WORKER_1/2` 两个 agent ontology；编程1/编程2 = `worker_slot_id` provenance。canonical source 为多 slot/lease registry（`coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`），避免 singleton overwrite。

### 实现要点

- 新增 `coordination/CONTROL-TOWER/worker_slots.py`：`WorkerSlot` 归一化/fingerprint、`validate_worker_slots`（重复 slot_id / 冒充 CODEX / self-review / closed-has-lease / 容量超限 / slot 间 O3-O4 碰撞）。
- `control_tower.py`：`scan_repository` 纳入 worker slot 校验；`render_projection_block` 增加 "GPT Engineering Worker slots" 区。
- `lane_claims.py`：`execution_agent=GPT_ENGINEERING_WORKER` 的 claim 必须绑定 exact `worker_slot_id` + task/epoch/issue/pr/branch。
- `authorization_witness.py`：witness material 纳入 worker slots fingerprint。
- `claim_projection.py`：投影显示 slot 绑定。
- `ACTIVE-PROGRAM-LANES.yaml`：新增 `gpt_engineering_worker_active_slots_max: 2`。
- `.github/workflows/program-control-tower.yml`：trigger paths 增加 `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`。
- 新测试 `test_worker_slots.py`：A–W 全套对抗测试。

### 命名核对

Task brief 写 `.github/workflows/program-control-tower-foundation.yml`；真实仓库文件为 `.github/workflows/program-control-tower.yml`（`name: Program Control Tower foundation`）。以真实仓库为准，本项目计划已如实记录此差异。

### Changed paths（全部在允许范围）

```
.github/workflows/program-control-tower.yml
coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml        (new)
coordination/ACTIVE-PROGRAM-LANES.yaml
coordination/CONTROL-TOWER/README.md
coordination/CONTROL-TOWER/authorization_witness.py
coordination/CONTROL-TOWER/claim_projection.py
coordination/CONTROL-TOWER/control_tower.py
coordination/CONTROL-TOWER/lane_claims.py
coordination/CONTROL-TOWER/worker_slots.py              (new)
coordination/CONTROL-TOWER/tests/test_worker_slots.py   (new)
coordination/PROGRAM-CONTROL-TOWER.md                   (deterministic generator)
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R144/PROJECT-PLAN.md
```

### 测试

- 全套 Control Tower 测试：**63**（原有 36 + 新增 27 对抗测试），本地 Python 3.13 / 3.12 均 OK。
- 新增对抗测试覆盖：valid slot PASS、execution_allowed=false FAIL、stale task/epoch/issue/pr/branch FAIL、stale slot FAIL、GPT worker 冒充 CODEX FAIL、两 slot 同 write/authority FAIL、非重叠 PASS、同 slot 双订 FAIL、silent overwrite FAIL、released slot 有 lease FAIL、closed tombstone PASS、route/peer-claim/release-policy 变化使 witness 失效 FAIL、CODEX 既有 route 保留 PASS、projection 确定性/幂等 PASS。

### Hard locks（全部遵守）

NO_TRADE · NO_W2_RUNTIME · NO_W3_WRITE · NO_SIGNAL_TOWER_RUNTIME_WRITE · NO production/private data · NO secret/permission expansion · NO validator weakening for R143 · NO GPT-worker CODEX impersonation · NO self-review · NO self-merge · NO rebase/reset/force-push/history-rewrite。

### 待 GPT 独立 review

execution identity ≠ acceptance authority。CI PASS ≠ Independent Review PASS。本 PR 不 merge、不 self-review。R143/#405 保持冻结，R144 accepted+merged 后 fresh preflight 才可恢复。

---

**completion_signal**: `R144_CONTROL_TOWER_GPT_ENGINEERING_WORKER_FIRST_CLASS_READY_FOR_GPT_REVIEW`
