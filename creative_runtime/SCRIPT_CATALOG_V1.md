# Persistent ScriptPackage catalog and DirectorBrief/v2 boundary

The A1.2 catalog is an offline, deterministic persistence layer for approved
`ScriptPackage/v1` content. It is not a player save system. It has no authority
over campaigns, sessions, ledgers, migrations, media jobs, providers or
canonical knowledge.

## Lifecycle

1. Approved immutable packages are sorted by exact
   `script_id + script_revision + package_hash`.
2. `materialize_catalog` writes one canonical UTF-8 JSON document through a
   same-directory temporary file, flushes it and atomically replaces the final
   path. Repeating identical content is idempotent; different content at the
   same path is rejected.
3. `load_catalog` rechecks strict JSON, the catalog schema/hash, canonical
   ordering, every package hash, approval, provenance, style and immutable
   revision rule.
4. The loaded `PersistentScriptCatalog` exposes only immutable list, get,
   select, bind and consume operations.

All paths are relative to an explicitly supplied root. Absolute paths,
traversal and resolved escape are rejected.

## DirectorBrief/v2 content identity

The catalog converts a validated `DirectorScriptSelection` into a frozen
`DirectorBriefV2ContentSelection`. The binding includes the exact catalog,
script, revision, package and style identities plus asset-manifest and source-
provenance hashes. Consumption revalidates all fields. Relabeling any field
after validation fails closed.

This is only the content-selection boundary for a future DirectorBrief/v2. It
does not compile shots, create a director job or mutate story state.
