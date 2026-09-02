# ScriptPackage/v1 and DirectorBrief/v2 selection boundary

`ScriptPackage/v1` is immutable shared content. It is not a player save, a
campaign, a director job, or generated media. A package is addressed by the
three-part identity `script_id + script_revision + package_hash`; changing any
story, style, asset, approval, or provenance field creates a different hash and
therefore requires a new revision.

Registration accepts only approved, non-explicit, synthetic packages with a
source approval record. Every beat has legal choices, every asset has a stable
synthetic ID, and each package exposes four presentation-only styles. A style
may change visual and audio language but cannot change story beats,
consequences, rewards, endings, character facts, or scene facts.

The registry returns `DirectorScriptSelection`, a frozen four-field projection:

```text
script_id
script_revision
package_hash
style_profile_id
```

This projection is the only A1.1 input intended for a future
`DirectorBrief/v2`. It deliberately grants no authority to create or mutate a
player campaign, session, story state, director job, media job, or canonical
knowledge record.

## Failure behavior

Unknown IDs, wrong revisions, wrong hashes, unapproved content, unknown or
malformed styles, duplicate metadata keys, invalid provenance, private metadata
and package/manifest tampering all fail closed. A rejection leaves the registry
unchanged and cannot create any runtime authority.

## Offline reproduction

From the repository root:

```text
python -m unittest discover -s tests -p "test_creative*.py" -v
python tools/verify_r176_scope.py --base 1502fb11f77cbe7b16f87ed6f0624a21cba303d8 --head HEAD
git diff --check 1502fb11f77cbe7b16f87ed6f0624a21cba303d8...HEAD
```

## Flagship authored prelude

`synthetic_mist_harbor_echoes@1.0.0` is the first approved, entirely synthetic
flagship prelude. It is fixed at three acts, six chapters and twelve ordered
major choices. Each choice has two authored outcomes with a visible reward and
cost, and changes at least one of clue, relationship, resource, risk, quest,
scene, or ending. Its `StaticStoryGraph/v1` and `StoryBibleBundle/v1` are bound
to the exact package hash; dangling edges, jumps, cycles, cross-script
references, missing assets and non-adult principals fail closed.

These are shared immutable content definitions only. They do not create or
mutate player campaigns, session state, director jobs, media jobs, or knowledge.
