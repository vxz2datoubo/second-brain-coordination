# Phase 3 Local Adapter Implementation

This is a public-safe, synthetic-first contract foundation. It does not bind real local data, connect realtime services, access credentials, or expose a trade/order path.

Run the synthetic contract suite from this directory:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Real-source binding is deliberately `NOT_ACTIVATED` until GPT accepts WorkBuddy Issue #49 evidence in a later task.
