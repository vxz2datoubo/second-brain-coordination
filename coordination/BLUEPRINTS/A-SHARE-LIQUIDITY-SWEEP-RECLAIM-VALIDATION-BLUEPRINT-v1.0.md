# A股扫流动性、收复、稳定与T+1验证技能蓝图 v1.0

> module_id: `A-SHARE-LIQUIDITY-SWEEP-RECLAIM-VALIDATION-0017`
>
> workstreams: `W4 Feature/Strategy Research + W7 Validation`, consuming `W2/W5/W13`
>
> implementation_issue: `#69`
>
> status: `REGISTERED_CANDIDATE / NOT_IMPLEMENTED / NOT_BACKTESTED`
>
> boundary: `research_only / NO_TRADE`

## 0. 结论

旧工程已经存在关键价位、流动性状态、突破/反转、T+1、成本和样本外验证碎片，但没有一个统一技能把以下问题连接起来：

1. 参考区必须在事件前定义；
2. 价格穿越必须用可观察数据描述；
3. 收复、失败、延续和稳定必须成为不同标签；
4. “承接”不能在BAR_ONLY或普通五档能力下冒充真实吸收；
5. T+1库存和不可退出必须进入事件标签与收益验证；
6. 任何参数和组合必须通过多时期样本外验证。

本模块不是“主力扫止损识别器”，而是一个**参考区穿越、价格收复、事后稳定、执行约束和验证编译层**。

## 1. 第一原则

### 1.1 可观察事实与叙事分开

系统可以观察：

- 某个事前定义价位被穿越；
- 穿越幅度、持续时间和速度；
- 成交量、波动率、价差或显示深度的变化；
- 价格是否重新进入参考区；
- 收复是否保持；
- 次日是否可卖、是否遇到涨跌停或停牌。

系统不能仅凭这些事实确认：

- 隐藏止损簇真实存在；
- 某个主体故意“扫流动性”；
- 主力、机构或游资真实身份；
- 隐藏流动性、真实吸收或订单队列；
- 之后必然反转或盈利。

### 1.2 名称降级规则

首版输出优先使用：

- `REFERENCE_ZONE_BREACH`
- `EXTREME_EXCURSION_EVENT`
- `SWEEP_CANDIDATE`
- `RECLAIM_CANDIDATE`
- `POST_SWEEP_STABILIZATION`

`LIQUIDITY_SWEEP_CONFIRMED`不是BAR_ONLY、L1快照或供应商聚合数据可以达到的状态。

## 2. 与旧资产的合并关系

D0必须审计并合并：

- Issue #42资金意图多周期证据蓝图中的价格结构、能力门和验证碎片；
- `A-SHARE-INDICATOR-KNOWLEDGE-MAP-0016`中的关键价位、突破、波动和参数候选；
- W2的点时行情、A股规则快照和回放；
- W7的样本外、过拟合、成本和风险门；
- W13的参与者资金证据，但只能作为独立上下文，不能反向证明主体身份；
- PR、Issue和可访问本地资料中的旧`sweep/reclaim/absorption/false-breakout`候选。

每个旧组件只能被分类为：

`REUSE / ADAPT / MIGRATE / REFERENCE_ONLY / DEPRECATE / NEW_CANDIDATE`。

## 3. 数据能力矩阵

| 能力 | 可研究 | 禁止声称 |
|---|---|---|
| `BAR_ONLY` | 参考区、穿越、收复、持续、波动和成交量状态 | 订单方向、吸收、止损簇、隐藏流动性、主体身份 |
| `L1_SNAPSHOT` | 显示价差、显示深度和快照变化 | 委托队列、连续撤单、真实OFI、真实吸收 |
| `L2_AGGREGATE` | 语义版本明确的供应商聚合字段 | 原始逐笔成交、逐笔委托、单笔撤单 |
| `RAW_TRADE_TICK` | 真实成交序列、成交方向分类误差研究 | 未提供的委托、撤单、队列、账户身份 |
| `RAW_ORDER_EVENT` | 委托、撤单、队列和真实OFI研究 | 经济动机和主体身份确定性 |

### 3.1 明确禁止的输入

- DDX、DDY及其变体；
- OHLCV推导并冒充真实Delta/CVD/OFI；
- 把内外盘或供应商资金流当作真实主动买卖；
- 把`L2TicNum/L2OrderNum/BCancel/SCancel`重命名为逐笔事件；
- 没有`available_at`和语义版本的历史字段。

## 4. 参考区本体

`ReferenceLiquidityZone`必须在事件发生前冻结，并记录：

- `zone_id`；
- `zone_type`；
- `lower_bound / upper_bound`；
- `defined_at / available_at`；
- `source_timeframe`；
- `lookback_window`；
- `construction_method`；
- `rule_snapshot_id`；
- `data_capability`；
- `expiration_rule`；
- `selection_provenance`。

候选参考区包括：

