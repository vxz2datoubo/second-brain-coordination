# RUN-RECEIPT — 执行回执

> 任务: BROKER-MARKET-DATA-ENTITLEMENT-COLLECTION-0012  
> 生成: 2026-07-17 00:33 UTC+8  
> 模型: DeepSeek-V4-Pro (reasoning)  
> 状态: ✅ 公开资料调查阶段完成

## 执行摘要

| 指标 | 值 |
|------|-----|
| 调查券商数 | **5家** |
| 已取得官方资料的券商 | **2家** (xtquant官方文档 + PTrade API文档, 框架级) |
| 需要用户手动联系的券商 | **4家** (国金/国信/中信建投/华泰; 广发不适合散户) |
| Python可读取Level-2候选路线 | ✅ **国金-miniQMT-xtquant** (最低10万门槛) |
| 十档候选 | ✅ 国金QMT / 国信QMT / 中信建投QMT |
| 逐笔成交候选 | ✅ xtdata tick (全推) + PTrade tick_data |
| 逐笔委托候选 | ✅ xtdata l2order + PTrade tick_data order |
| 委托队列候选 | ✅ xtquant **千档队列** `l2thousand_queue` (2024新增) |
| 集合竞价候选 | ❌ 所有券商公开文档未明确 |
| 最低成本 | **0元/月** (国金/国信, 资产达标后L2免费) |
| 最低资产门槛 | **10万元** (国金/国信 近20日日均) |
| 证据最完整路线 | **国金证券 miniQMT + xtquant SDK** (官方文档最全) |
| 无法隔离交易权限的路线 | 未发现 (miniQMT xtdata可独立于xttrader) |
| 散户不可用路线 | **广发证券** (300万专业投资者门槛) |

## 关键发现

### 🏆 最佳路线: 国金证券 miniQMT

- **门槛**: 10万资产, 线上审批
- **SDK**: xtquant (pip install, Python 3.12/3.13)
- **行情**: 十档 + 逐笔成交(tick全推) + 逐笔委托(l2order) + **千档队列**(l2thousand_queue)
- **安全**: xtdata独立模块, 不初始化xttrader即无下单能力
- **外部进程**: 支持PyCharm/VSCode直接调用
- **成本**: L2达标免费

### ⚠️ 待确认的关键缺口 (所有券商)

1. **集合竞价价量轨迹**: 无券商公开文档明确支持
2. **时间戳来源**: 交易所时间 vs 券商端时间, 待确认
3. **千档队列门槛**: 国金是否需要投研版本？
4. **华泰PTrade tick_data**: 是否真正逐笔 (非3秒聚合)？
5. **许可条款**: 是否允许ML训练/云端/跨机器 (无公开信息)

## 遵守的禁止规则

| 规则 | 状态 |
|------|:---:|
| 未登录券商账户 | ✅ |
| 未提交交易密码 | ✅ |
| 未调用交易API | ✅ |
| 未自动下单 | ✅ |
| 未访问持仓/资产/委托 | ✅ |
| 未支付费用 | ✅ |
| 未承诺入金/交易量 | ✅ |
| 未签署协议 | ✅ |
| 未下载未知程序 | ✅ |
| 未开通收费服务 | ✅ |
| 未发送外部消息 | ✅ (所有消息为草稿，需用户手动发送) |

## 交付物清单

所有文件位于: `F:\aidanao\交流文件\BROKER-MARKET-DATA-ENTITLEMENT-COLLECTION-0012\`

| # | 文件 | 状态 |
|---|------|:---:|
| 1 | BROKER-CANDIDATE-LIST.md | ✅ |
| 2 | PUBLIC-OFFICIAL-EVIDENCE.md | ✅ |
| 3 | EXPANDED-BROKER-QUESTIONNAIRE.md | ✅ |
| 4 | OUTREACH-MESSAGES.md | ✅ |
| 5 | BROKER-RESPONSE-SCHEMA-V2.json | ✅ |
| 6 | BROKER-ROUTE-SCORECARD-V2.csv | ✅ |
| 7 | BROKER-RAW-RESPONSES/ | ✅ (空目录, 等待券商答复) |
| 8 | MISSING-EVIDENCE.md | ✅ |
| 9 | SECURITY-AND-PERMISSION-BOUNDARIES.md | ✅ |
| 10 | USER-MANUAL-SEND-LIST.md | ✅ |
| 11 | STATUS.yaml | ✅ |
| 12 | RUN-RECEIPT.md | ✅ |

## 前置Codex文件引用

| 文件 | 路径 | 使用情况 |
|------|------|------|
| BROKER-OUTREACH-MESSAGE.md | coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/ | ✅ 已扩展整合到 OUTREACH-MESSAGES.md |
| BROKER-LOW-COST-MARKET-DATA-REQUEST.md | 同上 | ✅ 已扩展整合到 EXPANDED-BROKER-QUESTIONNAIRE.md |
| BROKER-RESPONSE-SCHEMA.json | 同上 | ✅ 已升级到 V2 (BROKER-RESPONSE-SCHEMA-V2.json) |
| BROKER-ROUTE-SCORECARD.csv | 同上 | ✅ 已升级到 V2 (BROKER-ROUTE-SCORECARD-V2.csv) |
