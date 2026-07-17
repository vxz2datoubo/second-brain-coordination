# 技能T+1修正 — 变更日志
# 日期: 2026-07-09  变更人: 迪迪
# 触发事件: 分析昆仑今日走势时，错误认为"今天追高的人在卖出"，
#           大头指出A股T+1规则——今日买入者当日无法卖出。
# 修正范围: 18个交易相关技能全量审查，实际修改7个。

---

## 变更摘要

| 技能 | 修改类型 | 插入位置 | 核心修正 |
|:--|:--|:--|:--|
| supply-test | 新增T+1段落 | "急落vs缓落矩阵"之前 | 缩量回落=通过→需区分T+1结构性缺卖方 vs 真正供应枯竭 |
| money-flow-divergence | 修改背离判定+新增T+1段落 | "背离判定规则"处 | CMF看跌背离不能简单归因于"主力出货"→是"昨日买方离场" |
| accumulation-detection | 新增T+1段落 | "昆仑当前吸筹阶段判定"之前 | 吸筹量需次日DDY验证，今日买家明日才释放为卖方 |
| phase-c-d-transition | 修改要素4+新增要素5 | 第20行 | 缩量需对比前日换手率；新增T+1验证(次日开盘不破过渡K线低点) |
| lps-upthrust-breakout | 修改量化判定矩阵 | LPS量化表 | 比例阈值需T+1宽松解读(SOS买方被锁，LPS回踩卖方池天然小) |
| imbalance-detection | 新增T+1注释 | 第一层单K失衡处 | 外盘>内盘在A股是结构性的(卖方池受限)，OFI阈值需上调 |
| a-stock-trading-hours | 新增T+1规则章节 | "常犯错误"之前 | 新增T+1铁律、卖方池推导、三个禁用推论 |

---

## 逐技能变更详情

### 1. supply-test (最高优先级)
**影响**: 核心逻辑修正——"缩量=没人卖"需要区分两种"没人"：T+1锁仓导致的结构性缺卖方 vs 真正的供应枯竭

**新增内容**:
```
🔴 T+1 核心修正 (A股特有)
- 卖方池推导: 卖方=昨日换手盘+长期持有者，不含今日买方
- "缩量回落=通过"修正: 缩量可能部分来自T+1约束
- 修正判定规则: 回踩量应对比昨日换手量(今日可卖池子)
  - 回踩量<昨日换手量30%→真正供应枯竭(强信号)
  - 回踩量在30-60%→混合信号
  - 回踩量>60%→昨日买家大量离场(弱信号)
- 急落矩阵T+1修正: 急落+低量也可能是T+1压缩卖方池
```

---

### 2. money-flow-divergence (高优先级)
**影响**: 看跌背离结论从"主力出货"修正为"昨日买方离场"，因T+1下今日买方无法出货。

**修改前**:
```
看跌背离: 价格创新高，但CMF创新低 = 主力在借拉高出货(Distribution)
```

**修改后**:
```
🔴 T+1修正版:
- 不能归因于"主力借拉高出货"——今日买方被T+1锁定
- 正确解读: 卖方来自昨日换手盘，CMF下滑=昨日买方在获利了结
- 需结合昨日换手率: 高换手+CMF降→真警示; 低换手+CMF微降→虚惊
```

---

### 3. accumulation-detection (高优先级)
**影响**: 吸筹量估算需要次日DDY验证，当日"吸收"可能含被锁定的短线客。

**新增内容**:
```
🔴 T+1 核心修正
- 真实吸收量≈净买入×(1-次日卖出意愿%)
- Phase表各阶段T+1修正:
  - Phase A: SC买方被锁→次日无大量卖出=确认卖压枯竭
  - Phase C: Spring买方被锁→Test缩量来自"选择持有"=更强
  - Phase D: SOS买方明日可变卖方→LPS质量取决于离场比例
```

---

### 4. phase-c-d-transition (高优先级)
**影响**: 过渡K线信号强度需前日换手率校准。

**修改**:
```
要素4修正: 缩量+前日高换手(>8%)=真正供应枯竭✅
           缩量+前日低换手(<5%)=可信度打折
新增要素5: T+1验证——过渡K线次日开盘不破过渡K线低点
```

---

### 5. lps-upthrust-breakout (高优先级)
**影响**: LPS回踩量比例阈值在A股需宽松解读。

