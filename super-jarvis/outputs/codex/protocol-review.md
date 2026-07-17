# Super Jarvis Shared Protocol Review

审查时间：2026-06-17  
审查对象：`F:/ai/super-jarvis`

## 结论

共享协议目录已经具备基础可用形态：任务、记忆、决策三个核心 schema 存在且均通过 JSON Schema Draft-07 元校验；当前 pending 任务、profile memory、decision record 样本均能通过对应 schema 校验。

主要问题有两个：`memory/episodic.jsonl` 当前内容是 `[]`，不符合 JSONL 记录流格式，也不符合 memory schema 的实例约束；任务清单要求读取的 `WORKBUDDY_EXECUTION_FRAMEWORK` / `workbuddy.execution.config.json` 未在 `F:/ai/super-jarvis` 或 `F:/ai` 文件清单中定位到。

## 目录完整性

已存在的核心目录：

- `protocols/`
- `tasks/pending/`
- `tasks/running/`
- `tasks/done/`
- `tasks/failed/`
- `memory/`
- `decisions/`
- `inbox/`
- `outputs/codex/`
- `outputs/qclaw/`
- `outputs/workbuddy/`
- `second_brain/indexes/`
- `second_brain/notes/`
- `second_brain/sources/`

已存在的核心文件：

- `protocols/task.schema.json`
- `protocols/memory.schema.json`
- `protocols/decision.schema.json`
- `protocols/ai_girlfriend_layer_config.json`
- `memory/profile.json`
- `memory/episodic.jsonl`
- `decisions/decision_records.jsonl`
- `inbox/user_requests.jsonl`

缺失或需要补齐的文件：

- `WORKBUDDY_EXECUTION_FRAMEWORK.md`
- `workbuddy.execution.config.json`
- inbox/user request schema，例如 `protocols/user_request.schema.json`
- agent 输出清单或结果 schema，例如 `protocols/output.schema.json`

## Schema 校验结果

使用 Python `jsonschema` 对三个 schema 执行 `Draft7Validator.check_schema()`，结果如下：

| Schema | 元校验 | 备注 |
| --- | --- | --- |
| `protocols/task.schema.json` | 通过 | Draft-07 schema 有效 |
| `protocols/memory.schema.json` | 通过 | Draft-07 schema 有效 |
| `protocols/decision.schema.json` | 通过 | Draft-07 schema 有效 |

实例校验结果：

| 实例 | Schema | 结果 | 备注 |
| --- | --- | --- | --- |
| `tasks/pending/task_20260617_001.json` | task | 通过 | 当前任务对象结构有效 |
| `memory/profile.json` | memory | 通过 | profile memory 结构有效 |
| `decisions/decision_records.jsonl:1` | decision | 通过 | 决策记录结构有效 |
| `memory/episodic.jsonl:1` | memory | 未通过 | 文件内容为 `[]`，不是单条 memory object，也不符合 JSONL 记录流 |

## Schema 正确性问题

1. `memory.schema.json` 的 `oneOf` 分支缺少显式 `"type": "object"`。根级已有 `"type": "object"`，所以正常校验实例时仍会阻止数组通过；但错误信息会显示数组同时匹配多个分支，说明分支本身不够自洽。建议每个分支都加 `"type": "object"`。

2. 三个 schema 都未设置 `"additionalProperties": false`。这会允许协议对象携带未定义字段，短期利于兼容，长期会降低跨 agent 协议的可审计性。建议核心记录先收紧，扩展字段放入明确的 `metadata` 对象。

3. `task.schema.json` 的 `input` 只要求 object，没有按 `type` 定义子结构。现在能承载任意任务，但不能防止关键字段缺失。建议按任务类型增加 `oneOf` 或 `$defs`，至少覆盖 `system_integration`、`code_generation`、`code_review`。

4. `memory.schema.json` 未覆盖当前 AI Girlfriend 配置中声明的 `preferences` 读权限。schema 目前只有 `profile`、`episodic`、`relationship`、`fact`。建议补充 `preference` 类型，或把配置里的 `preferences` 改成已有的 `profile`/`relationship`。

5. `decision.schema.json` 对 `tools_called`、`memory_used`、`knowledge_used` 只约束为字符串数组，没有记录状态、失败原因、耗时和产物路径。对后续审计和复盘不够。

## 协议文件问题

1. `memory/episodic.jsonl` 和 `inbox/user_requests.jsonl` 当前内容均为 `[]`。如果文件命名为 `.jsonl`，空文件应为 0 字节，或每行一条 JSON object；`[]` 是 JSON 数组，不是 JSONL。

2. `protocols/ai_girlfriend_layer_config.json` 是有效 JSON，但没有对应 schema。建议增加 schema，约束 `role`、`memory_access`、`calls_workbuddy_for` 和敏感操作规则。

3. `decisions/decision_records.jsonl` 使用 UTF-8 读取正常；PowerShell 默认读取时可能出现中文乱码。这不是文件内容错误，但建议所有脚本显式使用 UTF-8。

## 改进建议

优先级 P0：

- 将 `memory/episodic.jsonl` 改为空文件，或改为一行一条 episodic memory object。
- 将 `inbox/user_requests.jsonl` 改为空文件，或补充 `user_request.schema.json` 并使用一行一条请求对象。
- 补齐 `WORKBUDDY_EXECUTION_FRAMEWORK.md` 和 `workbuddy.execution.config.json`，否则后续 agent 只能从 decision record 反推协议约束。

优先级 P1：

- 给 `memory.schema.json` 的每个 `oneOf` 分支增加 `"type": "object"`。
- 给三个核心 schema 增加 `additionalProperties` 策略，推荐核心字段封闭、扩展字段统一进入 `metadata`。
- 增加 `preference` memory 类型，保持 schema 与 AI Girlfriend 配置一致。
- 给 `tasks/done` 中的完成任务约定 `result_summary`、`completed_at`、`output_path` 字段。

优先级 P2：

- 增加协议级 `README.md`，说明目录读写权责：WorkBuddy、Codex、QClaw、AI Girlfriend 分别读写哪些目录。
- 增加 `protocols/output.schema.json`，统一 agent 输出记录格式。
- 增加自动校验脚本，例如 `protocols/validate_protocol.py`，在任务移动到 `done` 前执行。

## 建议的最小修复清单

1. 清空 `memory/episodic.jsonl` 和 `inbox/user_requests.jsonl`，保留为真正 JSONL 空流。
2. 新增 `WORKBUDDY_EXECUTION_FRAMEWORK.md`，把当前目录契约、路由规则、任务生命周期写成源头文档。
3. 修改 `memory.schema.json`，给每个分支加 `"type": "object"` 并补充 `preference`。
4. 修改 `task.schema.json`，增加完成态字段：`completed_at`、`output_path`。
5. 新增 schema 校验脚本，校验 schema 元结构、JSON/JSONL 文件格式、实例是否匹配。
