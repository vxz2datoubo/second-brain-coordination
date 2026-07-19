# CODEX -> ChatGPT 报告：TDX L2 聚合能力、券商低成本行情权限与公开爬虫降级治理

task_id: `TDX-L2-AGGREGATE-EXHAUST-0010`

status: `SUCCESS_WITH_FINDINGS`

date: `2026-07-16`

from: Codex

to: ChatGPT

## 1. 本轮目标

根据用户指令：

> 把现有通达信 L2 聚合能力吃干榨净，同时找券商要正式低成本量化行情权限；公开爬虫只能做辅助证据。

Codex 已将该要求落成三个工程闭环：

1. 将现有通达信 / TdxQuant 已验证 L2 聚合字段纳入母系统治理层。
2. 准备券商低成本量化行情权限外联、回填、评分和分类流程。
3. 将公开爬虫 / WebSocket / Web 页面行情路线固定为 `auxiliary_crosscheck_only`，不得冒充原始 L2、真 DDX/DDY、逐笔成交或逐笔委托。

本轮未连接券商、未访问账户、未调用交易接口、未调用 TdxQuant runtime、未修改通达信目录、未执行实盘或模拟下单。

## 2. 当前已验证能力边界

基于仓库已有审计和本轮治理写入，当前可用能力为：

| 能力 | 当前状态 | 说明 |
|---|---|---|
| 五档盘口快照 | `verified / usable` | 可作为 governed snapshot 使用。 |
| 13项 TDX L2 聚合字段 | `verified aggregate / Experimental` | 可作为聚合证据使用。 |
| `subscribe_hq` 回调 | `UPDATE_TRIGGER_COMPATIBLE` | 只作为更新触发，不是逐笔流。 |
| 十档盘口 | `Not Verified / Interface` | 未证明可程序化获取。 |
| 原始逐笔成交 | `Not Verified / Interface` | `L2TicNum` 不能等同逐笔成交。 |
| 原始逐笔委托 | `Not Verified / Interface` | `L2OrderNum` 不能等同逐笔委托。 |
| 委托队列 | `Not Verified / Interface` | 未接入。 |
| 单笔撤单事件 | `Not Verified / Interface` | `BCancel/SCancel` 只能算聚合撤单指标。 |
| 集合竞价轨迹 | `Not Verified / Interface` | `OpenZTBuy` 不能等同完整未匹配量轨迹。 |
| 真 DDX/DDY | `Not Verified` | `Zjl/Zjl_HB` 标记为 vendor_defined，不能冒充交易所原生真资金流。 |

## 3. 新增与修改的核心代码

### 3.1 新增模块

`F:/aidanao/brain_core/realtime_l2_aggregate.py`

新增内容：

- `TDX_L2_AGGREGATE_FIELD_SPECS`
- `normalize_tdx_l2_aggregate_payload`
- `low_cost_broker_permission_questions`
- `public_crawler_auxiliary_policy`
- `classify_broker_market_data_response`

关键治理规则：

- `L2TicNum` 只表示聚合成交笔数指标，不是逐笔成交。
- `L2OrderNum` 只表示聚合委托笔数指标，不是逐笔委托。
- `BCancel/SCancel` 只表示聚合撤单指标，不是单笔撤单事件。
- `Zjl/Zjl_HB` 是供应商定义资金指标，不是真 DDX/DDY。
- 公开爬虫默认 `source_reliability <= 0.55`，`validation_status=auxiliary_only`。
- 券商回复即使声称有 Level-2，也必须通过字段表、SDK文档、样本 payload、时间戳/序列语义和许可条款验证。

### 3.2 修改模块

`F:/aidanao/brain_core/foundation_data_governance.py`

修正 `TdxMcpSnapshotAdapter` 的能力声明：

- 不再把 TDX snapshot route 描述成已验证真 `ddx/ddy`。
- 改为：
  - `realtime_snapshot`: price/change/volume/amount/inside/outside/quote_ts
  - `depth_levels`: partial bids/asks
  - `l2_aggregate`: partial 13项聚合字段
  - `true_ddx_ddy`: unverified
  - `raw_trade_tick`: unverified
  - `raw_order_event`: unverified

## 4. 券商低成本行情权限外联包

输出目录：

`F:/aidanao/coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/`

文件清单：

| 文件 | 用途 |
|---|---|
| `BROKER-OUTREACH-MESSAGE.md` | 可直接发给券商/客户经理的微信、短信、邮件模板。 |
| `BROKER-LOW-COST-MARKET-DATA-REQUEST.md` | 更完整的券商问询问题清单。 |
| `BROKER-RESPONSE-SCHEMA.json` | WorkBuddy 回填券商答复的结构化 schema。 |
| `BROKER-ROUTE-SCORECARD.csv` | 多券商路线比较评分表。 |
| `BROKER-RESPONSE-CLASSIFICATION.md` | Codex 分类券商回复的规则说明。 |
| `TDX-L2-AGGREGATE-FIELD-MAPPING.md` | 13项 TDX L2 聚合字段语义表。 |
| `PUBLIC-CRAWLER-AUXILIARY-EVIDENCE-POLICY.md` | 公开爬虫只能作为辅助证据的政策。 |
| `HANDOFF.md` | 给 WorkBuddy / Codex 下一轮的交接说明。 |
| `STATUS.yaml` | 当前任务状态。 |

## 5. 券商回复分类器

函数：

`brain_core.realtime_l2_aggregate.classify_broker_market_data_response`

输入：

WorkBuddy 按 `BROKER-RESPONSE-SCHEMA.json` 回填的券商答复。

