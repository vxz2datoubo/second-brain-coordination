# E28 Final Test Run Receipt

## Final head

- tested commit: `b578a14b613a9d34e058e951eb342f395b00c073`
- parent: `c790d0ee40a78b7a40644e22764c2409fcf12a85`
- tree: `d3f6b0854bbec8230ec605c32413ecfdd86ff8d8`

## Local commands

| Command | Exit | Result |
| --- | ---: | --- |
| `python -B tests/test_evaluation_v2.py` | 0 | 60 tests, OK |
| `python -B tests/run_evaluation_v2.py` | 0 | canonical report `480975bdb61c81b2b47293476104582e4ef7e13fe7fe45ffcec2128f2666c9bc` |
| `python -B portable_archive_evidence.py --commit b578a14b613a9d34e058e951eb342f395b00c073` | 0 | three independent Windows roots, 419 artifacts each |

Local portable archive output SHA-256:
`354c2df23ca4f4f2d35724bffbc9dda5a559104d1097d051479d956999d2a011`.
Local portable archive stderr is empty with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The public runner output in each local root is identical:
`4213c14d1ba0e8edf7ff18275980b2387d663f6ac74643c27b80c170cc90a044`.
Focused unittest stderr contains timing and differs by root; this is recorded
in the machine manifest, not silently normalized into a false equality claim.

## Exact remote matrix

Workflow-dispatch run [30649533447](https://github.com/vxz2datoubo/second-brain-coordination/actions/runs/30649533447)
checked out the exact final branch head.

| Runtime | Job | Result |
| --- | --- | --- |
| Python 3.11 | 91219114422 | success; 183 historical tests, 60 Evaluation V2 tests, runner and archive step |
| Python 3.13 | 91219114333 | success; 183 historical tests, 60 Evaluation V2 tests, runner and archive step |

Job log hashes:

- Python 3.11: `811491a7c46d0d5c1af7a035d26101fb7c52ae82a48907c86413e27c89fb6194`
- Python 3.13: `8f9bb32129fa9d48a7d337d143fc563e3070f668845b0241b1d5adbfd8149417`

The earlier PR-event run on `c790d0e` is diagnostic history only. All final
acceptance evidence is bound to `b578a14`.
