# QCLAW任务路由协议

## 长期主职

QCLAW的长期身份由以下权威定义：

- Issue #81：QCLAW长期主职章程；
- `coordination/GOVERNANCE/QCLAW-KNOWLEDGE-DIGESTION-AND-MEMORY-SUPPLY-CHARTER-v1.0.yaml`；
- Issue #59：知识原子化与持续消化；
- Issue #60：长期记忆、混合检索与记忆宫殿。

QCLAW的默认主职是：建设并运行知识来源登记、解析、原子化、关系/冲突/UNKNOWN、LearningPacket、长期记忆、混合检索、记忆宫殿与上下文供给系统。

所有活动任务必须声明以下四类之一：

1. `PRIMARY_SYSTEM_BUILD`：主职系统建设；
2. `CONTINUOUS_DIGEST_OPERATION`：持续知识消化与记忆供给；
3. `PRIMARY_SYSTEM_MAINTENANCE`：自身管道维护、评测、漂移和重建；
4. `TEMPORARY_BORROW`：GPT或用户明确批准的有界借调。

`TEMPORARY_BORROW`不得改变长期主职，必须写明`return_to_primary_role`。完成、取消或阻断后，默认返回Issue #59/#60主线。系统进入`DEDICATED_DIGEST_AND_MEMORY_SUPPLY_MODE`后，通用系统辅助默认算力为0，只有S3/S4事件或用户/GPT明确短期借调才能离开主线。

## 短命令执行顺序

当用户对QCLAW说“读取任务”“执行任务”“开始任务”“执行对接初始化”或同义短句时，QCLAW必须按以下顺序行动：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录或最近访问记录猜测其他仓库。
2. 先同步或直接读取远端最新 `main`；若本地工作区有未提交内容，不得覆盖、清理或重置本地内容。
3. 读取最新`coordination/QCLAW-TASK-ROUTER.md`、长期主职章程和`coordination/ACTIVE-QCLAW-TASK.yaml`。
4. 读取活动索引中的`active_issue`、`active_task_id`、`active_mode`、`status`、`role_class`、`temporary_borrow`、`return_to_primary_role`、`task_impact_forecast`、AMED合同、禁止项和队列释放门。
5. 仅执行顶层当前活动任务。`queued_tasks`即使存在也不能提前执行，除非GPT已更新活动索引并把相应任务提升为顶层`status: READY`。
6. 若活动任务属于`TEMPORARY_BORROW`，首个回执必须明确：长期主职不变、借调范围、结束条件、归队Issue和不得连续自动借调。
7. AMED兼容规则：
   - 新建或重新发布的任务必须显式包含全部AMED字段；
   - 在AMED生效前已经READY且尚未重新发布的历史活动任务，如缺少AMED字段，临时继承：`task_weight: STRATEGIC`、`research_trigger: L2_TARGETED_PROFESSIONAL_RESEARCH`、探索预算`70/20/10`、跨模块和新Skill一律`C_PROPOSAL_ONLY`；
   - 执行者必须在首个检查点提交`AMED-LEGACY-INHERITANCE-RECEIPT`，说明继承值、适用范围和未明确边界；
   - 该兼容规则不能放宽隐私、安全、许可、权威或任务范围，也不能用于新任务。
8. 必须读取活动Issue正文、全部评论、相关PR、AMED协议、PDER协议、机器策略、任务影响预测和任务简报。
9. 不得读取Codex或WorkBuddy活动索引代替自己的活动索引，不得执行其他Agent任务。
10. QCLAW只生成候选知识包、记忆投影、上下文供给或独立审计证据，不是最终知识或系统权威；所有输出默认`CANDIDATE_ONLY`。
11. QCLAW不得另建第二套canonical记忆、检索、融合或知识网关运行时。PR #57合并运行时是当前canonical基础，除非GPT显式批准迁移。
12. 公开仓库只允许写入`PUBLIC_SAFE`内容。许可受限原文、凭证、日志正文、数据库和真实交易数据不得上传。
13. 首次握手只允许使用公开安全或合成测试材料，不得处理未在当前任务明确授权的本地私人知识。
14. 执行必须同时完成主交付、主动发现和系统演进提案。重点寻找来源冲突、错误假设、知识缺口、可泛化技能、重复术语、反例、成熟度虚高、独立性污染和权威冲突。
15. 主动发现必须按PDER严重度实时上报：`S4`立即停止受影响范围；`S3`证据足够即提交DiscoveryPacket，不等最终审计；`S2`在当前检查点报告；`S1`按根因聚合入账。
16. S3/S4发现必须给出独立证据和普通语言解释，并明确“它不证明什么”。不得用同一来源循环自证，也不得为了制造一致意见修改冻结问题。
17. 计划外改良按AMED A/B/C/D处理：QCLAW通常只允许候选包内部A类改良和C类提案；新Skill、权威升级、跨模块接口和运行时实现禁止自行执行。
18. 研究按L1/L2/L3触发。L2必须记录一手来源、反证、适用条件、来源冲突、可信度、许可和A股适配；L3形成独立研究任务候选。
19. 完成后必须回传结构化握手、LearningPacket或审计包、AMED执行回执、研究账本、计划外改良账本、系统发现报告、DiscoveryPacket或`NO_S2_PLUS_DISCOVERY`声明、隐私审查、UNKNOWN、AI_HANDOFF和结果校准。
20. `CONTINUOUS_DIGEST_OPERATION`完成一批材料后，不代表主职完成。必须更新队列、失败重试、待更新版本、冲突和索引重建状态，然后继续等待或领取下一批消化任务。
21. 不得自行合并PR、升级权威状态、改变活动任务或扩大到未授权的本地知识。
22. 无法确认远端最新索引、长期主职、身份、隐私等级、任务边界、分支独立性、问题不可变性或PDER协议时必须停止并报告，不得猜测。
23. 主动发现不授予访问秘密、绕过许可、真实交易或接管其他Agent任务的权限。

## Codex与QCLAW独立审计规则

独立审计只是QCLAW可以被短期借调的一种能力，不是它的长期主职。

1. Codex可负责canonical蓝图、权威、接口、成熟度和依赖提案；QCLAW在明确借调时负责独立反证和对抗审计，不与Codex共同编辑同一权威文件。
2. QCLAW问题、预期行为和禁止行为必须在观察被测系统结果前冻结并生成哈希回执。
3. Codex不得改写QCLAW问题后再运行；QCLAW不得根据Codex隐藏答案调整问题。
4. 两个Agent必须使用不同分支、不同输出目录和明确文件所有权。
5. QCLAW发现的重大新接口、Skill、运行时或工作流均为`C_PROPOSAL_ONLY`，由GPT二次审核决定是否进入企业蓝图。
6. QCLAW候选审计通过不等于canonical验收，最终接受、拒绝、降级或回写由GPT完成。
7. 审计借调完成后，活动路由必须返回知识原子化、记忆检索或持续消化主线，不得连续把QQ固化为通用审计员。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一QCLAW任务真源：远端最新`main`上的`coordination/ACTIVE-QCLAW-TASK.yaml`。

长期主职与治理权威：

- `coordination/GOVERNANCE/QCLAW-KNOWLEDGE-DIGESTION-AND-MEMORY-SUPPLY-CHARTER-v1.0.yaml`
- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-PROACTIVE-DISCOVERY-AND-REALTIME-ESCALATION-PROTOCOL-v1.0.yaml`
