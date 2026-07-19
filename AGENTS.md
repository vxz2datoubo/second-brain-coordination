# Repository Agent Instructions

## Codex短命令路由

当用户对Codex说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 先读取 `coordination/CODEX-TASK-ROUTER.md`。
2. 再读取 `coordination/ACTIVE-CODEX-TASK.yaml`。
3. 只执行入口文件中 `status: READY` 的活动Issue。
4. 必须读取该Issue正文和全部评论，并遵守其中显式标注的Codex模式。
5. 不得根据历史TIMEOUT、INVALID、UNKNOWN回执推断任务已完成。
6. 不得自行选择其他Issue，不得猜测任务编号。
7. 完成后按Agent执行反馈v2回传实际证据。

固定协调仓库：`vxz2datoubo/second-brain-coordination`
