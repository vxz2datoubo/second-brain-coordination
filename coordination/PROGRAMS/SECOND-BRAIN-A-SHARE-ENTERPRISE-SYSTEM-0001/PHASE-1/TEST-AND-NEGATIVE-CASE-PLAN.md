# Test and Negative-Case Plan

## Coverage

The executable suite verifies JSON syntax and contract structure, then independently applies narrow semantic gates using only Python standard library code.

| Case | Expected result |
|---|---|
| Valid offline replay envelope | accepted |
| `available_at` after `as_of` | rejected as future leakage |
| Missing/unknown entitlement | degraded/rejected with abstention only |
| Candidate authority write | rejected |
| `no_trade_gate: false` | rejected |
| Execution action | rejected |
| Irreversible action without approval | rejected |
| Unsupported major schema version | rejected |
| Missing rollback pointer | rejected |
| Existing-type matrix | contains explicit action and no dual-authority rule |

## Command

```powershell
python -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-1/tests -p "test_*.py" -v
```

The suite does not start services, read data feeds, mutate databases, access credentials or execute replay/trade behavior.
