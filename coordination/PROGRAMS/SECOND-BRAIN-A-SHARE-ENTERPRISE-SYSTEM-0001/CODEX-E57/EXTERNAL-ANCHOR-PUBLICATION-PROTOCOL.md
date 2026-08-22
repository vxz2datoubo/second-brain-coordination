# E57 External Anchor Publication Protocol

This file defines a publication action; it is not the anchor itself.

After the one allowed receipt-only commit has a complete successful Provider
run, the executor must post the following literal values to both Issue #190
and Draft PR #191 without creating another Git commit:

1. task ID and route epoch;
2. completion signal exactly as declared in `EXECUTION-CONTRACT.yaml`;
3. tested head, tested tree, tested Provider run ID, complete evidence digest,
   and clean-archive verifier digest;
4. receipt head, receipt parent, receipt tree, receipt Provider run ID,
   complete evidence digest, and clean-archive verifier digest;
5. artifact count `13` and job count `7` for each run;
6. exact receipt path allowlist and verification result;
7. statement that no branch commit follows the receipt head;
8. link to the GitHub Actions runs and all explicit UNKNOWNs.

The publication verifier must reject control characters and escape sequences in
these identifiers. See `e57_authority.receipt.verify_literal_anchor`.
