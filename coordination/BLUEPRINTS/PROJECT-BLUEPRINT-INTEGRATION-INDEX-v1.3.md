# 第二大脑与A股交易系统项目蓝图集成索引 v1.3

> `agent_id: GPT`
>
> `supersedes: PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.2.md`
>
> `boundary: research_only / NO_TRADE`

## 一、用途

本索引继承v1.2的PEOS与W11凯利－索普登记，新增W12决策科学技能族和Blueprint-to-Skill Gap Compiler，解决“专业方法写进蓝图，却没有成为技能”的长期缺口。

## 二、新登记模块

- module_id: `DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012`
- specialized_blueprint: `coordination/BLUEPRINTS/DECISION-SCIENCE-SKILL-FAMILY-AND-GAP-COMPILER-BLUEPRINT-v1.0.md`
- root_cause_audit: `coordination/BLUEPRINTS/WHY-DECISION-SKILLS-WERE-MISSED-ROOT-CAUSE-AUDIT-v1.0.md`
- research_validation: `coordination/BLUEPRINTS/DECISION-SCIENCE-SKILL-FAMILY-RESEARCH-VALIDATION-v1.0.md`
- machine_registry: `coordination/SKILLS/DECISION-SCIENCE-SKILL-FAMILY-REGISTRY-v1.0.yaml`
- program_charter: `coordination/BLUEPRINTS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.3.md`
- implementation_issue: `#63`
- parent_program: `#31`
- dependencies: `#23 / #38 / #59 / #60 / #61 / #62`
- status: `SKILL_FAMILY_REGISTERED / PROJECT_PLAN_PENDING / RUNTIMES_NOT_IMPLEMENTED`

## 三、决策链中的位置

```text
DS-01 问题框定
→ DS-02 概率和预测融合
→ DS-03 信息价值
→ DS-04 稳健选择
→ DS-05 时机和序贯决策
→ W11 Kelly－Thorp资本配置
→ DS-07 组合权重
→ DS-08 下行和生存
→ DS-09 执行和TCA
→ DS-10 研究真实性
→ DS-11 状态和衰减
→ DS-12 归因
→ DS-13 多目标与资本配给
→ PEOS信念、能力和长期记忆更新
```

DS-06探索利用主要服务影子实验和研究资源分配，不直接进入真实资金路径。

## 四、候选技能登记

| 编号 | Skill ID | 阶段 | 优先级 | 当前成熟度 |
|---|---|---|---:|---|
| DS-01 | DECISION-FRAMING-INFLUENCE-DIAGRAM-SKILL-0012A | FRAME | P0 | CANDIDATE_SKILL_REGISTERED |
| DS-02 | BAYESIAN-BELIEF-UPDATE-FORECAST-FUSION-SKILL-0012B | BELIEVE | P0 | CANDIDATE_SKILL_REGISTERED |
| DS-03 | VALUE-OF-INFORMATION-RESEARCH-STOPPING-SKILL-0012C | LEARN | P0 | CANDIDATE_SKILL_REGISTERED |
| DS-04 | ROBUST-AMBIGUITY-MINIMAX-REGRET-SKILL-0012D | CHOOSE | P0 | CANDIDATE_SKILL_REGISTERED |
| DS-05 | SEQUENTIAL-DECISION-OPTIMAL-STOPPING-REAL-OPTIONS-SKILL-0012E | TIME | P2 | CANDIDATE_SKILL_REGISTERED |
| DS-06 | EXPLORATION-EXPLOITATION-ADAPTIVE-EXPERIMENT-SKILL-0012F | LEARN | P2 | CANDIDATE_SKILL_REGISTERED |
| DS-07 | PORTFOLIO-BELIEF-TO-WEIGHTS-SKILL-0012G | PORTFOLIO | P1 | CANDIDATE_SKILL_REGISTERED |
| DS-08 | RISK-BUDGET-DOWNSIDE-SURVIVAL-SKILL-0012H | SURVIVE | P1 | CANDIDATE_SKILL_REGISTERED |
| DS-09 | OPTIMAL-EXECUTION-IMPLEMENTATION-SHORTFALL-SKILL-0012I | EXECUTE | P1 | CANDIDATE_SKILL_REGISTERED |
| DS-10 | RESEARCH-MULTIPLE-TESTING-OVERFITTING-AUDIT-SKILL-0012J | VALIDATE | P0 | CANDIDATE_SKILL_REGISTERED |
| DS-11 | REGIME-CHANGE-MODEL-DECAY-SKILL-0012K | MONITOR | P1 | CANDIDATE_SKILL_REGISTERED |
| DS-12 | PERFORMANCE-DECISION-EXECUTION-ATTRIBUTION-SKILL-0012L | ATTRIBUTE | P1 | CANDIDATE_SKILL_REGISTERED |
| DS-13 | MULTI-OBJECTIVE-UTILITY-CAPITAL-RATIONING-SKILL-0012M | CHOOSE | P2 | CANDIDATE_SKILL_REGISTERED |

