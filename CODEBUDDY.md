# 第二大脑项目 · Codex 上下文地图

> 这个文件是 Codex 的入口级上下文说明。每次进入 F:/aidanao/ 工作空间，先读这个。
> 它告诉你整个系统的文件结构、模块职责、写入规则和约定。

---

## 一、文件系统地图

```
F:/aidanao/
├── CODEBUDDY.md         ← 项目上下文（本文件）
├── server.py             ← 第二大脑 HTTP 服务器 (localhost:8766)
│
├── core/                 ← 核心模块（可读写，注意依赖）
│   ├── qclaw.py          ← QClaw 桥接 (纯算力引擎)
│   ├── codex_bridge.py   ← Codex 桥接 (智能体)  
│   └── ...
│
├── mcp/                  ← MCP 协议桥接（可读写）
│   ├── qclaw_bridge.py   ← QClaw MCP 服务器
│   └── codex_bridge.py   ← Codex MCP 服务器
│
├── data/                 ← 知识图谱数据（谨慎写）
│   ├── knowledge-graph.json   ← 主知识图谱
│   ├── category-index.json    ← 分类索引
│   └── ...
│
├── qclaw-output/         ← QClaw 产出物（可追加，不删除）
│   └── codex-runs/       ← Codex 产出物
│
├── app/                  ← Web 前端
│   └── index.html        ← 关系图谱可视化
│
├── tools/                ← 工具脚本（可读写）
│
├── girlfriend/           ← 小樱花 AI 女友系统
│
├── .workbuddy/           ← WorkBuddy 记忆/技能
│
├── exports/              ← 导出文件
├── imports/              ← 导入文件
│
├── HUMAN_BRAIN_ARCHITECTURE.md  ← 人类级认知架构总纲
├── second_brain/         ← 高级认知模块 (6层架构)
├── daytrade_system/      ← 日内交易系统
├── bulletin/             ← 公告
├── logs/                 ← 日志
└── decisions/            ← 决策记录

F:/work/
└── prompt-system/        ← Prompt Studio (localhost:8765)

F:/AiGirl/
└── QQSafeChat/           ← 小樱花完整系统
    └── core/
        └── sakura_brain_bridge.py  ← 小樱花↔第二大脑桥接
```

---

## 二、每个目录的职能说明

### core/ — 核心模块
| 文件 | 职责 | 写入规则 |
|------|------|---------|
| `qclaw.py` | QClaw 纯算力桥接，自动检测端口 | ⚠️ 不改架构，可加新功能 |
| `codex_bridge.py` | Codex 智能体桥接，CLI 调用 | ⚠️ 不改 `run()` 签名，可加工具 |
| `decision_consult.py` | 决策前检查，读第二大脑的决策教训 | 可优化，不改 API 签名 |

### data/ — 知识图谱
| 文件 | 职责 | 写入规则 |
|------|------|---------|
| `knowledge-graph.json` | 节点+边结构的知识图谱 | ✅ 可追加节点/边，❌ 不改现有节点ID |
| `category-index.json` | 分类索引和关键词 | ✅ 可追加新分类 |

### super-jarvis/ — 共享协议目录 (Super Jarvis Orchestration)
| 路径 | 职责 |
|------|------|
| `inbox/` | 用户请求队列 |
| `tasks/pending/`, `tasks/running/`, `tasks/done/`, `tasks/failed/` | 跨Agent任务调度 |
| `memory/` | 长期/情景/关系/偏好记忆 |
| `second_brain/` | 笔记/来源/索引 |
| `decisions/` | 可审计决策记录 |
| `outputs/workbuddy/`, `outputs/qclaw/, outputs/codex/` | 各Agent产出 |
| `protocols/` | schema 定义 (task/memory/decision) |

### mcp/ — MCP 协议桥接
| 文件 | 职责 | 写入规则 |
|------|------|---------|
| `qclaw_bridge.py` | QClaw MCP 服务器（stdin/stdout JSON-RPC） | 可加新工具 |
| `codex_bridge.py` | Codex MCP 服务器（stdin/stdout JSON-RPC） | 可加新工具 |
| `fs_tools.py` | 文件系统辅助工具 MCP 服务器 | 可加新工具 |

### qclaw-output/ — 产出物
- QClaw 产出: `*.md` 文件
- Codex 产出: `codex-runs/codex-{timestamp}.md`
- 规则: **只追加，不删除**，历史可追溯

