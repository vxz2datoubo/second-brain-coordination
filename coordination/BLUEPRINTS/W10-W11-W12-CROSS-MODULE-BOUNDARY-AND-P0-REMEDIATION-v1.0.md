# W10/W11/W12跨模块边界裁决与P0整顿 v1.0

> `decision_owner: GPT`
>
> `related_issues: #31 / #59 / #60 / #61 / #62 / #63`
>
> `status: ACTIVE_ARCHITECTURE_DECISION`
>
> `boundary: research_only / NO_TRADE`

## 一、证据状态说明

QCLAW通过用户转述提交了五模块状态、ORPHAN-TERM-SCAN精选、跨模块冲突和待办摘要，但截至本裁决生成时，公开仓未检索到对应的独立`ORPHAN-TERM-SCAN`文件或新Draft PR。

因此：

- 架构边界和P0治理规则立即生效；
- “六个幽灵能力”等数量性结论暂列`CANDIDATE_FINDING_NEEDS_EVIDENCE`；
- Codex Issue #63 D0必须核对名称、原成熟度、文件/代码/测试路径和建议降级状态；
- 不因口头摘要直接批量修改成熟度。

## 二、五模块当前成熟度

| Issue | 模块 | 当前可信状态 | 不得声称 | 下一门 |
|---|---|---|---|---|
| #59 | 知识原子化与持续消化 | PR #64为P0候选交付；反馈、UNKNOWN和架构材料较完整，但元数据与自动验证仍需补齐 | 不得称P1已完成或canonical已集成 | 修复PR #64元数据/实测证据；QQ当前优先完成PR #58独立对抗包 |
| #60 | 长期记忆与混合检索 | PR #65仅为需要重新审计的M0候选；存在过时运行时路径和重复建设风险 | 不得开始M1/M2运行时，不得声称44项零重复已证明 | 先基于PR #57真实Python运行时和PR #58现状重做M0 |
| #61 | PEOS认知校准 | 蓝图和研究矩阵已登记；Schema/canonical接口尚未正式冻结 | 不得称DecisionEpisode/Probability运行时已实现 | C0非重复审计和共享Schema冻结 |
| #62 | Kelly-Thorp资本配置 | 专项蓝图、研究矩阵和机器Skill已登记；运行时与A股纵向验证未开始 | 不得称Robust Kelly或A股仓位能力已验证 | K0审计；共享ProbabilityEstimate冻结；A股单机会纵向验证 |
| #63 | 决策科学技能族与Gap Compiler | 蓝图、研究矩阵、注册表和控制面完成；Codex D0任务READY | 不得称Gap Compiler或十三项技能已实现 | D0全仓库＋可访问本地证据审计 |

QCLAW提出的“#59 P1剩余6个digest”须补来源清单和交付状态后确认；“#60 M2原型开发”当前明确禁止提前启动。

## 三、跨模块裁决一：W11与DS-08风险边界

### 3.1 权威层级

```text
用户批准的风险政策与资本边界
→ W7 Independent Hard Risk：最终硬约束、否决与降级权
→ DS-08 Portfolio Risk Envelope：组合风险预算、尾部、回撤、流动性和生存包络
→ W11 Kelly-Thorp Allocation：在上述包络内计算单机会/多机会候选仓位
→ DS-09 Execution：根据成交、冲击、T+1和流动性进一步缩小或ABSTAIN，绝不放大
```

### 3.2 谁说了算

- 用户：决定风险偏好、最大可承受损失、资本用途和高风险批准；
- W7：最终硬风险系统记录源和否决者；
- DS-08：风险预算与组合下行分析权威，不直接产生Alpha或订单；
- W11：期望值/Kelly资本配置权威，不得绕过W7或DS-08；
- DS-09：执行可行性权威，只能减少、延迟、拆分或拒绝仓位。

### 3.3 非重复合同

