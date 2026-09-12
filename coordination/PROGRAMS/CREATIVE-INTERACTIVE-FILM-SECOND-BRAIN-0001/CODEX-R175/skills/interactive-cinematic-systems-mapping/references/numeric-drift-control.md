# Numeric anchors and drift control

## Rule

A decision number needs: stable ID, unit, direction, status, formula revision,
population, time window, source, observation time, baseline, target/range,
warning and failure thresholds, owner, cadence, and response. If these are not
known, record `UNKNOWN_REQUIRES_MEASUREMENT` with a discovery plan.

## Three kinds of anchors

1. **Contract constants** — exact IDs, schema versions, zero-external-call
   boundaries, approved act/chapter/choice counts, provider-version limits.
   Change only by an explicit superseding decision.
2. **Measured operating metrics** — replay latency, storage per campaign,
   generation latency, failure rate, duplicate rate, human quality ratings.
   Store sample count, population, aggregation, window, and uncertainty.
3. **Integrity identities** — SHA-256, event sequence, graph revision, source
   artifact, policy revision. Compare exactly and fail closed on mismatch.

## Drift dimensions

- **identity:** SHA, event, graph, script, cast, asset, or policy mismatch;
- **semantic:** prefix replay disagrees with the legal transition even if final
  state looks plausible;
- **population:** metric population changes between synthetic, pilot, and real
  users;
- **formula:** calculation, weights, scale, or aggregation changes;
- **temporal:** observation window or provider documentation becomes stale;
- **authority:** a branch, score, model output, or green CI is mistaken for an
  approval or canonical state.

Formula, population, source, or window changes create a new metric revision.
Never silently overwrite history. Use `supersedes` and retain the previous
anchor.

## Quality measurement

Keep hard correctness gates separate from artistic evaluation:

- correctness examples: replay determinism, legal choice coverage, director
  compilability, cross-user isolation, source binding;
- artistic examples: tension, emotional payoff, character distinctness,
  cinematic clarity, replay desire.

Do not average correctness and art into one score. A beautiful segment with an
identity leak fails; a perfectly valid but dull scene still needs creative
improvement.

Human quality metrics remain `UNKNOWN` until a versioned rubric, rater protocol,
minimum sample, aggregation rule, and disagreement handling are approved.
