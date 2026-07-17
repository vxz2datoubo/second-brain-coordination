# PUBLIC-OFFICIAL-EVIDENCE — 公开官方证据汇总

> 来源: 公开网络搜索 (2026-07-17 00:33 UTC+8)  
> 注意: 所有内容为公开资料汇总，非客户经理书面确认。最终能力需官方答复。

---

## 一、QMT/miniQMT (迅投) — 通用框架

### 官方文档来源
- **网址**: https://dict.thinktrader.net/nativeApi/download_xtquant.html
- **SDK名称**: xtquant
- **最新版本**: xtquant_250807 (2025-12-19 发布)
- **安装**: `pip install xtquant`

### Python 兼容性
- 支持 Python 3.12, 3.13 ✅
- 外部 Python 进程可运行 (如 PyCharm/VSCode)
- 通过本地 TCP 连接 miniQMT 进程

### 行情数据能力 (公开文档确认)

| 能力 | xtquant 支持 | 接口/函数 | 备注 |
|------|:---:|------|------|
| 五档快照 | ✅ | `get_market_data(period='1d')` | 基础 |
| 十档快照 | ✅ | `get_full_tick()` | 含买卖十档+逐笔 |
| **千档行情(待验证)** | ⚠️ | `subscribe_l2thousand_queue()` / `get_l2thousand_queue()` | 版本记录出现千档, **官方字段页l2orderqueue仅定义一档委托队列**。待券商验证千档结构, 不预设为买卖各1000档 |
| 逐笔成交(真实L2) | ⚠️ | `l2transaction` 类型 | **GPT裁决: tick≠原始L2**。验证l2transaction(tradeIndex/buyNo/sellNo)才算通过, 不能用subscribe_quote period='tick'代替 |
| 逐笔委托 | ⚠️ | `l2order` 类型 | 官方含entrustNo, 需运行时payload验证 |
| 委托队列 | ⚠️ | `l2orderqueue` | **一档委托队列**(买一卖一), 非千档价格深度 |
| 撤单事件 | ⚠️ | 逐笔成交中 `trans_flag` 标记撤单 | 间接获取 |
| 集合竞价 | ⚠️ | 待确认是否有专门接口 | 公开文档未明确 |
| 历史L2回放 | ✅ | `download_history_data(period='tick')` | 历史tick可下载 |
| K线全推 | ✅ | `subscribe_whole_quote(['SH','SZ'])` | 全市场行情推送 |
| Level-2 全推 | ✅ | VIP模式支持 | 含逐笔成交笔数 |
| 大单统计 | ✅ | `get_transactioncount()` | 需要VIP权限 |
| **委托在队列中排名** | ✅ | `get_order_rank()` | 需要**投研版本** |

### 关键限制
- **投研版本** vs **普通版本**: 部分高级功能(委托排名/分类板块信息)需要投研版本
- **VIP权限**: 大单统计需要VIP权限
- **token模式**: 同datadir只允许启动一个xtdc进程
- **千档数据源模式**: token模式下需要 `xtdc.set_thousand_source_mode()`

### 时间戳 & 序列
| 项目 | 公开文档 |
|------|------|
| 时间来源 | ⚠️ 待确认 (交易所 vs 券商端) |
| 时间精度 | 毫秒级 (`business_time` 字段) |
| 成交编号 | ✅ `trade_index` |
| 委托编号 | ✅ `order_no` |
| 频道号 | ✅ `channel_num` (逐笔成交中有) |
| 序列号 | ⚠️ 待确认 |
| 丢包检测 | ⚠️ 待确认 |
| 断线重连 | ✅ K线全推有断线重连逻辑 |
| 事件顺序 | ⚠️ 待确认 |

---

## 二、PTrade (恒生电子) — 通用框架

### 官方文档来源
- **网址**: https://ptradeapi.com/
- **开发商**: 恒生电子
- **部署模式**: 券商机房云端托管 (内网环境)
- **Python版本**: 国金3.11 / 多数券商3.5

### 行情数据能力

| 能力 | 支持 | 接口 | 备注 |
|------|:---:|------|------|
| 五档快照 | ✅ | `get_snapshot()` | 基础 |
| 十档快照 | ✅ | `tick_data` → `tick` DataFrame | **默认支持, 免费** |
| 逐笔成交 | ✅ | `tick_data` → `transcation` DataFrame | **部分券商免费内置L2逐笔** |
| 逐笔委托 | ✅ | `tick_data` → `order` DataFrame | 需L2行情权限 |
| 委托队列 | ❓ | `bid_grp`/`offer_grp` 含委托量+笔数 | 非真正的队列排名 |
| 撤单事件 | ⚠️ | 逐笔成交中 `trans_flag=1` 标记 | 间接 |
| 集合竞价 | ✅ | `trade_status` 含 `OCALL`/`PRETR`/`PCALL` | 状态标记 |
| 集合竞价价量轨迹 | ❌ | 公开文档未提供 | 待确认 |
| 历史回放 | ✅ | `get_history()` / `get_price()` | 2005年至今 |

