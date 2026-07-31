# E26 Test Run Receipt

Tested executable commit: `b45ab1e27b066edfdf8354c580702406bc4a49ae`.

| Evidence | Result |
| --- | --- |
| Local focused suite | `57` tests, exit `0` |
| Local public runner | exit `0`; canonical report `5115ec6cc49edd9dbce1873de70f16d6efe7b36679d1c8820ebdf27169f85c88` |
| Exact remote workflow | [run 30590950622](https://github.com/vxz2datoubo/second-brain-coordination/actions/runs/30590950622), `workflow_dispatch`, head `b45ab1...`, success |
| Python 3.11 job | job `91032943998`, focused suite, runner and archive step passed |
| Python 3.13 job | job `91032944055`, focused suite, runner and archive step passed |
| Exact archive proof | three independent archive roots all passed on both Python versions |

The archive runner stdout SHA-256 was
`05cf11b1bf10231decab7940793f2493762cc45d57d7273de158d7fbd20aa168`.
Focused unittest stderr includes its duration and therefore differs across
archives; this variance is recorded rather than normalized away.

The earlier PR-event run `30590806984` passed but archived a temporary merge
SHA. It is retained as a diagnostic and not used as exact-commit evidence.
