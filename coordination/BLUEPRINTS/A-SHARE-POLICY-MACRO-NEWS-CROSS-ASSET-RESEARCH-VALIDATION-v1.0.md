# A股政策-宏观-消息-跨资产情报研究验证矩阵 v1.0

> module_id: `A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-INTELLIGENCE-0015`
>
> status: `RESEARCH_VALIDATION_COMPLETE / IMPLEMENTATION_NOT_STARTED`
>
> boundary: `research_only / NO_TRADE`

## 1. 证据分级

- `HIGH_TRANSFERABILITY`：方法论稳健，可直接作为系统合同，但参数仍须A股重估；
- `MEDIUM_TRANSFERABILITY`：方向可信，但市场制度、数据和时期差异较大；
- `HYPOTHESIS_ONLY`：可进入候选研究，不得直接成为生产规则；
- `REJECTED_AS_DIRECT_RULE`：不适合直接迁移为A股结论。

## 2. 核心研究映射

| 研究/机构 | 核心结论 | 系统吸收 | A股迁移判断 |
|---|---|---|---|
| Pearce & Roley, stock prices and economic news | 资产价格主要响应公告中未被预期的部分 | 强制`ExpectationSnapshot`和`Surprise`分离 | HIGH_TRANSFERABILITY |
| Rigobon & Sack, monetary policy and asset prices | 普通事件研究受政策和市场同步反应的内生性影响；可利用异方差识别 | 重大政策不得只用简单前后收益差解释因果 | HIGH_TRANSFERABILITY |
| Gürkaynak, Kısacıkoğlu & Wright, Missing Events | 公告包含标题之外的潜在信息；潜在因子可显著提高解释力 | `latent_detail_factor`和多维惊喜 | HIGH_TRANSFERABILITY |
| Cieslak & Schrimpf, BIS non-monetary news | 央行沟通同时传递货币、增长和风险溢价信息 | `policy_information_effect`与跨资产符号分解 | HIGH_TRANSFERABILITY |
| Neuhierl & Weber, Monetary Momentum | 政策会议前后可能存在持续漂移 | 抢跑和漂移作为待验证状态，不直接当泄漏 | MEDIUM_TRANSFERABILITY |
| Brooks, Katz & Lustig, post-policy bond drift | 公告后资金流和缓慢预期调整可造成债券漂移 | 将基金流、供给和注意力列为替代机制 | MEDIUM_TRANSFERABILITY |
| Goldberg & Grisse, time-varying macro news response | 同一宏观消息在不同利率和风险状态下反应不同 | 强制市场状态、政策时期和时变参数 | HIGH_TRANSFERABILITY |
| Morris & Shin, forward guidance feedback | 政策制定者和市场价格互相观察会形成反身性 | 市场隐含预期不得被当作独立真相 | HIGH_TRANSFERABILITY |
| Haddad, Moreira & Muir, conditional policy promises | 政策影响取决于市场对坏状态下后续支持的条件性预期 | `policy_put`和后续承诺可信度 | MEDIUM_TRANSFERABILITY |
| DellaVigna & Pollet, limited attention | 注意力不足会造成较弱即时反应和后续漂移 | 结合W5注意力、发布时间和传播速度 | MEDIUM_TRANSFERABILITY |
| Hirshleifer, Peng & Wang, news diffusion | 社会传播加快定价，也可能增加意见分歧和交易 | 区分信息扩散与噪声交易 | MEDIUM_TRANSFERABILITY |
| Ben-Rephael et al., demand for information | 机构信息需求本身与价格和成交相关 | 把搜索/调研需求作为低等级领先代理 | MEDIUM_TRANSFERABILITY |
| China EPU and A-share literature | 政策不确定性影响波动、崩盘风险、公告反应和行业差异 | 建立多类型政策不确定性和行业异质性 | MEDIUM_TRANSFERABILITY |
| Sino-US dispute event studies | 国内外行动对A股行业影响不同，且存在延迟吸收 | 地缘事件必须映射直接暴露和行业机制 | MEDIUM_TRANSFERABILITY |
| 国家统计局年度发布日程 | 大量宏观事件可获得官方预告和精确时间 | 官方日历为A1来源，版本化并处理调整 | HIGH_TRANSFERABILITY |

