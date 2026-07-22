# Repository Agent Instructions

## Codex短命令路由

当用户对Codex说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 先同步或直接读取远端最新 `main`，不得使用未经确认的本地旧索引；若本地有未提交内容，不得为了同步而覆盖工作区。
3. 读取最新 `coordination/CODEX-TASK-ROUTER.md`。
4. 再读取最新 `coordination/ACTIVE-CODEX-TASK.yaml`。
5. 只执行入口文件中 `status: READY`、依赖已满足的 `active_issue`。
6. 必须读取该Issue正文和全部评论，并遵守其中显式标注的Codex模式。
7. 必须读取AMED协议、机器策略、任务影响预测、任务重量、研究触发级别、探索预算和计划外改良权限。
8. 不得根据历史TIMEOUT、INVALID、UNKNOWN回执推断任务已完成。
9. 不得自行选择其他Issue，不得猜测任务编号，不得重新执行索引中 `supersedes` 的旧任务。
10. 执行时必须完成主交付、主动发现和系统演进提案三条链，但不得超预算或自行实施C/D级扩展。
11. 完成后按AMED执行回执、研究账本、改良账本、系统发现报告和Agent执行反馈v2回传实际证据，并创建独立PR；不得自行合并。
12. 无法确认远端最新索引、AMED字段或任务边界时必须停止并报告，不得继续执行。

固定协调仓库：`vxz2datoubo/second-brain-coordination`

唯一Codex任务真源：远端最新 `main` 上的 `coordination/ACTIVE-CODEX-TASK.yaml`。

## WorkBuddy短命令路由

当用户对WorkBuddy说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 必须先区分两个身份：
   - `WorkBuddy执行者`：执行自己的现场任务，唯一入口是 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`；
   - `Codex调度器维护者`：Issue #7仅用于建设或维护“唤醒Codex”的调度基础设施，不是WorkBuddy的任务收件箱。
3. 用户直接对WorkBuddy说“读取任务”时，禁止进入Issue #7的CodexDispatch流程，禁止因此反问用户“想做什么”。
4. Issue #26及其父任务已完成关闭，禁止继续以“等待GPT处理Issue #26”为当前状态。
5. 先同步或直接读取远端最新 `main`；若本地工作区有未提交内容或不能安全快进，不得覆盖本地内容，必须直接读取GitHub远端最新文件。
6. 读取最新 `coordination/WORKBUDDY-TASK-ROUTER.md`。
7. 再读取最新 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
8. 只执行其中 `status: READY`、依赖已满足的 `active_issue`，不得读取Codex活动索引、Issue #7、最近Issue或旧聊天记录代替。
9. 必须读取活动Issue正文、全部评论、任务影响预测、AMED任务合同、允许列表和安全边界。
10. 用户在本地临时讨论的策略、做T方案或其他研究内容，应保留为独立候选笔记；在GPT建立新Issue或显式调整优先级前，不得静默替换当前GitHub活动任务。
11. 现场操作不得超出Issue授权，不能因为拥有本机访问能力就扩大扫描、读取秘密或修改服务。
12. 执行时必须主动发现本地能力、接口、许可、路径、性能和部署问题，但超出探索预算或涉及跨模块权威时只允许提案。
13. 完成后按AMED完整回执、研究账本、改良账本、系统发现报告、Agent执行反馈v2和结果观察要求回传，创建独立PR，不自行合并。
14. 无法确认远端索引、AMED字段、路径允许列表或权限边界时必须停止并报告，但不得回退到Issue #7猜任务。

唯一WorkBuddy任务真源：远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。

## QCLAW短命令路由

当用户对QCLAW说“读取任务”“执行任务”“开始任务”“执行对接初始化”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 先同步或直接读取远端最新 `main`；本地有未提交内容时不得覆盖、清理或重置。
3. 读取最新 `coordination/QCLAW-TASK-ROUTER.md`。
4. 再读取最新 `coordination/ACTIVE-QCLAW-TASK.yaml`。
5. 只执行其中 `status: READY`、依赖已满足的 `active_issue`。
6. 必须读取Issue正文、全部评论、任务影响预测、AMED任务合同、隐私边界和权威等级。
7. 不得读取Codex或WorkBuddy活动索引代替自己的索引，不得进入Issue #7、Issue #26或其他Agent任务。
8. QCLAW是候选知识学习工作器，不是最终知识权威；所有输出默认 `CANDIDATE_ONLY`。
9. 公开仓库只允许写入 `PUBLIC_SAFE` 内容。私人知识、许可受限原文、凭证、数据库、日志正文和真实交易数据不得上传。
10. 初始化测试只能使用公开安全或合成材料；没有GPT审查不得扩大到本地私人知识或批量同步。
11. QCLAW必须主动寻找来源冲突、反证、知识缺口、可泛化技能和错误假设，但新Skill、权威升级和系统级接口只允许形成提案。
12. 完成后回传结构化握手、LearningPacket、AMED研究账本、主动发现和改良提案、隐私检查和结果校准；不得自行合并PR或升级权威状态。
13. 无法确认远端最新索引、AMED字段、身份、隐私等级或任务边界时必须停止并报告，不得猜测。

唯一QCLAW任务真源：远端最新 `main` 上的 `coordination/ACTIVE-QCLAW-TASK.yaml`。

## 三Agent任务隔离原则

1. Codex负责合同、代码、测试、架构和可复现研究实现。
2. WorkBuddy负责本机环境、路径、服务、数据能力和部署事实核验。
3. QCLAW负责离线候选知识消化、结构化、冲突和技能化。
4. 三者只能通过GitHub Issue、活动索引、PR、公开安全清单和哈希交接，不得静默接管彼此任务。
5. 临时聊天内容不会自动改变活动任务；必须由GPT写入对应Issue或活动索引。
6. 同一对象类只允许一个声明的系统记录源，投影、缓存和候选输出不得覆盖权威源。
7. 主动发现不授予跨Agent接管权；跨模块机会必须通过AMED提案和GPT路由进入队列。

## AMED企业级自适应任务执行硬规则

权威协议：

- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`

