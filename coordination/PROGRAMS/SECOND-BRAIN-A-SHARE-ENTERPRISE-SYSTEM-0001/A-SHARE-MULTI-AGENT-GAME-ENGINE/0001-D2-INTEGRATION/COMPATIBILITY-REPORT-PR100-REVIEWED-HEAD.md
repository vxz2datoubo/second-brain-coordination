# Candidate Compatibility Report

## Scope

This is a schema-level advisory against the route-pinned candidate reference:
PR #100 head `137ea13440ed61de9b240e475db8ffd081a217c9`. No atom text,
claim body, market assertion, participant identity, or runtime artifact was
loaded into this project.

## Result

`INCOMPATIBLE_FOR_RUNTIME_IMPORT / CANDIDATE_ONLY / ADVISORY`

The active E12 route identifies two fail-closed incompatibilities for the
reviewed candidate surface: misaligned family labels and a hard-coded verifier
claim. The port also requires full locks and verifier hashes; any abbreviated
lock or missing evidence is rejected.

## Consequence

Only a future synthetic fixture satisfying this port's complete contract may
exercise the compatibility code. Passing that fixture would still create only
a quarantined candidate relation. It cannot create a fact, probability,
identity, signal, action, or authority write.

## Rollback

The port exists solely under `0001-D2-INTEGRATION`. Reverting its commit
removes the compatibility surface without touching PR #100, QCLAW, D1, or
the second-brain memory runtime.
