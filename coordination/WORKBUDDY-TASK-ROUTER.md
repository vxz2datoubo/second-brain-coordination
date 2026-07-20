# WorkBuddy任务路由协议

当用户在WorkBuddy中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，WorkBuddy必须按以下顺序行动：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录猜测其他仓库。
2. 先同步或直接读取远端最新 `main`，不得使用未经确认的本地旧索引；若本地有未提交内容，不得为了同步而覆盖工作区。
3. 读取最新 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
4. 读取其中的 `active_issue`、`mode`、`status`、`dependencies`、`task_impact_forecast`、`required_action` 和 `safety_boundary`。
5. 仅当 `status: READY` 且依赖满足时，读取对应Issue正文与全部评论。
6. 按Issue显式标注的WorkBuddy模式执行，不得自行更换模式或扩大现场扫描范围。
7. 必须读取任务影响预测，观察实际收益、负面效果、意外事件和停止条件。
8. 不得执行Codex活动索引、其他Issue或已被 `supersedes` 替代的旧任务。
9. 完成后创建独立分支和PR，不自行合并，并按完整Agent执行反馈v2及结果校准要求回传。
10. 无法确认远端最新索引、权限边界、路径允许列表或安全状态时，停止并报告，不得猜测。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一WorkBuddy任务真源：远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
