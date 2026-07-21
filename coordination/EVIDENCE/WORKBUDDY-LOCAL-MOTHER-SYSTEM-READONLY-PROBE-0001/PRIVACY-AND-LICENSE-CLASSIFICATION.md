# 隐私与许可分级报告

## 分级总览

| 级别 | 数量 | 说明 |
|------|------|------|
| PUBLIC_SAFE | 3 | 脱敏元数据、审计摘要、统一Schema |
| PRIVATE_KNOWLEDGE | 7 | 知识图谱、数据缓存、因子索引 |
| LICENSE_RESTRICTED | 5 | Tushare/WeStock第三方数据 |
| SENSITIVE_LOCAL_ONLY | 1 | T仓追踪记录 |
| RESTRICTED_NEVER_SYNC | 1 | wallet.json (含Token引用) |
| UNKNOWN_CLASSIFICATION | 0 | 本轮全部已分类 |

## 逐项分级

### PUBLIC_SAFE — 可进入公开协调仓库
- `data/unified/`: Schema定义、数据清单
- `data/decision_audit/`: 脱敏决策审计
- `data/audit/` (脱敏摘要部分)

### PRIVATE_KNOWLEDGE — 仅私有Git
- `data/knowledge-graph.json`: 知识图谱结构和内容
- `data/news_index/`: 新闻因子索引
- `data/news_db/staging/`: 新闻缓存
- `data/evolution/`: 市场演化追踪
- `data/raw/westock_info/`: WeStock元数据
- `data/message_correlation/`: 消息关联
- vipdoc数据: 通达信离线K线 (本地解析，非原始分发)

### LICENSE_RESTRICTED — 元数据可同步，原文不可
- `data/raw/tushare/` (153MB): Tushare Pro API数据
- `data/news_db/` (新闻正文): 第三方新闻内容
- `data/chip_digestion/`: 筹码消化数据
- `data/raw/westock_info/`: WeStock数据

### SENSITIVE_LOCAL_ONLY — 永不上传
- `data/T仓接回链_昆仑_*.csv`: 个人交易追踪
- `data/T仓记录_昆仑_*.csv`: 个人交易记录
- `data/wallet.json` 中的资产清单(非Token部分)

### RESTRICTED_NEVER_SYNC — 硬阻止
- `data/wallet.json`: 包含API Token引用和账户信息

## 许可合规

- Tushare数据: 来自Tushare Pro API，使用需遵守Tushare许可协议
- WeStock数据: 来自腾讯自选股MCP，仅供个人分析使用
- vipdoc数据: 通达信本地缓存，仅供个人使用
- 新闻内容: 各来源版权归原作者所有
