# E44 Test Run Receipt

Pre-substantive local verification:

```text
PYTHONPATH=<program>/src py -3.12 -m unittest discover -s <program>/tests -p "test_e44_*.py" -v
exit=0; 83 tests; PASS

PYTHONPATH=<program>/src py -3.13 -m unittest discover -s <program>/tests -p "test_e44_*.py" -v
exit=0; 83 tests; PASS
```

Exact-head commit identity, command stream hashes, Python 3.11/3.13 CI runs and
receipt topology are recorded only after the substantive commit and cannot be
predicted in this pre-commit artifact.
