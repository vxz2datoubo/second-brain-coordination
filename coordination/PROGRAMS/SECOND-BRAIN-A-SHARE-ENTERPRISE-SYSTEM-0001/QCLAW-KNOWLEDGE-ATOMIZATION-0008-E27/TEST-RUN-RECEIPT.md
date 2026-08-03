# QCLAW E27 R1 — Test Run Receipt (Batch 001 + 002, Redaction)

- **Pipeline**: QCLAW-KNOWLEDGE-ATOMIZATION-CONTINUOUS-DIGESTION-0008-E27 R1
- **Test Suite**: tests/run_all_tests.py
- **Python 3.11.10**: F:/Program Files (x86)/QClaw/v0.2.35.624/resources/python/python.exe
- **Python 3.13.3**: C:/Program Files/Python313/python.exe
- **PYTHONHASHSEED**: 0

## Results

| Metric | 3.11.10 | 3.13.3 |
|--------|---------|--------|
| Tests Passed | 79/79 (100%) | 79/79 (100%) |
| Tests Failed | 0 | 0 |
| Exit Code | 0 | 0 |
| Dual Python Consistency | ✅ IDENTICAL | ✅ IDENTICAL |

## Integrated Pipeline

| Batch | Files | Atoms | Relations | Unknowns | Conflicts | Redactions | Zero-Secret |
|-------|-------|-------|-----------|----------|-----------|------------|-------------|
| 001 | 1 | 61 | 4 | 6 | 3 | 0 | ✅ N/A |
| 002 | 1 | 22 | 0 | 0 | 1 | 3 | ✅ VERIFIED |

## Command Evidence

```bash
PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 PYTHONPATH=src \
  python tests/run_all_tests.py

PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 PYTHONPATH=src \
  python run_integrated_pipeline.py
```
