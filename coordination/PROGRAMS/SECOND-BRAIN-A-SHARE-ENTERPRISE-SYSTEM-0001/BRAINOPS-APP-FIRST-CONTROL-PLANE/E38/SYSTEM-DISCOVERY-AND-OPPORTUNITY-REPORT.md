# E38 System Discovery and Opportunity Report

## DISC-E38-001

- Class: `CONTRADICTION_WITH_ASSUMPTION` / S2 material.
- Verified fact: current public routes explicitly keep automatic and canary
  execution disabled but do not declare a non-empty authorized approval actor
  policy.
- Meaning: route parsing can be proven, but no approval is permitted to become
  VERIFIED for a future canary.
- It does not prove: a missing policy is not evidence that any particular
  actor should be trusted.
- Current action: fail closed and preserve the exact reason.
- Owner and gate: GPT must publish matching policy fields in both route files
  in a later route; E38 must not edit the active route to self-authorize.

## Reuse opportunity

The fixed-host, ref-drift and tree-membership transport is reusable only as a
candidate control-plane primitive. It must not be promoted beyond this
pre-canary public-read boundary without a separate task and review.