**修改前**: 四个比例阈值直接判定
**修改后**: 添加T+1注释列，说明卖方池天然偏小导致的阈值偏移

---

### 6. imbalance-detection (中优先级)
**影响**: OFI和单K失衡需认知A股卖方池结构性偏小的底座。

**新增内容**:
```
🔴 T+1修正:
- 外盘(全量)>内盘(受限)=A股结构性常态
- 内盘>外盘的反转信号在A股更强(卖方池受限下仍能压倒买方)
- OFI公式天然偏正，阈值需上调
```

---

### 7. a-stock-trading-hours (高优先级)
**影响**: 从纯交易时间参考升级为涵盖T+1规则的交易框架基础。

**新增**: 完整的T+1规则章节，包含:
- 卖方池推导公式
- 卖出者判断铁律(修正版: 非"昨天买入的人=今天卖出的人"，而是"所有持有者-今日买方")
- 三个T+1禁用错误推论

---

## 未修改的技能 (全审查通过)

以下11个技能T+1合规，无需修改:
- footprint-detection (微观订单流，已合规)
- cause-effect-projection (跨月动量，日内无冲突)
- opening-range (已主动T+1适配，优秀)
- a-share-call-auction (竞价阶段，不适用)
- vwap-analyzer (已主动T+1增强适配，优秀)
- anchoring-detection (行为金融学，不适用)
- hvn-lvn-nodes (结构性分析，不适用)
- market-context (板块对比，不适用)
- delta-cvd (已有完整T+1适配)
- absorption-detection (已有完整T+1适配)
- liquidity-sweep (已有完整T+1适配)

---

## 2026-07-09 新增技能: volume-profile-chip

### 新增文件
- `C:\Users\Administrator\.workbuddy\skills\volume-profile-chip\SKILL.md`

### 内容概要
- Volume Profile (西方) + 筹码分布 (A股) 双框架
- 核心概念: POC/VAH/VAL/HVN/LVN/Naked POC + 单峰/双峰/多峰形态
- 联动8个现有技能: supply-test / absorption / accumulation / cause-effect / opening-range / hvn-lvn / market-context / phase-c-d-transition
- T+1适配: 换手率>8%时筹码精度打折，需DDX/DDY交叉验证
- 昆仑实战: 40-43底仓筹码未松动，50形成新堆积区，健康Phase D
- 来源: Steidlmayer(1985), Quantum-Algo(2026), 东方财富筹码分布指南(2026)

### 联动验证(昆仑7/9)
- Supply Test + POC: 两次回踩在POC下方0.5元停止 ✅
- Absorption + POC: 吸收区完美重叠于POC ✅
- 筹码增强因果目标(保守53, 适中56.5) 与纯因果目标(57.58) 互相验证 ✅

---

## 2026-07-09 新增技能: effort-result-climax

### 新增文件
- `C:\Users\Administrator\.workbuddy\skills\effort-result-climax\SKILL.md`

### 内容概要
- Wyckoff第三定律(Effort vs Result) 量价背离四象限
- 四类背离: 放量滞涨/放量止跌/缩量大涨/缩量大跌
- Phase A四事件: PS/SC/AR/ST 完整识别框架
- 二次测试(ST)量化标准(强/正常/弱三类)
- 联动6个技能: supply-test/absorption/accumulation/phase-c-d/volume-profile/anchoring
- T+1适配: 放量滞涨在A股需DDX方向确认
- 昆仑三个月Phase A追溯: 5月假SC→6月真SC，ST差异是判决书
- 来源: Wyckoff(1910), Villahermosa(2025), TradingView量化指标(2026), EJF学术验证(2024)

### 昆仑实战追溯
- 5/14假SC: ST突破低点→非真吸筹 ❌
- 6/11真SC(耗竭型): AR+17%, ST不破36.65→真底 ✅
- 两套SC的区分: AR质量(0.4% vs 17%) + ST是否破SC低(破了 vs 守住)

---

## 还原方法

如需还原某个技能到变更前状态:
1. 对照上面的"变更前状态快照"文件找到原逻辑
2. 在对应SKILL.md中删除 `🔴 T+1` 标记的段落
3. 对于money-flow-divergence，同时恢复"看跌背离=主力出货"的原结论

所有变更标记为 `🔴 T+1` 或 `T+1修正`，方便搜索定位。
