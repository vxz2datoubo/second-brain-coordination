# Capability dependency and maturity

Use the capability map before proposing code, assigning a department, or
claiming that the platform already supports a user-visible outcome.

## Read the map in this order

1. Start from the requested player or operator outcome.
2. Trace every `depends_on` edge back to a capability with evidence.
3. Read maturity literally. `MAPPED` is a design with an owner and boundary;
   it is not executable. `CONTRACTED` has a versioned interface but may still
   have no runtime. `IMPLEMENTED_OFFLINE` has code and negative tests.
   `REPRODUCED_CLEAN` additionally has an exact-head clean reproduction.
4. Stop at the first dependency whose maturity is below the requested stage.
   That capability, not the most visible downstream feature, is the next
   engineering constraint.
5. Preserve the named failure action. Never fill a missing dependency with a
   model guess, synthetic approval, default player state, or invented metric.

## Separate five kinds of proof

- A map proves that a boundary, owner and dependency were considered.
- A contract proves that a payload shape and rejection rule were versioned.
- Tests prove only the covered implementation behavior on the tested version.
- A clean reproduction proves another environment can replay those tests.
- A consented pilot is needed for claims about a named human population.

None of these automatically proves production approval. Production also needs
explicit user authority, privacy, rights, budget, operations, monitoring,
rollback and incident handling.

## Interface rule

Every department handoff must bind upstream identity and revisions. At minimum
record producer, consumer, contract, source identity/hash, revision, rejection
owner and rejection behavior. A downstream team may reject an input, but must
not modify the upstream story fact, consent, identity, source, rating or metric
definition to make its own output pass.

## Standards are patterns, not hidden dependencies

- ink demonstrates separation between authoring structures, a compiled JSON
  representation and a smaller deterministic runtime. It does not define this
  project's campaign, director or private-media semantics.
- JSON Schema can validate structure and declared vocabularies. Application
  code still validates story truth, authorization and consequence semantics.
- CloudEvents can normalize envelope metadata across future platform inputs.
  It does not guarantee ordering, replay or exactly-once behavior.
- W3C PROV provides entity/activity/agent lineage concepts. C2PA provides media
  ingredient and signed-manifest patterns. Neither makes a quality, rights or
  consent judgment.
- OpenTelemetry gives explicit metric identity, unit, temporality and
  single-writer rules. It does not choose product targets or authorize data
  collection.
- A virtual-actor runtime is one future campaign-isolation option. Do not add
  distributed infrastructure until measured concurrency and recovery evidence
  justify it.

## Stage-gate use

Stage gates are dependency summaries, not deadlines and not authority. A stage
may exit only when every required capability has the stated evidence. If an
external provider, private asset, real player or production environment is
involved, a new approval gate is required even if the offline stage is green.