### 逐笔数据字段 (公开)
- **逐笔委托**: business_time(毫秒), hq_px, business_amount, order_no, business_direction(0/1), trans_kind(1市价/2限价)
- **逐笔成交**: business_time(毫秒), hq_px, business_amount, trade_index, buy_no/sell_no, trans_flag(0普通/1撤单), channel_num

### 关键限制
- **内网环境** — 无法 pip 安装第三方库，无法连互联网
- **极少数券商支持外网** (可通过HTTP传输数据)
- 策略在券商机房托管运行，服务器重启策略中断
- Tick级别最小间隔：**3秒** (非真正逐笔，是3秒聚合)
- **不支持多线程** 同时调用 get_history/get_price

### 市场覆盖
上海A股 / 深圳A股 / 创业板 / 科创板 / 可转债 / ETF / LOF / 国债逆回购 / 期货(投机) / REITs(列表) / 融资融券 / 港股通 / 期权

---

## 三、各券商差异化信息

### 国金证券
- **API路线**: QMT + miniQMT + PTrade 三线全开
- **SDK**: xtquant (最新版, Python3.11+)
- **资产门槛**: 10万元近20日日均
- **L2行情**: 达标免费, 包含十档+逐笔成交+逐笔委托
- **xtquant函数开放度**: 三家(国金/中金/华西)最高
- **开通**: 线上审核, 风险测评C4, 半年交易经验
- **佣金**: 可谈, 基础万三
- **数据来源**: 叩富网/知乎/社区 多源一致
- **证据状态**: `COMMUNITY_CONSISTENT` — 待客户经理书面确认

### 华泰证券
- **API路线**: QMT完整版 + PTrade
- **资产门槛**: 50万元
- **L2行情**: 50万资产达标赠送免费Level-2
- **收费版L2**: 月88元(手机) / 年298元(云端)
- **PTrade**: 十档+Tick(3秒级), 部分券商内置L2逐笔
- **数据来源**: 叩富网/知乎/社区
- **证据状态**: `COMMUNITY_CONSISTENT` — 待客户经理确认

### 国信证券
- **API路线**: QMT + miniQMT
- **资产门槛**: 10万元
- **L2行情**: 达标免费
- **支持**: 十档+逐笔成交
- **数据来源**: 叩富网/社区 多源一致
- **证据状态**: `COMMUNITY_CONSISTENT`

### 中信建投
- **API路线**: QMT
- **资产门槛**: 20万元
- **L2行情**: 需付费/达标
- **数据来源**: 叩富网/社区
- **证据状态**: `COMMUNITY_CONSISTENT`

### 广发证券
- **API路线**: 量化通(自研WTP) + 广发易淘金量化策略商城
- **资产门槛**: **300万元** (专业投资者) — 散户基本不可用
- **L2行情**: 月费30元 / 年费298元
- **Python接口**: 机构级API (C++/Python/Java), 需"量化通"权限
- **散户替代**: 广发易淘金 — 策略商城(无需编程)
- **数据来源**: 叩富网
- **证据状态**: `COMMUNITY_CONSISTENT` — 散户门槛过高, 可能不适合个人量化
- **结论**: 本次调查的候选中最不适合个人量化

---

## 四、未获取到的官方证据 (全部券商)

| 证据类型 | 状态 |
|------|------|
| 官方字段表 (完整) | ❌ 未公开 (需客户经理/开通后获取) |
| SDK 完整文档 (非第三方) | ⚠️ xtquant部分公开 / PTrade部分公开 |
| 官方收费清单 | ❌ 只有社区整理的碎片信息 |
| 许可证/数据使用协议 | ❌ 未公开 |
| 时间戳语义说明 | ⚠️ PTrade文档有提及毫秒级, 但来源待确认 |
| 序列号语义说明 | ⚠️ 部分字段名已知, 完整说明待确认 |
| 限频说明 | ❌ 未公开 |
| 断线恢复细节 | ⚠️ xtquant提及K线全推有重连, 细节待确认 |
| 日初快照/订单簿基线 | ❌ 未提及 |
| 安全隔离(行情交易分离) | ⚠️ miniQMT可以作为纯行情SDK | 待确认 |

## 五、证据置信度标注

| 标注 | 含义 |
|------|------|
| `OFFICIAL_DOC` | 官方文档直接确认 |
| `COMMUNITY_CONSISTENT` | 多源社区一致, 待官方确认 |
| `COMMUNITY_SINGLE` | 单一社区来源, 需交叉验证 |
| `VERBAL_CLAIM_ONLY` | 仅口头声明, 不可作为能力证据 |
| `UNCONFIRMED` | 无任何公开资料 |
