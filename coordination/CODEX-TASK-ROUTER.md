# Codex任务路由协议

当用户在Codex中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，Codex必须按以下顺序行动：

1. 打开本仓库 `coordination/ACTIVE-CODEX-TASK.yaml`。
2. 读取其中的 `active_issue`、`mode`、`status`、`blocked_by` 与 `notes`。
3. 仅当 `status: READY` 时，读取对应GitHub Issue的正文与全部评论。
4. 按Issue中明确标注的Codex模式执行，不得自行更换模式。
5. 若Issue存在旧的 TIMEOUT、INVALID、UNKNOWN 或过期回执，只把它们当历史记录，不得当作本次任务完成证据。
6. 执行前确认仓库名、Issue编号和当前活动任务一致。
7. 任务完成后按Agent执行反馈v2回传，并在Issue中留下证据。
8. 若入口文件缺失、状态不是READY、Issue不存在或存在冲突，停止执行并报告，不得猜测任务。
9. 不得因为用户只说“读取任务”就扫描或执行其他Issue。

固定仓库：`vxz2datoubo/second-brain-coordination`
