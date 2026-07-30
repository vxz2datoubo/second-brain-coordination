# 第二大脑与A股交易研究项目蓝图集成索引 v1.5 候选

> `agent_id: CODEX`
>
> `reviewer: GPT`
>
> `base_index: PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.4.md`
>
> `authority: CANDIDATE_ONLY_DOES_NOT_SUPERSEDE_V1.4`
>
> `boundary: research_only / NO_TRADE`

## 一、版本目的

v1.5 候选在 v1.4 的 W1 至 W13、0010 至 0019 架构上登记一个
`0010 runtime protocol`，不新增 W14，不创建新记忆权威，不修改交易
执行边界。

## 二、四平面总架构

| 平面 | 工作流 | 核心职责 |
|---|---|---|
| 治理与控制 | W1、W8、W9 | AMED、任务、Agent运维、影子、工程学习 |
| 事实与证据 | W2、W3、W5、W13 | 市场、规则、回放、知识、事件、参与者资金证据 |
| 研究与模型 | W4、W6、W12 | 特征、策略、实验、竞争性假设、概率与决策科学 |
| 决策与生存 | W7、W10、W11＋0017/0018 | 认知上下文、配置、风险、验证、净优势与关停 |

厂商中立 Agent 内核横跨四平面，但只提供合同和编排语义，不拥有平面
数据。

## 三、模块登记

| ID | 名称 | 归属 | 成熟度 |
|---|---|---|---|
| 0010 | Personal Epistemic Cognitive OS | W10 | CONTRACTED_NOT_IMPLEMENTED |
| 0010-KERNEL | Vendor-Neutral Agent Operating Kernel Protocol | W10 runtime + W1/W3/W8 interfaces | IMPLEMENTED_CANDIDATE_PENDING_GPT_REVIEW |
| 0011 | Kelly-Thorp Expected Value and Capital Allocation | W11 | CONTRACTED_NOT_IMPLEMENTED |
| 0012 | Decision Science Skill Family | W12 | D0_COMPLETE_PENDING_MERGE |
| 0014 | Daily Participant Capital-Flow Intelligence | W13 | CONTRACTED_NOT_IMPLEMENTED |
| 0015 | Policy Macro News Cross-Asset Intelligence | W5 | CONTRACTED_NOT_IMPLEMENTED |
| 0017 | Liquidity Sweep/Reclaim Validation | W4＋W7 | CONTRACTED_NOT_IMPLEMENTED |
| 0018 | House-Edge Survival and Operating Control | W7＋W9＋W11 | CONTRACTED_NOT_IMPLEMENTED |
| 0019 | Enterprise Blueprint Convergence | W1 | ACTIVE_PROJECT_PLAN |

`0010-KERNEL` 是子协议标签，不是新的模块编号或工作流。

## 四、唯一权威表

| 权威 | 所有者 |
|---|---|
| 任务治理、AMED 和 AuthorityResolution 源 | W1 |
| Agent部署、能力注册和运行编排 | W8 |
| 市场时间、规则、成本与回放 | W2 |
| 知识、证据、冲突和长期记忆 | W3 |
| 事件、政策、预期和跨资产证据 | W5 |
| 参与者资金活动证据 | W13 |
| 策略、特征和实验族 | W4 |
| 竞争性参与者假设 | W6 |
| ProbabilityEstimate | W12/DS-02 |
| DecisionEpisode 与 PEOS 运行上下文 | W10 |
| Kelly和资本配置 | W11 |
| 统一验证和最终风险否决 | W7 |
| 结果校准和工程学习 | W9 |

Agent 内核只实现候选解析器和公共合同，不成为上述对象的系统记录。

## 五、核心决策链

```text
W1 AuthorityResolution
-> Agent Kernel TaskIntent + ContextAssembly + CapabilityRouting
-> W2/W3/W5/W13事实与证据
-> W4策略实验 + W6竞争性假设
-> W12问题框定、ProbabilityEstimate和研究真实性
-> W10 DecisionEpisode与用户上下文
-> W11净期望和资本配置
-> 0018净优势质量、有效次数、破产风险和容量约束建议
-> W7统一验证和最终风险否决
-> W9影子结果、归因、校准和成熟度回写
-> Agent Kernel CompletionReceipt + candidate MemoryWriteProposal
```

