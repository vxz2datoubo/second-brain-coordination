# WorkBuddy任务路由协议

当用户在WorkBuddy中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，WorkBuddy必须按以下顺序行动：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录猜测其他仓库。
2. 明确身份：本协议用于 `WorkBuddy执行者` 领取自身现场任务；Issue #7是Codex自动调度基础设施任务，只用于唤醒或维护Codex调度器，永远不是WorkBuddy任务入口。
3. 用户直接对WorkBuddy发出短命令时，不得跳转Issue #7，不得进入 `CodexDispatch` 等待态，也不得反问用户当前要做什么。
4. Issue #26及父Issue #22已完成关闭，不得继续把“等待GPT处理Issue #26”作为当前状态或阻断理由。
5. 先同步或直接读取远端最新 `main`。若本地工作区不适合快进、存在未提交内容或本地网络无法安全同步，不得覆盖工作区，应直接读取GitHub远端最新文件。
6. 读取最新 `coordination/WORKBUDDY-TASK-ROUTER.md`、`coordination/GOVERNANCE/AGENT-TASK-LEASE-AND-COMPLETION-FRESHNESS-PROTOCOL-v1.0.yaml`、`coordination/GOVERNANCE/DUAL-LAYER-INITIATIVE-AND-GPT-ORCHESTRATION-CONSTITUTION-v1.0.yaml`、`coordination/GOVERNANCE/AGENT-WORK-PROCESS-DIFFICULTY-DISCOVERY-AND-COORDINATION-REPORTING-PROTOCOL-v1.0.yaml` 和 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
7. 读取活动索引中的 `active_issue`、`mode`、`status`、`execution_allowed`、`route_epoch`、`route_issued_at`、`completion_signal`、`dependencies`、`task_impact_forecast`、`amed_policy`、`task_weight`、`research_trigger`、`exploration_budget`、`autonomy_grant`、`required_action`、`routing_guard` 和 `safety_boundary`。
8. 执行前必须提交任务租约声明，逐字回显：仓库、读取到的远端main head、task_id、route_epoch、Issue、PR、分支、状态、completion_signal和reviewed/base head。只有与最新活动索引完全一致，且 `status: READY`、`execution_allowed: true`、依赖满足、影响预测存在、AMED字段完整时，才可执行。
9. 如果活动索引为`PAUSED`、`execution_allowed: false`或尚未到显式恢复门，必须停止，不得因为主动性规则自行恢复、创建分支、提交或推送。
10. 必须读取对应Issue正文与全部评论、AMED协议、PDER协议、双层主观能动性宪法、机器策略、任务影响预测、任务简报、允许路径和安全边界。
11. 按Issue显式标注的WorkBuddy模式执行，不得自行更换模式或扩大现场扫描范围。
12. 执行必须同时完成主交付、主动发现和系统演进提案。重点发现本地真实能力、接口、权限、许可、路径、服务、数据质量、性能、部署、可观测性和云端设计与本地现实的偏差。
13. WorkBuddy不得采用被动工单模式。位于明确授权的现场路径、属于AMED A/B、可测试回滚且不改变服务权威或跨Agent所有权的高价值相邻改良，应一并完成并单独记录。
14. 主动发现必须按PDER严重度实时上报：`S4`立即停止受影响操作并保全日志；`S3`证据足够即向活动PR和Issue提交DiscoveryPacket；`S2`在当前检查点报告；`S1`按根因去重聚合。
15. S3/S4现场发现必须同时提供机器证据和普通语言解释，明确是否只影响某个路径、数据源或服务，不能把局部故障夸大成整个系统不可用。
16. 计划外改良按AMED A/B/C/D权限处理：A可直接实施；B实施后单列报告；C只提案；D停止并升级。
17. 研究按L1/L2/L3触发。涉及规则、数据许可、软件版本、接口能力或A股现场差异时，应进行定向一手资料核验；超出预算或涉及新系统级接口时拆分任务。
18. 用户临时讨论的做T策略或其他研究工作应独立保存，等GPT建立新Issue或显式调整队列；不得抢占当前活动Issue。
19. 不得执行Codex活动索引、Issue #7、其他Issue、最近聊天任务或已被 `supersedes` 替代的旧任务。
20. 完成后必须提交AMED执行回执、研究账本、计划外改良账本、系统发现报告、DiscoveryPacket或`NO_S2_PLUS_DISCOVERY`声明、真实命令和测试、UNKNOWN、AI_HANDOFF以及完整Agent执行反馈v2。
21. 完成交付必须明确分栏：主任务、主动发现、已实施主动改良、高价值新目标、替代方案、删除/拒绝项、现场影响、负面结果、UNKNOWN、回滚和下一步建议。
22. WorkBuddy不能自行宣布主动成果成为accepted、canonical、implemented或production authority。GPT必须理解其现场做法并决定接受、改良、删除不和谐候选部分、退回、拆分、延期或拒绝。
23. **发布完成信号前必须重新读取远端最新main。** 再次比较task_id、route_epoch、Issue、PR、分支、completion_signal和execution_allowed。任一不一致时，禁止发布旧完成信号，必须按任务租约协议提交`StaleRoutePacket`并停止。
24. 当前完成回执必须包含：领取与交付前的远端main head、task_id、route_epoch、完整40位delivered/tested/receipt head、精确命令、退出码、计数、stdout/stderr哈希和保留的失败/SKIP/UNKNOWN。
25. 低于当前route_epoch、task_id不匹配或completion_signal不匹配的评论，只是历史回执，不能覆盖当前PR结论、解除依赖或启动下游任务。
26. 创建独立分支和PR，不自行合并，不得直接写main。
27. 无法确认远端最新索引、任务租约协议、AMED字段、PDER协议、双层主观能动性宪法、权限边界、路径允许列表或安全状态时，停止并报告，不得回退到旧调度器猜任务。
28. 主动发现与实现权限不授予跨模块接管、服务生命周期变更、凭证访问、自动恢复或实盘权限。

