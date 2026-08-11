# AMED research ledger

REUSE: E64 R2 acyclic identity and resolver/CAS boundaries. EXTEND: strict
approval grammar and isolated Git marker semantics. Negative finding: an O_EXCL
consumer race originally surfaced `FileExistsError`; the store now reconciles
only an exact marker or fails closed on conflict.
