# E35 Evidence-only Receipt Allowlist

The final receipt may add exactly one path:

```text
RECEIPTS/E35-FINAL-RECEIPT.md
```

It must be a non-empty evidence document directly after the final tested commit.
It may report Git object identities, commands, exit codes, output hashes, file
scope, public-safe scan results, UNKNOWN retention, rollback instructions, and
external anchor URLs. It must not alter implementation, tests, schemas, route
selection, acceptance criteria, status configuration, plans, or any executable
or validator semantics.
