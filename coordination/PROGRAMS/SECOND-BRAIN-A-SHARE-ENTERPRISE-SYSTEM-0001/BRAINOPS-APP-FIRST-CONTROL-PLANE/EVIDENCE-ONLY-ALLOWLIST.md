# BrainOps Evidence-only Receipt Allowlist

The historical E37 receipt remains preserved. The E38 final receipt may add
exactly one additional path:

```text
E37/RECEIPTS/E37-FINAL-RECEIPT.md
E38/RECEIPTS/E38-FINAL-RECEIPT.md
```

Each receipt must be a non-empty evidence document directly after its declared
final tested commit.
It may report Git object identities, commands, exit codes, output hashes, file
scope, public-safe scan results, UNKNOWN retention, rollback instructions, and
external anchor URLs. It must not alter implementation, tests, schemas, route
selection, acceptance criteria, status configuration, plans, or any executable
or validator semantics.
