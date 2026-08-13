# CODEX-CLTM-0021 Epoch 95 — Read-only filesystem security-model attestation

Public-safe control note for route epoch 95. This route must not contain or publish any private path, user/SID identity, ACL raw text, candidate content, secret, or DailyMemoryCandidate-v2 body.

Purpose: reconcile the proven epoch-92 private-root writeability/SQLite success with epoch-94's inability to attest any applicable durable inheritable user/group Modify/FullControl ACE. The route therefore inspects only the exact bound root's filesystem/volume security model.

Read-only checks may derive the root volume from the already-bound `CLTM_PRIVATE_DATA_ROOT`, identify the filesystem type, determine whether that filesystem model supports persistent per-file ACLs, and inspect the exact root's reparse/volume shape. No child enumeration or content read is permitted.

If the filesystem is NTFS or ReFS, classify persistent ACL support as `SUPPORTED`; if exFAT or FAT/FAT32, classify it as `UNSUPPORTED`; otherwise return `UNKNOWN` and stop for GPT review. Do not infer a durable permission source when the filesystem itself does not support persistent ACLs.

No ACL mutation, write probe, SQLite probe, Daily-v2 access, candidate ingestion, recall, canary, security-policy change, linked-worktree repair, credential mutation, formal persistence, live/production, or trading/account action is authorized.
