# GitHub-to-Local Operations Roadmap

agent_id: CODEX

## Owner outcome

The program has two deliberately separate destinations:

1. **GitHub-first verification and demonstration** — all executable source,
   synthetic fixtures, tests, design maps, and reproducibility tooling are
   versioned and runnable without secrets, paid services, customer material, or
   a local chat history.
2. **Local customer operations, later** — only after the GitHub runtime is
   accepted does a separately configured local adapter receive actual customer
   inputs. Customer data, accounts, media, caches, and credentials never move
   back into Git history.

This is a staged delivery plan, not authorization to collect customer data
today.

## Current GitHub-runnable surface

| Capability | GitHub implementation | What it proves | What it does not prove |
| --- | --- | --- | --- |
| Exact source identity | `creative-runtime-offline.yml` checks out the exact event head | CI is executing the submitted commit, not a merge approximation | a human has accepted product behavior |
| Runtime tests | Python 3.11 and 3.13 run `test_creative*.py` | deterministic contracts work on clean Linux runners | real customer load or real media quality |
| Offline end-to-end route | `tools/verify_creative_runtime.py` | play → replay → director → simulated generation → feedback → audit is reproducible | any external provider is safe or approved |
| Safety boundary | static scan and no-provider offline adapter | this lane reads no credentials and makes no network/media request | all future local adapters are automatically safe |
| Durable evidence | ledger, v2 migration, receipts, feedback, workspace audit | every demo result has a source chain | an independent product reviewer has accepted it |
| Verified client projection | `InteractiveFrame/v1` and exhaustive `VerifiedInteractiveScenarioCatalog/v1` | a static player can navigate only source-bound, graph-covered choices | a browser has story authority or can accept customer data |
| Downloadable synthetic demo | Actions uploads `creative-runtime-synthetic-experience-<SHA>` with `experience.json` and a static player | GitHub produced a frame/catalogue artifact bound to the exact commit | public release, deployment, live media, or a signed production attestation |

The workflow is intentionally read-only and has `contents: read`. It cannot
publish, deploy, use an account, upload a secret, or call a paid generator.
The only uploaded result is a short-retention, repository-synthetic JSON
artifact plus its dependency-free static viewer; its envelope explicitly says
that it has no customer data and no external-provider result.

The same artifact also includes `VerifiedInteractiveSequencePlan/v1`: each
verified timeline prefix has its own frame, director plan, cut policy, and
duration. It remains a render/planning receipt, not a request to generate or
publish media.

The artifact job does not trust its just-written label: it immediately runs
`python tools/verify_experience_artifact.py --expected-head <SHA> --package-dir
creative-runtime-experience`.
That verifier rebuilds the fixed demo route and all covered catalogue paths
from the checked-out source, requires canonical JSON equality, checks the
fixed four-file layout and manifest hashes, and compares the downloaded player
and guide byte-for-byte with the same exact-head source. A reviewer can repeat
the same command after downloading the complete package, with no network,
account, provider, or executor chat history.

## Interactive delivery mapping

The runtime now has one-way authority from immutable evidence to presentation:

```text
append-only CreativeLedger
  -> exact-prefix timeline replay
  -> verified director input + hard quality gate
  -> InteractiveFrame/v1 (one current render state)
  -> VerifiedInteractiveExperience/v1 (one played route)
  -> VerifiedInteractiveScenarioCatalog/v1 (every covered legal route)
  -> static HTML player (renders nodes; follows precomputed edges only)
```

| Surface | Receives | Can do | Cannot do |
| --- | --- | --- | --- |
| `creativectl frame` | existing session ledger | show one verified current frame | decide an action or invent a state |
| `creativectl experience` | existing session ledger | export every prefix in the played route | expose an alternative branch not earned by that ledger |
| `creativectl catalog --scenario night_signal` | fixed synthetic graph | export all tested nodes/edges after exhaustive coverage | introduce a transition or state patch |
| `apps/web/verified_experience_player.html` | GitHub-built artifact | render, go back, and follow evidence-bound edges | make network calls, load a provider, store customer inputs, calculate narrative state |

The browser player validates envelope/status/boundary/node-edge references but
does **not** become a second verifier. Exact semantic verification remains in
the Python runtime and GitHub CI. Any mismatch is an error, not a “best effort”
fallback. This keeps the client simple while retaining a single deterministic
source of story authority.

## Local real-time session safety already present in the synthetic runtime

The future local service must never apply a click against a frame that has
already changed. The repository now enforces the same rule without receiving
customer content:

```text
client reads InteractiveFrame.frame_id
  -> client submits choice plus --expected-frame-id and optional opaque command_id
  -> slot-scoped non-blocking mutation lease
  -> runtime reloads ledger and compares exact prior frame ID
  -> append legal graph event + atomically replace complete session JSON
  -> return prior_frame_id and current_frame_id
```

