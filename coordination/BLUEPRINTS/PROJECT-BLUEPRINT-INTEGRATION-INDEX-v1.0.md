# 第二大脑与A股交易系统项目蓝图集成索引 v1.0

> `agent_id: GPT`
>
> 状态：公开安全协调索引，不替代本地受保护的三份权威总蓝图正文。
>
> 边界：`research_only / NO_TRADE`

## 一、用途

本文件解决“专项蓝图已经进入GitHub，但是否已成为整体系统正式组成部分”的索引问题。

它负责：

1. 标明各专项蓝图在整体项目中的所属层级；
2. 定义专项蓝图进入整体架构必须满足的接口、依赖、验收和回写要求；
3. 防止专项蓝图成为没有主干引用的孤立文档；
4. 为Codex、WorkBuddy、GPT和QCLAW提供统一入口；
5. 不公开本地受保护总蓝图正文、绝对路径、私人数据或秘密。

## 二、权威层级

### L0：本地受保护权威总蓝图

以下正文不在本公开仓库发布：

- 交易系统权威总蓝图；
- 第二大脑权威总蓝图；
- 交易系统与第二大脑协作机制权威蓝图。

它们是最终架构权威。专项蓝图完成后必须产出“回写差异包”，由用户批准后更新本地受保护正文。

### L1：项目集基础能力层

包括但不限于：

- 时序证据智能基础层；
- 证据账本、来源、版本、冲突和未知项；
- Agent执行反馈v2；
- GitHub任务路由与多Agent协作协议；
- 第二大脑知识云与旧后端兼容迁移架构。

### L2：交易研究核心能力层

- 市场数据、回放、特征、指标、策略、验证和风险；
- A股制度与微观结构模拟；
- 事件、公告、新闻、注意力与舆情；
- 多智能体战略博弈、对手建模和反事实推演。

### L3：专项业务与实验层

- 指标知识地图；
- 世界模型与注意力研究；
- 单标的、板块、事件或策略实验；
- 特定数据源和适配器。

## 三、已登记的多智能体博弈模块

### 模块ID

`A-SHARE-MULTI-AGENT-STRATEGIC-GAME-ENGINE-0001`

### 主蓝图

`coordination/BLUEPRINTS/A-SHARE-MULTI-AGENT-STRATEGIC-GAME-ENGINE-BLUEPRINT-v1.0.md`

### 配套优劣矩阵

`coordination/BLUEPRINTS/A-SHARE-MULTI-AGENT-FAMILY-ADVANTAGE-WEAKNESS-MATRIX-v1.0.md`

### 实施任务

GitHub Issue #23。

### 整体定位

该模块是交易系统的一级研究能力，不是外挂解释器。它位于：

```text
市场数据与事件
→ 统一市场状态与证据层
→ 隐藏类型与策略原型推断
→ 四类参与者多智能体博弈
→ 对手建模与反事实推演
→ 概率情景与验证任务
→ 交易研究决策支持
```

它必须能被第二大脑读取、检索、保存版本和失败经验，但不得由第二大脑或LLM直接生成真实订单。

## 四、四类参与者正式范围

1. 量化策略族；
2. 短线活跃资金族；
3. 大资金与机构库存族；
4. 散户群体族。

每个家族必须拆分为多个策略子类型，并显式建模：

- 目标函数；
- 信息集和信息盲区；
- 资金、库存、容量和执行约束；
- 时间尺度；
- 合理行动集合；
- 在当前约束下最符合其目标的候选行动；
- 结构优势和结构弱点；
- 优势激活、衰减、反转与失效条件；
- 弱点暴露和被利用条件；
- 对其他群体的最佳反应能力；
- 支持证据、反对证据、后验概率和失效条件；
- 身份误判和策略误判风险。

## 五、“合理做法”与“最符合做法”的计算合同

系统不得把“最符合某群体目标的行动”写成故事判断。必须区分：

