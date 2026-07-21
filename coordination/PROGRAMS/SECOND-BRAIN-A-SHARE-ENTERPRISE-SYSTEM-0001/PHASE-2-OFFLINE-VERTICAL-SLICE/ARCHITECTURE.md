# P2 Offline Vertical Slice

`fixtures -> load_fixture -> ContractRuntime -> DeterministicReplay -> candidate_signals -> simulate_portfolio -> validate -> evidence bundle -> LearningPacket / KnowledgeGateway`

`engine.py` is deliberately a compact public-safe reference implementation. It has no network client, service lifecycle operation, credential reader, broker adapter, or order serializer. P1 remains the exchange-contract authority; the P2 objects are runtime adapters and output projections, not a second source of record.

## Temporal control

Each bar carries event, observed, receive, entered-system, available, and as-of timestamps. `available_at > requested_as_of` is quarantined. Signals are not simulated until a later event has reached their availability time. Replay sorting is `(event_time, symbol, event_id)` and duplicate or near-duplicate records are quarantined deterministically.

## A-share research boundary

Simulation records candidate actions only. It enforces configurable T+1, suspension, ordinary/ST limit thresholds, fixed/volume-placeholder slippage, commission, stamp duty, SH transfer fee, maximum position weight and turnover. It cannot connect to a broker and every output retains `no_trade_gate: true`.

## Knowledge boundary

Synthetic atoms model independent `knowledge_status`, `gpt_access`, and `transport_visibility`. Candidate atoms remain readable through `FULL_SEMANTIC_ACCESS`; that never authorizes public transport or authority writes. Hard-secret-shaped queries abstain. Context budget omissions are named, not silently discarded.
