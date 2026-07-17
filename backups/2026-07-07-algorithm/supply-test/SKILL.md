# supply-test Analysis Skill v2

name: supply-test
description: >
  威科夫-VSA供应测试分析。触发词: probing for supply / supply test / 供应测试 / 抛压测试 / 
  试盘 / 威科夫 / Wyckoff / 缩量回落 / 卖方真空 / Spring / SOS。盘中主动监控三次供应测试节奏。

## 完整四步流程: Spring → Supply Test → SOS

```
Step 1: Spring (弹簧)
  价格试探性跌破支撑 → 迅速收复
  → 确认: 卖盘枯竭 ✓

Step 2: 首次拉升
  价格向上离开Spring区域，冲击阻力区
  → 试探上方卖盘量

Step 3: Supply Test (供应测试)
  价格回落，回踩Spring上方区域
  关键: 回落成交量 vs 拉升成交量
  → 缩量回落=通过 ✅ / 放量回落=失败 ❌

Step 4: SOS (Sign of Strength)
  测试通过后，价格放量突破阻力
  → 主升浪开始
```

## 核心原理: 为什么缩量回落=通过？

基于 Wyckoff Law #3 (Effort vs Result):
- 放量下跌 = 大量卖单砸下去的 (Effort=Result) → 卖盘还在 ❌
- 缩量下跌 = 没人卖，只是因为买方暂时撤单 → 卖盘枯竭 ✅

**散户行为实证**: Odean (1998) 分析7.8万散户账户，发现散户在下跌时表现出"鸵鸟效应"——关闭账户不看，而不是冲进去抄底。Chordia/Roll (JFE 2002) 证明缩量下跌说明主动性卖单极少，价格下滑是因为买方暂撤限价单，不是有人在砸。

所以缩量回落时没有人接的原因不是散户不敢接——是根本**没什么人卖**，几笔小单就让价格滑下去了。

## 急落 vs 缓落矩阵

|  | 急落 (快跌) | 缓落 (慢磨) |
|:--|:--|:--|
| 高成交量 | 🔴 真实供应涌入，有人在疯狂出货 | 🟡 钝刀放血，主力悄悄派发 |
| 低成交量 | 🟡 震仓陷阱 — 急跌吓人但无真实供应，目的是收集筹码 | 🟢 供应已枯竭，没人卖了 |

**急落+低量+快速回稳 = 震仓陷阱 (Shakeout)**：
一大单砸下去→后面没跟单→价格快速回弹。主力在低价吸走被吓跑的散户筹码。

## 三次测试跟踪法

每次供应测试需跟踪:

| 测试# | 时间 | 冲击高 | 成交峰值 | 回踩低 | 回踩量 | 衰减率 | 判定 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| T1 | — | — | —手 | — | —手 | — | — |
| T2 | — | — | —手 (应<T1) | — | —手 (应<T1) | — | — |
| T3 | — | — | —手 (应<T2) | — | —手 (应<T2) | — | T3通过=SOS触发 |

T3确认通过标准:
- 冲击量 < 第一轮峰值的60%
- 回踩量 < 第一轮低量的80%
- 回踩最低 > 前两轮回踩均值的+1%
- 回踩后反弹量 < 20K手 (供应真空确认)
- 后续任意一根5分K放量突破冲击高 → SOS ✅

## 实时监控命令

对昆仑/蓝标盘中自动分析:
```bash
python medallion_bridge/supply_tester.py 300418 <price> <high> <low> --detailed
```

## 论文与书籍
- Wyckoff "Studies in Tape Reading" (1910) — 供应测试起源
- Tom Williams "Master the Markets" (2005) — VSA方法论, No Supply/Test信号
- Gavin Holmes "Trading in the Shadow of the Smart Money" (2011) — VSA实战
- Anna Coulling "A Complete Guide to Volume Price Analysis" (2013)
- Chordia, Roll, Subrahmanyam "Order Imbalance, Liquidity, and Market Returns" (JFE 2002)
- Easley, O'Hara "Microstructure and Ambiguity" (JF 2010)
- Odean "Are Investors Reluctant to Realize Their Losses?" (JF 1998) — 散户行为
- Pruden "The Three Skills of Top Trading" (2007) — Wyckoff系统化
