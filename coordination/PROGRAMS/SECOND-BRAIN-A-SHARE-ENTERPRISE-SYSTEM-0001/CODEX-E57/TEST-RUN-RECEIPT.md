# E57 Test Run Receipt (Pre-final)

This is a pre-final local receipt, not the required receipt-only commit and
not a claim of remote Provider completion.

| Field | Value |
| --- | --- |
| Task | `CODEX-E56-POST-RECEIPT-ORDINARY-CALLER-CAPABILITY-REGISTRY-SEMANTIC-RECORD-RAW-DECODED-DUAL-PROVIDER-ANCHOR-AND-RECEIPT-CLOSURE-0053-E57` |
| Command | `python tools/provider_runner.py --out <temporary-directory>` from `CODEX-E57` |
| Python 3.13.13 result | exit `0`; `55` unittest cases; `15` genuine source mutations killed and restored; `62.481` seconds |
| Python 3.12 result | exit `0`; same `55` cases and `15` mutations; `14.542` seconds |
| Canonical SHA-256 on both versions | `4dbd42dee9255bfa41896fb431323089e569dccf9a65ebf8635662e59e57e619` |
| Python 3.13 environment SHA-256 | `2a068af85a5ce9e7dcde4eb67e10e1116636efb7d17ae024fbd2130de03c24cb` |
| Python 3.12 environment SHA-256 | `b4baf7c0310563c09474f523444a167035c35a854d1928b1dcf997789b7f610b` |

The canonical payload recorded every mutation's exact target-change-restoration
hashes. Temporary output directories were not tracked. The same command must
be rerun by the Provider workflow against the exact final tested head before a
receipt-only commit is allowed.
