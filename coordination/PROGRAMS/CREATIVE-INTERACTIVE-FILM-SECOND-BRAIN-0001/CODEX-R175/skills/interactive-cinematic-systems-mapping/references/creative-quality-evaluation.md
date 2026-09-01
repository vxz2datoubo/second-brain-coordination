# Creative quality evaluation

Use this reference when a task asks whether a branch, scene, character, player
choice, director output, or completed segment is not only valid but effective.

## Two decision layers

Never average machine correctness and human experience into one score.

1. **Hard correctness gates** answer whether the artifact is allowed to move
   forward: exact replay, legal state mutation, choice consequence, character
   knowledge and intention, director continuity, private-asset isolation, and
   provenance. One failure blocks the affected artifact.
2. **Human experience dimensions** answer what to improve: perceived agency,
   autonomy/competence/relatedness, meaning, curiosity, feedback, character
   believability, suspense, emotional payoff, pacing, film immersion, and replay
   desire. Keep the vector and reviewer rationale; do not hide trade-offs in a
   weighted total.

The machine may compute diagnostics such as choice-state differences, character
goal traces, threat alternatives, pacing intervals, continuity errors, or audio
levels. These are explanations and search aids, not a substitute for a person
reporting agency, suspense, emotion, or immersion.

## Artifact-level review

- **Choice:** show which situational dimensions the player could anticipate and
  which durable dimensions changed later. A branch difference hidden from the
  player does not by itself prove perceived agency.
- **Character action:** bind actor, goal, belief prefix, expected benefit, cost,
  alternatives and consequence. Causal validity without motivational coherence
  is not enough.
- **Suspense sequence:** record the threatened negative outcome, protagonist's
  plausible avoidance routes, obstacles and perceived feasibility. Compare the
  diagnostic with human ratings; never impose one universal tension curve.
- **Director segment:** rate film immersion only after story/continuity gates.
  Preserve captivation, comprehension and transportation as separate signals.
- **Session/chapter:** use a validated player-experience instrument when the
  research plan permits. Do not edit item wording or collapse constructs and
  still call the result validated.

## Calibration before thresholds

The task-local `CREATIVE-EXPERIENCE-EVALUATION-PROTOCOL.yaml` defines a candidate
1–5 response scale only to stabilize data shape. It does not define a passing
score. Before a release threshold exists, approve and version:

- rubric wording and language;
- artifact population and audience;
- minimum sessions and rater classes;
- aggregation and missing-data rules;
- disagreement/reliability method;
- baseline corpus and comparison method;
- decision owner and remediation response.

A population, wording, scale, formula, or window change creates a new revision.
Keep old results and `supersedes` links. Report uncertainty and disagreements;
do not turn missing evidence into zero.

## Production clocks

Run deterministic gates per turn and segment. Run expert creative review per
scene, player-experience review per chapter, a consented blind panel per season,
and exact-head cross-module review per release. This provides fast feedback
without asking players to complete a long survey after every choice.

Only reviewed findings become `CreativeKnowledgeCandidate/v1`. Ratings must
retain scene/segment, script, rubric, population and evidence hashes. Human
approval is required before any candidate changes a formal creative skill.