输出状态：

| 状态 | 含义 |
|---|---|
| `insufficient` | 没有足够能力证据。 |
| `needs_review` | 有部分行情能力，但字段、样本、许可或时间戳证据不足。 |
| `raw_l2_candidate_needs_runtime_probe` | 字段表、SDK文档、样本、时间戳/序列、许可边界齐全，可进入只读探针计划。 |
| `blocked` | 路线要求账户/下单/持仓等高风险能力同进程，或违反安全边界。 |

该分类器不会自动启用交易，不会访问券商，不会连接实盘，只做离线判断。

## 6. 母系统写回

已写回公告栏：

- `tdx_l2_aggregate_exhaust_registered`
- `broker_low_cost_market_data_outreach_pack_ready`
- `broker_market_data_reply_classifier_ready`

已写入母系统记录：

### L2 聚合治理注册

- `SkillRegistryEntry`: `skill_dbf271470f3772`
- `ModuleStatusRecord`: `mod_dbf271470f3772`
- `BulletinStateRecord`: `bstate_0fb6ec04a57048`
- `SelfEvolutionLog`: `evo_fad7c16326a042`

### 券商外联包注册

- `SkillRegistryEntry`: `skill_956e0dcdb1a65d`
- `ModuleStatusRecord`: `mod_956e0dcdb1a65d`
- `BulletinStateRecord`: `bstate_af1e0bd1459944`
- `SelfEvolutionLog`: `evo_578ee8cc042d43`

### 券商回复分类器注册

- `SkillRegistryEntry`: `skill_1ea0d68141c1d2`
- `ModuleStatusRecord`: `mod_1ea0d68141c1d2`
- `BulletinStateRecord`: `bstate_eaa52784b8be42`
- `SelfEvolutionLog`: `evo_5cb632a1b36d41`

## 7. 测试结果

已执行：

```bash
python -m unittest tests.test_realtime_l2_aggregate tests.test_foundation_data_governance
```

结果：

```text
Ran 11 tests in 0.449s
OK
```

覆盖内容：

- TDX 13项 L2 聚合字段正常归一化。
- 聚合字段不会被错误升级为原始逐笔或逐笔委托。
- `Zjl/Zjl_HB` 保持供应商定义资金指标。
- `TdxMcpSnapshotAdapter` 不再宣称已验证真 DDX/DDY。
- 券商外联包 JSON / CSV 可读。
- 券商回复分类器能够区分缺证据口头承诺与证据齐全的 raw L2 候选路线。
- 公开爬虫保持 `auxiliary_crosscheck_only`。

## 8. 风险与边界

1. 当前没有新增真实数据源。
2. 当前没有联系券商。
3. 当前没有开通或验证任何券商 API。
4. 当前没有证明十档、原始逐笔成交、原始逐笔委托、委托队列、单笔撤单、集合竞价轨迹可用。
5. 公开爬虫路线不得用于清除 `a_share_proxy_guard_clear`。
6. 券商回复必须有官方文档、字段表、样本和许可条款，不能只凭客户经理口头描述升级。
7. 任意后续 runtime probe 必须继续只读，不得调用账户、资产、持仓、委托、撤单、下单或券商登录自动化函数。

## 9. 给 ChatGPT 的审核请求

请 ChatGPT 审核以下判断是否合理：

1. 当前将 TDX/TdxQuant 能力限定为“五档快照 + 13项L2聚合字段”，是否符合审计证据。
2. 将 `L2TicNum/L2OrderNum/BCancel/SCancel/Zjl/Zjl_HB` 作为聚合或供应商定义指标，而非原始事件流，是否符合 A股数据治理边界。
3. 券商回复分类器的四档状态是否足够：
   - `insufficient`
   - `needs_review`
   - `raw_l2_candidate_needs_runtime_probe`
   - `blocked`
4. 是否需要在券商问询模板中增加更多字段，例如：
   - 上海/深圳分别授权
   - ETF/可转债/北交所覆盖
   - 历史 L2 回放权限
   - 接口限频
   - 掉线重连
   - 本地缓存许可
5. 是否批准 WorkBuddy 使用 `BROKER-OUTREACH-MESSAGE.md` 联系券商/客户经理，并按 `BROKER-RESPONSE-SCHEMA.json` 回填结果。

## 10. 建议下一步

建议下一轮任务：

`BROKER-MARKET-DATA-ENTITLEMENT-COLLECTION-0011`

执行主体：

- WorkBuddy：联系券商、收集字段表、SDK文档、样本、许可条款、成本门槛。
- Codex：对 WorkBuddy 回填的 JSON 运行 `classify_broker_market_data_response`，并给出是否进入只读 runtime probe 的建议。
- ChatGPT：审核是否允许进入只读探针计划。

验收标准：

1. 至少 2 家券商路线被回填到 `BROKER-RESPONSE-SCHEMA.json` 格式。
2. 每条路线有明确字段覆盖、成本、许可、时间戳语义和风险边界。
3. Codex 分类结果不得越过证据。
4. 没有任何实盘、账户、下单、撤单、持仓、资产访问。

## 11. 结论

Codex 认为当前路线已经从“想办法低成本获取 L2”推进为一个可审计工程闭环：

- 现有 TDX L2 聚合能力已纳入系统，且没有越权冒充原始 L2。
- 券商低成本正式权限路线已有外联、回填、评分、分类器。
- 公开爬虫已被制度性降级为辅助证据。
- 下一步必须由 WorkBuddy / 用户通过真实券商渠道收集正式答复和样本，然后再由 Codex/ChatGPT 审核是否进入只读探针阶段。
