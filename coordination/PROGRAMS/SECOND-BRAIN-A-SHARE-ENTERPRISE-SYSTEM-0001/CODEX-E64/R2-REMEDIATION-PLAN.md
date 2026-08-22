# E64 R2 acyclic admission-identity plan

agent_id: CODEX

## Defect

R1 bound admission evidence to the final candidate identity while that final
identity included the hash of the same admission-evidence object. A truthful
persisted hash would require an impractical SHA fixed point.

## Narrow correction

1. Define `pre_admission_subject_sha256` from repository, task/route, full E48
   digest bundle, provenance, target and proposed admission class, excluding
   admission evidence reference and object hash.
2. Serialize `CanonicalAdmissionEvidence` deterministically and derive its
   object SHA-256 from its actual bytes. The evidence binds the pre-admission
   subject identity, repository, and `PUBLIC_SAFE` decision.
3. Construct final candidate identity only after the evidence exists; it may
   include the evidence reference and derived object hash.
4. Preserve the reviewed resolver and durable CAS interfaces; add only golden
   synthetic serialization and tamper-regression tests.

E48 live integration remains blocked pending E48 R2 acceptance. No real writer
or resolver implementation is in this patch.
