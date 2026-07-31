# Test Run Receipt

> `agent_id: CODEX`
>
> `tested_commit: 216ff0e053907d5eecad9fe4245cc163991cb69f`
>
> `tested_tree: 663e7392f31c2d70e19042e7a942ea2ccef4c2d2`
>
> `boundary: synthetic and static candidate validation only`

## Git Chain

| Item | SHA |
|---|---|
| Base | `5a36ebcfaf3bd890d7c2a4a16c29a4b03cb02398` |
| Plan commit | `be60caad11f37d87c4e43710959882cb3cc76937` |
| Substantive parent | `be60caad11f37d87c4e43710959882cb3cc76937` |
| Substantive commit | `216ff0e053907d5eecad9fe4245cc163991cb69f` |
| Substantive tree | `663e7392f31c2d70e19042e7a942ea2ccef4c2d2` |

`git merge-base --is-ancestor` confirmed that the base is an ancestor of the
substantive commit.

## Runtime Tests

Command:

```powershell
python -B coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL/run_all_tests.py
```

Result:

```text
Ran 73 tests in 0.134s
OK
exit_code=0
output_sha256=740adf67176d4fe1dd6c459353c5f5a7b1ffbb44d1e9c0e79ab0e4acadde0139
```

The output file was created in the local temporary directory and is not part of
the repository.

## Static Validation

```text
PYTHON_AST_OK=18
JSON_OK=1
YAML_OK=6
STRICT_YAML_OK=6
```

The strict YAML pass recursively rejected duplicate mapping keys.

## Public and Secret Scans

```text
branch_changed_files=36
changed_file_secret_scan_matches=0
common_kernel_named_vendor_matches=0
raw_capture_committed=false
canonical_peos_sha256=261afc7d16ecb35ca139e68e9ae6e2724104ee8fc8e3c7abdd97a7fca714af51
```

The full-repository secret scan has a pre-existing historical fixture match
outside this branch's change set. It was not copied or modified. The scoped
scan of all files changed by this branch has zero matches.

## Key Artifact Hashes

| Artifact | SHA256 |
|---|---|
| Protocol blueprint | `05159ca37fda80ec325fb1a3058e4b822e0dd3b973ea84af7952f4318534f4cf` |
| Runtime Prompt | `dbce9b128d34de728a499d227bb3aa23c984cd7b35c0968b5c79802e07973bcc` |
| Aggregate Schema | `51b05b2d9dae6565d1aac7d9a5e65134bad68547eb6cc7e3c8a372e88241743a` |
| Named Skill | `56164818261013532782ee381a4bb68b69f3f03268609124911a44c1a0cfcc6b` |

## Claim Limits

The evidence proves the candidate reference implementation and documentation
behave as tested. It does not prove cross-model equivalence, production
readiness, provider optimality, or market validity. Runtime activation remains
disabled.

## GPT Review Remediation Evidence (2026-07-30)

This receipt supersedes the earlier 73-test local receipt for the current
candidate review. It is anchored to the substantive hardening commits rather
than to its own future commit:

| Item | Value |
|---|---|
| Hardening commit | `67a4c68c290d8b7db02b5c44d553c7add3b0cd5e` |
| Archive-safety commit | `7ff963753f1ef50c56635bcef872f05f584b5dcb` |
| Reviewed tree | `bd7daaf9d38cb89c419559340e6b625bf6e22242` |
| Draft PR | [#107](https://github.com/vxz2datoubo/second-brain-coordination/pull/107) |
| Parent issue | [#31](https://github.com/vxz2datoubo/second-brain-coordination/issues/31) |

Validated locally in an isolated test environment:

```text
PASS_84_OF_84
Draft202012 meta-schema: PASS
serialized instances for all 10 contracts: PASS
AST files: 20
strict YAML files: 8
changed-file secret matches: 0
common-prompt vendor matches: 0
raw capture files: 0
machine evidence sha256: b06c5088d8a141f7f83e1ba135136cc70306decb866d7a5841bcff0b0b29b00e
```

Three separately generated clean Git archives ran the same machine-readable
verification under `PYTHONHASHSEED=1`, `2`, and `3`. All emitted the identical
report hash:

```text
8ee88ceec3dc4cae385d6a26133210c374208c30872782f869ee49e080a65954
```

The initial archive run found a hidden `.git` dependency in the
public-neutrality test. Commit `7ff9637` replaces it with a fixed repository
layout reference; the three subsequent clean-archive runs passed. This is a
test-hardening finding, not evidence of runtime activation.

## E29 Final Tested Evidence

The E29 route revalidated PR #107 from reviewed head
`ccbdcd27a8e4da0b653de3c387a18e87e3a33e92` and finished at tested head
`686518aa93e37613d6c8e4ab936d0fdd816b403c` with tree
`4b95f956eb0bd120deff2d3462fa0da9077843bc`. The substantive E29 commit is
`e16878a4007e67718d6419d0f7fa9dca490dfa7a`; the two bounded corrective commits
are `b8332f7b33c56c1ed9898e37cbcee2b688072018` and
`686518aa93e37613d6c8e4ab936d0fdd816b403c`.

The local command passed 91/91 tests. The pull-request CI run
`30669990210` passed on Python 3.11 and 3.13 with 51 changed files scanned,
21 AST files, 14 strict YAML files, 0 secret matches, 0 raw-capture files and
0 vendor-leakage matches. The manual corroborating run was `30669990212`.

Three clean archive runs under `PYTHONHASHSEED=1`, `2` and `3` produced the
same machine-readable report hash:
`f04fc18f4d7f34fb24cb5242511e1d7af7b641dfff7d60466b05f4d167d758cc`.
The verifier reported exact head/tree context, Draft 2020-12 validation,
strict duplicate-key rejection and a frozen 91-case manifest. Adapter
implementation, cross-model evaluation and shadow activation remain disabled.
