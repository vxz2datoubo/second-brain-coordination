# anchoring-detection Skill

name: anchoring-detection
description: >
  行为金融学锚定效应检测与纠正。触发词: 锚定效应 / anchoring bias / 心理锚定 /
  参考点 / 卖价锚定 / 成本锚定 / 高估低吸 / 舍不得卖 / 后悔没卖 / 追回去 /
  处置效应 / 鸵鸟效应 / 心理账户 / mental accounting / reference point。

## 核心理论

### 1. 锚定效应 (Anchoring Effect)
> Kahneman & Tversky, Science 1974

**定义**: 决策时过度依赖初始信息("锚点")的认知偏差。即使锚点与当前决策无关，仍会显著影响判断。

### 2. 处置效应 (Disposition Effect)
> Shefrin & Statman, JF 1985; Odean, JF 1998 (7.8万账户实证)

**定义**: 投资者过早卖出盈利股票、过久持有亏损股票的趋势。
Odean 实证：散户卖出赢家概率比卖出输家高**50%**。

### 3. 交易中的四种锚定陷阱

| 陷阱 | 表现 | 学术术语 | 昆仑案例 |
|:--|:--|:--|:--|
| **卖价锚定** | 卖了之后，用卖出价判断"现在贵不贵" | Reference Point Anchoring | 12.57出蓝标→12.42弹就想要回去 |
| **成本锚定** | "我不卖，因为我还没回本" | Disposition Effect | 45.13成本在44不舍得割（今天做了✅） |
| **高点锚定** | "之前到过46，所以应该还能到46" | Peak-End Anchoring | 上午冲过46.07，下午还在等 |
| **转仓锚定** | "我昨天卖了蓝标所以今天不该买回" | Mental Accounting | 卖完后锚定卖出价为"正确价" |

### 4. 破解六法

| 方法 | 操作 | 来源 |
|:--|:--|:--|
| 重置锚点 | 每笔交易当成独立决策，不问"我多少钱买的" | Thaler 1999 |
| 多视角估值 | 用量价剖面、POC替代记忆中的价格 | Chen & Wang 2023 |
| 系统性决策 | 用系统规则替代直觉："卖出后等30分钟再判断" | 自研 |
| 定期重评 | 每30分钟重新判断："现在如果是现金你买吗？" | 论文建议 |
| 反向提问 | "如果我没持仓，看到44.5会买吗？" | 认知干预 |
| 结果范围 | 不锚定单一目标价，用保守/适中/激进三档 | Shiller 2015 |

## 盘中自动检测

系统自动识别以下行为和对应陷阱:

```
用户说"要不要转回蓝标"  → 检测: 卖价锚定 → 自动提醒
用户说"我成本44.61还没回本" → 检测: 成本锚定 → 提醒重置锚点
用户说"以前到过46" → 检测: 高点锚定 → 引用量价数据对照
```

## 学术论文

- Tversky & Kahneman "Judgment under Uncertainty: Heuristics and Biases" (Science, 1974)
- Shefrin & Statman "The Disposition to Sell Winners Too Early and Ride Losers Too Long" (JF, 1985)
- Odean "Are Investors Reluctant to Realize Their Losses?" (JF, 1998)
- Thaler "Mental Accounting Matters" (JBDM, 1999)
- Benartzi & Thaler "Myopic Loss Aversion and the Equity Premium Puzzle" (QJE, 1995)
- Barberis, Shleifer & Vishny "A Model of Investor Sentiment" (JFE, 1998)
- Shiller "Irrational Exuberance" (2015, 3rd ed.)
- Chen & Wang "Anchoring Effect in Chinese Stock Markets" (2023)
