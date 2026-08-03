# Participant Alignment, Mismatch and Narrative Ledger Plan

## Candidate data flow

Governed `SourceRecord` and `EvidenceItem` inputs feed one or more latent `ParticipantArchetypeHypothesis` records. The future engine may create `ParticipantAlignmentScore`, `ParticipantMismatchRisk` and `NarrativeForecastLedger` records as candidate research artifacts. These are linked to the existing `DecisionRecord`, `ForecastRecord`, `ValidationReport` and `SelfEvolutionLog` only through provenance and review references.

## Boundaries

* Alignment measures consistency of a hypothesis with declared evidence, not a person's identity or intent.
* Mismatch measures model fragility and alternative explanations, not wrongdoing or manipulation.
* Narrative forecasts record source claims and later resolution; they are never direct signals.
* Missing provenance, unavailable rule snapshots, aggregate-only data, correlated sources or unavailable labels force abstention or downgrade.

## Future validation

Pre-register hypothesis, baseline, timestamps, resolution rules, source dependence, evidence cutoffs and failure handling. Test calibration by claim class, retain negative results and compare against a simple no-participant baseline. No score gains authority without independent validation and GPT approval.
