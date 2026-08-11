# Security and privacy

Only `PUBLIC_SAFE` subjects can build a public-promotion candidate. Private or
credential classifications fail before candidate construction. Approval and
marker payloads contain only identifiers, hashes, route/parent bindings and
no raw conversation body, secret, token, credential or user text. Tests use
synthetic hashes and a temporary local Git repository only.

Live E48 is blocked pending independent E48 R3 acceptance. This candidate does
not perform a formal PROJECT/GLOBAL write.
