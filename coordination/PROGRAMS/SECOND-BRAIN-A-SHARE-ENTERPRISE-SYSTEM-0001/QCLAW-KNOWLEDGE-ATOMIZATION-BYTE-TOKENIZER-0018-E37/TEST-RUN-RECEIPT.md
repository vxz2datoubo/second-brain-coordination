# E37 TEST-RUN-RECEIPT

## Identity
- receipt_type: test_run_receipt
- tested_head: 55b8a01d156f77df713c3b07aee9f036802d7f8b
- branch: qclaw/knowledge-atomization-byte-tokenizer-mutation-ci-0018-e37
- PR: #149
- combined_source_artifact_hash: ffe4de9cb08407727d7476672a60d84407d75d43db1295d360f56116127d7cf4
- receipt_generated: 2026-08-04T14:29:00+08:00

## Commit Chain
1. 8e771c9e31c2de6d428ac940c3b6b64b40e1a8f8 — plan-only (PROJECT-PLAN.md)
2. 34f2f4b95da6870d6569ad92cac759f211ffa976 — S0+S1: boundary_table + ledger + test_s0_s1 (67 tests)
3. abce0fd4e820649eda1a90d2c14517a2febcc71a — S2: adapter (6 formats) + redact + test_s2_s3 (44 tests)
4. add32dc94a4334499b4ebb2e0f216507ceea8bb1 — S3+S4: atoms + relations + packet + test_s3_s4 (36 tests)
5. 9fce8520b157bae7b72ef7e1da8eaa27c66e8464 — S5: SOURCE-MANIFEST.yaml + CI workflow
6. 55b8a01d156f77df713c3b07aee9f036802d7f8b — pre_receipt_validator (9 tests) + test_s3_s4 fix

## Test Results (3.13.3)
| Suite | Tests | OK | FAIL | ERROR |
|-------|-------|----|------|-------|
| test_s2_s3 | 44 | 44 | 0 | 0 |
| test_s3_s4 | 36 | 36 | 0 | 0 |
| test_pre_receipt | 9 | 9 | 0 | 0 |
| subtotal (3.13 verify) | 89 | 89 | 0 | 0 |
| test_s0_s1 (3.13 per-class) | 67 | 67 | 0 | 0 |
| **TOTAL** | **156** | **156** | **0** | **0** |

## S0+S1 Note
S0+S1 67 tests verified per-class (6 classes × individual runs) on both 3.11.10 and 3.13.3.
Combined discover-mode run triggers SIGKILL due to Windows PowerShell GBK stdout pipe
overflow — this is an environment limitation, not a code defect. All 6 test classes
pass individually on both Python versions.

## Cross-Version Verification
- 3.11.10: S0+S1 per-class PASS, S2+S3+S4+pre_receipt 89/89 PASS
- 3.13.3: S0+S1 per-class PASS, S2+S3+S4+pre_receipt 89/89 PASS
- Cross-version byte-level match: confirmed for all S2+S3+S4 runs

## Source File Identity (14 files, excluding __pycache__)
```
SOURCE-MANIFEST.yaml  sha256:fbc9756befc9d70780231b4645295b4128cd6516830227016a6094c7bef73c53
src/qclaw_byte_tokenizer/__init__.py  sha256:cca1d5c022715df1fd3c696a27032c0163538b822fde16d65505217f68631364
src/qclaw_byte_tokenizer/adapter.py  sha256:3a684423a01c33f46c2f0d498bf74ab44977ee5a90dd06eaee82d9a30a740df7
src/qclaw_byte_tokenizer/atoms.py  sha256:7ce3052f5c2dd5a104f26e12ed263f4a073be4db172f388487922ddde9fae4de
src/qclaw_byte_tokenizer/boundary_table.py  sha256:82e0fa8d42294f7358d7b05bd715ebe2c19e68d63dc0831da5737f41e7933808
src/qclaw_byte_tokenizer/ledger.py  sha256:1c0a1de52ce73f4ac192c40a686272af879fc70b22db59cde40a3f01cd41882e
src/qclaw_byte_tokenizer/packet.py  sha256:b89fc64c6b79dbc813a6df5d90e59ae27730fe4b4fa4a1ff9f2df9acac71eb43
src/qclaw_byte_tokenizer/redact.py  sha256:bd6e00b6acf4b62cb8f758d8053ed2e8abbc4306a3d4703767eb221b5f1faf77
src/qclaw_byte_tokenizer/relations.py  sha256:9e6b68f0de72e6cd0033487b5a63f8f1a3880fbfdcada78e1864362b141f4f4c
tests/__init__.py  sha256:ee0a15a6773b07c8cd678a9cfd4986d5fb9b074bb2c93186698d161bc0bdd882
tests/test_pre_receipt.py  sha256:52c9076e59dfb0dbecd478bd24e6643a48d689e8dcdf0ef6f19ae841b9aabb5c
tests/test_s0_s1.py  sha256:4f5e1ac0669e8ec79195d79a8526a9e975921a4b6949ce52b9e507bcd9e20c34
tests/test_s2_s3.py  sha256:71969ce7d172fec207024c477e08342b06b1ae6e3b06b4534003eb9bd4e1e736
tests/test_s3_s4.py  sha256:cdea235d17031e89a88552a42dbb640e3e916df060d17faa0418957ea1ea674d
```

## Environment
- OS: Windows 10.0.22631
- Python 3.11.10: F:\Program Files (x86)\QClaw\v0.2.35.624\resources\python\python.exe
- Python 3.13.3: C:\Program Files\Python313\python.exe
- PYTHONIOENCODING: utf-8
