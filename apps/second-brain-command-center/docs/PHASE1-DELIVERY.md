# Second Brain Command Center — Phase 1 MVP 交付报告

## 一句话

为整个第二大脑生态建立了一个**企业级、只读、全真实数据**的统一前端，**不是 Demo**。

---

## 一、现场审计结论（Reality Audit）

| 项 | 发现 |
|---|---|
| 协调仓库 | `F:\SecondBrainWorkspace\second-brain-coordination`，本地 main = origin/main = `3bda040f`（与需求 snapshot 一致） |
| 已有前端资产 | `apps/web/` 仅有 README（"Offline browser surface"），**无可复用前端** |
| `apps/` 结构 | 已有 `cli/` + `web/`，故新前端落在 `apps/second-brain-command-center/`（沿用现有 convention） |
| 4 个一级项目 | 从 `PROJECT-REGISTRY.yaml` 真实发现；AI导演的领域权威在 `eustia-ai-film`（HEAD `62e72999`） |
| 治理真源 | `ACTIVE-PROGRAM-LANES.yaml`（4 泳道）、`ACTIVE-{AGENT}-TASK.yaml`、`CONTROL-TOWER/` |
| GitHub 连通 | ✅ 账号 `vxz2datoubo`，token 齐全（只读使用，且只在服务端） |
| R175 未关闭 | 作为 SYSTEM_GOVERNANCE_WARNING **如实展示**，未顺手修改 |
| 环境 | Node 22.22.2 / Python 3.13.14 均可用 |

---

## 二、已交付能力（Phase 1，全部真实数据）

### 后端 · Thin BFF（FastAPI，READ-ONLY）
- `GET /api/health` — 5 组件健康（W3/Host Broker **诚实标 UNAVAILABLE**）
- `GET /api/system` — 仓库同步状态（**REMOTE vs LOCAL 严格区分**）
- `GET /api/projects` — **从 registry 动态发现**项目（非硬编码）
- `GET /api/projects/{id}` — 项目详情（碰撞域 / 硬边界 / 关系）
- `GET /api/tasks` — 活跃路线
- `GET /api/control-tower` — 控制塔投影（泳道 / 路线 / 状态分布）
- `GET /api/agents` — 施工者活跃度（**不从 PID/心跳判定**）
- `POST /api/commands/dispatch-intent` → **501 fail-closed**（Phase 2 预留）
- `POST /api/commands/start` → **501 fail-closed**（Phase 3 预留）

### 前端 · React + TS + Vite（零外部 CDN / 内联 SVG 图标）
- 首页：系统健康条 + 4 项目卡 + 控制塔摘要 + 同步状态 + 活跃路线
- 项目独立页面（通用模板，**适配器驱动，不加项目就无需改代码**）
- 控制塔页 / 任务页 / 施工者页 / 系统健康页
- 深色企业级设计令牌，可切浅色；响应式（含 390px 移动端）

### 核心真实性保证（你的硬要求）
| 要求 | 实现 |
|---|---|
| candidate / canonical / active 严格区分 | 状态语义层独立映射，绝不折叠 |
| false-alive 不显示为施工中 | WORKBUDDY/CODEX 显示 **IDLE** + 判定依据"no session evidence" |
| 每个状态带来源与 freshness | 每个响应带 `meta{observed_at, authority, trust, sources, warnings}` |
| 0 ahead/0 behind ≠ 全同步 | DIRTY 状态单独标注，横幅提醒 |
| 未连接源不假装 healthy | W3 / Host Broker / Trading 诚实标 UNAVAILABLE / NO_TRADE |
| 不用 mock 宣布完成 | 全部 REAL_LOCAL + REAL_GITHUB |

---

## 三、验收证据

### 契约测试：**14 passed**
`tests/test_bff_contract.py` 直接断言语义保证（非仅 200）：
- false-alive 防护、candidate≠canonical、sync 语义、fail-closed、provenance 完整性、registry 驱动

### 真实浏览器截图（8 张）
`evidence/screenshots/` — 首页 / 交易项目页 / 第二大脑页 / 控制塔 / 任务 / 施工者 / 健康 / 移动端

### 真实数据验证（实测输出）
```
SECOND_BRAIN        | PAUSED | Preserve the R181 A2.2 executor checkpoint...
TRADING_SYSTEM      | ACTIVE | Implement the DS-10 P0C PBO/CSCV reference module...
REALTIME_INTERACTIVE_FILM_GAME | UNKNOWN | 规范入口：PROJECT-BATON.yaml...
AI_DIRECTOR         | UNKNOWN | 权威域：screenplay/adaptation...
```
```
WORKBUDDY  | IDLE     | route READY, not yet executing (no session evidence)
CODEX      | IDLE     | route READY, not yet executing (no session evidence)
```

---

## 四、本地访问

- **前端**：http://localhost:5173 （Vite HMR，改代码即刷新）
- **后端**：http://127.0.0.1:8790 （BFF，只读）
- 统一启动：`apps/second-brain-command-center/start.sh`

> 注：后端因 Windows socket 残留从约定的 8788 换到 8790，Vite 代理已同步。

---

## 五、明确未做（越界即违规）

- ❌ 无任何写操作 / merge / 建第二 Control Tower
- ❌ 无交易 / 下单 / 账户权限
- ❌ 无自动派发 / 进程启动
- ❌ 浏览器不含任何 secret

---

## 六、Phase 2/3 扩展点（已声明，fail-closed）

- **Phase 2**：`dispatch-intent` 接 Control Tower 校验（route/claim/lease/collision）
- **Phase 3**：`start` 接 Host Broker（需 R194 physical canary 证明）
- **Phase 4+**：W3 认知 UI / 知识图谱 / Decision Episodes / 交易情报 / AI导演深度 UI
- **Project Plugin**：新增项目 = registry + adapter + frontend manifest，**不改 Shell**

---

## 七、待跟进

1. **前端已 commit 到 `workbuddy/command-center-mvp` 分支，未 merge main**（遵守禁自审自合铁律，等你走 review→canonicalize）
2. W3 真实接口接入后，`/api/health` 的 W3 组件可从 UNAVAILABLE 升级
3. 项目插件契约中的 `ProjectFrontendManifest` 为 Phase 2 设计稿，尚未实施
4. Windows 端口残留问题：建议后续在 `start.sh` 加端口占用检测