---

## 三、关键模块依赖关系

```
WorkBuddy (迪迪)
  ├── QClaw (纯算力)           → core/qclaw.py + mcp/qclaw_bridge.py
  │    输出 → qclaw-output/*.md
  │    自动摄入 → 第二大脑 (POST /api/digest/text)
  │
  ├── Codex (智能体)            → core/codex_bridge.py + mcp/codex_bridge.py
  │    输出 → qclaw-output/codex-runs/*.md
  │    自动摄入 → 第二大脑 (POST /api/digest/text)
  │
  ├── 第二大脑 (知识库)         → server.py + data/*.json
  │    API: localhost:8766
  │    核心端点: /api/digest/text, /api/retrieve/search
  │
  ├── 小樱花 (AI女友)           → F:/AiGirl/QQSafeChat/
  │    桥接: sakura_brain_bridge.py → 第二大脑
  │
  └── Prompt Studio (提示词工坊) → F:/work/prompt-system/ (localhost:8765)
```

---

## 四、Codex 使用约定

### 调用方式
```bash
# 从 WorkBuddy 调
codex_run(prompt, cwd="F:/aidanao", sandbox="workspace-write", model="gpt-5-codex")

# 直接从 CLI
codex exec "任务" -C F:/aidanao -s workspace-write
```

### 沙箱策略
| 策略 | 权限 | 适用场景 |
|------|------|---------|
| `readonly` | 只读 | 审查代码、分析文件 |
| `workspace-write` | 可读写 CWD | 默认，改文件 |
| `danger-full-access` | 整个文件系统 | ⚠️ 必须显式声明 |

### 可用的 CWD（工作目录）
| CWD | 覆盖范围 | 推荐沙箱 |
|-----|---------|---------|
| `F:/aidanao` | 第二大脑核心 | workspace-write |
| `F:/` | 整个 F 盘 | readonly 或 显式 danger |
| `F:/work` | 工作区 | workspace-write |
| `F:/AiGirl` | 小樱花 | workspace-write |

### 产出规范
- Codex 产出保存到 `F:/aidanao/qclaw-output/codex-runs/`
- 文件名格式: `codex-{YYYYMMDD-HHMMSS}.md`
- 产出头部包含: 任务描述、CWD、沙箱、耗时
- 产出自动摄入第二大脑 (通过 POST /api/digest/text)

---

## 五、知识图谱结构

文件: `F:/aidanao/data/knowledge-graph.json`

```json
{
  "nodes": [
    {"id": "abc123", "type": "knowledge", "title": "节点标题", 
     "content": "内容", "category": "tech-ai", "tags": [...]},
    ...
  ],
  "edges": [
    {"source": "abc123", "target": "def456", "relation": "关联类型", "weight": 1.0},
    ...
  ]
}
```

### 节点分类
| 分类 | 含义 |
|------|------|
| `film-video` | AI视频/电影/运镜/提示词 |
| `tech-ai` | AI技术/工具/框架 |
| `business` | 商业/市场/投资 |
| `decision-lessons` | 决策教训/硬规则 |
| `girlfriend` | 小樱花系统 |
| `inbox` | 待分类 |

### 节点ID规则
- 格式: 6位 hex (如 `a1b2c3`)
- 写新节点时保持唯一性

---

## 六、Codex 常见任务模式

### 模式1: 分析现有产出
```
读取 qclaw-output/ 下最近的文件，总结产出趋势和模式
```
→ CWD: F:/aidanao, 沙箱: readonly

### 模式2: 重构模块
```
重构 core/decision_consult.py，保持 API 签名不变
```
→ CWD: F:/aidanao, 沙箱: workspace-write

### 模式3: 跨工作区分析
```
对比 F:/work/prompt-system/ 和 F:/aidanao/data/ 的数据结构
```
→ CWD: F:/, 沙箱: readonly

### 模式4: 知识图谱维护
```
读取 data/knowledge-graph.json，找出孤立节点
```
→ CWD: F:/aidanao, 沙箱: workspace-write

### 模式5: 小樱花系统优化
```
分析 F:/AiGirl/QQSafeChat/ 的代码结构
```
→ CWD: F:/AiGirl, 沙箱: readonly

---

_版本: 2.0 | 迁移至 F:/aidanao: 2026-06-30_
_维护: 如果文件系统结构有大的变化，更新本文件_
