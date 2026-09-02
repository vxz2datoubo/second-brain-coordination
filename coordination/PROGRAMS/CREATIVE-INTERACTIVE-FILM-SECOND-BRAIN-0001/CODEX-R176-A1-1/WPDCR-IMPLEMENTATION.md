# R176 implementation discovery and WPDCR

`agent_id: CODEX`  
`status: EXECUTOR_VERIFIED_ONLY`

## Seven discovery questions

1. **What authority existed?** Issue #534, route 176, the active claim, lease,
   reservation and pre-write snapshot authorized only A1.1 on the snapshot-bound
   Codex branch.
2. **What already existed at the implementation baseline?** A canonical JSON
   serializer and SHA-256-based creative ledger existed. The serializer was
   reused and made compatible with deeply frozen dataclasses; no noncanonical
   R175 implementation code was imported.
3. **What did not exist?** There was no multi-script registry, immutable script
   package, style registry, strict package parser, DirectorBrief/v2 selection
   boundary or repository workflow at the baseline.
4. **Who owned adjacent state?** GPT R172 retained PlayerCampaign/session
   authority. WorkBuddy #532 retained its validation and attack-test subtrees.
5. **What data was admissible?** Only newly authored synthetic, non-explicit,
   approval-tagged fixtures and synthetic asset IDs. No Eustia files, photos,
   comments, credentials, customer data or generated media were read or copied.
6. **What deterministic primitive was selected?** Existing `canonical_json`
   plus SHA-256, extended with deep-freeze-safe dataclass traversal and strict
   duplicate-key JSON parsing.
7. **What proves the boundary?** A minimal four-field frozen selection object,
   37 tests, an allowlist verifier, provider-import scan, patch check and a
   clean-clone reproduction at the exact implementation checkpoint.

## Actual work process

The implementation began from the exact frozen baseline in a clean task-owned
worktree. It added contracts, registry validation, two fixtures, negative and
tamper tests, documentation, a scope verifier and an offline CI workflow. One
ordinary checkpoint was committed and pushed before clean-clone reproduction.

## Planned versus actual difficulty

Planned difficulty was D2 and remained D2. Deep immutability required adapting
the shared canonical serializer so frozen mapping proxies serialize without
copy failures. The change preserved all pre-existing hash and replay tests.

## Failed attempts and pivots

- The first local command tried `pytest`, which is not installed; the repository
  is unittest-based, so the implementation was converted to zero-dependency
  unittest tests.
- The first fixture validation treated a narrative character's `secret` field
  as a credential secret. The gate was narrowed to credential-specific keys so
  narrative secrets remain legal while token/password/cookie fields stay blocked.
- The first clean-clone command used an incompatible absolute unittest discovery
  form. It failed before test import; running from the clean clone root passed.

## Discoveries

- Deep-freezing nested content is necessary; a frozen outer dataclass alone does
  not prevent story or asset mutation.
- Exact triple identity and a separate revision-to-hash index are both needed:
  the triple supports lookup while the index prevents replacing an approved
  revision with different content.
- Strict duplicate-key parsing is required because ordinary JSON parsing would
  silently let a later identity field replace an earlier one.

## Expansion opportunities

| Opportunity | Owner | Cost | Risk | Trigger |
|---|---|---:|---|---|
| Persistent package catalog using the same immutable identity | Codex | medium | migration drift | A1.2 authorization |
| DirectorBrief/v2 compiler consuming only `DirectorScriptSelection` | Codex | medium | authority creep | explicit director slice |
| PlayerCampaign selection binding | GPT R172 owner | medium | dual session authority | R172 integration gate |
| Extra adversarial/property tests | WorkBuddy | low | false assumptions | WB batch reaches relevant step |

## Unresolved unknowns and negative results

- No Python 3.11 interpreter exists locally. CI uses the user-requested single
  primary Python 3.13 suite rather than duplicating every CI run.
- No external provider, deployment or production-storage capability was tested;
  those capabilities are deliberately absent and unauthorized.
- No independent reviewer has evaluated the final exact head.

## Cross-agent coordination and unaffected work

No file under `tests/workbuddy/**`, `tools/workbuddy/**` or `WORKBUDDY-R175/**`
was changed. No PlayerCampaign/session source was introduced. Frozen PRs and
historical candidates were neither imported nor modified.

## System feedback and prevention lessons

Evidence should distinguish a command-harness failure from product-test failure
without deleting either fact. Future review activation should occur only after
the final exact head exists; delivery receipts and CI remain evidence, not an
independent verdict.
