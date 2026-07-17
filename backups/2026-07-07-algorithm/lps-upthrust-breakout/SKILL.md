# lps-upthrust-breakout Skill

name: lps-upthrust-breakout
description: >
  威科夫突破确认检测。LPS(Last Point of Support)+Upthrust+真假突破判定。
  触发词: LPS / 最后支撑点 / Upthrust / 上冲 / 假突破 / 真突破 / BUEC / SOS确认 /
  突破回踩 / breakout test / 跃过溪流。

## 核心概念

### LPS (Last Point of Support / 最后支撑点)

> 来源: Wyckoff (1931), Rubén Villahermosa "Trading Wyckoff 2.0"

SOS 之后的缩量回踩。是**机构最偏好的买入位置**——比突破点更安全。

**判定三要素:**
1. 回踩量 < SOS突破量的 60%
2. 回踩 K线 ***窄振幅***（范围收缩）
3. 价格**不重新进入交易区间**——即回踩低点 > 区间上沿

```
Valid LPS:    放量突破46 → 缩量回踩46.2 → 弹起 ✅
Invalid LPS:  放量突破46 → 放量回踩45.5 → 弹起 ⚠️ 回踩太深
False LPS:    放量突破46 → 放量回踩44.8 → 跌破 ❌ 不是 LPS，是 Shakeout
```

### 三种 LPS 位置

| 类型 | 位置 | 风险收益比 |
|:--|:--|:--|
| **Spring后 LPS** | 紧随震仓之后 | 最优（最低买入价） |
| **区间内 LPS** | Phase B/C 区间内 | 中等 |
| **区间外 LPS (BUEC)** | 突破后回踩区间上沿 | 次优（确认性最高） |

BUEC = "Back Up to Edge of the Creek" — 突破后重返溪流边缘。

### LPSY (Last Point of Supply / 最后供给点)

派发区间的空头版 LPS。SOW 之后的缩量反弹，然后继续暴跌。

### Upthrust (上冲陷阱)

> 来源: Wyckoff Distribution Phase, Rubén Villahermosa

**定义:** 假突破——价格突破区间上沿，但伴随着：
- 突破后**放量回落**（不是缩量！）
- 价格**重新回到区间内**
- 成交量在回踩时放大 → **有大资金在卖**

**与SOS的区别:**
| | SOS (真突破) | Upthrust (假突破) |
|:--|:--|:--|
| 突破时量 | 大 | 大 |
| 回踩时量 | **小** (<60%) | **大或中等** |
| 回踩振幅 | 窄 | 宽 |
| 是否回区间 | 否（守住上沿） | 是（跌回） |
| 后续 | LPS→Phase E | 回到区间继续或下破 |

### UTAD (Upthrust After Distribution)

派发阶段的终极上冲。出现在长时间派发后，是**最后一次诱多陷阱**。
等价于吸筹阶段的 Spring 的反向——都是清洗反向交易者。

## LPS 量化判定矩阵

| 回踩量/SOS量 | 回踩深度 | 判定 |
|:--|:--|:--|
| < 0.4 | 守在上方 1% 以上 | ✅ 强 LPS — 最佳买点 |
| 0.4-0.6 | 守在上方 0-1% | ✅ 正常 LPS — 可买 |
| 0.6-0.8 | 略破区间上沿 | ⚠️ 弱 LPS — 减仓观察 |
| > 0.8 | 明显跌回区间内 | ❌ Upthrust — 立刻走 |
| 任何 | 跌破区间中位 | ❌ 假突破 — 止损 |

## 学术参考

- Wyckoff, R. "Studies in Tape Reading" (1910)
- Villahermosa, R. "Trading Wyckoff 2.0" (2021) — LPS/SOS 系统化
- Pruden, H. "The Three Skills of Top Trading" (2007)
- Volume Spread Analysis — Tom Williams (2005) — Upthrust 成交量确认

## 昆仑实时应用

SOS触发价 = 46（区间上沿）
监控对象：第三次突破46后的回踩

if 突破46 and 回踩量 < 突破量的60% and 回踩低点 > 45.8:
  → LPS 确认 ✅ → Phase E 开始 → 加仓买入
elif 突破46 and 回踩量 > 突破量的80%:
  → Upthrust 陷阱 ❌ → 全部平仓
