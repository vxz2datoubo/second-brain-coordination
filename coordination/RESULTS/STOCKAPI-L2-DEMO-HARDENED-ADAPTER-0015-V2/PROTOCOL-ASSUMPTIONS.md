# Protocol Assumptions

- Frames are delimited by `<` and `>` at byte level.
- Payloads are UTF-8 candidates, but corrupt bytes are preserved and reported rather than ignored.
- On-demand mode uses 18100 Market, 18103 Order, 18104 Queue, 18105 Tran.
- Full-push mode uses 28100 Market, 28103 Order, 28104 Queue, 28105 Tran.
- On-demand mode sends `DY2`; full-push mode does not send `DY2` unless a future verified protocol says otherwise.
- Queue version is explicit: V1 and V2 are supported, ambiguous queue payloads remain `AMBIGUOUS_QUEUE_FORMAT`.
- Prices, quantities, and amounts keep raw strings. Decimal candidates are secondary and do not become sole facts.
- `source_time_raw` is separated from local receive time. `135306980` is only a candidate parse to `13:53:06.980`.
