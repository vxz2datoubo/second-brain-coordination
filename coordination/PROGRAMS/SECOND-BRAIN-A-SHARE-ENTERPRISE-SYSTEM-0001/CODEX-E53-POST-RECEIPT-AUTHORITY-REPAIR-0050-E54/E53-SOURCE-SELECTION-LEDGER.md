# E53 Exact Source Selection Ledger

## Authority boundary

This ledger was created before any E53 source file was copied into E54. E53 at
`95f3d4b9e2149c5bce4e22d94755900335ae75d1` is frozen evidence, not a trusted
implementation. A listed blob may be inspected for a local design constraint;
it is not incorporated unless this ledger explicitly says `COPY_EXACT`.

**E54 decision:** no E53 production implementation, test, tool, or workflow
blob is copied verbatim. All candidate implementation is re-authored under the
E54 path so the E53 defects cannot be inherited as invisible semantics. The
entries remain exact review anchors and map every old surface to its E54
replacement obligation.

| E53 path | blob | content SHA-256 | bytes | disposition | E54 obligation |
| --- | --- | --- | ---: | --- | --- |
| `src/e53_authority/__init__.py` | `607c2c1c25131b9fe03dc17e0a016c3df16607f1` | `43777475f95500eba6a0c765345d009406a603bdee436f0476d4b66e099e20d2` | 758 | REPLACE | Export only E54-owned public surface. |
| `src/e53_authority/adapters.py` | `f8502b3fd38c190eb7b329f5ee5dab674208ac54` | `dc97318d8e837d7d9ec64b1b1841ff23ceefd7181b2820d59e6054bb2e43fb6f` | 2353 | REPLACE | Format-specific JSON/JSONL/Markdown ownership. |
| `src/e53_authority/atoms.py` | `8ea49af05e26c20aab73ca8f0ccc26f06b88b4c2` | `c87886331702ed9b3ee2815c0cc566fc2659f9496d98ce85d2a756e5e138ad21` | 7173 | ADAPT | Exact source-bound atom and field checks. |
| `src/e53_authority/corpus.py` | `3223240721f04020a6858f804a1168cc69c079fd` | `83a2d63152ba52895dc007118410e9a242449f6b2d7faf9e85a9995fd56a7efe` | 1654 | REPLACE | Expanded synthetic adversarial corpus. |
| `src/e53_authority/evidence.py` | `473d8cc5dc7755e28099299e65dec2e3f1e2bfcf` | `4080ba9e77a9cd39d42bda4dab571d3cf26217807598f359357e01ccc7a459b9` | 2487 | ADAPT | Immutable byte evidence and identity recomputation. |
| `src/e53_authority/hygiene.py` | `f767744ca0668c4cea9401014bee512159cad2d9` | `6c732aa8917a0cd305dd4cf0f85be15ceb7e05043446ad6a10c38e60d7a96244` | 1483 | REPLACE | Per-commit plus final-tree hygiene. |
| `src/e53_authority/ledger.py` | `2d56b0dec44ee2460a3884cc739a2f812720263d` | `6952c4364bf6c47fe83e5d77b053488841dd11e3ce22ef2581aed4ffa7d13ba1` | 4969 | REPLACE | Deep-frozen, fully recomputed manifest. |
| `src/e53_authority/mutations.py` | `3606c64359587327b42d052df24b27d1c25e8710` | `546914385f65aeeab508016b6109eb4306cef2d30b3d326a2c047b8f832748a3` | 5977 | REPLACE | Full copied-production mutation matrix. |
| `src/e53_authority/packet.py` | `0d4462fa22c76b1e6474353888873fb96b2477e2` | `806dcdf5dd9868cf6bd56de46884fa414fc82e25e73efa28845a64018ec211b2` | 5850 | REPLACE | Complete immutable graph rebuild. |
| `src/e53_authority/registry.py` | `6e75db434ae873b231e78302a1ee6d1c5d77be7a` | `820315c2e0b235a1fd32100473f8e2938d8a659b9291b5fb7c22a14879495814` | 4416 | REPLACE | Exact slice digest and endpoint registry. |
| `src/e53_authority/topology.py` | `2027a401001fd3f66e35fdc00cb6578f437e60ca` | `04f56464de8810c2b6b7c5dcf3ab371c2b5df7b1db3d71958eda871918b762b2` | 2012 | REPLACE | Strict receipt topology and binding validation. |
| `src/e53_authority/utf8_index.py` | `7c271a59c90ba8f075a8c5b3bed9cadcb5e59d81` | `8a41da4f8f009d6ed1092ace1e99508b3077db698fa3c30042911017843b4131` | 2552 | ADAPT | Strict byte boundaries. |
| `tests/__init__.py` | `3db0d3ddefa3910876604c4e9d9602b75981ed7b` | `72a0f72da9e5305497ba4dea9716fa7e85c7707b52f05860a6ddb16275d777cd` | 35 | REPLACE | E54 test package marker. |
| `tests/test_mutation_and_hygiene.py` | `36f3f5341568b563b4ed01587c15d485b085f6c1` | `c962713d32c6074ef17b65e5257a53e9a864c83fff7ff0d9269fa6a8be4810db` | 5578 | REFERENCE_ONLY | New tests must prove every commit and real mutation. |
| `tests/test_provider_evidence.py` | `6ce76086ab71593aa34064d29b961ba96a306b36` | `dfe0e4e1e1866826c243bc5f9cc99788981b357766d9b66bf8a083a86f4dc3e5` | 2757 | REFERENCE_ONLY | New tests bind jobs, artifacts, commands, IDs. |
| `tests/test_source_bound_authority.py` | `041a03b71d3d3a1d26db648e4f23671988022b2f` | `9a52c14f9ecd0d95215ee5668ea13f5ed9b0f3405f98755a8fa97fd49841eae7` | 13707 | REFERENCE_ONLY | Regression inputs only; no inheritance of assertions. |
| `tools/compare_provider_artifacts.py` | `7835a2502a774426a276d7923b022cc668132264` | `6594c5753aa9747bd62e2ca15e36d8e3ed95f211b744487afffc3b57c691d14d` | 1377 | REPLACE | Independent canonical/metadata comparison. |
| `tools/write_provider_evidence.py` | `2732b547d9f442ae21bfa22cc2d0a61a77267216` | `6001bdc35fd16652bd7ddd2ee21e174bd6fe6a8958555d21e784bd45f140aa51` | 3633 | REPLACE | Include mutation/test counts and command hashes. |

## Rejected E53 artifacts

- E53 reports, receipts, generated provider artifacts, and its workflow are
  `REFERENCE_ONLY`; none are valid E54 evidence.
- No real source, credential, market, account, or private artifact was selected
  or read.

## Reproducibility check

The blob SHA-1 is Git's object identity from the frozen receipt tree. The
content SHA-256 and byte count were recomputed with `git cat-file blob` before
this ledger was written. Recompute from the frozen receipt, not a worktree:

```text
git cat-file blob <blob> | sha256sum
```
