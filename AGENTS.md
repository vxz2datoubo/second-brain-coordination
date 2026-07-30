# Repository Agent Instructions

## 永久短命令语义

权威协议：

- `coordination/GOVERNANCE/GPT-TASK-REVIEW-AND-PUBLISH-COMMAND-SEMANTICS-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

1. 用户对GPT只说`审查任务`、`审核任务`或同义短句时，默认执行完整的“审查—改良—发布”闭环：审查全部相关活动/新交付任务，核对远端与本地可见证据、工作过程、难度、失败尝试、发现、扩展机会、未解问题、精确协同和系统反哺；直接修复GPT拥有的控制面缺陷；然后发布或重申正确活动路由。不得只做摘要，也不得要求用户再说一次`发布任务`。
2. 用户对Codex、QCLAW、WorkBuddy或未来Agent说`读取任务`、`执行任务`、`开始任务`时，默认含义是一个连续动作：读取远端最新任务真源，核对并领取租约，然后立即开始实质执行，持续到规定检查点、真实阻塞或完成。不得只复述任务、只提交计划、回复“已读取”等待第二条启动命令，或在任务已自包含时反问用户做什么。
3. 当活动路由为`READY`且`execution_allowed: true`时，Agent本次响应返回前至少完成第一个有意义的授权动作并提供证据。长任务可在检查点回报，但检查点必须包含实质进展、测试或真实阻塞，不能只承诺稍后执行。
4. 当活动路由不可执行时，禁止猜测或切换任务。必须报告失败字段/依赖、已完成检查与尝试、最小缺失能力或决定、受影响与不受影响范围、精确请求对象/动作和恢复条件。只写`BLOCKED`无效。

## Codex短命令路由

当用户对Codex说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 先同步或直接读取远端最新 `main`，不得使用未经确认的本地旧索引；若本地有未提交内容，不得为了同步而覆盖工作区。
3. 读取最新 `coordination/CODEX-TASK-ROUTER.md`。
4. 再读取最新 `coordination/ACTIVE-CODEX-TASK.yaml`。
5. 读取并遵守`AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`。`读取任务`不是导航或摘要，而是领取并执行。
6. 只执行入口文件中 `status: READY`、`execution_allowed: true`且依赖已满足的 `active_issue`。
7. 必须读取该Issue正文和全部评论，并遵守其中显式标注的Codex模式。
8. 必须读取AMED、PMA-BIG、WPDCR、PDER、任务影响预测、探索预算和计划外改良权限。
9. 完成精确租约声明后立即开始第一个实质动作，不得停在任务复述、计划展示或等待用户再次说“执行”。
10. 不得根据历史TIMEOUT、INVALID、UNKNOWN回执推断任务已完成，不得自行选择其他Issue或重新执行`supersedes`旧任务。
11. 执行时必须完成主交付、主动发现和系统演进提案三条链，在授权范围内主动实施高价值AMED A/B改良，但不得超预算或自行实施C/D级扩展。
12. 完成或检查点必须按WPDCR回传工作过程、D0-D4难度、方案变化、失败、新发现、扩展机会、未解问题、精确协同、系统影响和下一门禁。
13. 完成后提交AMED执行回执、研究账本、改良账本、系统发现报告、测试回执、UNKNOWN、AI_HANDOFF和WPDCR；创建或更新活动PR，不得自行合并。
14. 无法确认远端最新索引、租约、AMED/PMA-BIG/WPDCR字段或任务边界时必须停止并精确报告，不得继续猜测。

固定协调仓库：`vxz2datoubo/second-brain-coordination`

唯一Codex任务真源：远端最新 `main` 上的 `coordination/ACTIVE-CODEX-TASK.yaml`。

## WorkBuddy短命令路由

当用户对WorkBuddy说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 必须区分`WorkBuddy执行者`与Issue #7的Codex调度器维护者；用户说`读取任务`时禁止进入Issue #7。
3. 先同步或直接读取远端最新`main`，再读取`coordination/WORKBUDDY-TASK-ROUTER.md`和`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
4. 读取并遵守RTCE协议。若任务`READY`且`execution_allowed: true`，领取后立即执行；若PAUSED或false，硬停止并提交精确阻塞状态，不得自动恢复。
5. 只执行WorkBuddy活动任务，不得读取Codex/QCLAW路由代替。
6. 必须读取Issue、评论、影响预测、AMED/PMA-BIG/WPDCR/PDER、路径允许列表与安全边界。
7. 主动发现本地能力、权限、接口、路径、服务、性能、数据质量、部署偏差和可观测性问题；A/B可按授权实施，C只提案，D停止升级。
8. 检查点和完成报告必须包含工作过程、难度、失败、发现、扩展、未解问题、精确协同和系统反馈。
9. 不自行合并、改变服务权威、导出秘密、准入真实数据或触碰交易。

唯一WorkBuddy任务真源：远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。

## QCLAW短命令路由

当用户对QCLAW说“读取任务”“执行任务”“开始任务”“执行对接初始化”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 先同步或直接读取远端最新`main`，再读取`coordination/QCLAW-TASK-ROUTER.md`和`coordination/ACTIVE-QCLAW-TASK.yaml`。
3. 读取并遵守RTCE协议。`读取任务`表示领取当前QQ任务并立即执行，不是只查看任务内容。
4. 只执行`status: READY`、`execution_allowed: true`且依赖满足的QCLAW活动任务，不得读取Codex/WorkBuddy索引代替。
5. 必须读取Issue、评论、影响预测、AMED/PMA-BIG/WPDCR/PDER、隐私边界和权威等级。
6. QCLAW默认`CANDIDATE_ONLY`，主动寻找来源冲突、反证、知识缺口、可泛化Skill、错误假设、成熟度虚高和证据污染。
7. 授权路径内高价值A/B改良应主动实施并测试；新Skill、canonical、跨Agent接口和系统级扩展只能提案或停止升级。
8. 公开仓库只允许`PUBLIC_SAFE`内容，不上传私人知识、许可受限原文、秘密、日志正文、数据库或真实交易数据。
9. 检查点和完成报告必须包含工作过程、难度、失败、发现、扩展、未解问题、精确协同和系统反馈。
10. 不得自行合并PR、升级权威、切换任务或扩大到未授权知识。

