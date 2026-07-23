# Blueprint-to-Skill Gap Compiler Contract

Status: `PLANNED_NOT_AUTHORIZED`

Target phase: D1

Runtime implemented by this task: no

## Inputs

- protected blueprint manifests and immutable hashes;
- Issue, PR and artifact metadata;
- skill manifests and capability registries;
- code symbols, tests and run receipts;
- ownership boundaries and official A-share rule snapshots.

## Deterministic Pipeline

```text
source inventory
-> normalized term and method extraction
-> lifecycle mapping
-> existing skill/runtime/test resolution
-> ownership and duplication checks
-> maturity derivation from evidence
-> gap findings and dependency ordering
-> stable report serialization and hash
```

## Required Outputs

- `SkillManifest`
- `MaturityRecord`
- `GapFinding`
- `OwnershipBoundary`
- `EvidenceReference`
- deterministic `GapReport`

Every finding must contain a stable ID, source locator, evidence class, current
state, expected state, owner, rationale, dependency IDs and suggested action.

## Non-Negotiable Rules

- Documentation is never implementation evidence.
- A test name is not a passing run receipt.
- No term may silently disappear during normalization.
- Synonyms may merge only with retained source mappings.
- Multiple wrappers around one canonical runtime are not independent voters.
- The compiler cannot alter runtime state, blueprints or maturity by itself.
- Missing source, effective date or applicability remains `UNKNOWN`.

## D1 Acceptance

The same ordered inputs must produce byte-identical output. Golden fixtures must
detect orphan terms, ghost capabilities, duplicate runtimes, ownership overlap,
stale rule mappings and maturity inflation. A reverse mapping must explain every
merge, rename and exclusion.
