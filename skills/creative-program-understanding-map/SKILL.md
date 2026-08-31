---
name: creative-program-understanding-map
description: Translate an evolving creative-runtime or second-brain program into a traceable four-layer user understanding map, with numeric anchors, evidence tiers, drift checks, and a handoff packet. Use when planning, implementing, explaining, auditing, or handing off interactive-film, AI-director, or knowledge-base work.
---

# Creative Program Understanding Map

Use this skill to keep product intent, runtime facts, evidence, and explanations
aligned while the creative program evolves. It is a project skill: it does not
authorize deployment, external generation, credential access, public release,
or a canonical knowledge-store write.

## Non-negotiable rules

1. **Record before inference.** Preserve the direct request, source reference,
   commit, test output, or runtime event before creating any conclusion.
2. **Do not promote a hypothesis to a fact.** Keep observed, inferred, tested,
   independently reproduced, and externally attested claims distinct.
3. **Every number needs a unit, source, time basis, and threshold.** A score
   without those four fields is a display value, not a decision input.
4. **One source of record per fact class.** A summary, cache, dashboard, or
   generated briefing may never overwrite its source ledger.
5. **Human decisions remain explicit.** This skill can describe a decision and
   its tradeoffs; it cannot infer approval for budget, credentials, publication,
   deployment, or content-boundary changes.

## The four understanding layers

For every material capability, create one `UnderstandingCard/v1` and classify
each statement into exactly one layer:

| Layer | Meaning | How to present it |
| --- | --- | --- |
| `explicit_known` | The user directly stated it or formally approved it. | State it as a requirement and quote/reference the authority. |
| `implicit_known` | The user appears to rely on it, but did not explicitly say it. | State it as a labelled inference with confidence and ask only if it changes scope or risk. |
| `explainable_unknown` | The user did not state it, but can act on a short model. | Give a plain-language model, options, benefits, costs, and a recommendation. |
| `opaque_unknown` | The user does not need implementation detail to choose safely. | Expose the impact, guardrail, observable signal, and escalation condition; hide needless internals. |

Never put private chain-of-thought in a card. Record observable evidence,
assumptions, decisions, and testable consequences only.

## Required card fields

```yaml
schema: UnderstandingCard/v1
card_id: UC-<stable-slug>
subject: <capability or decision>
layer: explicit_known | implicit_known | explainable_unknown | opaque_unknown
statement: <short, falsifiable statement>
authority_ref: <issue, file, event id, URL, or commit>
evidence_tier: E0 | E1 | E2 | E3
confidence: 0.0-1.0
valid_from: <ISO-8601 UTC>
supersedes: []
numeric_anchors: []
drift_checks: []
decision_impact: none | informs | blocks
owner: USER | CODEX | GPT | HUMAN_REVIEWER
human_explanation: <plain Chinese explanation>
```

## Evidence tiers

- `E0_observed`: a recorded request, source item, or unverified report.
- `E1_deterministic`: a repeatable local parser, hash check, unit test, or
  state-machine replay passes.
- `E2_clean_reproduced`: the same result is reproduced in a fresh worktree or
  clean environment from committed inputs.
- `E3_independently_attested`: a genuinely uninvolved reviewer or an external
  signed attestation validates a precisely identified artifact.

An executor's test is `E1` or `E2`; it is never an independent acceptance by
itself.

## Numeric anchors and drift

Use `MetricAnchor/v1` for any value used to decide, compare, or gate work.

```yaml
schema: MetricAnchor/v1
metric_id: M-<stable-slug>
name: <what is measured>
unit: count | ratio | seconds | bytes | sha256 | enum
direction: higher_is_better | lower_is_better | exact_match | bounded_range
baseline: <number/string>
current: <number/string>
target: <number/string>
source_ref: <test, event range, commit, or artifact>
measured_at: <ISO-8601 UTC>
hard_gate: true | false
warning_threshold: <explicit rule>
failure_threshold: <explicit rule>
```

For hashes use `direction: exact_match`; for safety conditions use an enum or
boolean hard gate rather than inventing a composite score. For quality scores,
store each contributing measurement separately and state the formula/version.

## Working procedure

1. Read the authoritative program status, current branch SHA, tests, and source
   records. Mark the time of observation.
2. Build a capability map spanning: user intent, story/runtime state, director
   output, knowledge candidates, evidence, and handoff.
3. For each edge, name its source of record, allowed writers, serializer/hash,
   failure behavior, and reader-facing explanation layer.
4. Add or update cards and anchors only from recorded evidence. Represent a
   changed fact with `supersedes`; never silently overwrite history.
5. Create deterministic drift checks. Prefer exact IDs/hashes and state replay
   for identity; use bounded thresholds only for measured quality/performance.
6. Test a happy path, a corruption/contradiction path, a stale-reference path,
   and a clean-environment replay.
7. At handoff, emit one packet containing exact head/base, source inventory,
   cards changed, anchors, commands/results, known risks, rollback, and the
   next concrete action.

## Coordination map

| Domain | System of record | Writer | Consumer | Mandatory guard |
| --- | --- | --- | --- | --- |
| Product approvals | issue/decision record | USER or delegated integrator | all agents | explicit authority reference |
| Story state | append-only creative ledger | runtime | CLI, director, replay | hash-chain and graph replay |
| Director plan | deterministic compilation | director compiler | offline generator | content/asset/continuity gates |
| Knowledge candidate | review packet store | runtime/user correction | human reviewer | no canonical write before approval |
| Evidence | committed test receipt and CI artifact | executor/CI | reviewer | exact commit and command |
| Explanation | understanding cards | any agent with evidence | USER | four-layer classification |

## Handoff template

```yaml
schema: CreativeProgramHandoff/v2
source_agent: CODEX
target_agent: GPT_INDEPENDENT_REVIEWER
reviewer: null
base_sha: <sha>
head_sha: <sha>
execution_window: continuous_until_user_closeout
evidence_tier_reached: E2_clean_reproduced
changed_contracts: []
understanding_cards_changed: []
metric_anchors: []
commands: []
negative_cases: []
known_risks: []
rollback: <normal revert from a successor branch>
next_action: <one concrete action>
```

## References

- Read [references/evidence-and-drift.md](references/evidence-and-drift.md)
  for the decision rules and source register.
- Read [references/explanation-layers.md](references/explanation-layers.md)
  before writing a user-facing mapping or audit summary.
