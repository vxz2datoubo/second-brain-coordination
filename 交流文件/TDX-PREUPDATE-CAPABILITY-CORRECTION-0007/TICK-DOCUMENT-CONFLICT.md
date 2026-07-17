# TICK-DOCUMENT-CONFLICT — Tick 数据支持性矛盾

## 三方矛盾
| 来源 | 对 Tick 的陈述 | 置信度 |
|---|---|---|
| tqcenter.py v1.0.4 运行时 | ❌ get_market_data(period='tick') → error -5, valid_periods 不含 tick | RUNTIME_VERIFIED |
| TQ-Python v1.0.12 SKILL.md | ✅ 明确列出 period='tick' 选项 | STATIC_DOCUMENTED |
| TQ-Local v1.0.12 SKILL.md | 未明确列出 tick (period 列表为 1m/5m/.../1y) | STATIC_DOCUMENTED (缺) |
| 官方网页/更新日志 | 声称支持 Tick/分笔数据 | 二手信息 |

## 判定
**`DOCUMENT_CONFLICT_RUNTIME_NOT_VERIFIED_ON_V1_0_12`**

- v1.0.4 运行时确认不支持 tick（此点无误）
- v1.0.12 TQ-Python 文档**声称**支持 tick — 但这是文档不是运行时
- 不得写成"最新版本确认支持"（未实测 v1.0.12）
- 不得写成"最新版本确认不支持"（文档声称支持）

## 可能的解释（推测，未证实）
1. v1.0.12 将 'tick' 加入 valid_periods 列表 → `get_market_data(period='tick')` 可达
2. Tick 仅通过 subscribe_hq 推送，非 get_market_data 轮询
3. TQ-Python 文档可能超前于实现

## 升级后必须验证
```python
tq.initialize(__file__)
result = tq.get_market_data(stock_list=["300418.SZ"], period='tick', count=10)
# 检查: 是否有 'Date'/'Time' 字段? 是否触发 _fast_format_tick_data?
```
