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

- **Event sourcing:** the append-only player stream is the source of record;
  snapshots and review boards are rebuildable projections. Snapshot cadence is
  measured from replay cost and storage cost, not guessed once for all users.
- **Provenance vocabulary:** map entities, activities, agents, derivations, and
  plans to project artifacts, generation/validation steps, actual executors,
  parent artifacts, and policies. Use the smallest useful subset first.
- **AI risk measurement:** record metrics, uncertainty, population/window,
  owner, feedback channel, and review cadence. Unknown or hard-to-measure risk
  stays explicit instead of receiving a decorative composite score.

## Provider and platform boundary

- Structured JSON output is syntax help, not semantic validation. Parse,
  schema-check, bind to current state, verify policy, and reject stale or empty
  output before it can become a proposal.
- Comment APIs require permissions and user authorization. Comment text can be
  an intake source; undocumented image retrieval remains gated with a manual
  fallback.
- No research URL authorizes credential access, network calls, paid generation,
  importing copyrighted assets, or processing real customer media.
