# E47 Decision Log

## D1: replace process-local positive permits with receipt-bound state

- Decision: model all six required post-capability positive transitions as
  durable, request-bound stages and make cross-record operations recoverable.
- Reason: an applied CAS followed by a lost response must be distinguishable
  from a never-applied CAS after restart.
- Alternative rejected: treating a function return or an in-memory permit as
  authority. It cannot survive a response loss.

## D2: separate public-safe hashes from internal binding hashes

- Finding: the imported public-safe `canonical_hash` redacts values under
  secret-shaped keys. Two different `authorization_id` inputs therefore had an
  identical public-safe digest in an E47 focused test.
- Decision: retain the imported function for public-safe output and introduce
  an E47-local structural digest for durable request/receipt/journal identity.
- Boundary: this is not a change to frozen E46 or a claim about a production
  secret-management system. A future shared-contract migration requires its own
  task and compatibility review.

## D3: receipt preparation is a separate fail-closed decision

- Decision: add an offline pre-receipt validator.
- Reason: successful local code is insufficient if the checked-out CI SHA,
  lifecycle coverage, or receipt-only topology is wrong.
- Alternative rejected: writing the final receipt alongside the tested commit.
  It would remove the independently verifiable second exact-head CI gate.
