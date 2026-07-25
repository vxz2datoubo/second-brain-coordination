# D1 Test Receipt

agent_id: CODEX

Tested local head: `e565864c3a8f5c0f5ccea1659d3eb0c20f6a04b1`.

- `python tests/test_synthetic_engine.py`: exit `0`; two test groups passed, containing 12 named fixtures and 24 executable invariant checks.
- `python tests/run_determinism.py`: exit `0`; isolated directories with `PYTHONHASHSEED=1` and `PYTHONHASHSEED=777` emitted identical normalized output, SHA256 `93b552726b6e51ab6ebce486976da2e57f2e4376bd9ea8cee1ca85f2a9a687f7`.

No real source, local market file, replay, backtest, participant identity, broker, account, routing or trade operation occurred.
