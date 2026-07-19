# QClaw 输出 | 2026-06-17 13:45
> 模型: openclaw/default | 端口: 6362 | Token: 0

我来先确认一下共享工作区的实际情况和协议文档，然后再正式回答你的问题。

我已经把 `CODEBUDDY.md`、`TRI-WORKSPACE-GUIDE.md`、`task.schema.json`、`collaboration-prompts.json` 和现有 `tasks/`、`memory/`、`decisions/`、`inbox/` 全部读了一遍，工作区结构与协议都对得上。下面按你 4 个问题逐条回复。

---

# QClaw 角色确认 — Super Jarvis 三方协作框架

## 1. 角色定位：理解 ✅

我的定位是 **后台算力**（QClaw），三方协作中的第二象限：

- **我做什么**：长文本分析、资料总结、知识图谱理解、索引构建、批处理、趋势归纳、跨文件检索、可复用知识沉淀
- **我不做什么**：直接落地工程代码、修改 `core/`、`mcp/`、`server.py`、`app/`；需要工程实现时，我输出**分析建议 + Codex 可执行的结构化输入**
- **我的协作姿态**：只响应 `assignee == "qclaw"` 的任务，遵循 `TRI-WORKSPACE-GUIDE.md` 5.3 节的回退策略（分块摘要、保留冲突列表、索引失败时输出可读摘要）

`collaboration-prompts.json` 中"发给 QClaw 的协作 prompt"我已通读，定位与它完全一致。

## 2. 共享工作区结构与权限：理解 ✅

实际验证过的目录树（`F:\ai\super-jarvis\`）：

| 路径 | 状态 | 我的权限 |
|------|------|---------|
| `CODEBUDDY.md`、`TRI-WORKSPACE-GUIDE.md` | ✅ 已读 | 只读 |
| `super-jarvis/inbox/user_requests.jsonl` | 已有 1 条 setup_complete | 只读（不写） |
| `super-jarvis/tasks/pending/` | **当前为空** | 读 + 移动（领取） |
| `super-jarvis/tasks/running/` | **当前为空** | 写（领取时移入） |
| `super-jarvis/tasks/done/` | 已有 `task_20260617_001`（codex 的） | 只读 |
| `super-jarvis/tasks/failed/` | 空 | 写（失败时移入） |
| `super-jarvis/outputs/qclaw/` | 空 | ✅ **写分析报告/摘要/批处理** |
| `super-jarvis/second_brain/notes/` | 空 | ✅ 写人类可读笔记 |
| `super-jarvis/second_brain/indexes/` | 空 | ✅ 写索引/标签/映射 |
| `super-jarvis/second_brain/sources/` | 空 | ✅ 写原始资料（任务要求时） |
| `data/knowledge-graph.json` | 待读 | 只读 |
| `qclaw-output/` | 既有目录 | ✅ 继续使用 |
| `core/`、`mcp/`、`server.py`、`app/` | 工程代码 | ❌ 不写 |
| `memory/profile.json`、`decisions/decision_records.jsonl` | 由 WorkBuddy 写 | ❌ 不直接写；如需沉淀，写入任务结果由 WorkBuddy 决定入库 |

边界清楚。我会严守"`core/`/`mcp/`/应用代码 = Codex 的地盘"这条线。

## 3. 任务队列工作方式：理解 ✅

我完全理解状态机与协议：

```
pending/task_YYYYMMDD_NNN.json  ──领取──▶  running/task_*.json  ──完成──▶  done/task_*.json
                                                                  ╰──失败──▶  failed/task_*.json
```

**领取流程**（我会做的事）：
1. 扫 `tasks/pending/`，过滤 `assignee == "qclaw"`
2. 校验任务对象是否满足 `task.schema.json`（id、created_at、source、assignee、type、priority、status、input、expected_output、requires_user_approval 全部必填）
3. 从 `pending/` 移到 `running/`
4. `status: "pending" → "running"`
5. 读 `expected_output` 和 `requires_user_approval`（高风险任务会先停手确认）

**交付流程**：
1. 长产物写入 `super-jarvis/outputs/qclaw/`，命名 `YYYYMMDD-HHMM-{task_id}-{short-topic}.md` 或 `.json`
2. 任务 JSON `status: "running" → "done"`，填 `result_summary`（简短结论 + 产物路径）
3. 移动到 `tasks/done/`

**失败流程**：
- `status: "failed"`，在 `result_summary` 写清失败点、已完成内容、可重试条件
- 移动到 `tasks/failed/`，**不静默重试**，**不伪造依赖结果**

**当前观察**：
- `pending/` 和 `running/` 都是空的 → 还没有分配给 qclaw 的任务在排队
- `inbox/user_requests.jsonl` 只有 1 条 `setup_complete` 历史记录
- 我已经处于"待命就绪"状态，等 WorkBuddy 派发

## 4. 我的观察与建议（可调整项）

读完后我有 3 条不痛不痒但值得提一句的建议，**仅供你参考，不改动**：

1. **`task.schema.json` 没有 `metadata` 字段** — `TRI-WORKSPACE-GUIDE.md` 第 7 节已建议补 `artifacts`、`dependencies`、`error`、`started_at`、`completed_at`。这 5 个字段在做依赖图和审计时非常实用，建议在下一个协议迭代里加上。我领取任务时会在 `input` 之外、本地补这些时间戳到 `result_summary` 文本里，不强行改 schema。

2. **`memory/episodic.jsonl` 当前是空文件** — 符合 JSONL 标准（不是 `[]` 数组），干净。

3. **`outputs/qclaw/` 当前为空** — 我第一次交付时会顺便写一个 `QCLAW_HANDOVER.md` 概览（角色边界、常用读取路径、产物命名约定），方便 WorkBuddy 后续审计时一眼看清我的状态。这是我**主动**会做的，但如果你不喜欢这种自描述文件，告诉我我就停。

---

**结论**：角色、结构、协议三件套我都对得上了。pending 队列当前为空，我可以立即开始领任务。如果你下一条消息给我派 `assignee: "qclaw"` 的第一个任务，我会按上述流程走一遍：校验 → 移 `running/` → 执行 → 写 `outputs/qclaw/` → 改 `done/` → 回 `result_summary` 摘要。

需要我先在 `outputs/qclaw/` 落一份 `QCLAW_HANDOVER.md` 吗？还是直接等第一个任务派发？