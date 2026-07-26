# D2 Architecture Decisions

1. **Compose D1, do not wrap or replace it.** The accepted reducer remains the
   only synthetic feasibility/transition authority.
2. **Treat archetypes as hidden-type hypotheses.** Four families and nine
   subtypes are a scenario language, never identity classification.
3. **Make time and UNKNOWN first-class.** An agent cannot act on information
   after the D1 market cutoff, and declared complete-information actions abstain
   when required inputs remain UNKNOWN.
4. **Use deterministic, append-only event sourcing.** Events are canonically
   hashed and sorted by agent/action IDs; rejected actions remain visible.
5. **Bound counterfactuals.** They remove one declared assumption per step, at
   most twelve steps, and cannot manufacture data or observations.
6. **Keep scores and narratives uncalibrated.** The containers explicitly
   prohibit probability, identity, performance, and signal interpretations.
