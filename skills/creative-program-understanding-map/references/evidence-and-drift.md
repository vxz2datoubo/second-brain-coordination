# Evidence, provenance, and drift rules

## Why this exists

The creative runtime is simultaneously a game state machine, a director input,
and a knowledge-candidate source. A plausible prose summary is therefore not
enough: an error in one layer can become a false story fact, an invalid shot,
or a misleading reusable lesson. The system records exact inputs and applies
deterministic validation before it explains or promotes anything.

## Evidence decision table

| Claim type | Minimum evidence | May block work? | May enter canonical knowledge? |
| --- | --- | --- | --- |
| User-requested product direction | direct request/decision record (E0) | yes | no, until separately reviewed |
| Runtime state or transition | valid chain plus graph replay (E1) | yes | candidate only |
| Reproducible implementation result | clean clone/worktree test (E2) | yes | candidate only |
| Release/acceptance conclusion | exact-head independent review or signed attestation (E3) | yes | subject to authority |
| Web/paper insight | immutable source URL plus extracted proposition (E0) | informs | candidate only |

## Drift rules

1. **Identity drift:** SHA, event hash, graph revision, transition ID, and
   source hash must match exactly. Any mismatch is fail-closed.
2. **Temporal drift:** every fact has observation time; effective story facts
   additionally have event sequence. A later record supersedes an earlier one
   only with an explicit link.
3. **Semantic drift:** compare a replayed prefix against the graph transition,
   not merely against the final state. A correct final state cannot excuse an
   invented intermediate consequence.
4. **Metric drift:** compute only against a versioned formula and baseline.
   Changes to formula, population, data source, or time window create a new
   metric revision, not a silent new value.
5. **Authority drift:** a branch, prompt, or CI success never changes who is
   authorized to approve, publish, spend, or use credentials.

## Source register

| Source | Durable lesson used here | Integration decision |
| --- | --- | --- |
| [GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations) | Provenance claims need an explicit verification step; they are not proof that the artifact is safe. | Keep exact SHA, command, and clean-run receipts. Reserve signed attestations for release artifacts, not frequent source edits. |
| [GitHub reusable workflows](https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations) | Deterministic validated work should be centralized and reused rather than copied into each route. | Later factor the continuous-build verification matrix into a reusable workflow after its behavior stabilizes. |
| [Less Context, More Accuracy](https://arxiv.org/abs/2606.09900) | Append lossless episodes, extract compact facts asynchronously, and invalidate rather than delete conflicting facts. | Keep the creative event ledger authoritative; derived cards and candidates carry supersession rather than overwrite history. |
| [Zep temporal graph memory](https://arxiv.org/abs/2501.13956) | Long-lived agents require temporal links and provenance beyond static-document retrieval. | Record observed/effective time, source reference, and relationship edges in the program map. |
| [SodaMem](https://arxiv.org/abs/2608.08055) | Typed facts with mandatory provenance and temporal contradiction links make outputs citable and current. | Use typed cards, evidence tiers, and explicit `supersedes` links; do not treat research claims as automatic truth. |
| [OpenAI harness engineering](https://openai.com/index/harness-engineering/) | Long-running agents benefit from isolated worktrees, executable verification, and application legibility. | Use a persistent isolated branch plus clean-environment reproduction; do concentrated review at the close-out boundary. |

## Scope and caution

The cited papers inform architecture; they do not prove the quality of this
repository. Their reported results and benchmarks are not copied as project
metrics. External URLs are research provenance only, not a license to import
content, assets, credentials, or code.
