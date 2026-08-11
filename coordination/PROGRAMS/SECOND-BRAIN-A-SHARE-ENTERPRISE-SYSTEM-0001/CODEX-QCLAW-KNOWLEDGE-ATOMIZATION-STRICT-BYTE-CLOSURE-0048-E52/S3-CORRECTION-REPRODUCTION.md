# S3 Correction Reproduction Ledger

This ledger preserves the independent-review defects and the local red-to-green
sequence. All fixtures are synthetic and public-safe.

## Plan identity re-derivation

On 2026-08-05, the GitHub commit and compare APIs resolved
`875a7281b21dbb74dc9021b3ad159d05cdd2eb08` as a direct child of
`3d15f0c62877db5841b985f740e9bc348f65ddc5`, with one commit ahead and one
added file: this program's `PROJECT-PLAN.md`. The previously recorded suffix
was malformed and is superseded by `PLAN-IDENTITY-EVIDENCE.md`.

## Red evidence before repair

```text
python -m unittest discover -s <E52>/tests -p test_s3_correction_gates.py -v
exit=1
ImportError: cannot import name 'RelationType'
```

After the initial implementation draft, the same focused suite still failed:

```text
Ran 9 tests
FAILED (failures=1, errors=5)
```

The errors exposed shallow field-container freezing; the failure exposed that a
blank Markdown separator had no byte-owning structural label. Both failures
were repaired before the full suite was accepted.

## Green local checkpoint, not provider credit

```text
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s <E52>/tests -v
Ran 41 tests
OK
```

This is only local S3-correction evidence. It does not start S4, does not grant
provider/receipt credit, and does not change `research_only / NO_TRADE`.