适用于所有非trivial的GPT、Codex、WorkBuddy、QCLAW及未来Agent任务。

### 任务发布前

1. 必须声明任务重量：`LIGHT / STANDARD / STRATEGIC`。
2. 必须声明研究触发：`L1 / L2 / L3`及原因。
3. 必须声明探索预算、主交付优先级和计划外改良A/B/C/D权限。
4. 必须说明任务意图、系统位置、系统记录源、上下游、不得复制组件、成功标准和停止条件。
5. 缺少AMED任务合同的非trivial任务不得标记为`READY`。

### 执行期间

1. 执行者必须同时完成主交付、主动发现和系统演进提案。
2. A级可直接实施；B级可实施但必须单列证据、影响和回滚；C级只提案；D级停止并升级。
3. L2研究必须优先一手资料，记录反证、适用条件、来源冲突、可信度和A股适配。
4. L3事项必须拆分独立任务，不得静默扩张当前范围。
5. 主动研究不能成为未完成主交付的理由。
6. 发现的失败、无增量和负面结果不得隐藏。

### 交付与GPT验收

标准和战略任务必须提交：

- `AMEDAgentExecutionReceipt`；
- `AMEDResearchLedger`；
- `UnplannedImprovementLedger`；
- `SystemDiscoveryAndOpportunityReport`；
- 测试和命令回执；
- `UNKNOWN-REGISTRY`；
- `AI_HANDOFF`。

GPT必须执行七门二次审核：任务完成、事实证据、研究质量、工程正确、改良净值、系统演进和下一行动。执行者不能自批重大扩展。

## 工程学习与结果校准硬规则

适用于所有非 trivial 的GPT、Codex、WorkBuddy和QCLAW任务。权威蓝图：

`coordination/BLUEPRINTS/ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM-v1.0.md`

### 任务发布前

1. GPT必须先完成第一性原理拆解：真实目标、因果机制、约束、证据、失败模式、可观察性、替代方案和停止条件。
2. 必须建立 `TaskImpactForecast`，记录预期正面收益、预期负面影响、执行成本、机会成本、净价值和验证信号。
3. 任务Issue正文或评论必须包含简明的“预期收益与潜在负面影响”段落，并链接或内嵌预测记录。
4. 低风险、可逆风险由GPT自行设置控制并继续，不必频繁打断用户。
5. 出现不可逆损害、真实资金、凭证、重大数据风险、系统级传播、高概率高严重度风险、无可靠回滚或预期净价值为负时，必须先告知用户并等待决定。
6. 没有完成影响预测和AMED任务合同的任务不得标记为 `READY`，紧急止损、安全隔离和纯信息读取除外，但必须事后补录。

模板：

- `coordination/ENGINEERING-LEARNING/TASK-IMPACT-FORECAST-TEMPLATE.yaml`
- `coordination/TEMPLATES/AMED-TASK-BRIEF-TEMPLATE-v1.0.yaml`

### 执行期间

1. 执行者必须观察预测收益和风险信号，并在AMED回执和Agent执行反馈v2中报告实际正负效果。
2. 意外损害达到高严重度、跨模块传播或接近停止条件时，立即中止或报告，不得等任务结束。
3. 不得为了符合任务前预测而隐藏相反证据。

### 交付验收时

1. GPT必须建立 `OutcomeCalibrationReview`和`AMEDGPTSecondPassAudit`，逐项对比预期收益、预期负面影响和实际结果。
2. 必须识别意外收益、意外损害、执行成本偏差、复杂度偏差和风险控制副作用。
3. 偏差必须分类为：预测错误、执行错误、环境变化、测量错误或未知未知。
4. 实际负面效果高于预期时，不得只写“下次注意”，必须形成根因、控制更新和回归测试。
5. 意外正收益必须分析因果链、必要条件、替代解释、放大风险和最小复现实验。
6. 单次成功不能直接升级为长期标准，必须保留反证并通过复现提高成熟度。

模板：

- `coordination/ENGINEERING-LEARNING/OUTCOME-CALIBRATION-REVIEW-TEMPLATE.yaml`
- `coordination/TEMPLATES/AMED-GPT-SECOND-PASS-AUDIT-TEMPLATE-v1.0.yaml`

### 经验回写

1. 可复用经验写入：
   `coordination/ENGINEERING-LEARNING/ENGINEERING-LEARNING-REGISTRY.yaml`
2. 根据影响范围同步更新任务模板、AGENTS规则、路由、专项蓝图、测试、禁止清单或本地权威蓝图差异包。
3. 每个后续任务必须检查是否存在可继承的相关工程经验。
4. 新证据推翻旧经验时，必须将旧经验降级为 `DEPRECATED` 或 `CONTRADICTED`，不得维护虚假一致性。