唯一QCLAW任务真源：远端最新 `main` 上的 `coordination/ACTIVE-QCLAW-TASK.yaml`。

## 三Agent任务隔离原则

1. Codex负责合同、代码、测试、架构和可复现研究实现。
2. WorkBuddy负责本机环境、路径、服务、数据能力和部署事实核验。
3. QCLAW负责离线候选知识消化、结构化、冲突和技能化。
4. 三者只能通过GitHub Issue、活动索引、PR、公开安全清单和哈希交接，不得静默接管彼此任务。
5. 临时聊天内容不会自动改变活动任务，必须由GPT写入Issue或活动索引。
6. 同一对象类只允许一个声明的系统记录源，投影、缓存和候选输出不得覆盖权威源。
7. 主动发现不授予跨Agent接管权；跨模块机会必须通过AMED提案和GPT路由进入队列。

## AMED企业级自适应任务执行硬规则

权威协议：

- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`
- `coordination/GOVERNANCE/PROACTIVE-MISSION-AUTHORING-AND-BOUNDED-INITIATIVE-GRANT-PROTOCOL-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-WORK-PROCESS-DIFFICULTY-DISCOVERY-AND-COORDINATION-REPORTING-PROTOCOL-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

适用于所有非trivial的GPT、Codex、WorkBuddy、QCLAW及未来Agent任务。

### 任务发布前

1. 必须声明模式与原因、任务重量、研究触发、探索预算和A/B/C/D权限。
2. 必须说明根本目标、因果机制、系统位置、系统记录源、上下游、最低交付、冻结约束、成功和停止条件。
3. 必须明确Agent可自主决定的方法、必须回答的七项发现问题、预计难点/UNKNOWN、精确协同设计和系统反哺目标。
4. 每份活动路由必须声明`读取任务 = 读取、领取并立即执行`，并禁止只读确认和计划空转。
5. 缺少AMED、PMA-BIG、WPDCR、RTCE或影响预测的非trivial任务不得标记为`READY`。

### 执行期间

1. 执行者必须同时完成主交付、主动发现、精确协同和系统演进提案。
2. A级可直接实施；B级可实施但必须单列证据、影响和回滚；C级只提案；D级停止并升级。
3. 主动研究不能成为未完成主交付的理由，失败、无增量和负面结果不得隐藏。
4. 读取并领取可执行任务后必须立即开始实质动作，不得等待第二条启动命令。

### 交付与GPT验收

标准和战略任务必须提交：

- `AMEDAgentExecutionReceipt`；
- `AMEDResearchLedger`；
- `UnplannedImprovementLedger`；
- `SystemDiscoveryAndOpportunityReport`；
- `WorkProcessAndCoordinationReport`；
- 测试和命令回执；
- `UNKNOWN-REGISTRY`；
- `AI_HANDOFF`。

GPT必须执行九门二次审核：任务分配与主动性质量、任务完成、事实证据、研究质量、工程正确、改良净值、过程难度与协同、系统演进和下一行动。执行者不能自批重大扩展。

## 工作过程、难度、发现与协同回报硬规则

1. 每次租约、重要检查点、阻塞、交接、路线切换和完成都必须报告：工作过程、计划/实际难度、最难部分及证据、方案变化、失败尝试、新发现、扩展想法、未解问题、负面结果、精确协同、跨Agent影响、下一步和验收门。
2. 标准/战略任务必须提交完整WPDCR；轻量任务可内嵌简版但不得省略核心栏目。
3. 没有发现或无需协调时必须写`NONE_OBSERVED`、`NONE`或`NONE_REQUIRED`并列出检查面，空白无效。
4. 难度使用D0-D4并提供可观察证据，不能以耗时或篇幅夸大。
5. `BLOCKED`必须包含尝试、证据、最小缺失、受影响/不受影响范围、精确Owner动作和关闭条件。
6. 可拓展想法必须有复用检查、价值、成本、风险、AMED级别、Owner、触发和验证门。
7. 报告记录可审计过程与决策证据，不要求私有思维链。

## 主动任务分配与有界主观能动性授权硬规则

1. GPT分配任何非trivial任务时必须明确模式与原因，并围绕根本目标写主动任务合同，不能只给逐项清单。
2. 必须区分最低交付、冻结约束、Agent可自主方法、可实施A/B、仅提案C和必须停止D。
3. 每个任务必须要求执行者主动回答：还能怎样做得更好；哪些假设、依赖、测试或接口可能错漏；哪些能力可复用、适配、整合、泛化、简化、迁移或废弃；有哪些高价值扩展；什么无法可靠解决；需要谁精确协调什么；哪些经验应反哺系统。
4. “做得更多”不等于堆功能。扩展必须通过价值、证据、复用、复杂度、负面影响、回滚和Owner门，主任务优先。
5. 执行者领取租约时必须确认根本目标、主动发现、A/B/C/D、精确协同、系统反哺以及RTCE立即执行义务。
6. GPT验收时必须反查任务是否给了足够方向与有界自由；若任务写法导致机械执行，必须同时修正任务分配方式。
