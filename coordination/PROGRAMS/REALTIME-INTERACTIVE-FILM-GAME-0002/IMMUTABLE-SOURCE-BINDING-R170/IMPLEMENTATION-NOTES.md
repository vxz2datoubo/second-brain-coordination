# R170 immutable legacy-source binding

The original legacy file remains the root of trust after migration.  Loading a
migrated v2 save reads `session.json` again, derives its SHA-256 digest, parses
its canonical action history, and reconstructs the only permitted v2 prefix.
The persisted v2 receipt is accepted only when it exactly equals that fresh
derivation.  Replacing receipt and ledger together therefore cannot create a
new trusted history.
