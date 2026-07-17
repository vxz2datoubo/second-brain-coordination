# 技能T+1修正 — 变更前状态快照
# 日期: 2026-07-09
# 目的: 记录被修改的7个技能在添加T+1规则之前的关键内容，
#       以便将来需要还原时可以参考。

---

## 1. supply-test (最高优先级)
**文件**: `C:\Users\Administrator\.workbuddy\skills\supply-test\SKILL.md`
**变更前状态**: 没有T+1相关内容。核心逻辑"缩量回落=通过"中，"缩量下跌=没人卖"的结论未考虑T+1下卖方池被人为压缩的因素。
**缺少的要素**:
- 卖方池=昨日换手盘+长期持有者，不包括今日买方
- 低成交量可能部分来自T+1卖方池约束，非纯供应枯竭
- 急落矩阵中的"震仓陷阱"未区分T+1卖方池限制

---

## 2. money-flow-divergence (高优先级)
**文件**: `C:\Users\Administrator\.workbuddy\skills\money-flow-divergence\SKILL.md`
**变更前状态**: 背离判定规则直接套用西方CMF逻辑。
- "价格创新高但CMF创新低=主力在借拉高出货(Distribution)" — 此结论在T+1下不成立，因今日买方被锁定无法出货
- 未区分CMF下降是"昨日买方离场"还是"今日新买方减少"
- 未将昨日换手率纳入CMF解读

---

## 3. accumulation-detection (高优先级)
**文件**: `C:\Users\Administrator\.workbuddy\skills\accumulation-detection\SKILL.md`
**变更前状态**: 吸筹量估算直接使用成交量乘以百分比。
- "净流入占比约30%=约30亿筹码被主力吃入" — 未考虑这30亿买方今日被锁定，次日才释放为卖方
- Phase各阶段成交量解读未区分被锁定的换手 vs 真正的吸收
- 无"今日吸收需次日验证"的滞后确认机制

---

## 4. phase-c-d-transition (高优先级)
**文件**: `C:\Users\Administrator\.workbuddy\skills\phase-c-d-transition\SKILL.md`
**变更前状态**: 四要素判定中第四条"成交量萎缩/LB<1.5"未与T+1关联。
- 过渡K线的缩量可能部分来自前日换手率低(卖方池本就小)
- 无过渡K线"次日开盘验证"(昨日买方在过渡日被锁定，次日可能离场)

---

## 5. lps-upthrust-breakout (高优先级)
**文件**: `C:\Users\Administrator\.workbuddy\skills\lps-upthrust-breakout\SKILL.md`
**变更前状态**: LPS量化判定矩阵完全基于成交量比例，未考虑T+1。
- "回踩量<SOS突破量的60%" — SOS突破中的买方被T+1锁定，无法在回踩中卖出，导致回踩量系统性偏低
- 判定阈值(0.4/0.6/0.8)在A股需要更宽松的解读

---

## 6. imbalance-detection (中优先级)
**文件**: `C:\Users\Administrator\.workbuddy\skills\imbalance-detection\SKILL.md`
**变更前状态**: 单K失衡分析中，外盘vs内盘对比未考虑结构性不对称。
- 外盘(主动性买)=全量参与者
- 内盘(主动性卖)=仅昨日换手盘+长线持有者(被T+1限制)
- 因此外盘>内盘在A股是结构性常态，OFI公式天然偏正

---

## 7. a-stock-trading-hours (高优先级)
**文件**: `C:\Users\Administrator\.workbuddy\skills\a-stock-trading-hours\SKILL.md`
**变更前状态**: 只有交易时间信息，没有T+1规则。
**缺少的要素**:
- T+1规则本身
- 卖方池受限的核心推导
- 卖出者判断铁律
- T+1相关的禁用错误推论("今天追高的人在恐慌出逃"="今天买入者不能卖！")
