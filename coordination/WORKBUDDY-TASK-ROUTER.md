# WorkBuddy任务路由协议

当用户在WorkBuddy中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，WorkBuddy必须按以下顺序行动：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录猜测其他仓库。
2. 明确身份：本协议用于 `WorkBuddy执行者` 领取自身现场任务；Issue #7是Codex自动调度基础设施任务，只用于唤醒或维护Codex调度器，永远不是WorkBuddy任务入口。
3. 用户直接对WorkBuddy发出短命令时，不得跳转Issue #7，不得进入 `CodexDispatch` 等待态，也不得反问用户当前要做什么。
4. Issue #26及父Issue #22已完成关闭，不得继续把“等待GPT处理Issue #26”作为当前状态或阻断理由。
5. 先同步或直接读取远端最新 `main`。若本地工作区不适合快进、存在未提交内容或本地网络无法安全同步，不得覆盖工作区，应直接读取GitHub远端最新文件。
6. 读取最新 `coordination/WORKBUDDY-TASK-ROUTER.md`和`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
7. 读取活动索引中的 `active_issue`、`mode`、`status`、`dependencies`、`task_impact_forecast`、`amed_policy`、`task_weight`、`research_trigger`、`exploration_budget`、`required_action`、`routing_guard` 和 `safety_boundary`。
8. 仅当 `status: READY`、依赖满足、影响预测存在且AMED字段完整时，读取对应Issue正文与全部评论。
9. 必须读取AMED协议、机器策略、任务影响预测、任务简报、允许路径和安全边界。
10. 按Issue显式标注的WorkBuddy模式执行，不得自行更换模式或扩大现场扫描范围。
11. 执行必须同时完成主交付、主动发现和系统演进提案。重点发现本地真实能力、接口、权限、许可、路径、服务、数据质量、性能、部署和可观测性问题。
12. 计划外改良按AMED A/B/C/D权限处理：A可直接实施；B实施后单列报告；C只提案；D停止并升级。
13. 研究按L1/L2/L3触发。涉及规则、数据许可、软件版本、接口能力或A股现场差异时，应进行定向一手资料核验；超出预算或涉及新系统级接口时拆分任务。
14. 用户临时讨论的做T策略或其他研究工作应独立保存，等GPT建立新Issue或显式调整队列；不得抢占当前活动Issue。
15. 不得执行Codex活动索引、Issue #7、其他Issue、最近聊天任务或已被 `supersedes` 替代的旧任务。
16. 完成后必须提交AMED执行回执、研究账本、计划外改良账本、系统发现报告、真实命令和测试、UNKNOWN、AI_HANDOFF以及完整Agent执行反馈v2。
17. 创建独立分支和PR，不自行合并，不得直接写main。
18. 无法确认远端最新索引、AMED字段、权限边界、路径允许列表或安全状态时，停止并报告，不得回退到旧调度器猜任务。
19. 主动发现不授予跨模块接管、服务生命周期变更、凭证访问或实盘权限。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一WorkBuddy任务真源：远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。

AMED权威：

- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`