## 3. 不能直接迁移的结论

以下不得被写成A股固定规则：

- “政策会议前股票必涨”；
- “利好落地必然兑现”；
- “股涨债跌是唯一正常关系”；
- “债券收益率下降就是宽松政策”；
- “新闻越正面，股票越涨”；
- “价格提前上涨证明有人获得内幕消息”；
- “国际市场论文中的分钟参数可直接用于中国市场”；
- “单一EPU指数可以代表全部政策不确定性”；
- “政策意图等于地方执行和公司利润兑现”。

## 4. A股特有强化项

### 4.1 政策层级和执行链

A股政策研究必须记录：

- 中央顶层会议；
- 国务院和部门细则；
- 地方政府执行；
- 国企和金融机构响应；
- 上市公司订单、投资和财务兑现。

上层政策信号和基层执行之间可能存在长时滞和强异质性。

### 4.2 交易制度

必须处理：

- T+1；
- 涨跌停、停牌和复牌；
- 集合竞价和尾盘竞价；
- 节假日和隔夜外部事件；
- ST、板块和产品规则；
- 北向披露制度变化；
- 程序化交易规则变化；
- 国家队和政策性资金的不可观测边界。

### 4.3 新闻生态

必须区分：

- 官方首发；
- 新华社/中国政府网授权发布；
- 权威媒体政策解读；
- 券商和机构预期；
- 自媒体二次加工；
- 传闻和匿名截图；
- 后续辟谣、修订和执行文件。

转载数量不是独立证据数量。

## 5. 可信度结论

### 高可信合同

- 时间和来源点时化；
- 预期与结果分离；
- 多维惊喜而非单一情绪；
- 跨资产和替代解释；
- 状态依赖与时期切分；
- 抢跑不等于泄漏；
- 事件验证与经济增量验证分离；
- 多重检验和最终锁箱。

### 中等可信、必须本地验证

- 政治局等政策窗口的历史先验；
- 抢跑和消息兑现的具体阈值；
- 文本新颖度对A股各行业的预测力；
- 国家队政策承诺的市场定价；
- 地缘事件对行业的持续时间；
- 搜索和社交信号的领先性。

### 当前UNKNOWN

- 可合法持续获得的专业共识数据覆盖；
- 中国利率衍生品和期权隐含预期的历史点时可得性；
- 国内政策传闻的可标注历史样本；
- 官方日历历史修订链是否可完整重建；
- 本地系统已有新闻/日历/跨资产数据接口；
- PR #8中哪些合同可迁移到当前canonical事件层；
- 不同事件族可达到的最小可靠样本量。

## 6. 研究源清单

优先复核来源：

- 国家统计局年度主要统计信息发布日程；
- 中国政府网、新华社、人民银行、财政部、发改委、证监会、交易所和行业主管部门；
- Pearce & Roley (1985), Stock Prices and Economic News；
- Rigobon & Sack (2004), The Impact of Monetary Policy on Asset Prices；
- Gürkaynak, Kısacıkoğlu & Wright (2020), Missing Events in Event Studies；
- Cieslak & Schrimpf (2018), Non-monetary News in Central Bank Communication；
- Neuhierl & Weber, Monetary Momentum；
- Brooks, Katz & Lustig, Post-FOMC Announcement Drift in Bond Markets；
- Goldberg & Grisse, Time Variation in Asset Price Responses to Macro Announcements；
- Morris & Shin, Central Bank Forward Guidance and the Signal Value of Market Prices；
- Haddad, Moreira & Muir (2025), Whatever It Takes?；
- Doh, Song & Yang (2026), Deciphering Federal Reserve Communication；
- 中国A股政策不确定性、投资者注意力、地缘冲突和行业波动研究。

所有外部研究只提供方法和假设，不证明在A股可直接盈利。
