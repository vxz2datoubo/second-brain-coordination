# 第二大脑与A股交易研究项目蓝图集成索引 v1.4

> `agent_id: GPT`
>
> `supersedes: PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.3.md`
>
> `governance_task: #72`
>
> `boundary: research_only / NO_TRADE`

## 一、版本目的

v1.4将近期新增的AMED、W13、PMN、0017和0018与既有W1-W12重新收敛，建立统一的职责、权威、接口、成熟度和任务顺序。它不新增W14，也不授权任何业务运行时、回测执行或交易。

权威收敛蓝图：

- `coordination/BLUEPRINTS/ENTERPRISE-BLUEPRINT-CONVERGENCE-AND-DEPENDENCY-MAP-v1.0.md`
- `coordination/GOVERNANCE/ENTERPRISE-BLUEPRINT-AUTHORITY-AND-INTERFACE-REGISTRY-v1.0.yaml`

## 二、四平面总架构

| 平面 | 工作流 | 核心职责 |
|---|---|---|
| 治理与控制 | W1、W8、W9 | AMED、任务、Agent运维、影子、工程学习 |
| 事实与证据 | W2、W3、W5、W13 | 市场、规则、回放、知识、事件、参与者资金证据 |
| 研究与模型 | W4、W6、W12 | 特征、策略、实验、竞争性假设、概率与决策科学 |
| 决策与生存 | W7、W10、W11＋0017/0018 | 认知上下文、配置、风险、验证、净优势与关停 |

## 三、模块登记

| ID | 名称 | 归属 | Issue | 成熟度 |
|---|---|---|---:|---|
| 0010 | Personal Epistemic Cognitive OS | W10 | 61 | CONTRACTED_NOT_IMPLEMENTED |
| 0011 | Kelly-Thorp Expected Value and Capital Allocation | W11 | 62 | CONTRACTED_NOT_IMPLEMENTED |
| 0012 | Decision Science Skill Family | W12 | 63 / PR66 | D0_COMPLETE_PENDING_MERGE |
| 0014 | Daily Participant Capital-Flow Intelligence | W13 | 67 | CONTRACTED_NOT_IMPLEMENTED |
| 0015 | Policy Macro News Cross-Asset Intelligence | W5 | 68 | CONTRACTED_NOT_IMPLEMENTED |
| 0017 | Liquidity Sweep/Reclaim Validation | W4＋W7 | 69 | CONTRACTED_NOT_IMPLEMENTED |
| 0018 | House-Edge Survival and Operating Control | W7＋W9＋W11 | 71 | CONTRACTED_NOT_IMPLEMENTED |
| 0019 | Enterprise Blueprint Convergence | W1 | 72 | ACTIVE_PROJECT_PLAN |

## 四、唯一权威表

| 权威 | 所有者 |
|---|---|
| 任务治理和AMED | W1 |
| Agent部署和运行编排 | W8 |
| 市场时间、规则、成本与回放 | W2 |
| 知识、证据、冲突和长期记忆 | W3 |
| 事件、政策、预期和跨资产证据 | W5 |
| 参与者资金活动证据 | W13 |
| 策略、特征和实验族 | W4 |
| 竞争性参与者假设 | W6 |
| ProbabilityEstimate | W12/DS-02 |
| DecisionEpisode | W10 |
| Kelly和资本配置 | W11 |
| 统一验证和最终风险否决 | W7 |
| 结果校准和工程学习 | W9 |

0017和0018均为嵌入式跨模块能力，不拥有上述平行权威。

## 五、核心决策链

```text
W2/W3/W5/W13事实与证据
→ W4策略实验＋W6竞争性假设
→ W12问题框定、ProbabilityEstimate和研究真实性
→ W10 DecisionEpisode与用户上下文
→ W11净期望和资本配置
→ 0018净优势质量、有效次数、破产风险和容量约束建议
→ W7统一验证和最终风险否决
→ W9影子结果、归因、校准和成熟度回写
```

0017可作为W4策略/事件候选进入W7验证，但不得直接产生主力意图或订单。

## 六、共享合同

1. `MarketTimeAndAvailabilityEnvelope`，W2写；
2. `AShareRuleSnapshot`，W2写；
3. `SourceRecord/EvidenceItem/KnowledgeAtom`，W3写；
4. `EventEvidencePacket`，W5写；
5. `ParticipantFlowEvidencePacket`，W13写；
6. `StrategyExperimentFamily`，W4写；
7. `ProbabilityEstimate`，W12/DS-02写；
8. `DecisionEpisode`，W10写；
9. `W11CandidateAllocation`，W11写；
10. `W7RiskEnvelope/ValidationReport`，W7写；
11. `OutcomeCalibrationRecord`，W9写。

完整producer/consumer约束见机器注册表。

## 七、非重复边界

- AMED只治理任务和系统演进，不建业务运行时；
- W13只提供公开参与者活动证据，不确认真实账户身份；
- PMN不复制事件、市场、概率或风险系统；
- 0017不使用DDX/DDY、伪逐笔、伪Delta/CVD/OFI或主力意图；
- 0018不复制W12概率、W11 Kelly、W7风险和订单系统；
- W10个人模型不能静默修改概率、效用或风险上限；
- W12子技能不能绕过W11和W7；
- 所有模块复用W2的A股规则和点时回放。

## 八、当前关键路径

1. PR #66已完成R3并获得GPT有界验收记录，保持不自动合并；
2. Issue #72成为唯一活动Codex任务，完成蓝图、权威、接口和依赖冻结；
3. 完成后重新排序W13、PMN、0017、0018、W11和W12首批切片；
4. 每次只激活一个业务纵向切片；
5. 业务切片先单独验证，再做联合经济增量；
6. 所有资本成熟度升级必须经过W11、0018和W7共同门禁。

## 九、统一成熟度定义

- `BLUEPRINT_ONLY`：仅概念和蓝图；
- `REGISTERED_CANDIDATE`：有Issue和候选对象；
- `CONTRACTED_NOT_IMPLEMENTED`：有机器合同和验证协议；
- `IMPLEMENTED_NOT_A_SHARE_VALIDATED`：代码存在但未完成A股验证；
- `A_SHARE_BACKTESTED`：点时、规则、成本和样本外通过；
- `SHADOW_VALIDATED`：影子运行与回测可对账；
- `VALIDATED_RESEARCH_CAPABILITY`：GPT验收后的研究能力；
- `LIVE_TRADING`：本工程当前禁止。

## 十、WIP规则

- Codex一个活动任务；
- 首批业务纵向切片最多一个；
- 同一共享接口冻结前不并行实现多个消费者；
- 规划和研究不能静默扩大运行时；
- 发现的新Skill默认C类提案；
- 不自动合并，不进入真实交易。

## 十一、Issue #72验收门

- PROGRAM-INDEX、集成索引、执行序列和ACTIVE路由一致；
- 所有核心对象只有一个写权威；
- 0017/0018正式嵌入原工作流；
- 模块成熟度有证据；
- 重复、孤儿、幽灵和过时引用有处置；
- 下一纵向切片排序有数据准备度、价值、依赖、风险和成本依据；
- YAML、UTF-8、引用与秘密扫描通过；
- 全程`research_only / NO_TRADE`。
