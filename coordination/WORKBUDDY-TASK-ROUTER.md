# WorkBuddy任务路由协议

当用户在WorkBuddy中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，WorkBuddy必须按以下顺序行动：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录猜测其他仓库。
2. 明确身份：本协议用于 `WorkBuddy执行者` 领取自身现场任务；Issue #7是Codex自动调度基础设施任务，只用于唤醒或维护Codex调度器，永远不是WorkBuddy任务入口。
3. 用户直接对WorkBuddy发出短命令时，不得跳转Issue #7，不得进入 `CodexDispatch` 等待态，也不得反问用户当前要做什么。
4. Issue #26及父Issue #22已完成关闭，不得继续把“等待GPT处理Issue #26”作为当前状态或阻断理由。
5. 先同步或直接读取远端最新 `main`。若本地工作区不适合快进、存在未提交内容或本地网络无法安全同步，不得覆盖工作区，应直接读取GitHub远端最新文件。
6. 读取最新 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
7. 读取其中的 `active_issue`、`mode`、`status`、`dependencies`、`task_impact_forecast`、`required_action`、`routing_guard` 和 `safety_boundary`。
8. 仅当 `status: READY` 且依赖满足时，读取对应Issue正文与全部评论。
9. 按Issue显式标注的WorkBuddy模式执行，不得自行更换模式或扩大现场扫描范围。
10. 必须读取任务影响预测，观察实际收益、负面效果、意外事件和停止条件。
11. 不得执行Codex活动索引、Issue #7、其他Issue、最近聊天任务或已被 `supersedes` 替代的旧任务。
12. 用户临时讨论的做T策略或其他研究工作应独立保存，等GPT建立新Issue或显式调整队列；不得抢占当前活动Issue。
13. 完成后创建独立分支和PR，不自行合并，并按完整Agent执行反馈v2及结果校准要求回传。
14. 无法确认远端最新索引、权限边界、路径允许列表或安全状态时，停止并报告，不得回退到旧调度器猜任务。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一WorkBuddy任务真源：远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。