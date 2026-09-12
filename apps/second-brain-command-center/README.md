# Second Brain Command Center (洛雪认知控制中心)

> **UI 状态不是系统真源。** 本前端是 READ-ONLY 投影层，只读取既有权威来源。

整个第二大脑生态的统一人机交互入口。为 4 个一级项目 + 全局 Control Plane 提供一个长期可扩展、可恢复、可追溯、可操作的企业级前端。

## 当前阶段：Phase 1 — READ-ONLY MVP

**已实现（真实数据，非 mock）：**

- 从 `PROJECT-REGISTRY.yaml` **动态发现**项目（不是硬编码 4 个）
- 项目看板：进度 / 阶段 / 施工者 / 当前任务 / 下一步门 / Issue / PR
- 项目独立页面（通用模板 + 适配器驱动）：使命、碰撞域、硬边界、关系、任务
- Control Tower 摘要与详情页（泳道 / 路线 / 状态分布 / 派发边界）
- 施工者页面：**绝不从 PID / 心跳判定"正在施工"**（liveness 基于任务级证据）
- 系统健康 + 数据新鲜度 + 来源可追溯（Provenance 抽屉）
- Remote vs Local 同步状态严格区分（SYNCED / REMOTE_AHEAD / LOCAL_AHEAD / DIVERGED / DIRTY）
- candidate / review / canonical / active **严格区分**，不折叠
- 手动刷新优先（避免高频 poll GitHub）

**明确未实现（fail-closed，接口已预留）：**

- `POST /api/commands/dispatch-intent` → 501（Phase 2：控制塔派发校验）
- `POST /api/commands/start` → 501（Phase 3：Host Broker 自动施工）
- W3 / Host Broker → 健康页诚实标注 `UNAVAILABLE`
- 无任何交易、写入、merge、进程启动能力

## 快速开始

```bash
# 1) 启动只读 BFF（依赖见 api/requirements.txt）
cd api
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8790

# 2) 启动前端（另一个终端）
npm install
npm run dev
# 打开 http://localhost:5173
```

推荐使用统一启动脚本：`./start.sh`（见仓库根）。

## 架构

```
apps/second-brain-command-center/
├── api/                      # Thin BFF (FastAPI, READ-ONLY)
│   └── app/
│       ├── main.py           # 端点 + fail-closed 扩展点
│       ├── schemas.py        # ViewModel 投影契约（非 canonical schema）
│       ├── repo_paths.py     # 可移植的仓库发现（跨机器 / 跨 AI 宿主）
│       └── adapters/
│           ├── github.py     # gh CLI 只读；BFF 是凭据边界
│           ├── git_local.py  # 本地仓库真实状态
│           ├── coordination.py  # registry / lanes / active tasks / adapters
│           └── control_tower.py # 控制塔投影
├── src/                      # React + TS + Vite 前端
│   ├── api.ts, hooks.ts, types.ts, semantics.ts
│   ├── components/           # 内联 SVG 图标 + 共享 UI（零外部依赖）
│   └── pages/                # Home / Project / ControlTower / Tasks / Agents / Health
├── scripts/screenshot.mjs    # Playwright 验收证据
└── docs/                     # 架构 / 数据源矩阵 / 状态语义 / 扩展契约
```

## 权限边界（硬规则）

| 能力 | 状态 |
|---|---|
| 读取 GitHub / 本地仓库 / 控制塔 | ✅ 允许 |
| 归一化 / 投影 ViewModel | ✅ 允许 |
| 暴露 secret 到浏览器 | ❌ 禁止（BFF 持凭据） |
| 写系统真源 / merge / 建第二 Control Tower | ❌ 禁止 |
| 交易 / 下单 / 账户 | ❌ 禁止（NO_TRADE） |
| 启动进程 / 自动派发 | ❌ 未启用（Phase 2/3） |

## 门禁与治理

本目录属于 `SECOND BRAIN GLOBAL UX`，是**人机界面层**，不是第 5 个 domain project。
所有 truth 来自现有 authority：GitHub engineering truth / Control Tower execution
authority / W3 semantic memory / AI Director domain repo。

**不建立第二 control plane。**

---

*Phase 1 · READ-ONLY · 全真实数据 · 非 Demo*
