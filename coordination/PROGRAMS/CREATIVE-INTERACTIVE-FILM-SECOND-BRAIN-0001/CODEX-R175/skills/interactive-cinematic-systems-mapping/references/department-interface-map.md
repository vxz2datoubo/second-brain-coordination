# Department interface and production cycles

Departments exchange versioned artifacts, not ambiguous chat summaries. Every
handoff names the source artifact/hash, approved revision, writer, consumer,
acceptance gate, and rejection owner.

## Department interfaces

| Department | Owns | Consumes | Publishes | Gate before downstream use |
| --- | --- | --- | --- | --- |
| Product / showrunner | audience, promise, content boundary, season goals | research, pilot evidence, budget | approved product decisions and priorities | user authority and version |
| Narrative room | world/character bible, beat graph, dialogue intent, endings | product decision, review findings | `ScriptPackage`, approved beats and legal choices | rights, content, reachability, consequence coverage |
| Game systems | choice intent, quest/reward/resource/risk rules, state transitions | script package, player input | verified events and narrative state | schema, legal edge, deterministic replay |
| Drama management | pacing and eligible-beat ranking policy | verified state, approved beats, candidate proposal | `DramaticBeatSelection` | preserved choice/facts, policy revision, visible consequence |
| Director / cinematography | scene duty, performance, shot, axis, lighting, edit intent | verified state, scene/character/style bibles | `DirectorBrief` and `ShotBundle` | identity, knowledge, space, continuity, duration |
| Character / art / VFX | appearance anchors, wardrobe, injury, prop, set and style variants | character/scene bibles, approved private refs | versioned asset manifest and continuity record | source/right/consent/approval and exact revision |
| Sound / music | dialogue, ambience, effects, score duty and transition | director brief, character emotion, scene space | audio plan bound to shot bundle | rights, intelligibility, content, duration and continuity |
| Media generation / editorial | segment jobs, results, assembly and export | shot bundle, asset refs, audio plan, budget gate | `MediaResult`, timeline and provenance | idempotency, quality report, source binding, human approval |
| Platform operations | manual/Douyin intake, dedup, wait queue, operator notification | platform events and user authorization | normalized intake and capability receipt | permission, source ID, privacy, retry and fallback |
| Privacy / rights / safety | consent, retention, age/content, license and publication rules | proposed intake/assets/scripts/exports | approvals, denials and expiration events | explicit human authority; no inference from model output |
| Evaluation / QA | deterministic corpus, robustness matrices, human rubric, games-user-research protocol | exact candidates and approved evaluation protocol | hard-gate receipts, dimension vectors, disagreement and findings | exact head/artifact, rubric, population/window, no oracle co-edit |
| Second brain | candidate lessons and correction lineage | source artifacts, user feedback, review decisions | reviewable skill/knowledge candidates | provenance and human review; no automatic canonical promotion |
| Local infrastructure | private store, runtime environment, backup and recovery facts | approved deployment plan and secrets manager | environment/capability evidence | separate authorization; never publish private bytes to GitHub |

## Production clocks

The system has nested clocks; a later clock may summarize but never overwrite
the earlier source of record.

| Clock | Trigger | Mandatory closure |
| --- | --- | --- |
| turn | one player input | normalized intent, accepted/rejected result, event/state hash, choice foresight/consequence, visible feedback |
| segment | one 4-15 second candidate | director/asset/continuity checks, media receipt, provenance, next-choice bridge |
| scene | scene entry or exit | spatial state, cast knowledge, injuries/props, quest/relationship consequences, key-character intent trace, expert dimension findings |
| chapter | chapter terminal beat | objective resolution, unresolved threads, reward/cost, recovery point, approved player-experience vector when piloting |
| season | ending | ending path, relationship/quest closure, replayable ledger, blind comparative human vector, candidate learning packet |
| release | exact Git candidate | full tests, scope/privacy/network scans, clean reproduction, dimension-level human evidence, rollback and independent review |
| operations review | approved cadence after pilot | privacy/rights incidents, cost/latency/storage, user feedback, drift and improvement decisions |

## Change propagation

1. A script change creates a new script revision, then reruns reachability,
   consequence, director-compilability, asset, and replay gates.
2. A character/asset revision changes only approved future segments and creates
   a continuity event; it does not rewrite completed player history.
3. A provider or adapter revision creates a new capability record and reruns
   offline contract fixtures before any approved private trial.
4. A metric formula, population, scale, source, or window change creates a new
   metric revision; dashboards do not silently reinterpret old values.
5. A human correction creates a candidate correction linked to its source and
   affected artifacts; formal rules change only after review.
6. A rubric wording, scale, language, population, artifact scope, aggregation,
   or decision-rule change creates a new evaluation revision; old ratings are
   not silently normalized into the new protocol.

## Conflict rule

When two departments disagree, preserve both source artifacts and stop at the
first common contract. The owner of that contract resolves the conflict. A
downstream department may report a finding but cannot silently rewrite an
upstream fact to make its own output pass.
