# E43 Test Run Receipt

Pre-substantive local verification:

```text
py -3.12 -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests -p "test_e43_*.py" -v
exit=0; 71 tests; PASS

py -3.13 -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests -p "test_e43_*.py" -v
exit=0; 71 tests; PASS

py -3.12 -c "import pathlib,yaml; yaml.safe_load(pathlib.Path('.github/workflows/brainops-e43.yml').read_text(encoding='utf-8'))"
exit=0; workflow YAML parsed
```

Exact stdout/stderr stream hashes, tested commit SHA, receipt commit SHA and
Python 3.11/3.13 exact-head CI identifiers are added only after the substantive
commit and receipt topology exist. They must not be predicted here.
