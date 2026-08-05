# E44 Work Plan Deviation And Change Record

## Source Disposition

E43 PR #136 remains frozen and is used only through the exact file/blob list in
`SOURCE-IMPORT-MANIFEST.yaml`. E44 imports selected primitives as source files;
it does not cherry-pick, merge, revive or modify the source branch.

## Deviations

1. The initial plan did not name the storage-id validator distinction. The
   implementation discovered that durable storage IDs are hashes and added a
   hash-specific validation rule with regression coverage.
2. The plan required terminal exit semantics. The implementation strengthened
   this to require evidence-family and exit-code equality between the sealed
   owner decision and the raw observation.

Neither deviation expands external authority, production runtime scope or any
forbidden operation.
