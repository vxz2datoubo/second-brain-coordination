# Super Jarvis 三方协作工作区指南

生成时间：2026-06-17  
工作区根目录：`F:/ai`

本文定义 WorkBuddy、Codex、QClaw 在 `F:/ai` 下共享协作的目录边界、读写权限、任务协议、结果交付和异常回退策略。现有 `super-jarvis/` 已具备 Phase 1 的协议基础，三方协作应优先复用现有目录与 schema，而不是另起一套并行协议。

## 1. 工作区全景图

```text
F:/ai/
├─ super-jarvis/                         # 三方共享协议与协作状态中心
│  ├─ inbox/
│  │  └─ user_requests.jsonl             # 用户入口请求流，由 WorkBuddy 优先读取和分流
│  ├─ tasks/
│  │  ├─ pending/                        # 待执行任务，每个任务一个 JSON 文件
│  │  ├─ running/                        # 执行中的任务，领取后从 pending 移入
│  │  ├─ done/                           # 已完成任务，写入 result_summary
│  │  └─ failed/                         # 失败或取消任务，保留错误原因
│  ├─ outputs/
│  │  ├─ workbuddy/                      # WorkBuddy 的计划、路由、复盘产物
│  │  ├─ codex/                          # Codex 的代码审查、实现说明、补丁报告
│  │  └─ qclaw/                          # QClaw 的分析、摘要、索引、批处理产物
│  ├─ decisions/
│  │  └─ decision_records.jsonl          # WorkBuddy 决策审计记录
│  ├─ memory/
│  │  ├─ profile.json                    # 稳定画像与长期偏好
│  │  └─ episodic.jsonl                  # 事件记忆流，每行一个 memory object
│  ├─ protocols/
│  │  ├─ task.schema.json                # 跨 agent 任务对象 schema
│  │  ├─ memory.schema.json              # 记忆对象 schema
│  │  ├─ decision.schema.json            # 决策记录 schema
│  │  └─ ai_girlfriend_layer_config.json # 已有角色层配置
│  ├─ second_brain/
│  │  ├─ sources/                        # 原始资料和外部输入材料
│  │  ├─ notes/                          # 人类可读笔记、摘要、复盘
│  │  └─ indexes/                        # 检索索引、标签、映射表
│  ├─ TRI-WORKSPACE-GUIDE.md             # 本文件
│  └─ collaboration-prompts.json         # 三个角色可直接复制使用的协作 prompt
├─ data/
│  └─ knowledge-graph.json               # 项目知识图谱，QClaw 与 WorkBuddy 优先读取
├─ core/                                 # 核心模块，如 qclaw.py、codex_bridge.py
├─ mcp/                                  # MCP 桥接工具，如 qclaw_bridge.py、codex_bridge.py、fs_tools.py
├─ qclaw-output/                         # QClaw 既有输出目录，需归档摘要到 super-jarvis/outputs/qclaw/
├─ CODEBUDDY.md                          # 项目上下文说明，三方都应读取
├─ server.py                             # 第二大脑 HTTP 服务
└─ app/index.html                        # 前端入口
```

## 2. 角色分工与路径权限

| 角色 | 定位 | 主要读取路径 | 主要写入路径 | 不应直接写入 |
| --- | --- | --- | --- | --- |
| WorkBuddy | 中枢调度器，负责路由、记忆、决策、工具调用 | `CODEBUDDY.md`、`super-jarvis/inbox/`、`super-jarvis/tasks/`、`super-jarvis/memory/`、`super-jarvis/outputs/*/`、`data/knowledge-graph.json` | `super-jarvis/tasks/pending/`、`super-jarvis/decisions/decision_records.jsonl`、`super-jarvis/memory/`、`super-jarvis/outputs/workbuddy/` | `core/`、`mcp/`、`app/` 的代码文件，除非任务明确要求且用户授权 |
| Codex | 工程实现者，负责代码生成、重构、审查、调试 | `CODEBUDDY.md`、`super-jarvis/tasks/pending|running/` 中分配给 `codex` 的任务、`protocols/`、`core/`、`mcp/`、`server.py`、`app/` | `core/`、`mcp/`、`server.py`、`app/`、`super-jarvis/outputs/codex/`、对应任务状态目录 | `memory/profile.json`、`decisions/decision_records.jsonl`，除非任务明确要求补充工程事实 |
| QClaw | 后台算力，负责分析、总结、索引、批处理 | `CODEBUDDY.md`、`data/knowledge-graph.json`、`qclaw-output/`、`second_brain/sources/`、分配给 `qclaw` 的任务 | `super-jarvis/outputs/qclaw/`、`super-jarvis/second_brain/notes/`、`super-jarvis/second_brain/indexes/`、`qclaw-output/` | 工程代码目录，除非任务类型是分析或生成建议且不直接落地代码 |

### 2.1 写入原则

