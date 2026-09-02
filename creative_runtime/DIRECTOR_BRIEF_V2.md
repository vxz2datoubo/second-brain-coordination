# DirectorBrief/v2 compiled content and multi-script switching

R178 adds a pure, read-only compiler above the validated R177 catalog. It does
not create a director job, media job, player campaign, session or save slot.

The compiler accepts only a `DirectorBriefV2ContentSelection` that the catalog
can revalidate. It copies immutable package truth into
`DirectorBriefV2CompiledContent`: world, characters, scenes, beats, legal
choices, selected presentation style, asset manifest and content rating. The
result has a deterministic hash and ID.

`MultiScriptDirectorCompiler` exposes five operations:

- `list_scripts`: immutable approved catalog entries;
- `select`: exact script, revision, package hash and style to validated binding;
- `compile`: validated binding to deterministic compiled content;
- `inspect`: recompile and compare every field;
- `switch`: inspect the current input, then compile a different validated target.

Switching is pure. It does not mutate the current input or remember a global
current script. Cross-catalog bindings, stale hashes, wrong versions, unknown
styles, asset/provenance substitutions and even tampering followed by a
recomputed compile hash fail closed.
