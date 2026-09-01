# Research-to-architecture decisions

Research sources are design evidence, not product acceptance. Store the source,
retrieval date, proposition used, integration decision, limitation, and a
revalidation trigger in `RESEARCH-SOURCE-LEDGER.yaml`.

## Interactive narrative

- **Meaningful choice:** compare the durable, player-visible situation reached
  by alternatives. Integrate this as 100% coverage of approved primary edges
  having at least one durable state difference. Do not assume state difference
  alone guarantees emotional quality; retain human story review.
- **Drama management:** choose among approved plot points/actions under an
  explicit evaluation policy. The manager may pace or present; it may not invent
  player facts, override a selected choice, or write state directly.
- **Player modelling:** inferred preferences are uncertain and temporal. Use
  them to rank eligible content candidates; never silently promote them to
  canonical scripts, identity, content boundaries, or knowledge.
- **Character intentionality:** causal order is not motivational coherence.
  Bind each key action to the actor's goal, belief prefix, expected benefit,
  cost, alternatives, and consequence. Let characters fail or conflict when
  that is coherent; do not make them irrational only to satisfy the author.
- **Suspense diagnostics:** model a threatened negative outcome and the
  protagonist's known avoidance routes and perceived feasibility. Treat this
  as a diagnostic to compare with human tension reports, not as one mandatory
  dramatic curve or an automatic artistic score.

## Player and film experience

- **Player experience:** preserve functional and psychosocial dimensions. A
  validated instrument may connect mechanics to autonomy, competence,
  relatedness, meaning, curiosity, feedback, mastery, and immersion, but its
  wording, population, language, and aggregation must remain versioned.
- **Rapid measurement:** a short instrument can reduce production-cycle cost,
  but construct reliability varies. Use it for directional iteration, not as a
  drop-in substitute for full stage evidence.
- **Film immersion:** captivation, comprehension, transportation, and
  real-world dissociation are distinct from interactive agency. Measure only
  on completed audiovisual artifacts after story and continuity hard gates.
- **Motivational needs:** design rewards and relationships to support autonomy,
  competence, and relatedness. Points, praise, or unlocks are not evidence that
  these needs were satisfied.

## Directing and media

- **Cinematographic idioms:** compile scene responsibilities into small,
  inspectable camera/shot policies with exception handling. Keep low-level
  framing separate from narrative authority. A visually attractive shot cannot
  repair an invalid story state.
- **Short media segments:** provider duration/aspect/audio limits belong in a
  versioned adapter capability record. They must be rechecked before real use;
  the GitHub runtime remains offline.
- **Scene composition:** model character, costume, prop, environment, and style
  as independently versioned layers/variants. This informs a future asset
  adapter; it does not require adopting OpenUSD in the first local pilot.
- **Media provenance:** bind generated assets to source ingredients and edits.
  Provenance can show origin and tamper evidence; it cannot prove that depicted
  content is factually true or artistically good.

## Runtime and evidence

- **Standards roles:** JSON Schema checks structural contracts; CloudEvents
  normalizes event envelopes; W3C PROV records lineage; C2PA records media
  ingredients and claims; OpenTelemetry defines metric-stream semantics. None
  substitutes for story truth, human quality judgment, rights, consent or
  execution authority.
- **Architecture precedents:** ink shows an authoring-to-compiled-runtime
  boundary, while virtual actors are one possible many-campaign isolation
  model. Treat both as options. Do not create a dependency until repository
  constraints, measured load and recovery evidence justify it.
- **Event sourcing:** the append-only player stream is the source of record;
  snapshots and review boards are rebuildable projections. Snapshot cadence is
  measured from replay cost and storage cost, not guessed once for all users.
- **Provenance vocabulary:** map entities, activities, agents, derivations, and
  plans to project artifacts, generation/validation steps, actual executors,
  parent artifacts, and policies. Use the smallest useful subset first.
- **AI risk measurement:** record metrics, uncertainty, population/window,
  owner, feedback channel, and review cadence. Unknown or hard-to-measure risk
  stays explicit instead of receiving a decorative composite score.
- **Human evidence:** bind every rating to an exact artifact, rubric revision,
  population, rater class, and evidence hash. Preserve disagreement and never
  auto-promote a rating into formal creative knowledge.

## Provider and platform boundary

- Structured JSON output is syntax help, not semantic validation. Parse,
  schema-check, bind to current state, verify policy, and reject stale or empty
  output before it can become a proposal.
- Comment APIs require permissions and user authorization. Comment text can be
  an intake source; undocumented image retrieval remains gated with a manual
  fallback.
- No research URL authorizes credential access, network calls, paid generation,
  importing copyrighted assets, or processing real customer media.
