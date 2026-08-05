# E47 Tested-Head Evidence

## Exact external matrix

- workflow: `BrainOps E47 Exact Head`
- tested SHA: `f6835949b111134dea5734217a2074d169f897d3`
- run: [30849891380](https://github.com/vxz2datoubo/second-brain-coordination/actions/runs/30849891380)
- checkout assertion: passed in both jobs
- Python 3.11 job: `91807069283`, success
- Python 3.13 job: `91807069160`, success

The workflow uses `github.event.pull_request.head.sha || github.sha` as its
checkout ref and compares the resulting `HEAD` to that expected SHA before any
compile or test step.

## Local evidence at the tested head

Command:

```text
PYTHONPATH=<PROGRAM_ROOT>/src python -m unittest discover -s tests -p "test_e*.py" -v
```

- interpreter: Python `3.13.13`
- compile exit: `0`
- test exit: `0`
- result: `172` tests passed
- stdout SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- stderr SHA256: `a1b104eb7d93710eee54fd31c35408310257f64e9e9c9d0259d8f3abd0b852b3`

The same full local suite also passed under Python `3.12`; Python 3.11 is
verified by the exact-head external matrix rather than claimed locally.

## Receipt gate exercise

The offline pre-receipt validator accepted the tested head only after it was
given the matching `30849891380` 3.11/3.13 successful matrix and all seven
lifecycle stages. It rejects missing or mismatched CI, incomplete matrix/stage
coverage, placeholders, runtime/test files in a receipt, and an incorrect
receipt parent.