## 六、共享合同

既有合同：

1. `MarketTimeAndAvailabilityEnvelope`
2. `AShareRuleSnapshot`
3. `SourceRecord/EvidenceItem/KnowledgeAtom`
4. `EventEvidencePacket`
5. `ParticipantFlowEvidencePacket`
6. `StrategyExperimentFamily`
7. `ProbabilityEstimate`
8. `DecisionEpisode`
9. `W11CandidateAllocation`
10. `W7RiskEnvelope/ValidationReport`
11. `OutcomeCalibrationRecord`

0010-KERNEL 候选合同：

12. `AuthorityResolution`
13. `TaskIntent`
14. `EpistemicClaim`
15. `MemoryWriteProposal`
16. `CapabilityDescriptor`
17. `ToolRouteDecision`
18. `ExecutionCheckpoint`
19. `CompletionReceipt`
20. `AgentHandoff`
21. `ModelBehaviorProfile`

新增合同必须通过 Adapter 映射到既有对象，不得平行复制。

## 七、生产者与消费者

| 合同 | 候选生产者 | 消费者 |
|---|---|---|
| AuthorityResolution | W1 runtime adapter | all agents |
| TaskIntent | Agent Kernel | W3/W8/W10/domain skills |
| EpistemicClaim | W3/domain adapters | W10/Kernel |
| MemoryWriteProposal | Kernel/domain skills | W3/Phase 3 |
| CapabilityDescriptor | W8/provider adapters | Kernel |
| ToolRouteDecision | Kernel | W8/W10/audit |
| ExecutionCheckpoint | executing agent | recovery/control plane |
| CompletionReceipt | executing agent | GPT/W1/W9 |
| AgentHandoff | source agent | target agent/GPT |
| ModelBehaviorProfile | evaluation owner | Agent runtime |

## 八、非重复边界

- 内核不创建第二套记忆、证据、图谱、检索、回放或交易系统；
- `MemoryWriteProposal.authority_write` 固定为 false；
- `ModelBehaviorProfile.authority_overrides` 固定为空；
- 厂商显示名不参与能力评分；
- A股规则仍由 W2 版本化；
- ProbabilityEstimate 仍由 W12/DS-02 拥有；
- DecisionEpisode 仍由 W10 拥有；
- 最终风险否决仍由 W7 拥有；
- Agent 内核不能启动订单或修改生产审批。

## 九、成熟度

当前 0010-KERNEL 状态：

```yaml
blueprint: CANDIDATE_COMPLETE
contracts: IMPLEMENTED_CANDIDATE
reference_runtime: IMPLEMENTED_CANDIDATE
tests: LOCAL_SYNTHETIC_ONLY
cross_model_evaluation: NOT_RUN
w1_adapter: NOT_IMPLEMENTED
w3_phase3_adapter: NOT_IMPLEMENTED
w8_adapter: NOT_IMPLEMENTED
shadow_activation: DISABLED
canonical_status: NOT_APPROVED
live_trading: PROHIBITED
```

## 十、激活顺序

1. GPT 审查当前 Draft PR；
2. 冻结合同字段、所有权和非重复映射；
3. 单独建立 W1、W3/Phase 3、W8 Adapter 任务；
4. 建立至少两个模型的行为 Profile 与合同等价评测；
5. 完成中断恢复、重复副作用和权限漂移对抗测试；
6. 仅在 feature flag 下进行 shadow；
7. 通过后由 GPT 决定是否更新 canonical PEOS 和 Root `AGENTS.md`。

## 十一、验收

- 原始第三方捕获不进入 Git；
- Prompt 不包含厂商产品推荐或商业伙伴优先级；
- 显示品牌重命名不改变路由结果；
- 推断不能变成工具观察；
- UNKNOWN 保留；
- 内核不能写 canonical memory；
- 模型 Profile 不能改变权威；
- 中断恢复不重复副作用；
- 完成声明逐项绑定证据；
- 所有测试和公开扫描通过；
- 全程 `research_only / NO_TRADE`。

## 十二、回滚

本文件不 supersede v1.4。关闭候选 PR 即可恢复，现有 canonical 蓝图、
活动路由和运行时均不受影响。
