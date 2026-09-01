---
name: interactive-cinematic-systems-mapping
description: Map an interactive-film, AI-director, player-state, private-media, operations, or creative-knowledge decision into four user-understanding layers, source-bound interfaces, numeric anchors, drift checks, and multi-agent ownership. Use when planning, implementing, explaining, auditing, or handing off this creative platform; do not use it as execution authority or permission for external models, real user data, publication, or deployment.
---

# Interactive Cinematic Systems Mapping

Turn a product request, implementation fact, research result, operational
constraint, or unexplained subsystem into a traceable decision map. The output
must help the program owner understand what matters without pretending every
technical detail needs a human decision.

This is a candidate project skill. It does not make an unmerged branch
canonical, grant an Agent a route, approve a provider, or authorize credentials,
personal media, paid generation, public release, deployment, trading, or a
canonical second-brain write.

## Four-layer model

Classify each material statement into exactly one layer:

- `explicit_known`: directly requested or formally approved by the user.
- `implicit_known`: a high-confidence inference needed to realize the request;
  label it as an inference and do not treat it as approval.
- `explainable_unknown`: unfamiliar but decision-relevant; explain what it is,
  what changes, benefits/costs, and the recommended decision point.
- `opaque_unknown`: the user need not understand internals; expose the guard,
  observable signal, owner, and stop condition.

Never record private chain-of-thought. Record observable evidence, assumptions,
decisions, interfaces, and falsifiable consequences.

## Required workflow

1. Fresh-read canonical main, the active route, exact branch SHA, and the
   relevant source-of-record files. A Baton or candidate branch is navigation,
   not authority.
2. Identify the affected module and interface edge: intake, intent, story
   runtime, drama selection, director compilation, asset/appearance continuity,
   media job, operations, evidence, or knowledge candidate.
3. Create or update a mapping card with one layer, source reference, evidence
   tier, confidence, owner, allowed writer, failure behavior, interface list,
   metric anchors, and drift checks.
4. Separate product facts from research hypotheses. A paper or vendor document
   can justify a design experiment; it cannot prove repository quality or user
   approval.
5. Fix numbers only when authority or measurement supports them. Use an
   explicit `UNKNOWN` measurement contract instead of invented precision.
6. Validate one normal path, contradiction/tamper path, stale-reference path,
   and clean-environment replay when the affected capability is executable.
7. Hand off exact head/base, changed cards/contracts, commands/results, known
   risks, rollback, and one next action. Executor evidence is not independent
   acceptance.

## Read-on-demand references

- Read [references/four-layer-map.md](references/four-layer-map.md) when writing
  user-facing cards or deciding which layer owns a statement.
- Read [references/research-to-architecture.md](references/research-to-architecture.md)
  when using papers, standards, provider docs, or film/game precedents.
- Read [references/numeric-drift-control.md](references/numeric-drift-control.md)
  before adding a KPI, threshold, latency, quality score, storage number, or
  provider limit.
- Read [references/coordination-and-evidence.md](references/coordination-and-evidence.md)
  when assigning Codex/WorkBuddy/GPT work, reconciling branches, or preparing a
  closeout.
- Read [references/department-interface-map.md](references/department-interface-map.md)
  when planning how writing, game systems, directing, art, sound, operations,
  privacy, evaluation, and the second brain exchange work across production
  cycles.

## Project machine sources

The task-local candidate registries are:

- `INTERACTIVE-CINEMATIC-SYSTEM-MAP.yaml`
- `NUMERIC-ANCHOR-AND-DRIFT-REGISTRY.yaml`
- `RESEARCH-SOURCE-LEDGER.yaml`
- `CANDIDATE-LINEAGE-AND-INTEGRATION-MAP.yaml`

Validate them with `python tools/validate_interactive_cinematic_mapping.py`.
The validator checks structure and reference integrity; it does not grant
canonical status, review, merge, provider access, or production permission.