- `super-jarvis/tasks/*` 是任务状态事实源。任务从 `pending` 到 `running` 到 `done` 或 `failed`，不得只改 `status` 而不移动目录。
- `outputs/{role}/` 是角色产物归档区。较长报告、审查、摘要、索引结果写入这里，任务 JSON 只保留 `result_summary` 和产物路径。
- `decisions/decision_records.jsonl` 只记录调度决策，不记录完整推理链。`reason_summary` 应是可审计摘要。
- `memory/` 只写稳定事实、用户偏好、重要事件。临时过程信息写入任务或输出文件，不污染长期记忆。
- `second_brain/` 用于知识沉淀。原文进 `sources/`，人类可读摘要进 `notes/`，机器检索结构进 `indexes/`。

## 3. 文件格式与命名规则

### 3.1 任务文件

任务文件遵循 `super-jarvis/protocols/task.schema.json`。

命名：

```text
task_YYYYMMDD_NNN.json
```

示例：

```json
{
  "id": "task_20260617_002",
  "created_at": "2026-06-17T14:00:00+08:00",
  "source": "workbuddy",
  "assignee": "codex",
  "type": "system_integration",
  "priority": "high",
  "status": "pending",
  "input": {
    "action": "implement_bridge",
    "paths": ["F:/ai/mcp/codex_bridge.py"],
    "constraints": ["preserve_existing_behavior"]
  },
  "expected_output": "working_code_and_summary",
  "requires_user_approval": false,
  "tags": ["integration", "codex"]
}
```

状态流转：

```text
pending/task_*.json -> running/task_*.json -> done/task_*.json
                                  \---------> failed/task_*.json
```

领取任务时：

- 将文件从 `pending/` 移动到 `running/`。
- 将 `status` 改为 `running`。
- 如需补充执行计划，可在 `input.execution_plan` 或 `outputs/{role}/` 写计划文件。

完成任务时：

- 将 `status` 改为 `done`。
- 填写 `result_summary`。
- 长结果写到 `outputs/{role}/`，在 `result_summary` 或 `input.artifacts` 中引用路径。
- 移动到 `done/`。

失败任务时：

- 将 `status` 改为 `failed`。
- 在 `result_summary` 中写明失败点、已完成内容、可重试条件。
- 若有诊断报告，写入 `outputs/{role}/`。
- 移动到 `failed/`。

### 3.2 决策记录

决策记录遵循 `super-jarvis/protocols/decision.schema.json`，追加到：

```text
super-jarvis/decisions/decision_records.jsonl
```

命名 ID：

```text
decision_YYYYMMDD_NNN
```

每行一个 JSON object，不使用数组包裹。

### 3.3 记忆记录

`memory/profile.json` 保存稳定 profile object。  
`memory/episodic.jsonl` 应为 JSONL：每行一个 memory object，不应写成 `[]`。

记忆写入标准：

- 只记录对未来任务有复用价值的事实。
- 明确 `source` 或 `recorded_at`。
- 不把临时代码日志、失败堆栈、长报告写入记忆。
- 重要性低于 3 的事件优先写任务摘要，不进入长期记忆。

### 3.4 输出文件

输出文件建议命名：

```text
YYYYMMDD-HHMM-{task_id}-{short-topic}.md
YYYYMMDD-HHMM-{task_id}-{short-topic}.json
```

示例：

```text
super-jarvis/outputs/codex/20260617-1415-task_20260617_002-bridge-implementation.md
super-jarvis/outputs/qclaw/20260617-1420-task_20260617_003-knowledge-index.json
```

Markdown 报告建议结构：

```text
# 标题

任务：task_YYYYMMDD_NNN
角色：codex|qclaw|workbuddy
时间：ISO 8601

## 结论
## 关键发现
## 产物路径
## 风险与后续动作
```

## 4. 三方通信协议

### 4.1 发起任务

1. 用户请求先进入 `super-jarvis/inbox/user_requests.jsonl`，或由 WorkBuddy 直接接收。
2. WorkBuddy 读取 `CODEBUDDY.md`、`memory/`、`data/knowledge-graph.json` 和相关输出。
3. WorkBuddy 生成决策记录，追加到 `decisions/decision_records.jsonl`。
4. WorkBuddy 根据任务类型创建 `tasks/pending/task_*.json`。

推荐路由：

| 任务类型 | 默认 assignee | 说明 |
| --- | --- | --- |
| `code_generation` | `codex` | 新增代码、脚本、配置、测试 |
| `code_review` | `codex` | 审查缺陷、风险、测试缺口 |
| `system_integration` | `codex` | 桥接、服务、前后端集成 |
| `knowledge_analysis` | `qclaw` | 图谱分析、资料理解、结构化洞察 |
| `conversation_summary` | `qclaw` | 长上下文摘要、归档 |
| `knowledge_indexing` | `qclaw` | second_brain 索引和标签 |
| `batch_planning` | `qclaw` | 批处理计划、离线任务分解 |
| `memory_consolidation` | `workbuddy` 或 `qclaw` | WorkBuddy 决策，QClaw 可辅助压缩 |
| `daily_review` / `weekly_review` | `workbuddy` 或 `qclaw` | WorkBuddy 汇总，QClaw 做长文本分析 |

