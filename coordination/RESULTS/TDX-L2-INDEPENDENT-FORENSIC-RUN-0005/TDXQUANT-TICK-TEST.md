# TDXQUANT-TICK-TEST

- generated_at: `2026-07-16T10:22:07.966+08:00`
- method: `get_market_data(period='tick')`
- symbol: `300418.SZ`
- result:

```json
{
  "error": -5,
  "msg": "周期格式错误：tick（支持['5m', '15m', '30m', '1h', '1d', '1w', '1mon', '1m', '10m', '45d', '1q', '1y']）"
}
```

Capability note: this file only records whether the wrapper returned repeatable per-record tick data. A snapshot, callback, NowVol, aggregate amount, or method name is not sufficient for `TICK_VERIFIED`.
