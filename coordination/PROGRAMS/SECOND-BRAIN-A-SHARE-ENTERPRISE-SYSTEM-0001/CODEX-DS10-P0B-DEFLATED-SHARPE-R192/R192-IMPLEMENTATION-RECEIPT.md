# R192 implementation receipt — DS-10 P0B Deflated Sharpe

## Execution identity

- Clone: `F:\tmp\r192-exec`
- Initial exact HEAD: `a341bfc0dd114bf333dfc385707be31993babf80`
- Branch: `codex/r192-ds10-p0b-deflated-sharpe`
- Route: `CODEX-DS10-P0B-DEFLATED-SHARPE-R192` / Issue #561
- Executor: `CODEX_STANDARD`; Codex GPT-5 standard profile; planning enabled; no Astra or Frontier used.
- Boundary retained: `RESEARCH_ONLY / NO_TRADE`; no W4/P0A/control-plane writes, no store/ledger, W7, risk, position, order, or trade authority.

## Pinned consumption boundary

The reference module executes the W4 reader only after comparing both local bytes and
`git show a341bfc0dd114bf333dfc385707be31993babf80:<path>` bytes to these identities:

| Read-only source | Git blob SHA-1 | SHA-256 of source bytes |
| --- | --- | --- |
| `W4-STRATEGY-EXPERIMENT-FAMILY-P0/src/w4_experiment_family/registry.py` | `0f6b197c500412f814c38aee347f5a86d8fa8632` | `c38e480694852579a2fc2b9afbb0dbcd00614314566fd2109c766b4e6642cd31` |
| `W4-STRATEGY-EXPERIMENT-FAMILY-P0/src/w4_experiment_family/read_binding.py` | `0e2640d3135553435ec06d99ed9f25c9d146a1e4` | `a2dcaa73c8a2e55102e291f7d2243a51ddf08696e5bcae8f848fb4f6f257228a` |

The module accepts a count only when the pinned reader re-verifies the canonical
receipt, P0A reports `ELIGIBLE_FOR_W7_VALIDATION`, the P0A audit digest verifies,
and the receipt/audit/family/selected-trial/count fields all agree.  This is evidence
only: `PASS_COMPUTED` is never W7 acceptance.

## Commands and results

```text
python -m py_compile .../DS10-DEFLATED-SHARPE-P0B/src/offline_research/deflated_sharpe.py
python -m json.tool .../DS10-DEFLATED-SHARPE-P0B/DEFLATED-SHARPE-RESULT.schema.json
python -m unittest discover -s .../DS10-DEFLATED-SHARPE-P0B/tests -p 'test_deflated_sharpe.py' -v
# PASS: 18 tests

python -m unittest discover -s .../DS10-RESEARCH-INTEGRITY-P0A/tests -p 'test_research_integrity.py' -v
# PASS: 74 tests

python -m unittest discover -s .../W4-STRATEGY-EXPERIMENT-FAMILY-P0/tests -p 'test_experiment_family.py' -v
# PASS: 9 tests

python -m unittest discover -s coordination/CONTROL-TOWER/tests -p 'test_w4_canonical_experiment_family_read_binding.py' -v
# PASS: 11 tests

git diff --check
# PASS
```

## Determinism and portability

The module uses Python float64 operations and `statistics.NormalDist` for Normal CDF
and inverse CDF.  The frozen reference fixture is checked using absolute and relative
tolerance `1e-12` (with a documented 16-ULP cross-runtime budget).  This environment
contains Python 3.13.12 only, so a local 3.11-vs-3.13 comparison was not possible.
The exact-head workflow enforces the same reference suite on both Python 3.11 and 3.13.

## Scope and handoff state

- Added only `.github/workflows/ds10-deflated-sharpe-p0b.yml`, the P0B module tree,
  and this R192 receipt.
- Existing untracked `CODEX-R192-BRIEF.md` and `codex-r192.log` were preserved.
- Changes are intentionally uncommitted, unstaged, and unpushed for independent review.
