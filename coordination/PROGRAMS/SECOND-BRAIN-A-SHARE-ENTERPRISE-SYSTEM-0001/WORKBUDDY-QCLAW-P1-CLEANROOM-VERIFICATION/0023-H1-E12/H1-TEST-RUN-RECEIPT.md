# H1 Independent Verifier Test Receipt

## Identity

| Field | Value |
| --- | --- |
| task_id | `CODEX-INTEGRATED-H1-CLOSURE-AND-D2-SYNTHETIC-GAME-CORE-0002-E10` |
| agent_id | `CODEX` |
| verifier-tested head | `b2d8603859902da9741dda016a3daf3ffeb0772b` |
| receipt head | `THIS_COMMIT` |
| local execution carrier | 3111121b01f54a161a195a52bd81b2f737142542; verifier blob equals published commit |
| frozen QCLAW source | `63c344084d9af86cb26c1cc65a30d409fefa872f` |
| boundary | `PUBLIC_SAFE / SYNTHETIC_ONLY / candidate_only / research_only / NO_TRADE` |

The verifier independently extracted each of the 15 expected frozen P1 artifacts
from Git, compared every extracted byte sequence with its Git object, then ran the
extracted validator. It does not read a service, account, live market source, or
credential material.

## Literal Commands And Results

Commands were executed from the repository root with Python 3.13.13 on Windows.
`stdout_sha256` and `stderr_sha256` refer to the verifier process; child hashes
refer to the extracted P1 validator.

| Command | Top exit | Child exit | Status | stdout_sha256 | stderr_sha256 | child stdout_sha256 | child stderr_sha256 |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| `python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/WORKBUDDY-QCLAW-P1-CLEANROOM-VERIFICATION/0023-H1-E12/H1-INDEPENDENT-VERIFIER.py normal` | 0 | 0 | PASS; `37 PASS / 0 FAIL / 0 SKIP`; 14 validator-hashed files | `e49ad73a9fa4ca45c38c0bb7577a88d8c290b44e7e771190ea99ee1b22912d0a` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `ca75bad8b1d912264b82d7691d1ee88ccf3e56039d3780f2390415e958ba8975` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/WORKBUDDY-QCLAW-P1-CLEANROOM-VERIFICATION/0023-H1-E12/H1-INDEPENDENT-VERIFIER.py nt1` | 1 | N/A | expected public-safety detection | `b6bee4d9f9079ab87683cfd69e7301b7b8545d075baf3cfddc55f910fd661c13` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | N/A | N/A |
| `python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/WORKBUDDY-QCLAW-P1-CLEANROOM-VERIFICATION/0023-H1-E12/H1-INDEPENDENT-VERIFIER.py nt2` | 1 | 1 | expected missing-artifact rejection; `36 PASS / 1 FAIL / 0 SKIP` | `75ecfaacfc176a969ab4bfb1938eec589c29ea098db13f43548be35de9562ab3` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `c0771aa58a939052b161cefed8d6759f7c01e573ed966cb10b4228650b4f9038` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/WORKBUDDY-QCLAW-P1-CLEANROOM-VERIFICATION/0023-H1-E12/H1-INDEPENDENT-VERIFIER.py nt3` | 1 | 7 | expected child-exit propagation | `d5bac35ab9a87a99d3ea80254426bed3fb66f6e815e76f5efa376a686ba7bacd` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

All temporary extraction and negative-test directories were removed; each run
reported `cleanup_status=PASS`. The validator's 14-file hash count is its own
declared mandatory set; the independent verifier checked all 15 frozen artifacts,
including the validator itself, before invoking it.
