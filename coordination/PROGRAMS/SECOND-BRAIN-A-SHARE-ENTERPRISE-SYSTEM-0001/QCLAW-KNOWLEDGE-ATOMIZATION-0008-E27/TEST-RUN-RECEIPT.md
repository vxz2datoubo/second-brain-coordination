# QCLAW E27 — First Delivery Test Run Receipt

- **Pipeline**: QCLAW-KNOWLEDGE-ATOMIZATION-CONTINUOUS-DIGESTION-0008-E27
- **Test Suite**: tests/run_all_tests.py
- **Python 3.11.10**: F:/Program Files (x86)/QClaw/v0.2.35.624/resources/python/python.exe
- **Python 3.13.3**: C:/Program Files/Python313/python.exe
- **PYTHONHASHSEED**: 0

## Results

| Metric | Value |
|--------|-------|
| Tests Passed | 64/64 (100%) |
| Tests Failed | 0 |
| Python 3.11 exit code | 0 |
| Python 3.13 exit code | 0 |
| Dual Python byte-consistency | ✅ IDENTICAL |

## Digest Pipeline Results

| Metric | 3.11.10 | 3.13.3 | Match |
|--------|---------|--------|-------|
| Atoms | 61 | 61 | ✅ |
| Relations | 4 | 4 | ✅ |
| Unknowns | 6 | 6 | ✅ |
| Conflicts | 3 | 3 | ✅ |
| Packet ID | 3f1daf01069b... | 3f1daf01069b... | ✅ |
| Content Hash | d6c39347a3e0... | d6c39347a3e0... | ✅ |

## Command Evidence

```bash
PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 PYTHONPATH=src \
  python tests/run_all_tests.py

PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 PYTHONPATH=src \
  python -m qclaw_knowledge_digest.cli digest \
  digest_queue/batch_001 --output output_batch_001
```