If the slot is busy, the client submits a stale frame ID, or an interrupted
atomic-write temporary file exists, the update fails closed and the existing
session bytes are preserved. The correct recovery is to reload the verified
frame, not to retry a blind action. The command remains optional for simple
single-user CLI use, but a future local client gateway should require
`--expected-frame-id` (or its protocol-equivalent field) on every mutation.

For network retry safety, callers may also use `cmd_<20 lowercase hex>` as a
`command_id`. It is included in the immutable player-action event itself. A
repeated identical command returns its original frame boundary without
appending a second event; reusing the same ID for a different action is a hard
error. This is intentionally ledger-backed rather than a separate mutable
receipt cache, so replay, migration, audit, and evidence verification retain
the same operation identity.

Before any future local gateway performs a mutation, it can run the already
GitHub-tested read-only command `creativectl --workspace <synthetic-workspace>
operations`. Its `CreativeRuntimeOperationsReport/v1` enumerates only
confinement-safe slots, replays each ledger, checks any V2 source binding, and
reports fixed counts for valid slots, invalid slots, active mutation locks,
stranded atomic-write temporaries, and unsafe path shapes. It repairs nothing:
any nonzero risk count sets `mutation_safe: false`, so an operator must first
investigate rather than silently clear a crash/concurrency marker.

## Four-layer operational map

| Information layer | GitHub phase | Later local phase | Rule |
| --- | --- | --- | --- |
| Explicitly known | safety policy, non-explicit content, no credentials, no auto-paid generation | owner-approved intake scope, retention and budget | fixed written contract |
| Implicitly known | contributors need reproducible checks | operators need fast route/session lookup | label inference; do not treat it as approval |
| Explainable unknown | CI failure reason, timeline mismatch, quality gate result | intake validation, consent/retention response | show cause, impact, option and stop condition |
| Opaque unknown | hash serialization and runner internals | encryption implementation and account-provider internals | expose a bounded status/evidence reference, not secrets |

## Future local adapter contract — boundary skeleton implemented, no operations

`creative_runtime.local_intake` now supplies a deterministic projection and
gate for the fixed fields below. It does not perform filesystem, network,
credential, vault, media, provider, or customer-content operations. The actual
local adapter remains a new, separately reviewed boundary. It may not
reuse the GitHub CLI's workspace paths for raw customer material.

```text
Customer-local input
  → consent / schema / size / malware gate
  → local customer vault (gitignored)
  → sanitized CreativeRequest/v1 projection
  → existing offline story + director contracts
  → local result pointer and immutable operation receipt
  → human review / explicitly confirmed provider action, if ever approved
```

Required future fixed fields include:

| Field | Type | Gate |
| --- | --- | --- |
| `request_id` | UUID or equivalent immutable ID | exact uniqueness |
| `customer_reference` | local opaque ID, never a GitHub username/email | vault-only lookup |
| `consent_revision` | versioned string | must match an approved local policy |
| `input_hash` | SHA-256 | exact identity check |
| `retention_deadline` | RFC 3339 timestamp | no processing after expiration |
| `content_rating` | controlled enum | non-explicit boundary remains hard |
| `cost_limit` | integer minor currency units | no paid call above explicit owner budget |
| `provider_confirmation` | explicit one-time human action | absent means no external call |

No local customer adapter is allowed to read `.env`, browser cookies, account
stores, or provider tokens indirectly. Any future credential use requires an
explicit, separate approval and a local-only secret provider.

## Promotion gates

| Gate | Required evidence | Decision authority |
| --- | --- | --- |
| GitHub runnable | exact-head Actions pass, clean reproduction receipt, source-bound audit | CODEX supplies evidence; GPT independently reviews at close-out |
| GitHub accepted | independent review plus owner-directed merge authority | GPT reviewer/integrator and owner |
| Local adapter design | privacy/consent/retention/cost contract and threat review | owner approval required |
| Local synthetic pilot | no customer data; local receipt and rollback drill | owner approval required |
| Customer intake | explicit data scope, budget, retention, incident path, support owner | owner approval required |

## Numeric anti-drift rules

- IDs, commits, receipt hashes, timeline hashes, input hashes and consent
  revisions use **exact equality**. There is no average score that can override
  an identity mismatch.
- Ratings remain integer `0..5`; money is integer minor units; sizes are bytes;
  durations are milliseconds or seconds with a stated unit.
- Every metric includes a source, observed timestamp, unit, formula revision,
  threshold and gate classification before it is used for an automated decision.
- GitHub synthetic results and later customer-local results are separate metric
  populations. They must never be averaged into one “quality” number.

## Current status

The GitHub-first stage is under continuous construction on
`codex/creative-runtime-continuous-build`. It is intentionally **not** yet a
customer intake service, public deployment, media generator, or payment path.
The next safe implementation work remains within the GitHub synthetic runtime:
more route coverage, deterministic director checks, and reproducible CI.