## 五、非重复建设矩阵

| 已有工作流 | 已有职责 | W12吸收/补充 | 禁止 |
|---|---|---|---|
| W2 | 市场事实、时间和成交 | 为决策和执行提供点时数据 | 重建数据权威 |
| W4 | 特征、模型、策略和实验 | 读取收益样本与试验族 | 用技能族重做信号平台 |
| W5 | 事件和信息到达 | VOI、概率更新和时机输入 | 故事直接变概率 |
| W6 | 多Agent情景 | 条件预测候选和反方 | 多Agent自信变仓位 |
| W7 | 统一验证与硬风险 | DS-08/10调用其门禁和记录 | 第二套风险引擎 |
| W9 | 影子和工程学习 | 自适应实验、归因和成熟度回写 | 影子结果变订单 |
| W10 | 世界/个人/任务模型、DecisionEpisode | 框定、信念、效用和归因视图 | Personal模型篡改世界事实 |
| W11 | EV、Kelly和稳健资本配置 | 接收上下游技能结果 | 重复仓位优化器 |
| Issue #38/#59/#60 | canonical知识、原子、长期记忆 | 保存研究、技能、失败和版本 | 第二套知识源 |
| OMS/Execution | 订单状态、真实执行和对账 | DS-09研究合同和TCA | LLM直接下单 |

## 六、蓝图缺口编译器验收

Gap Compiler必须：

1. 扫描蓝图、Issue、PR、Skill、代码和测试；
2. 发现术语是否只有提及；
3. 识别已有碎片和重复建设；
4. 映射决策生命周期；
5. 给出成熟度和证据；
6. 生成候选Skill ID但不自动实施；
7. 支持`REFERENCE_ONLY / REJECTED / UNKNOWN`；
8. 记录误报和漏报；
9. 输出用户可审查的优先级和依赖DAG；
10. 不把文档存在当成运行能力。

## 七、A股跨技能约束

所有交易技能共享一个版本化A股约束合同，不得各自维护冲突规则：

- 交易所、板块、证券类型和生效日期；
- T+1和可卖库存；
- 涨跌幅、停牌、复牌和无涨跌幅阶段；
- 申报单位、价格步长、整数股和现金；
- 竞价、连续、收盘与盘后；
- 税费、成本、滑点、冲击、容量和成交概率；
- 融资融券资格、标的、券源和成本；
- ST、退市、新股和历史制度回放；
- NO_TRADE和人工审批。

## 八、集成验收门

1. 根因审计、总蓝图、研究矩阵、机器注册和Issue完成；
2. 母章程v1.3与PROGRAM-INDEX v1.3引用W12；
3. D0完成公开仓和本地受保护蓝图实况审计；
4. 所有旧蓝图重要术语有明确状态；
5. 第一轮最多三个P0纵向切片；
6. 每个技能有非目标、反例和停止条件；
7. 研究技能披露总试验和失败；
8. 交易技能使用点时A股规则与成本；
9. 与W7/W10/W11/OMS无第二套权威运行时；
10. 结果进入DecisionEpisode、工程学习和长期记忆；
11. GPT验收，用户保留目标、风险和高风险批准权；
12. 不以技能数量、论文清单或模型自报完成。

## 九、当前状态

```yaml
module_id: DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012
root_cause_audit: COMPLETE
specialized_blueprint: COMPLETE
research_validation_matrix: COMPLETE
machine_skill_registry: COMPLETE
program_charter_v1_3: COMPLETE
implementation_issue: 63
codex_project_plan: NOT_STARTED
gap_compiler_runtime: NOT_IMPLEMENTED
child_skill_runtimes: NOT_IMPLEMENTED
a_share_validation: NOT_STARTED
shadow_mode: NOT_STARTED
live_trading: PROHIBITED
protected_master_backwrite: USER_APPROVED_LOCAL_EXECUTION_PENDING
```
