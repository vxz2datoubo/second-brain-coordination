# Repository Agent Instructions

## Codex短命令路由

当用户对Codex说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 先同步或直接读取远端最新 `main`，不得使用未经确认的本地旧索引；若本地有未提交内容，不得为了同步而覆盖工作区。
3. 读取最新 `coordination/CODEX-TASK-ROUTER.md`。
4. 再读取最新 `coordination/ACTIVE-CODEX-TASK.yaml`。
5. 只执行入口文件中 `status: READY`、依赖已满足的 `active_issue`。
6. 必须读取该Issue正文和全部评论，并遵守其中显式标注的Codex模式。
7. 不得根据历史TIMEOUT、INVALID、UNKNOWN回执推断任务已完成。
8. 不得自行选择其他Issue，不得猜测任务编号，不得重新执行索引中 `supersedes` 的旧任务。
9. 完成后按Agent执行反馈v2回传实际证据，并创建独立PR；不得自行合并。
10. 无法确认远端最新索引时必须停止并报告，不得继续执行。

固定协调仓库：`vxz2datoubo/second-brain-coordination`

唯一任务真源：远端最新 `main` 上的 `coordination/ACTIVE-CODEX-TASK.yaml`。
