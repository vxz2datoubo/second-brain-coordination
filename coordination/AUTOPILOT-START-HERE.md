# Autopilot 全自动推进：启动入口

这是「睡觉自动运行模式」的本地执行载体。它把既有的治理零件（durable_mission_kernel、CONTROL-TOWER、Unified Execution Fabric）串成一个无人值守闭环。

## 一句话原理

```
sync → discover → claim → execute → verify → report
     → commit → push → PR → tiered-merge → next
```

引擎是**编排层**，不重写治理逻辑，不授予任何新的 secret / production / trading / funds / orders / review / merge 权限。

## 三种模式（来自 OWNER-AGENT-BEHAVIOR-AND-INTERRUPTION-PROTOCOL）

| 模式 | 触发 | 行为 |
|---|---|---|
| `SLEEP_AUTONOMY` | 说「睡觉自动运行模式」 | Owner 问题数为 0，遇 gate 就 checkpoint 继续其他合法/非依赖/非冲突工作，全受阻才安全暂停 |
| `WRAP_UP` | 说「开始收尾」 | 不开新 mission，完成当前安全 bounded step 后安全暂停 |
| `NORMAL_AUTONOMY` | 默认 | 已有 authority 内自动续行 |

## 全自动的边界（必须先理解）

- ✅ 可以全自动：同步 → 发现 READY 任务 → 领取租约 → 执行 → 本地测试 → 提交 → 推送 → 创建 PR
- ⚠️ merge 分层（受治理，不是无脑突破禁令）：
  - **Tier1**：机械低风险 PR（closeout / 收据 / 快照 / 路由翻转），满足 CI 全绿 + 白名单 + 无 self-merge 锁时自动 merge
  - **Tier2**：实质代码 / 架构 / 交易变更，保持 `author != reviewer != canonicalizer` 独立 review，绝不自动 merge
- 任何带有 `NO_SELF_REVIEW_SELF_ACCEPT_SELF_MERGE` 硬锁、或 `merge_authorized: false` 的任务，引擎一律 checkpoint 并跳过 merge，转去下一个合法任务。

## 怎么用

### 1. 准备配置

```bash
cd tools/autopilot
cp config.example.yaml config.yaml
# 按需改 max_duration_hours（你睡多久填多少）、mode 等
```

### 2. 开启全自动（睡觉前）

```bash
# 干跑：只发现任务、不产生任何副作用
python -m tools.autopilot.autopilot --dry-run --repo-root .

# 单轮循环（观察一次完整闭环）
python -m tools.autopilot.autopilot --once --repo-root .

# 全自动推进（默认按 config 里的时长跑）
python -m tools.autopilot.autopilot --repo-root .
```

### 3. 控制塔 Web 看板

睡觉醒来打开 GitHub Pages 看板（由 CI/CD 的 deploy job 自动发布），看到各泳道/Agent 的进度、冲突与 gate 状态。

本地生成看板：

```bash
python -m tools.autopilot.dashboard --repo-root . --out docs/index.html
```

### 4. 收尾交接（睡醒后说「收尾」）

引擎每轮循环都会把状态追加到 `.autopilot-state/cycles.jsonl`，并在结束时自动生成交接文档：

```bash
# 直接看交接文档（引擎自动生成）
cat .autopilot-state/handoff.md

# 或手动重新生成
python -m tools.autopilot.handoff --state-dir .autopilot-state --out handoff.md
```

交接文档聚合了 8 小时自动驾驶的完整账本：已完成 / 待 review / 待独立验算的 PR、门禁 checkpoint、阻塞问题、未释放租约、日志摘要。醒来直接读这一份即可。

### 5. 双模型交叉验算（CLI）

全自动模式下，CLI 比 App 更适合，因为能脚本化切换模型、完全无头：

```bash
# 主执行：强模型 headless 跑（codex exec 非交互）
codex exec -m <强模型> "任务描述"

# 独立验算：快模型 review 每个 PR（与主执行隔离，避免自审）
codex review -m v4.1-flash <PR_URL>
```

- `codex exec`：非交互执行，无人值守。
- `codex review`：非交互代码 review，天然适合做"第二双眼睛"的验算。
- `-m` / `--model`：一行切换模型，无需 GUI。
- 配置里的 `verification` 段（`enabled: true` 时）可让引擎在每轮 verify 后自动追加一次独立 review；默认 `false`，由你睡醒后手动用 `codex review` 验算。

## 目录结构

```
tools/autopilot/
├── __init__.py        版本 / 任务标识
├── config.py          配置加载 + 校验（fail-fast）
├── github_client.py   gh CLI 封装（同步/PR/review/merge 原语）
├── autopilot.py       主引擎（主循环 + discover + claim + 分层 merge）
├── dashboard.py       控制塔 Web 看板生成
├── handoff.py         收尾交接报告生成（handoff.md）
└── config.example.yaml
```

## 安全红线（不可变）

1. 单写者：同一 task/collision domain 只允许一个写者。
2. 绝不覆盖未提交工作区（sync 只做 `ff-only`，dirty 时跳过）。
3. 绝不突破 `author != reviewer != canonicalizer`：Tier2 一律独立 review。
4. 绝不自动 merge 带 `NO_SELF_MERGE` 锁或 `merge_authorized: false` 的任务。
5. 绝不触碰 NO_TRADE / secret / production / funds / orders 边界。
