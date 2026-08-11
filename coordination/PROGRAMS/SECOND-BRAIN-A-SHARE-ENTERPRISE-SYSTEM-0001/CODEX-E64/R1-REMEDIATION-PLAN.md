# E64 R1 remediation plan

agent_id: CODEX

## Review findings addressed

1. Replace caller-provided approval strings with resolver-verified structured
   canonical GitHub approval evidence.
2. Replace process-local claim state as the security claim with a durable
   marker/CAS store interface. A lock inside the mock is only an implementation
   detail of the shared test double.
3. Bind an upstream classification evidence reference and immutable evidence
   digest to the candidate identity; E64 still does not inspect or publish raw
   private content.

## Design limits

- The production resolver is a read-only boundary that must fetch canonical
  GitHub evidence; E64 provides only a synthetic in-memory resolver for tests.
- The production durable store is a future Git expected-parent/marker CAS
  boundary; E64 provides only a shared in-memory deterministic model.
- No GitHub API call, credential, real formal write, merge, AWS, or repository
  visibility change is added.

## Evidence

The R1 suite will retain prior adversarial coverage and add fake/wrong evidence,
two-adapter durable consumption, existing marker, stale parent, unknown outcome,
idempotent completed receipt, and classification-evidence mismatch checks.
