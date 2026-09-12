# 数据源权威矩阵 · Data Source Authority Matrix

> 核心原则：**UI STATE IS NOT SYSTEM TRUTH.** 前端只投影，不定义权威。

## 权威来源（Authority of Record）

| 领域 | 权威来源 | 前端读取方式 | 信任等级 |
|---|---|---|---|
| 工程同步 | GitHub canonical `main` | `gh api repos/.../commits/main` | CANONICAL |
| 项目集合 | `coordination/EXECUTION/PROJECT-REGISTRY.yaml` | 本地 YAML | CANONICAL |
| 执行权威 | `coordination/ACTIVE-*` + `ACTIVE-PROGRAM-LANES.yaml` | 本地 YAML | CANONICAL |
| 项目适配器 | `coordination/EXECUTION/PROJECT-ADAPTERS/*.yaml` | 本地 YAML | CANONICAL |
| 控制塔投影 | `coordination/PROGRAM-CONTROL-TOWER.md` (autogen 区) | 本地 Markdown | DERIVED |
| 本地运行时 | git working tree / worktrees | `git` 只读命令 | RUNTIME_OBSERVED |
| 语义记忆 | W3 / CLTM MemoryStore | **Phase 1 未连接** | UNKNOWN |
| 交易数据 | 声明的数据提供方（运行时可验证来源） | **Phase 1 未连接** | UNKNOWN |
| AI 导演领域 | `vxz2datoubo/eustia-ai-film` | 仅本地 git 状态 | RUNTIME_OBSERVED |

## 前端不得成为权威的场景

- 不得复制一份 task 状态后自行维护（用 GitHub/ACTIVE-* 真源）
- 不得从 Markdown 假装生成真实 memory 状态（W3 未连接 → UNAVAILABLE）
- 不得用 legacy broken `knowledge-graph.json` 冒充 canonical graph
- 不得把 PID / heartbeat 当作"正在施工"证据

## 明确不使用（Phase 1）

| 来源 | 原因 |
|---|---|
| W3 真实接口 | 契约未接入，诚实标注 UNAVAILABLE |
| Trading provider | 无授权 data adapter，标 NO_TRADE |
| Host Broker runtime | 自动派发未启用（Phase 3 需 canary 证明） |
| 浏览器直连 GitHub token | 安全边界：凭据只在 BFF |

## Provenance 传播规则

每个重要 API 响应携带 `meta`：

```json
{
  "data": { },
  "meta": {
    "observed_at": "2026-09-11T22:40:00Z",
    "freshness": "FRESH | AGING | STALE | UNKNOWN",
    "authority": "GITHUB | CONTROL_TOWER | PROJECT_REGISTRY | LOCAL_GIT_RUNTIME",
    "trust": "CANONICAL | CANDIDATE | RUNTIME_OBSERVED | DERIVED | HISTORICAL | UNKNOWN",
    "projection_status": "COMPLETE | PARTIAL | UNAVAILABLE",
    "sources": [ { "kind": "local_file", "path": "..." } ],
    "warnings": [ ]
  }
}
```

UI 的 Provenance 抽屉直接消费该结构，保证"这个状态不是 UI 编出来的"可被验证。