- DS-08输出：`PortfolioRiskEnvelope`、`RiskBudget`、`ExpectedShortfall`、`DrawdownScenario`、`LiquidityBuffer`、`SurvivalGate`；
- W11输入：上述包络＋概率/收益分布；
- W11输出：`KellyAllocationCandidate`或`AllocationRange`；
- W7输出：`HardRiskDecision = ALLOW / CAP / FREEZE / REJECT`；
- 不允许DS-08维护第二套Kelly求解器；
- 不允许W11维护第二套独立硬风险引擎。

## 四、跨模块裁决二：DS-04与W11 Robust Kelly

### 4.1 DS-04职责

DS-04是通用模糊不确定性与稳健决策技能，负责：

- 概率区间和分布集合；
- 场景集合及其可信边界；
- worst-case与minimax regret；
- 参数敏感区域；
- 决策脆弱性；
- `ABSTAIN / WAIT / COLLECT_MORE_INFORMATION`。

DS-04输出统一命名：

`AmbiguityAndRobustDecisionEnvelope`

包括：`ProbabilitySet / DistributionSet / RegretTable / SensitivityRegion / RobustChoiceConstraints / AbstentionCondition`。

### 4.2 W11职责

W11是唯一Kelly资本配置权威，负责：

- Raw Kelly；
- Fractional Kelly；
- posterior/conservative-quantile Kelly；
- risk-constrained Kelly；
- 使用DS-04包络的Robust Kelly；
- A股可执行仓位映射。

W11输出统一命名：

`RobustKellyAllocation`

### 4.3 硬边界

- DS-04不得输出资本比例、目标股数或第二套Kelly优化结果；
- W11不得自行伪造模糊集合或跳过DS-04/W7来源；
- 注册表中DS-04的`existing_fragments: robust Kelly`应改为`robust-decision inputs consumed by W11 Robust Kelly`；
- 一个Robust Kelly求解器，只归W11。

## 五、跨模块裁决三：PEOS ProbabilityEstimate与DS-02字段对齐

### 5.1 单一对象原则

建立共享canonical合同：

`ProbabilityEstimate`

- Schema Owner：W12 / DS-02；
- Computation Owner：DS-02；
- Persistence/Ex-ante Freeze：W10 PEOS的DecisionEpisode引用；
- Consumer：W11、DS-03、DS-04、DS-05、W7；
- PersonalCognitiveModel不得修改概率，只能附加展示、理解和提醒信息。

### 5.2 最小字段

```yaml
ProbabilityEstimate:
  estimate_id: string
  event_id: string
  decision_id: string | null
  outcome_space: list
  as_of_time: datetime
  horizon: object
  point_estimate: number | map
  interval_or_distribution: object
  unknown_mass: number
  base_rate: object | null
  source_forecasts: list
  source_lineage: list
  dependence_clusters: list
  fusion_method: string
  effective_sample_size: number | null
  calibration_group: string | null
  calibration_history: object | null
  calibration_status: string
  supporting_evidence: list
  counterevidence: list
  assumptions: list
  regime_scope: object | null
  drift_status: string
  invalidation_conditions: list
  model_versions: list
  rule_versions: list
  status: CANDIDATE | FROZEN_EX_ANTE | SUPERSEDED | INVALIDATED
```

### 5.3 数据流

```text
原始来源预测
→ DS-02去重、依赖聚类、基准率和校准融合
→ FusedProbabilityEstimate（符合ProbabilityEstimate Schema）
→ DecisionEpisode只保存estimate_id＋事前快照哈希
→ W11只读消费
→ 结果发生后写CalibrationRecord，不回改原事前概率
```

禁止：

- PEOS复制一份概率后静默修改；
- 多Agent输出因语言不同被当成独立证据；
- LLM置信感直接变成point_estimate；
- 事后结果覆盖事前冻结记录。

## 六、P0立即整顿

### P0-1 T+1与“换手”语义修正

必须拆分四个对象，禁止统称`turnover`：

1. `market_turnover_rate`：市场层面的成交额/流通市值等指标；
2. `portfolio_turnover`：策略组合买卖规模与组合资本之比；
3. `sellable_quantity`：账户在当前时点真实可卖库存；
4. `round_trip_eligibility`：证券品种是否允许交收前回转交易。

