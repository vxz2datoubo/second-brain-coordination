# Participant Alignment Score Specification

Status: `Interface / Candidate Only`.

The score measures consistency between a latent participant hypothesis and an observed, governed evidence bundle. Required inputs are hypothesis posterior, market phase, feasible inventory/action constraints, source lineage, supporting and counterevidence, and missing-capability flags. Confounders include correlated sources, shared market response, event timing, aggregate-field semantics and missing participant labels.

The score must expose its component evidence and uncertainty. It is calibrated only after preregistered, point-in-time validation. Failure conditions include unresolved identity labels, unavailable rule/status snapshots, unverified raw-event semantics or score instability across plausible alternatives. Forbidden use: direct order, position sizing, factual identity assertion or performance claim.
