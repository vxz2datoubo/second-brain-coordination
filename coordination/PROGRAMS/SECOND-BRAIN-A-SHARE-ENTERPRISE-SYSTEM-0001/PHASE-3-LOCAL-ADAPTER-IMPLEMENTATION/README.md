# Phase 3 Local Adapter Implementation

This is a public-safe, synthetic-first contract foundation. It does not bind real local data, connect realtime services, access credentials, or expose a trade/order path.

Run all P1/P2/Phase 3 offline tests from this directory:

```powershell
python run_all_tests.py
```

Real-source binding is deliberately `NOT_ACTIVATED` until GPT accepts WorkBuddy Issue #49 evidence in a later task.

`schemas/` contains versioned JSON Schema projections for cross-agent validation. Python serialization rejects unknown fields and incompatible major versions.
