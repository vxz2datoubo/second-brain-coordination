# Codex任务路由协议

当用户在Codex中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，Codex必须按以下顺序行动：

1. 固定目标仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录猜测其他仓库。
2. **先同步远端最新 `main`**：优先执行安全的 `git fetch origin main`，并从最新 `origin/main` 读取路由和活动索引。若本地工作区不适合快进或存在未提交改动，不得覆盖本地内容，应直接读取GitHub远端最新文件。
3. 禁止使用未验证的新旧本地缓存副本作为任务来源；必须确认读取到的 `coordination/ACTIVE-CODEX-TASK.yaml` 来自当前远端最新 `main`。
4. 打开最新 `coordination/ACTIVE-CODEX-TASK.yaml`。
5. 读取其中的 `active_issue`、`mode`、`status`、`blocked_by`、`dependencies` 与 `notes`。
6. 仅当 `status: READY` 且依赖状态满足时，读取对应GitHub Issue的正文与全部评论。
7. 按Issue中明确标注的Codex模式执行，不得自行更换模式。
8. 若Issue存在旧的 TIMEOUT、INVALID、UNKNOWN 或过期回执，只把它们当历史记录，不得当作本次任务完成证据。
9. 执行前确认仓库名、最新远端索引、Issue编号和当前活动任务完全一致。
10. 任务完成后按Agent执行反馈v2回传，并在活动Issue和父Issue中留下证据。
11. 若远端入口文件缺失、状态不是READY、依赖未满足、Issue不存在、索引版本冲突或无法确认远端最新状态，停止执行并报告，不得猜测任务。
12. 不得因为用户只说“读取任务”就扫描、选择或执行其他Issue。
13. 不得重新执行 `supersedes` 中记录的旧活动任务。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一任务真源：远端最新 `main` 上的 `coordination/ACTIVE-CODEX-TASK.yaml`。
