# Phase-C-D-Transition Skill

name: phase-c-d-transition
description: >
  威科夫Phase C→D过渡K线检测。识别缩量十字星+供应测试完成后的转折点。
  触发词: Phase C→D / 缩量十字星 / C→D过渡 / 转折K线 / 供应测试完成 / 
  low volume doji / 蓄力完成 / transition candle。

## 核心定义

Phase C→D过渡标志K线 = 供应测试完成后出现的缩量十字星/小实体K线。

### 必备四要素

| 要素 | 标准 | 今天昆仑 |
|:--|:--|:--|
| 1. 前有Spring | 之前出现过假跌破+快速收回 | ✅ 36.65 (6/11) |
| 2. 当天有供应测试 | 冲高回踩缩量 | ✅ 46→44→44.5 |
| 3. K线实体小 | 开收差<1.5% | ✅ 42.94→44.5 (1.3%) |
| 4. 成交量萎缩 | LB<1.5 且连续2日递减 | ✅ 1.14, 连续3天降 |

### 判定等级

| 评分 | 条件 | 结论 |
|:--|:--|:--|
| 4/4 | 全满足 | ✅ C→D过渡确认 - 明天大概率向上 |
| 3/4 | 缺1项 | ⚠️ 疑似过渡 - 等明天确认 |
| <3 | 不足 | ❌ 不构成过渡信号 |

### 后续走势规律

C→D过渡K线出现后:
- 次日平开+上午放量 → 50%概率当天触发SOS
- 次日低开<1%+30分钟翻红 → 标准LPS，2-3天到目标
- 次日低开>1.5%+30分钟不翻红 → 过渡失败，回到Phase C

## 来源
- Wyckoff "Studies in Tape Reading" (1910): Phase transition volume principles
- Pruden "The Three Skills of Top Trading" (2007): Phase identification
- Villahermosa "Trading Wyckoff 2.0" (2021): Transition patterns
