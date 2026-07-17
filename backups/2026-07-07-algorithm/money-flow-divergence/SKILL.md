# money-flow-divergence Skill

name: money-flow-divergence
description: >
  Chaikin Money Flow (CMF) 资金流价格背离分析。触发词: money flow / CMF / 资金流背离 /
  净流入偏差 / 主力资金背离 / Chaikin / Marc Chaikin / 买盘压力。持续跟踪净流入与价格关系，
  发现资金面与价格面的偏差来预判阻力。

## 核心概念: 资金流与价格的背离

### 你的发现是正确的

> 价格回升，净流入走同样价格的幅度是否一致 → 偏差值 = 卖方力量

这恰好是 Marc Chaikin 发明的 **Chaikin Money Flow (CMF)** 指标的核心逻辑。学术界称为 **Money Flow Divergence** 或 **Order Flow Imbalance**。

### CMF 公式 (Chaikin, 1980s)

```
Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
  → 范围 -1 到 +1
  → +1 = 收盘在最高 = 全部买入压力
  → -1 = 收盘在最低 = 全部卖出压力

Money Flow Volume = MFM × Volume

CMF(20) = Σ(MF Volume, 20根bar) / Σ(Volume, 20根bar)
  → CMF > 0 = 买方主导 (Accumulation)
  → CMF < 0 = 卖方主导 (Distribution)
  → CMF > +0.25 = 强买入
  → CMF < -0.25 = 强卖出
```

### 背离判定规则

**看跌背离 (Bearish Divergence):**
- 价格创新高，但 CMF 创新低
- = 价格上升时，资金流在减弱
- = 主力在借拉高出货 (Distribution)
- 胜率 ~64%, R:R 1:2-1:3

**看涨背离 (Bullish Divergence):**
- 价格创新低，但 CMF 创新高
- = 价格下跌时，资金在悄悄流入
- = 主力在低位吸筹 (Accumulation)
- 胜率 ~63%

### 实盘应用: 结合供应测试

当盘中出现以下组合 = 最高置信度信号:
1. 供应测试通过 (缩量回落) ✓
2. CMF 看涨背离确认 (价格回踩低点，CMF在高位) ✓
3. 成交量确认 (回踩量缩至前期30%以下) ✓

→ SOS 信号, 强烈买入

### CMF负值的三种可能原因 — 必须结合其他数据判断

单独CMF为负无法区分以下三种情况:

| 情况 | CMF | 供应测试 | 量价剖面 | 判断 |
|:--|:--|:--|:--|:--|
| 主力抛压测试 | 负 | ✅ 缩量回落 | 站在支撑层上 | 🟢 虚惊, 测试中吸筹 |
| 真实派发 | 负 | ❌ 放量回落 | 跌破支撑层 | 🔴 危险, 真出货 |
| 正常获利回吐 | 负→正 | 进行中 | 支撑未破 | 🟡 观望, 等CMF翻正 |

**今天昆仑案例:**
- CMF = -0.209 (负, 卖压)
- 供应测试 = 未触发 (振幅衰竭, 缩量中)
- 量价剖面 = S2强支撑 (44.5-45, 9.6%)

→ 判断: 46附近有获利盘在出 (正常), 但支撑稳固 + 缩量 = 偏 🟡 等待CMF翻正或第三次供应测试通过

### 学术支撑

- Chaikin, M. "Chaikin Money Flow" (1980s) — 原始指标发明
- Chordia, Roll, Subrahmanyam "Order Imbalance, Liquidity, and Market Returns" (JFE 2002)
  — 订单流不平衡与收益率关系的奠基论文
- Easley, Kiefer, O'Hara, Paperman "Liquidity, Information, and Infrequently Traded Stocks" (JF 1996)
  — PIN模型, 信息不对称与资金流向
- Cont, Kukanov, Stoikov "The Price Impact of Order Book Events" (JFM 2014)
  — 订单流对价格的冲击模型
- Biais, Hillion, Spatt "An Empirical Analysis of the Limit Order Book" (JF 1995)
  — 限价订单簿的实证分析

### 盘中监控命令
```bash
python medallion_bridge/flow_divergence.py 300418 --cmf --divergence
```
