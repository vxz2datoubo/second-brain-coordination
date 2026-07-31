# E28 Evaluation V2 Receipt

- task: `CODEX-E26-HARNESS-LEVEL-DIVERGENCE-ARCHIVE-MANIFEST-WPDCR-CONFORMANCE-CLOSURE-0020-E28`
- route epoch: `29`; Issue: [#23](https://github.com/vxz2datoubo/second-brain-coordination/issues/23); Draft PR: [#106](https://github.com/vxz2datoubo/second-brain-coordination/pull/106)
- branch: `codex/d2-evaluation-v2-0014-e22`
- completion signal: `CODEX_E28_E26_HARNESS_DIVERGENCE_ARCHIVE_MANIFEST_AND_WPDCR_CONFORMANCE_READY_FOR_GPT_REVIEW`
- reviewed/base: `07ce7e468949822b72975b9f8e3d18cc85c1f119`
- final tested head: `b578a14b613a9d34e058e951eb342f395b00c073`
- tested parent: `c790d0ee40a78b7a40644e22764c2409fcf12a85`
- tested tree: `d3f6b0854bbec8230ec605c32413ecfdd86ff8d8`
- remote main at completion reread: `a3faaab6509facf503b568c5e231bda55cdb27e8`

## Delivered

The R1 correction normalizes archive command paths to POSIX form on every host,
keeps root containment fail-closed, and makes the WPDCR validator require the
base contract plus `AUTONOMOUS_REMEDIATION_LEDGER` and
`MODEL_REASONING_AND_EXECUTION_PROFILE`. The final tested commit changes only
the three R1-authorized files.

## Evidence

| Evidence | Result |
| --- | --- |
| Local focused suite | 60 tests, exit 0 |
| Local public runner | exit 0; report `480975bdb61c81b2b47293476104582e4ef7e13fe7fe45ffcec2128f2666c9bc` |
| Local exact-head archive | 3 roots, 419 artifacts each, exit 0 |
| Archive SHA/size | `f5dbe7557d90cc62025bdf9ffb337c5d25c3105dfa0aca9b5ede880dd72e0c6a` / 901766 bytes |
| Exact-ref CI | workflow-dispatch `30649533447`, Python 3.11 job `91219114422`, Python 3.13 job `91219114333`, success |
| CI checkout head | `b578a14b613a9d34e058e951eb342f395b00c073` |

The full per-root and per-artifact manifest is in
`E28-COMPLETION-EVIDENCE.json`; the summarized matrix is in
`E28-ARCHIVE-PROVENANCE-MATRIX.yaml`.

## Negative evidence and boundary

The earlier Linux-green `c790d0e` run remains diagnostic only because Windows
exposed a separator defect. The first Windows failure is preserved in the
WPDCR, AMED ledger and Issue/PR comments. This package remains
`PUBLIC_SAFE / SYNTHETIC_ONLY / CANDIDATE_ONLY / research_only / NO_TRADE`.
It proves no market behavior, profitability, production readiness, account,
order or trading capability. Gate C/D and Issues #92/#108 remain frozen.

The later receipt-only commit SHA is externally anchored in the final PR and
Issue comments because a receipt file cannot truthfully contain its own future
Git commit SHA before that commit exists.
