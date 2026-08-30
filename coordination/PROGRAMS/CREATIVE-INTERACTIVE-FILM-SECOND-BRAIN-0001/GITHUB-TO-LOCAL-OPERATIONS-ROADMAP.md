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

The workflow is intentionally read-only and has `contents: read`. It cannot
publish, deploy, use an account, upload a secret, or call a paid generator.

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
