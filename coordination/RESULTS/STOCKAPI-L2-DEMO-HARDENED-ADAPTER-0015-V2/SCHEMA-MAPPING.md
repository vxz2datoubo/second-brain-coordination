# Schema Mapping

## Market V2

Preserves 66 raw fields and maps packet number, symbol, trade date, source time raw/candidate, status, OHLC/last raw, 10-level ask/bid price and quantity raw arrays, trade count/volume/amount raw, total bid/ask volume raw, weighted prices, limit prices, and Shanghai cancel aggregates.

## Order V2

Maps packet number, symbol, trade date, source time raw/candidate, order number, price raw, quantity raw, order type, side, original order number, event sequence, and channel number.

## Tran V2

Maps packet number, symbol, trade date, source time raw/candidate, trade number, price raw, quantity raw, amount raw, side, trade type, original number, sell order number, and buy order number.

## Queue

Supports explicit Queue V1 and Queue V2. Ambiguous queue payloads are not guessed and receive `AMBIGUOUS_QUEUE_FORMAT`.

All events keep `raw_l2_gate_cleared=false` and `live_trading_enabled=false`.
