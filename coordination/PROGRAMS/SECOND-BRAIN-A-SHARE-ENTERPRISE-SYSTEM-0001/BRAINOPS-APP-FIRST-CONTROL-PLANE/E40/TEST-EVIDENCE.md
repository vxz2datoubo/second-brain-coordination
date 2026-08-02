# E40R1 Test Evidence

## Local Deterministic Validation

Working directory: task-isolated E40R1 worktree.

```powershell
$env:PYTHONPATH = "<worktree>\\coordination\\PROGRAMS\\SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001\\BRAINOPS-APP-FIRST-CONTROL-PLANE\\src"
python -m unittest discover -s "<worktree>\\coordination\\PROGRAMS\\SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001\\BRAINOPS-APP-FIRST-CONTROL-PLANE\\tests" -v
python -m compileall -q "<worktree>\\coordination\\PROGRAMS\\SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001\\BRAINOPS-APP-FIRST-CONTROL-PLANE\\src"
```

Result: `126` tests passed in `4.292s`; `compileall` exit code `0`. The
captured unittest standard-error SHA256 is
`2c0c0f9e7acef77c098c78d94554380281bf12d2eff7ad476fd7383347277d51`.
Unittest wrote no standard output (SHA256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).

Coverage includes legacy pre-canary fail-closed semantics, executable-route
proofs, malformed/expired/wrong-actor approvals, one-shot atomic reservation,
duplicate suppression, fallback eligibility, terminal immutability, concurrent
claims, workflow exact-head assertions, and prohibited terminal states.

## Corrected Local Failures Before Canary Execution

The imported E39 tests initially referenced workflows outside the E40R1
allowlist. They were redirected to the task-owned E40R1 workflow. A missing
identifier validator import and an E40-specific fixture issue/comment pairing
were then corrected. These failures were local implementation feedback; no
real canary was invoked until the final passing suite.

## Remote Validation

Remote Python 3.11 and 3.13 exact-head CI is pending after the substantive
commit is pushed. The evidence-only receipt will be created only after that CI
has passed.

## Public-Safety Scan

The changed surface was scanned for credential-like literal values. The only
two pattern matches were the deliberately generic detection regular expressions
in `src/brainops_control_plane/models.py`; neither is a credential value.
