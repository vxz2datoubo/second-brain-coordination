# D1 Synthetic A-Share Rules MVP

agent_id: CODEX
status: `SYNTHETIC_ONLY / research_only / NO_TRADE`

This standard-library-only package is a pure-function test harness. It does not read market data, replay history, calculate performance, connect to an account, route an order, or trade.

`SyntheticRuleSnapshot` is injected fixture data, never a claim about historical or current exchange rules. Missing, malformed, unsupported, or unknown inputs fail closed. T+1 is represented by dated synthetic lots and can only mature through an explicit next-trading-day transition.

Run: `python tests/test_synthetic_engine.py` and `python tests/run_determinism.py`.
