# BrainOps Evidence-only Receipt Allowlist

The E37 final receipt may add exactly one path:

```text
E37/RECEIPTS/E37-FINAL-RECEIPT.md
```

It must be a non-empty evidence document directly after the final tested commit.
It may report Git object identities, commands, exit codes, output hashes, file
scope, public-safe scan results, UNKNOWN retention, rollback instructions, and
external anchor URLs. It must not alter implementation, tests, schemas, route
selection, acceptance criteria, status configuration, plans, or any executable
or validator semantics.
