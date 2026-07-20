# QCLAW任务路由协议

当用户对QCLAW说“读取任务”“执行任务”“开始任务”“执行对接初始化”或同义短句时，QCLAW必须按以下顺序行动：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录或最近访问记录猜测其他仓库。
2. 先同步或直接读取远端最新 `main`；若本地工作区有未提交内容，不得覆盖、清理或重置本地内容。
3. 读取最新 `coordination/QCLAW-TASK-ROUTER.md`。
4. 再读取最新 `coordination/ACTIVE-QCLAW-TASK.yaml`。
5. 仅执行其中 `status: READY`、依赖已满足的 `active_issue`。
6. 必须读取活动Issue正文、全部评论、任务影响预测、隐私边界和权威级别。
7. 不得读取Codex或WorkBuddy活动索引代替自己的活动索引，不得执行Issue #7、Issue #26或其他Agent任务。
8. QCLAW只生成候选知识包，不是最终知识权威；所有输出默认 `CANDIDATE_ONLY`。
9. 公开仓库只允许写入 `PUBLIC_SAFE` 内容。私人知识、许可受限原文、凭证、日志正文、数据库和真实交易数据不得上传。
10. 首次握手只允许使用公开安全或合成测试材料，不得处理用户本地私人知识。
11. 完成后在活动Issue回传结构化握手、最小LearningPacket、隐私审查和结果校准；不得自行合并PR或升级权威状态。
12. 无法确认远端最新索引、身份、隐私等级或任务边界时必须停止并报告，不得猜测。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一QCLAW任务真源：远端最新 `main` 上的 `coordination/ACTIVE-QCLAW-TASK.yaml`。
