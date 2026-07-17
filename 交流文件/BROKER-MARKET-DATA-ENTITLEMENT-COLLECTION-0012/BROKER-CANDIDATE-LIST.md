# BROKER-CANDIDATE-LIST — 候选券商列表

> 任务: BROKER-MARKET-DATA-ENTITLEMENT-COLLECTION-0012  
> 生成: 2026-07-17 00:33 UTC+8  
> 模型: DeepSeek-V4-Pro (reasoning)  
> 状态: DRAFT — 所有数据来自公开资料，需客户经理确认

## 候选券商 (5家)

| # | 券商 | API路线 | 资产门槛 | L2行情 | 十档 | 逐笔成交 | 逐笔委托 | 委托队列 | 集合竞价 |
|---|------|---------|----------|--------|------|----------|----------|----------|----------|
| 1 | **国金证券** | QMT / miniQMT / PTrade | **10万** (BROKER_POLICY_UNVERIFIED) | ✅ 免费(达标) (BROKER_POLICY_UNVERIFIED) | ✅ | ⚠️ l2transaction待验证 | ✅ l2order | ⚠️ 一档委托队列(千档待验证) | ⚠️ 待确认 |
| 2 | **华泰证券** | PTrade / QMT | 50万 | ✅ 送免费L2 | ✅ | ✅ tick_data | ✅ tick_data | ❓ 待确认 | ❓ 待确认 |
| 3 | **国信证券** | QMT / miniQMT | **10万** | ✅ 免费(达标) | ✅ | ✅ xtdata tick | ✅ | ⚠️ 待确认 | ⚠️ 待确认 |
| 4 | **中信建投** | QMT | 20万 | ✅ 付费/达标 | ✅ | ✅ | ⚠️ 待确认 | ⚠️ 待确认 | ⚠️ 待确认 |
| 5 | **广发证券** | WTP/量化通 | **300万**(专业投资者) | ✅ 月费30元 | ✅ UI十档 | ⚠️ 机构API | ⚠️ 机构API | ❌ 散户不可用 | ❌ |

## 优先推荐顺序

1. **国金证券** — 门槛最低(10万), 双路线(QMT+PTrade), xtquant SDK文档最全, L2免费
2. **国信证券** — 同样10万门槛, QMT/miniQMT, L2达标免费
3. **中信建投** — 20万门槛略高, 但QMT接口稳定
4. **华泰证券** — 50万门槛偏高, 但PTrade云端策略+免费L2
5. **广发证券** — 300万专业投资者门槛, 散户基本不可用; 仅作参考

## 数据源声明

- 所有数据来自 **公开网络资料** (叩富网/知乎/券商社区/官方文档)
- 未登录任何券商账户
- 未联系客户经理
- 能力标注为 `✅` 的来自公开文档或社区多源一致; `❓` / `⚠️` 表示公开资料未明确或官方文档有保留
- 最终能力必须由客户经理书面确认

## Codex 生成的原有文件引用

- `BROKER-OUTREACH-MESSAGE.md` → 位于 `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/`
- `BROKER-LOW-COST-MARKET-DATA-REQUEST.md` → 同上
- `BROKER-RESPONSE-SCHEMA.json` → 同上 (v0.1, 本任务升级至 V2)
- `BROKER-ROUTE-SCORECARD.csv` → 同上 (v1, 本任务升级至 V2)
