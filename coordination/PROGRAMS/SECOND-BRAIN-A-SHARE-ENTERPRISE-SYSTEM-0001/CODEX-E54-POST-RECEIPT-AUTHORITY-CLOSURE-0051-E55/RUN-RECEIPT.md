# E55 Run Receipt

## Exact route
- Base: `71221117b2e15a5437bed27b95fced5e00d11157`
- Plan: `257bcc90b7c2a7a3942a735f61343bd339c8dea8`
- Tested head: `1377d7cc298c9c1db6c5c05c69971551330afba8`
- Tested tree: `827eacf70a6863ff33ef52b695b4b89eed489fe5`
- Draft PR: `#182`; Issue: `#179`; route epoch: `57`.

## Local execution
- Command: `python -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E54-POST-RECEIPT-AUTHORITY-CLOSURE-0051-E55/tests -v`
- Command SHA-256: `2861857f0b132c3d2f9adf1da46c387cb231aedf98ab374292d44b3a200e634e`
- Python: `3.13` local. Python `3.11` was not locally installed.
- Exit: `0`; tests: `30`; duration: `281813856600 ns`.
- stdout SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- stderr SHA-256: `1d87fc52644fabce94ca35017fa94c6fe3f2f2df69bec66e8c4635c9848e0ad9`

## Mutation execution
- Command SHA-256: `6f9b2d03c80b2385f225a3f6d1784ba367c0a81f4ff3f87a09057e7be63f2609`
- Each mutation changed an actual E55 candidate source file in this isolated worktree, produced exit `1`, restored exact pristine bytes, and then produced exit `0`.
- `MUT-SOURCE-ISSUANCE-REGISTRY`: `authority.py@9052`, `5f11e3b5...bc52e`, restored `7149175e...6e560`.
- `MUT-RAW-ADMISSION`: `authority.py@6215`, `fbca70ec...f776`, restored `7149175e...6e560`.
- `MUT-JSON-ESCAPE-OWNERSHIP`: `authority.py@14484`, `2906f1d6...ab2d`, restored `7149175e...6e560`.
- `MUT-JSON-DUPLICATE-KEY`: `authority.py@4339`, `1a71e3c1...4c3b`, restored `7149175e...6e560`.
- `MUT-RELATION-SEMANTIC-RECORD`: `authority.py@25533`, `aa57750c...16b8`, restored `7149175e...6e560`.
- `MUT-PACKET-SUBRECORD`: `authority.py@30519`, `f3e7b034...d799`, restored `7149175e...6e560`.
- `MUT-HYGIENE-GENERATED`: `hygiene.py@1846`, `255bda47...7e45`, restored `a0a74fc8...efe64`.
- `MUT-TOPOLOGY-ACTUAL-PARENT`: `topology.py@4326`, `f761b3b8...f2f6`, restored `98dd8aeb...b33de`.
- `MUT-TOPOLOGY-ROUTE`: `topology.py@2119`, `48d77a8e...7304`, restored `98dd8aeb...b33de`.
- `MUT-PROVIDER-RUN-METADATA`: `provider.py@1931`, `479e1901...a0c7`, restored `d776da09...9e387`.
- `MUT-PROVIDER-BYTES`: `provider.py@4428`, `bb3f1853...0413`, restored `d776da09...9e387`.

## Provider verification
- Final run: `31064395077`; exact head: `1377d7cc298c9c1db6c5c05c69971551330afba8`.
- Six jobs: Python `3.11` and `3.13` at seeds `0`, `1`, `777`; all succeeded.
- Independently downloaded 13 artifact archives, compared each downloaded archive SHA-256 against GitHub metadata, extracted the canonical/environment/compare inner files, and verified the six-pair matrix plus byte-bound compare manifest.
- Compare digest: `a3c74fe85db37caedc98a7fb76bf247b60c081149f00030610a9e0286c85a8a9`.
- Provider test count per environment: `29`; registered mutations: `11`.
