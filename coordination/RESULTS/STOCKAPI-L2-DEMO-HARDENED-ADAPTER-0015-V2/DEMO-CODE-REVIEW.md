# Demo Code Review

## Demo A: `test_demo (2)(1).py`

Evaluation: reference-only negative example. It is not reused directly.

Key issues:

- Uses one-shot `recv()` plus regex frame extraction; unsafe for half/sticky TCP frames.
- Performs a second `<...>` regex pass after payload extraction, which can skip business records.
- Mixes full-push 281xx ports with on-demand subscription commands.
- Logs login/subscribe commands and may expose credentials.
- Omits Queue port 18104/28104.
- Fixed 5-second reconnect can be too aggressive.

## Demo B: `test_demo.py`

Evaluation: useful skeleton reference, not production-ready.

Key issues:

- Has incremental string buffer but decodes chunk with `errors=ignore` before frame boundary handling.
- Sends subscribe after fixed sleep instead of verified login success.
- Fixed 5-second reconnect can cause churn.
- Omits Queue stream.
- Hardcodes credential placeholders and writes direct local files without governed raw metadata.
- Has unbounded queue, no high watermark/drop metrics, no sequence/gap detection, no HTTP backfill reconciliation.
- Does not preserve raw frame, connection id, local sequence, receive wall/monotonic clocks, frame hash, or parse status.
