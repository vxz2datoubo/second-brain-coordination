# A股赌场优势启发的生存、容量与运营控制研究可信度矩阵 v1.0

> module_id: `A-SHARE-HOUSE-EDGE-SURVIVAL-AND-OPERATING-CONTROL-0018`
>
> status: `RESEARCH_MATRIX_COMPLETE / IMPLEMENTATION_NOT_VALIDATED`
>
> boundary: `research_only / NO_TRADE`

## 1. 研究结论摘要

赌场长期经营的可信核心不是“每次都赢”，而是：已知规则下的正优势、大量试验、赌注上限、资本准备、审计和游戏保护。交易系统可以迁移这些治理思想，但不能迁移“固定赔率”和“稳定日盈利”的结论。

A股实现必须增加：概率和收益分布不确定性、成本与冲击、相关性、厚尾、优势衰减、拥挤、T+1、涨跌停、停牌和不可退出。

## 2. A_STRONG：强证据，可作为原则或官方控制事实

### A1. Kelly长期增长原则

来源：J. L. Kelly Jr., 1956, *A New Interpretation of Information Rate*, Bell System Technical Journal.

支持：在概率和赔率已知等理想条件下，最大化期望对数财富可得到长期资本增长准则。

不支持：市场概率已知、Full Kelly适合现实A股、可以忽略参数误差和厚尾。

### A2. 赌场需要资本准备与最大风险控制

来源：Nevada Gaming Control Board现行Bankroll Formula Information与Regulation 6相关要求。

支持：赌场即使拥有规则优势，也需要按业务和赔付风险维持最低资金准备；优势不能替代资本缓冲。

A股映射：策略需要压力资本、不可退出缓冲和最大暴露门。

### A3. 赌场内部控制与对账是经营基础

来源：Nevada Gaming Control Board Minimum Internal Control Standards、Internal Control Information与合规检查体系。

支持：现金、授权、记录、审计、IT、桌面游戏和体育博彩等均需要成文控制、独立检查和对账。

A股映射：数据、模型、配置、风险门、回放、影子和归因必须可追溯对账。

### A4. 风险破产受优势、资本、最大赌注和分布共同影响

来源：Siu, Chan & Im, 2023, *A Study of Assessment of Casinos’ Risk of Ruin in Casino Games with Poisson Distribution*.

支持：仅看平均house advantage不足以覆盖极端路径，现金流和最大赌注会改变破产风险。

不支持：其Poisson或特定赌场模型可直接用于A股。

### A5. 做市收益必须扣除库存与逆向选择

来源：O'Hara & Oldfield, 1986；Sandås, 2001；Bollen, Smith & Whaley, 2004；Liu & Wang, 2016；Guéant, Lehalle & Fernandez-Tapia, 2011/后续研究。

支持：价差收入不是免费优势，库存风险、信息不对称、竞争、成本和逆向选择是核心扣减项。

A股映射：任何“高频、小利、多次”的赌场式叙事必须先扣除这些损失。

## 3. B_TRANSFER_REQUIRED：可信研究，但必须完成A股迁移验证

### B1. House advantage随总投注额显现

来源：Ethier & Stefanello, *Long-term behavior of casino games*（2025预印本，2026 UNLV会议展示）。

可信度：理论方向较强，但新近研究且赌场条件与市场不同。

A股迁移条件：优势稳定、条件期望受控、依赖结构明确、成本和容量未反转。

### B2. House edge与hold/游戏时长关系不是简单线性

来源：Lucas & Singh, UNLV Gaming Research & Review Journal相关模拟研究。

支持：玩家停止规则、买入、波动和游戏结构会使短中期经营结果偏离简单house-edge直觉。

A股映射：策略持有期、退出规则、样本选择和资金路径会影响优势显现。

### B3. 博彩公司平衡账本降低方差但可能牺牲利润

来源：Arscott, 2022, *Risk management in the shadow economy: Evidence from the sport betting market*.

支持：book balancing可作为均值-方差权衡，而不是免费提高收益。

A股映射：对冲、行业中性或因子中性必须重算净期望、基差和成本。

### B4. Fractional Kelly可降低短期风险

来源：Thorp、MacLean、Ziemba及相关资本增长文献。

支持：Full Kelly在短期可能产生大幅回撤，fractional Kelly以增长换取风险下降。

A股迁移条件：由W11统一实现，0018不得复制配置引擎。

### B5. 监控、游戏保护与独立审计降低运营损失

来源：赌场监管MICS、赌场安全与监控专业文献。

A股映射：适用于数据污染、回测泄漏、模型漂移、异常成交和权限越界；具体阈值需本地验证。

## 4. C_ENGINEERING_HYPOTHESIS：工程假设，尚未被A股验证

1. `net_edge_interval`下界门比单点净期望更稳健；
2. 有效独立次数可以显著降低过度自信和过度扩张；
3. “开桌/限额/关桌”状态机能减少策略优势衰减后的损失；
4. 运营损失准备能够改善回测到影子的可解释差异；
5. 0018与W11联合优于单独Kelly或简单风险门；
6. 赌场式最大赌注框架可映射为多层暴露上限；
7. 游戏保护指标可提前识别拥挤和逆向选择。

这些假设必须通过多时期点时回测、对抗测试和影子运行验证。

## 5. REJECTED_UNSUPPORTED：明确拒绝

- “赌场稳定盈利，因此交易系统也可以稳定盈利”；
- “交易次数越多越接近盈利”；
- “高胜率就是house edge”；
- “低波动或高Sharpe就是固定优势”；
- “马丁格尔、亏损加倍或补仓能创造期望”；
- “多只股票或多个策略名称等于独立试验”；
- “Full Kelly在A股是默认最优”；
- “赌场监管资本公式可直接计算交易资本”；
- “价差或手续费返还天然构成正优势”；
- “短期连续盈利证明优势稳定”；
- “回测理论成交可以替代实际可执行成交”；
- “任何模型可以自行修改W7/W11或自动交易”。

## 6. A股适配可信度门

任何研究结论只有同时满足以下条件，才可进入候选：

1. 数据和字段点时可得；
2. 规则按生效日版本化；
3. T+1、涨跌停、停牌和不可退出已模拟；
4. 成本、滑点、冲击和容量已扣除；
5. 相关性和有效次数已处理；
6. 概率和收益分布已校准；
7. 多时期样本外和最终锁箱通过；
8. 负面结果和失效状态完整保留；
9. 影子结果与回测可对账；
10. GPT完成AMED七门审核。

## 7. 当前可信度结论

- 赌场经营原则可作为风险和运营治理参考：`HIGH`；
- Kelly、风险破产、最大暴露和内部控制理论：`HIGH_WITH_ASSUMPTIONS`；
- 博彩/做市方法迁移到A股：`MEDIUM_TRANSFER_REQUIRED`；
- 0018具体净优势门、有效次数和关停阈值：`UNKNOWN_NOT_BACKTESTED`；
- 稳定盈利或实盘有效性：`NOT_ESTABLISHED`。
