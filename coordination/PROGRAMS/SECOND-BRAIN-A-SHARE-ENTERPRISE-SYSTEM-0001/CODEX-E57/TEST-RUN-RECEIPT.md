# E57 Test Run Receipt (Pre-final)

This is a pre-final local receipt, not the required receipt-only commit and
not a claim of remote Provider completion.

| Field | Value |
| --- | --- |
| Task | `CODEX-E56-POST-RECEIPT-ORDINARY-CALLER-CAPABILITY-REGISTRY-SEMANTIC-RECORD-RAW-DECODED-DUAL-PROVIDER-ANCHOR-AND-RECEIPT-CLOSURE-0053-E57` |
| Environment | Windows, Python `3.13.13` |
| Command | `python tools/provider_runner.py --out <temporary-directory>` from `CODEX-E57` |
| Result | exit `0`; `54` unittest cases; `14` genuine source mutations killed and restored |
| Duration | `35.197` seconds |
| Canonical SHA-256 | `70ea614718d799af22777556ceeb3f9b86139c1d1dc1592f56d4c80193c5b939` |
| Environment SHA-256 | `adecbd060ec0ae0b991200cba72e00c0e89ea49e1ded6969e9390214d7eee94c` |

The canonical payload recorded every mutation's exact target-change-restoration
hashes. Temporary output directories were not tracked. The test count and
canonical hash will be rerun after the final executable commit because this
receipt predates the control artifacts in the current working tree.
