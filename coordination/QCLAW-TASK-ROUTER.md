# QCLAW任务路由协议

当用户对QCLAW说“读取任务”“执行任务”“开始任务”“执行对接初始化”或同义短句时，QCLAW必须按以下顺序行动：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录或最近访问记录猜测其他仓库。
2. 先同步或直接读取远端最新 `main`；若本地工作区有未提交内容，不得覆盖、清理或重置本地内容。
3. 读取最新 `coordination/QCLAW-TASK-ROUTER.md`和`coordination/ACTIVE-QCLAW-TASK.yaml`。
4. 读取活动索引中的`active_issue`、`mode`、`status`、`dependencies`、`task_impact_forecast`、`amed_policy`、`task_weight`、`research_trigger`、`exploration_budget`、隐私边界和权威级别。
5. 仅执行 `status: READY`、依赖已满足且影响预测存在的活动任务。
6. AMED兼容规则：
   - 新建或重新发布的任务必须显式包含全部AMED字段；
   - 在AMED生效前已经READY且尚未重新发布的历史活动任务，如缺少AMED字段，临时继承：`task_weight: STRATEGIC`、`research_trigger: L2_TARGETED_PROFESSIONAL_RESEARCH`、探索预算`70/20/10`、跨模块和新Skill一律`C_PROPOSAL_ONLY`；
   - 执行者必须在首个检查点提交`AMED-LEGACY-INHERITANCE-RECEIPT`，说明继承值、适用范围和未明确边界；
   - 该兼容规则不能放宽隐私、安全、许可、权威或任务范围，也不能用于新任务。
7. 必须读取活动Issue正文、全部评论、AMED协议、机器策略、任务影响预测和任务简报；历史兼容任务没有任务简报时，必须从Issue与活动索引形成最小AMED任务意图并在回执中明确。
8. 不得读取Codex或WorkBuddy活动索引代替自己的活动索引，不得执行Issue #7、Issue #26或其他Agent任务。
9. QCLAW只生成候选知识包，不是最终知识权威；所有输出默认 `CANDIDATE_ONLY`。
10. 公开仓库只允许写入 `PUBLIC_SAFE` 内容。私人知识、许可受限原文、凭证、日志正文、数据库和真实交易数据不得上传。
11. 首次握手只允许使用公开安全或合成测试材料，不得处理用户本地私人知识。
12. 执行必须同时完成主交付、主动发现和系统演进提案。重点寻找来源冲突、错误假设、知识缺口、可泛化技能、重复术语和反例。
13. 计划外改良按AMED A/B/C/D处理：QCLAW通常只允许A类候选包内部改良和C类提案；新Skill、权威升级、跨模块接口和运行时实现禁止自行执行。
14. 研究按L1/L2/L3触发。L2必须记录一手来源、反证、适用条件、来源冲突、可信度、许可和A股适配；L3形成独立研究任务候选。
15. 完成后必须回传结构化握手、LearningPacket、AMED执行回执、研究账本、计划外改良账本、系统发现报告、隐私审查、UNKNOWN、AI_HANDOFF和结果校准。
16. 不得自行合并PR、升级权威状态、改变活动任务或扩大到本地私人知识。
17. 无法确认远端最新索引、身份、隐私等级或任务边界时必须停止并报告，不得猜测。
18. 主动发现不授予访问秘密、绕过许可、真实交易或接管其他Agent任务的权限。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一QCLAW任务真源：远端最新 `main` 上的 `coordination/ACTIVE-QCLAW-TASK.yaml`。

AMED权威：

- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`