## 工作过程、难度、发现与协同强制回报

29. 任务租约、每个重要检查点、阻塞、暂停、现场交接、路线变化和完成回执必须使用或完整映射：
   - `coordination/GOVERNANCE/AGENT-WORK-PROCESS-DIFFICULTY-DISCOVERY-AND-COORDINATION-REPORTING-PROTOCOL-v1.0.yaml`；
   - `coordination/TEMPLATES/AGENT-WORK-PROCESS-AND-COORDINATION-REPORT-TEMPLATE-v1.0.yaml`。
30. WorkBuddy每次必须报告：现场操作阶段、计划与实际难度D0-D4、最难路径/权限/服务/数据问题及证据、方案改变、失败尝试、意外环境发现、可拓展现场能力、未解决难题、发现的故障与负面结果、需要GPT/Codex/QCLAW/用户提供的精确协调动作、仍可继续的范围、交接制品和下一门禁。
31. `BLOCKED`报告若没有已尝试方法、日志或可验证摘要、真正缺少的最小权限/路径/服务/输入、受阻范围、仍可继续工作、请求对象与关闭条件，一律视为不完整阻塞报告。
32. 没有发现或不需要协调时必须明确写`NONE_OBSERVED`或`NONE_REQUIRED`，并列出检查过的本地服务、路径、权限、数据或部署面；不得留空。
33. 所有未关闭的D2以上难点、S2以上发现、协调请求和UNKNOWN必须在后续检查点持续携带，直到被验证关闭、拒绝或延期并写明Owner与触发条件。
34. 本规则只要求可审计操作过程、决策依据和证据，不要求也不得输出私有思维链、秘密值或受限原始数据。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一WorkBuddy任务真源：远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。

任务租约与完成新鲜度权威：

- `coordination/GOVERNANCE/AGENT-TASK-LEASE-AND-COMPLETION-FRESHNESS-PROTOCOL-v1.0.yaml`

AMED、主动发现、双层主观能动性与工作过程协同回报权威：

- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-PROACTIVE-DISCOVERY-AND-REALTIME-ESCALATION-PROTOCOL-v1.0.yaml`
- `coordination/GOVERNANCE/DUAL-LAYER-INITIATIVE-AND-GPT-ORCHESTRATION-CONSTITUTION-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-WORK-PROCESS-DIFFICULTY-DISCOVERY-AND-COORDINATION-REPORTING-PROTOCOL-v1.0.yaml`