普通股票买入后在交收前不得卖出，实行回转交易的证券品种除外。任何模拟、仓位或执行逻辑必须按交易所、板块、证券类型和规则生效日读取快照，而非用一个布尔`T_PLUS_ONE=true`覆盖全部证券。

最低状态字段：

```yaml
PositionLot:
  instrument_id: string
  trade_date: date
  quantity: integer
  settled_quantity: integer
  sellable_quantity: integer
  frozen_quantity: integer
  already_sold_quantity: integer
  round_trip_eligible: boolean
  rule_snapshot_id: string
```

### P0-2 A股规则快照

建立`A_SHARE_RULE_SNAPSHOT`，至少包含：

- exchange / board / security_type；
- effective_from / effective_to；
- source_url_or_document_id / source_hash；
- settlement_and_round_trip；
- price_limit；
- lot_size / tick_size；
- auction_sessions；
- suspension/reopening；
- fees/taxes；
- margin/borrow capability；
- temporarily_suspended_clauses；
- verification_status。

当前规则不得从记忆硬编码，历史回放必须使用当时有效版本。

### P0-3 六个幽灵能力降级

立即生效的是降级规则，而非未经证据确认的六个名称：

- 无代码/运行时：最高`CONTRACTED`；
- 有代码无自动测试：最高`IMPLEMENTED`；
- 有合成测试无A股点时回放：不得标`A_SHARE_BACKTESTED`；
- 有历史回测无影子运行：不得标`SHADOW_VALIDATED`；
- 文档、Schema或Issue存在：不得等同实现；
- Codex D0必须列出每个候选幽灵能力的名称、证据路径、当前声明、应降级状态和影响。

### P0-4 Romano-Wolf补登记

Romano-Wolf stepdown multiple testing登记为：

- Parent Skill：`RESEARCH-MULTIPLE-TESTING-OVERFITTING-AUDIT-SKILL-0012J`；
- Classification：`EXISTING_SKILL_SUBCAPABILITY`；
- 不是新的独立Skill；
- Purpose：在多个相关假设/策略与共同基准比较时，通过重抽样stepdown程序控制familywise error rate，并利用统计量的联合依赖结构提高相对单步方法的检验力；
- Required Inputs：完整试验族、共同基准、时间依赖保留的重抽样方案、studentized统计量、预注册显著性水平；
- Outputs：stepdown rejection set、adjusted p-values（若采用相应算法）、familywise-error audit receipt；
- Non-goals：不替代PBO、DSR、SPA、最终锁箱、交易成本、容量和影子验证；
- A-share requirement：使用适合时序和横截面依赖的block/stationary bootstrap或经论证替代方案，禁止iid重抽样默认化。

## 七、待办裁决

1. #59：QQ当前P0仍是完成PR #58独立100+对抗包；PR #64整改与剩余digest排在该阻塞门之后；
2. #60：M2原型开发冻结，先重做M0真实非重复审计；
3. #61：将`ProbabilityEstimate`和`DecisionEpisode reference`登记为正式共享Schema；
4. #62：等待ProbabilityEstimate、风险包络和规则快照合同冻结后，执行单一A股历史机会纵向验证；
5. #63：Codex D0必须吸收本裁决，完成全仓库＋可访问本地证据审计；
6. 第一轮仍最多三个P0纵向切片，不因本次扫描扩大并行运行时数量。

## 八、当前状态

```yaml
cross_module_decisions: APPROVED
p0_semantic_and_rule_remediation: APPROVED
romano_wolf_registration: APPROVED_AS_DS10_SUBCAPABILITY
six_ghost_capabilities: CANDIDATE_FINDING_NEEDS_NAMES_AND_EVIDENCE
qclaw_orphan_scan_artifact: NOT_FOUND_IN_PUBLIC_REPOSITORY
codex_d0_verification: REQUIRED
runtime_changes: NOT_AUTHORIZED_BY_THIS_DECISION
live_trading: PROHIBITED
```
