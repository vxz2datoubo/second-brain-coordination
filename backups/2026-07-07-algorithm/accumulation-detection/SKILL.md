# accumulation-detection Skill

name: accumulation-detection
description: >
  主力吸筹检测。威科夫五阶段吸筹识别 + Volume Profile 吸筹量估算。
  触发词: 吸筹 / accumulation / Wyckoff Phase / 主力建仓 / 机构吸货 /
  POC / 筹码收集 / 蓄力 / Cause Building / 弹簧 / Spring。

## 威科夫吸筹五阶段 (Wyckoff Accumulation Phases A-E)

> 来源: Richard Wyckoff (1931), 完整方法论

```
Phase A: 止跌       Phase B: 蓄力       Phase C: 震仓
PS → SC → AR → ST    区间震荡吸筹       Spring → Test → SOS
(卖压枯竭确认)      (机构慢慢吃)       (假跌破清洗→确认)
    ↓                    ↓                    ↓
  "跌不动了"          "在偷偷买"          "洗掉最后的不坚定者"

Phase D: 趋势确认    Phase E: 主升浪
SOS → LPS           Markup ↑↑↑
(突破+回踩确认)      (起飞)
```

## 各阶段识别特征

| 阶段 | 价格 | 成交量 | 时间跨度 | 关键事件 |
|:--|:--|:--|:--|:--|
| Phase A | 跌势放缓, SC后反弹 | SC高量, ST低量 | 1-3天 | PS/SC/AR/ST |
| Phase B | 区间震荡,无明确趋势 | 不规���(erratic) | 数周~数月 | 多次ST, 确立区间 |
| Phase C | 假跌破(Spring) | Spring放量, Test缩量 | 1-3天 | Spring/Test/SOS |
| Phase D | 突破+回踩 | SOS放量, LPS缩量 | 1-5天 | LPS形成更高低点 |
| Phase E | 持续上涨 | 正常放量 | 数周+ | 趋势确立 |

## 吸筹量估算 — Volume Profile 三工具

### 1. POC (Point of Control / 控制点)
- 定义: 交易区间内成交量最大的单一价格
- 含义: 机构建仓成本的核心位置
- 估算: POC附近的成交量 = 区间内最大筹码集中区

### 2. Value Area (价值区域)
- 定义: 涵盖70%成交量的价格区间 (VAH→VAL)
- 含义: 大部分筹码的成本范围
- 估算: VA内总成交量 = 约70%的区间累积量

### 3. Cause Building (因的构建)
- 威科夫因与果法则: 横盘时间 ∝ 后续涨幅
- 估算: 横盘天数 × 日均成交量 = 总吸筹量估算
- 经验: 横盘越久, 筹码越集中, 后续涨幅越大

## 昆仑当前吸筹阶段判定

基于今天(7/7)数据:

| 判断维度 | 证据 | 判定 |
|:--|:--|:--|
| 前期趋势 | 6/11-6/18 从36.65→43 (Spring), 后续盘整 | ✓ 已完成Phase C |
| Spring | 6/11 最低36.65, 之后反弹至43 | ✓ Spring完成 |
| 46区测试 | 今天两次测试46回落, 缩量 | ✓ 处于Phase D |
| SOS | 尚未出现 | ⚠️ 等待放量突破46 |
| LPS | 回踩44.89→45.57→45.09, 缩量 | ✓ 在形成LPS |

**当前: Phase D → 等待SOS确认**

吸筹量估算:
- 吸筹区间: 38-46 (5/25至今约6周)
- POC (控制点): ~42.0 (6月份成交量密集区)
- Value Area: 40-44 (70%成交量区间)
- 横盘6周 × 日均40万手 = 约100亿总吸筹量
- 主力比例估算: 净流入占比约30% = 约30亿筹码被主力吃入

## 学术与实战参考
- Wyckoff, R. "Studies in Tape Reading" (1910) — 原版方法论
- Pruden, H. "The Three Skills of Top Trading" (2007) — Wyckoff系统化
- Volume Profile 方法论 — Steidlmayer "Markets and Market Logic" (1984)
- Volume by Price — Chicago Board of Trade Market Profile