- `FeasibleActions`：制度、库存、资金、流动性和时间允许的行动；
- `RationalCandidateActions`：在当前信念和目标函数下具有合理性的候选；
- `BestResponseCandidates`：考虑其他群体反应后的候选最佳反应；
- `MostConsistentAction`：与当前观察证据最一致的行动假设；
- `RobustAction`：在多个反情景下仍相对稳健的行动；
- `InvalidOrBlockedActions`：因T+1、涨跌停、停牌、容量、成本或证据不足而不可行的行动。

每项候选必须包含：效用分解、成本、成交概率、冲击、风险、对手反应、置信度、反证和失效条件。

## 六、动态优劣与可利用性输出

每次推演必须输出：

- `ActiveAdvantages`；
- `ExposedWeaknesses`；
- `ExploitabilityMap`；
- `MisclassificationMatrix`；
- `BestResponseSet`；
- `CounterScenarioSet`；
- `NextObservableValidationSignals`。

优势与弱点不得作为固定标签。它们必须随市场阶段、流动性、拥挤度、事件、库存、时间尺度和A股制度动态激活或失效。

## 七、进入整体系统的强制接口

Issue #23首轮计划必须明确映射：

1. 现有实时数据、历史回放和数据质量事件；
2. 指标知识地图与FeatureSet；
3. 竞价、连续竞价、涨跌停、T+1、停牌和跨日库存；
4. 新闻、公告、事件、注意力和舆情；
5. 第二大脑证据、版本、冲突、未知项和检索；
6. 交易验证、成本、滑点、容量、样本外和walk-forward；
7. 风险、权限和NO_TRADE门禁；
8. GPT、Codex、WorkBuddy、QCLAW的职责边界。

## 八、Issue #23新增强制交付

除Issue #23现有交付外，必须增加：

- `OVERALL-BLUEPRINT-INTEGRATION-MAP.md`；
- `PROTECTED-BLUEPRINT-BACKWRITE-PACKAGE.md`；
- `BLUEPRINT-MANIFEST-DELTA.yaml`；
- `CAPABILITY-DEPENDENCY-GRAPH.yaml`；
- `RATIONAL-AND-BEST-RESPONSE-ACTION-CONTRACT.yaml`；
- `SYSTEM-OF-RECORD-AND-DATA-FLOW-MAP.md`；
- `INTEGRATION-ACCEPTANCE-GATES.yaml`。

其中 `PROTECTED-BLUEPRINT-BACKWRITE-PACKAGE.md` 只描述应向三份本地权威总蓝图增加、修改或引用的章节，不得把受保护正文复制到公开仓库。

## 九、集成验收门禁

专项模块只有同时满足下列条件，才可标记为“已进入整体蓝图”：

1. 在本索引登记模块ID、主蓝图、依赖和实施Issue；
2. 产出整体接口与数据流映射；
3. 产出本地权威总蓝图回写差异包；
4. 产出机器可读能力和依赖图；
5. 产出验证、风险、权限、回滚和未知项；
6. GPT验收后合并公开安全交付；
7. 用户批准本地受保护总蓝图回写；
8. 完成回写后登记版本或哈希变化，不公开正文。

在第7项完成前，状态必须是：

`SPECIALIZED_BLUEPRINT_REGISTERED / PROTECTED_MASTER_BACKWRITE_PENDING`

## 十、当前状态

```yaml
module_id: A-SHARE-MULTI-AGENT-STRATEGIC-GAME-ENGINE-0001
specialized_blueprint: COMPLETE
advantage_weakness_matrix: COMPLETE
github_registration: COMPLETE
implementation_issue: 23
implementation_status: QUEUED
public_integration_index: COMPLETE
protected_master_blueprint_backwrite: PENDING
runtime_engine: NOT_IMPLEMENTED
validation: NOT_STARTED
boundary: research_only / NO_TRADE
```

## 十一、执行顺序

1. 完成并验收旧第二大脑后端Phase C；
2. 将Issue #23设为Codex活动任务；
3. Codex先做真实系统审计和自包含项目计划；
4. GPT验收计划后再拆规则型MVP、仿真器、推断、对手建模和验证子任务；
5. WorkBuddy承担真实数据接线、部署和运行态验证；
6. 通过影子模式和样本外验证前，不进入真实交易路径。