### 4.2 领取与执行

执行者只领取 `assignee` 等于自己的任务。领取后：

1. 校验任务 JSON 是否满足 `task.schema.json`。
2. 从 `pending/` 移到 `running/`。
3. 更新 `status` 为 `running`。
4. 读取 `expected_output` 和 `requires_user_approval`。
5. 若任务需要写代码、删除文件、调用外部服务或触及用户敏感数据，先确认是否已有授权。

### 4.3 传递结果

执行结果分三层：

- 简短结论：写入任务 JSON 的 `result_summary`。
- 完整产物：写入 `super-jarvis/outputs/{role}/` 或角色专属产物目录。
- 可复用知识：由 WorkBuddy 或 QClaw 评估后写入 `memory/` 或 `second_brain/`。

结果完成后：

1. 更新任务 JSON 为 `done`。
2. 移动到 `tasks/done/`。
3. WorkBuddy 读取完成任务并决定是否继续拆分新任务。

### 4.4 状态同步

WorkBuddy 是状态汇总者：

- 定期扫描 `tasks/running/`，发现超时任务后标记风险。
- 定期扫描 `tasks/done/`，提取 `result_summary` 到决策或记忆。
- 定期扫描 `tasks/failed/`，决定重试、降级或请求用户确认。

Codex 和 QClaw 不应互相直接改对方输出。需要协作时，由 WorkBuddy 创建新任务或在当前任务中声明依赖。

### 4.5 依赖任务

任务依赖建议写入 `input.dependencies`：

```json
{
  "dependencies": [
    {
      "task_id": "task_20260617_003",
      "artifact": "F:/ai/super-jarvis/outputs/qclaw/20260617-1420-task_20260617_003-knowledge-index.json",
      "required": true
    }
  ]
}
```

若依赖不存在或未完成，执行者应将任务留在 `pending/`，或移动到 `failed/` 并说明阻塞条件。不要伪造依赖结果。

## 5. 错误处理与回退策略

### 5.1 通用错误分类

| 错误类型 | 处理策略 |
| --- | --- |
| schema 不合法 | 不执行任务；写入失败摘要；由 WorkBuddy 重建任务 |
| 缺少输入文件 | 标记 failed，说明缺失路径；WorkBuddy 决定补充资料或改派 |
| 权限不足 | 停止写入；记录所需权限；请求用户或 WorkBuddy 明确授权 |
| 任务目标不清 | 不做大范围猜测；写入澄清问题；WorkBuddy 回到用户侧确认 |
| 代码修改失败 | 保留诊断报告；不回滚非本任务变更；Codex 给出最小修复建议 |
| 分析结果不确定 | QClaw 标注置信度和数据来源；WorkBuddy 决定是否追加验证任务 |
| 长时间运行 | WorkBuddy 检查 `running/` 年龄；必要时拆分或重试 |

### 5.2 Codex 回退

- 修改前读取相关文件和现有模式。
- 遇到脏工作区时，不回退用户已有改动。
- 若测试不可运行，说明原因并提供手动验证路径。
- 若任务要求超出工程边界，写入审查或设计建议，不直接改业务决策。

### 5.3 QClaw 回退

- 输入过大时先做分块摘要，再合并结论。
- 来源冲突时保留冲突列表，不强行合并为单一事实。
- 索引失败时输出可读摘要，等待 WorkBuddy 或 Codex 修复索引管线。

### 5.4 WorkBuddy 回退

- 无法判断路由时，优先拆成低风险分析任务给 QClaw，再交给 Codex 实现。
- 高风险操作必须创建 `requires_user_approval: true` 的任务。
- 连续失败任务不应无限重试；第三次失败后请求用户确认或降级目标。

## 6. 最小协作闭环

```text
用户请求
  -> WorkBuddy 记录 inbox 和 decision
  -> WorkBuddy 创建 pending task
  -> Codex/QClaw 领取 running task
  -> 执行者写 outputs/{role}/
  -> 执行者更新 done 或 failed
  -> WorkBuddy 汇总结果，必要时写 memory 或 second_brain
  -> WorkBuddy 返回用户或创建下一步任务
```

## 7. 当前建议补强项

- 为 `inbox/user_requests.jsonl` 增加 `protocols/user_request.schema.json`。
- 为 `outputs/{role}/` 增加统一产物 manifest 或 `output.schema.json`。
- 将 `memory/episodic.jsonl` 保持为真正 JSONL；如果当前内容是 `[]`，下次写入前应转换为空文件或逐行对象。
- 对 `task.schema.json` 增加 `metadata` 字段，用于记录 `artifacts`、`dependencies`、`error`、`started_at`、`completed_at`。
