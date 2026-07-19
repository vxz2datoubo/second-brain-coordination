# StockAPI L2 Demo Hardened Adapter Architecture

This implementation creates an offline-only, production-before-readonly candidate adapter under `brain_core/market_data/stockapi/`.

## Modules

- `protocol.py`: connection modes, 181xx/281xx ports, session states, command builders, command redaction.
- `framing.py`: byte-level incremental `<...>` frame parser with raw bytes, SHA256, double clock, connection metadata, local sequence, partial/empty/oversize/decode status.
- `schemas.py`: normalized event envelope and quality/governance defaults.
- `parser.py`: Market/Order/Tran/Queue parsing, raw field preservation, source time candidate parsing, optional gzip/base64 helper.
- `runtime_client.py`: read-only runtime skeleton; disabled network by default and blocks subscribe before authenticated state.
- `raw_writer.py`: append-only JSONL writer for raw frame first, normalized event second.
- `gap_detector.py`: configurable gap/duplicate/reset/out-of-order detector.
- `http_backfill.py`: no-network backfill mock.
- `health.py`: bounded queue and backpressure metrics.

## Governance

The adapter is `Implemented_Experimental`, not production. It registers only:

- `PROTOCOL_SCHEMA_IMPLEMENTED`
- `OFFLINE_FIXTURE_TESTED`
- `RUNTIME_CLIENT_SKELETON_READY`

It does not verify raw trade ticks, raw order events, ten-level depth, queue-50, or auction trajectory.
