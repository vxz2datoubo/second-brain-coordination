# Codex任务路由协议

当用户在Codex中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，Codex必须按以下顺序行动：

1. 固定目标仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录猜测其他仓库。
2. **先同步远端最新 `main`**：优先执行安全的 `git fetch origin main`，并从最新 `origin/main` 读取路由和活动索引。若本地工作区不适合快进或存在未提交改动，不得覆盖本地内容，应直接读取GitHub远端最新文件。
3. 禁止使用未验证的新旧本地缓存副本作为任务来源；必须确认读取到的 `coordination/ACTIVE-CODEX-TASK.yaml` 来自当前远端最新 `main`。
4. 打开最新 `coordination/ACTIVE-CODEX-TASK.yaml`。
5. 读取其中的 `active_issue`、`mode`、`status`、`blocked_by`、`dependencies`、`task_impact_forecast`、`amed_policy`、`task_weight`、`research_trigger`、`exploration_budget` 与 `notes`。
6. 仅当 `status: READY`、依赖状态满足、任务影响预测存在且AMED字段完整时，读取对应GitHub Issue的正文与全部评论。
7. 读取：
   - `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`；
   - `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`；
   - `coordination/GOVERNANCE/AGENT-PROACTIVE-DISCOVERY-AND-REALTIME-ESCALATION-PROTOCOL-v1.0.yaml`；
   - 当前任务影响预测与任务简报。
8. 读取任务影响预测中的第一性原理目标、预期收益、预期负面影响、风险门禁、停止条件和执行观测要求。不得为了完成任务而忽略预测中的反证或风险信号。
9. 按Issue中明确标注的Codex模式执行，不得自行更换模式。
10. 执行必须同时覆盖：
    - 主任务交付；
    - 主动发现错误假设、缺口、重复、接口、风险、负面结果和机会；
    - 系统演进提案。
11. 计划外改良必须按AMED分类：A可直接实施；B可实施但单独报告；C只提案；D停止并升级。不得突破探索预算。
12. 研究必须按L1/L2/L3触发执行。L2记录一手来源、反证、适用条件、来源冲突、可信度和A股适配；L3拆分新任务，不得静默扩张。
13. 若Issue存在旧的 TIMEOUT、INVALID、UNKNOWN 或过期回执，只把它们当历史记录，不得当作本次任务完成证据。
14. 执行前确认仓库名、最新远端索引、Issue编号、影响预测、AMED合同、PDER主动发现协议和当前活动任务完全一致。
15. 执行期间不得把主动发现推迟到最终交付：
    - `S4_CRITICAL`必须立即停止受影响范围、保全证据并上报；
    - `S3_MAJOR`在证据足够时立即向活动PR和Issue提交DiscoveryPacket，不得等任务结束；
    - `S2_MATERIAL`在当前检查点报告；
    - `S1_MINOR`进入发现账本，按根因去重聚合。
16. 每个S3/S4发现必须同时提交机器可读证据和人类可读翻译，明确：发现了什么、普通语言含义、为什么重要、它不证明什么、是否应停工、建议下一步。
17. Codex可以在授权范围内主动做只读核查、反证和小型验证，但主动发现不授予自行切换任务、扩大WIP、改变canonical权威、访问秘密、突破许可或进入实盘的权限。
18. 发现可能影响其他模块时，必须先报告受影响范围、证据与推荐分流，不得直接接管其他Agent或建立平行运行时。
19. 执行期间在AMED回执和Agent执行反馈v2中报告实际正面效果、负面效果、意外事件、研究发现、计划外改良和风险信号；高严重度意外损害必须立即停止或上报。
20. 任务完成后必须提交：
    - `AMEDAgentExecutionReceipt`；
    - `AMEDResearchLedger`；
    - `UnplannedImprovementLedger`；
    - `SystemDiscoveryAndOpportunityReport`；
    - DiscoveryPacket或明确的`NO_S2_PLUS_DISCOVERY`声明；
    - 真实命令、退出码和测试回执；
    - `UNKNOWN-REGISTRY`；
    - `AI_HANDOFF`。
21. 在活动Issue和父Issue中留下证据，创建独立PR，不得自行合并。
22. 若远端入口文件缺失、影响预测缺失、AMED字段缺失、PDER协议缺失、状态不是READY、依赖未满足、Issue不存在、索引版本冲突或无法确认远端最新状态，停止执行并报告，不得猜测任务。
23. 不得因为用户只说“读取任务”就扫描、选择或执行其他Issue。
24. 不得重新执行 `supersedes` 中记录的旧活动任务。
25. 主动发现不授予自行切换任务、扩大WIP或改变canonical权威的权限。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一任务真源：远端最新 `main` 上的 `coordination/ACTIVE-CODEX-TASK.yaml`。

工程学习蓝图：

`coordination/BLUEPRINTS/ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM-v1.0.md`

AMED与主动发现权威：

- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-PROACTIVE-DISCOVERY-AND-REALTIME-ESCALATION-PROTOCOL-v1.0.yaml`
