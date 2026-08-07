# E58 run receipt (pre-anchor)

This receipt-only commit does not claim completion until its own receipt-head
Provider matrix and independent artifact download both complete.

## Tested head

* Head: `44eeca76113bb1376c89af550216a93df824191d`
* Parent: `8349d420bf95831c479d57e462b5a0065ec91d30`
* Tree: `455b6c064f50bd2950c6ea652d16f0f77f47c586`
* Local suite: `python tools/run_local_suite.py`, 46 tests passed in `0.224s`;
  Python count was 0 before and after.
* Local genuine mutation catalog: 7/7 temporary-copy mutations were killed and
  restored exactly; Python count was 0 before and after.
* Remote tested Provider: run `31142425299`, 7 jobs, 13 artifacts, exact head.
  Six canonical inner files were byte-identical with SHA-256
  `e1770a1f1903ec328ae56ed708b28b0c9b5c153c3cc05c63fa3a58e85c36b5a6`.

The earlier run `31142239202` is retained as a corrective discovery only: its
environment self-report hashed canonical bytes before their final newline.
Commit `44eeca7` corrected that field; the accepted second run's environment
artifacts match the final-file hash.

## Resource receipt

P0 command `python -m unittest discover -s tests -v` passed 10 tests in 0.187s.
stdout SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
stderr SHA-256: `30bc9e7649fc6639a6326443e77b22e447fc2e585ebde7bf3d06363421ab4874`.

The desktop host denied nested Job assignment with `ERROR_ACCESS_DENIED (5)`;
the owned registry recorded explicit process-group fallback. No unrelated process
was terminated and postflight owned children were zero.

At receipt preparation CPU measured 73% then 74%, so a fresh local full-suite
rerun was `SKIPPED_RESOURCE_THROTTLE`; no Python workload was launched by that
blocked attempt. The remote tested Provider is still complete.

## Pending closure

1. Push this direct receipt-only child of the tested head.
2. Wait for its automatically triggered 3.11/3.13 x seed 0/1/777 + compare matrix.
3. Independently download all 13 receipt artifacts and verify byte bindings.
4. Post literal tested/receipt evidence to PR #196, Issue #192, Issue #194, and Issue #31.
