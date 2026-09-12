# 架构 · Architecture

## 定位

Command Center 是 **READ MODEL + COMMAND SURFACE + VISUALIZATION + HUMAN INTERACTION**
层。它**不是**新的 W3 / Control Tower / Signal Tower / scheduler / task registry /
canonical database。

## 三层结构

```
┌─────────────────────────────────────────────┐
│  Browser (React + TS + Vite)                │
│  - 零外部 CDN/框架依赖，内联 SVG 图标        │
│  - 不持有任何凭据                            │
│  - UI STATE IS NOT SYSTEM TRUTH             │
└──────────────────┬──────────────────────────┘
                   │ /api (Vite proxy)
┌──────────────────▼──────────────────────────┐
│  Thin BFF (FastAPI, READ-ONLY)              │
│  - READ / NORMALIZE / PROJECT               │
│  - 凭据边界（gh CLI 在此）                   │
│  - 统一 ViewModel + meta(provenance)        │
│  - 不重新决定 authority / truth              │
└──────────────────┬──────────────────────────┘
      ┌────────────┼────────────┬─────────────┐
      ▼            ▼            ▼             ▼
  GitHub      本地仓库      Control Tower   （W3 / Trading
  (gh CLI)   (git只读)     (ACTIVE-*/lanes)   Phase 1 未连接）
```

## 数据流（单向，无环）

`authority source → adapter → normalize → ViewModel + Meta → API → hook → page render`

- 渲染层不互相调用，统一由 `App.tsx` 的 `refreshAll()` 调度
- 每个 adapter 只读，绝不写回
- 每个响应带 `meta`，前端 Provenance 抽屉可追溯

## 可移植性（跨 AI 宿主 / 跨机器）

- `repo_paths.py` 不硬编码绝对路径：环境变量 → 候选根目录 → 包位置回溯
- 新 AI 只需读 `COMMAND-CENTER-BOOTSTRAP.yaml` 即可定位系统
- 不依赖任何 WorkBuddy 本地记忆

## 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 前端 | React + TypeScript + Vite | 企业级、HMR、类型安全 |
| 路由 | React Router | 深度链接（稳定 URL） |
| 样式 | 手写 CSS + 设计令牌 | 零外部依赖，可主题化 |
| 图标 | 内联 SVG path | 无 emoji，无图标库 |
| BFF | FastAPI + Pydantic | OpenAPI 契约、类型生成友好 |
| Git 读取 | subprocess `git` | 无额外依赖，只读 |
| GitHub 读取 | `gh` CLI | 已认证，只读命令面 |

> 第一版 **LOCAL-FIRST / SINGLE-USER / READ-MOSTLY / MODULAR / RELIABLE**。
> 不在 Phase 1 引入 microservices / K8s / OAuth / RBAC server。

## 阶段路线

| Phase | 内容 | 状态 |
|---|---|---|
| 1 | READ-ONLY Command Center MVP | ✅ 本目录 |
| 2 | 控制塔派发（DispatchIntent，不启动进程） | ⏳ 接口已预留 |
| 3 | Host Broker 自动派发（需 R194 canary 证明） | ⏳ 接口已预留 |
| 4 | 认知 UI（W3 / 知识图谱 / Decision Episodes） | 规划 |
| 5 | 交易情报 UI（只读 market adapter） | 规划 |
| 6 | AI 导演 / 互动电影深度 UI | 规划 |

## 错误与降级

- 单个 source 失败不白屏：显示哪个 source 失败 + 最后成功数据 + 重试
- GitHub 断网时本地快照仍可读，标 `REMOTE_NOT_VERIFIED`
- 未连接的真实源诚实标 `UNAVAILABLE`，不伪造 healthy