- 前一交易日高低点；
- 点时可知的N日摆动高低点；
- 开盘区间；
- 已完成bar形成的局部极值区；
- 实际成交数据计算的VWAP或Volume Profile区域；
- 涨跌停价和制度边界；
- 预先登记的整数/价格聚集候选。

禁止使用事后最优高低点或未来成交数据构建参考区。

## 5. 事件状态机

```text
ZONE_ACTIVE
→ APPROACH
→ REFERENCE_ZONE_BREACH
→ EXTREME_EXCURSION
→ INTRABAR_REENTRY
→ BAR_CLOSE_RECLAIM
→ SUSTAINED_RECLAIM
→ POST_SWEEP_STABILIZATION

并行失败路径：
→ FAILED_RECLAIM
→ CONTINUATION_AFTER_BREACH
→ LIMIT_LOCK / SUSPENSION / DATA_INVALID / ABSTAIN
```

### 5.1 穿越事件

`ReferenceZoneBreachEvent`至少记录：

- 方向；
- 首次穿越时间；
- 最大穿越幅度；
- 相对ATR/波动率标准化幅度；
- 穿越持续时间；
- 事件内成交量和波动；
- 大盘、行业和同类股票控制；
- 是否接近涨跌停；
- 数据质量和能力等级。

### 5.2 收复

必须区分：

- `INTRABAR_REENTRY`：bar内返回；
- `BAR_CLOSE_RECLAIM`：确认bar收回；
- `SUSTAINED_RECLAIM`：后续多个bar保持；
- `FAILED_RECLAIM`：重新失守；
- `CONTINUATION_AFTER_BREACH`：穿越后继续同向。

### 5.3 承接与稳定

在没有真实订单事件时，不使用`ABSORPTION_CONFIRMED`。可输出：

- 回撤收窄；
- 再次测试不创新低/新高；
- 收复保持时间；
- 波动衰减；
- 成交量与价格响应关系；
- 相对市场/行业的稳定；
- 有及时五档时的显示深度候选。

统一对象为`PostSweepStabilizationAssessment`。

## 6. T+1库存模型

`TPlusOneInventoryState`至少包括：

- `trade_date`；
- `quantity`；
- `settled_quantity`；
- `sellable_quantity`；
- `frozen_quantity`；
- `already_sold_quantity`；
- `round_trip_eligible`；
- `overnight_gap_exposure`；
- `limit_down_lock_state`；
- `suspension_state`；
- `rule_snapshot_id`。

验证必须区分：

1. 已有可卖库存上的减仓/回补研究；
2. 当日新买库存不可卖；
3. 次日开盘跳空；
4. 次日跌停或停牌无法退出；
5. 不同证券类型的回转交易资格。

不得用一个全局`T_PLUS_ONE=true`代替lot-level库存。

## 7. 与其他技能联动

- **W2**：提供点时行情、规则快照和回放；
- **W4**：拥有参考区、事件标签和研究候选；
- **W5/PMN**：标注同期政策、公告和突发事件，防止把新闻冲击误写为纯技术结构；
- **W7**：拥有样本外、成本、过拟合和风险门；
- **W9**：影子运行与结果校准；
- **W10**：DecisionEpisode记录当时证据和弃权；
- **W11**：只有通过验证的概率分布可被只读消费，0017不直接定仓；
- **W13**：参与者活动只作为外部上下文和交互项，不作为扫流动性的身份确认。

## 8. 参数与实验族

每个`SweepReclaimExperimentFamily`必须登记：

- 参考区家族；
- 穿越阈值；
- 确认窗口；
- 收复保持窗口；
- 波动和成交量过滤；
- 市场/行业控制；
- 持有期；
- 搜索空间和试验总数；
- 训练、验证、锁箱和影子时期；
- 成本、容量和规则版本；
- 失败、无效和被拒参数。

禁止挑选单一最佳参数后只展示其结果。

## 9. 第一纵向切片

`0017-VS1 BAR-ONLY REFERENCE-ZONE BREACH AND RECLAIM`

输入仅限：

- 点时分钟/日线bar；
- 指数和行业bar；
- 版本化规则；
- lot-level T+1库存模拟；
- 事件/公告排除或分层标签。

输出：

- 参考区；
- 穿越与收复标签；
- 稳定/失败/延续标签；
- 次日可交易性；
- MFE/MAE与多期限结果；
- 数据质量和弃权。

首版不允许使用订单流、DDX、参与者身份或自动交易。

## 10. 成功标准

1. 旧候选被合并而非复制；
2. 参考区和标签可以点时确定性重放；
3. 不存在虚假订单流或身份语义；
4. T+1、涨跌停和不可退出进入第一类对象；
5. 与简单突破、反转、随机价位和波动冲击基线比较；
6. 多时期、多状态样本外结果完整保留；
7. 无增量和反向结果可见；
8. 通过GPT AMED七门审核前不升级成熟度。
