# E57 Decision Log

## D-001: narrow the authority claim to a process-owned issuer ledger

- Decision: keep live issuance state and the HMAC material in a child process;
  ordinary records, direct constructors, normal module globals, and verifier
  channels cannot mint a presentation accepted by that ledger.
- Evidence: direct-construction, copy, `object.__new__`, foreign-issuer,
  same-ID substitution, local-permit mutation, module-global enumeration, and
  verifier-issue-channel tests; three corresponding real source mutations.
- Alternative rejected: a Python module-private registry or a caller-supplied
  factory. It is reachable or replaceable by ordinary same-process imports.
- Limitation: this is not an OS or cryptographic boundary against hostile code
  already controlling the issuer process.

## D-002: reconstruct semantic records from raw ownership and execution

- Decision: typed JSON values retain raw byte ranges; Markdown that cannot be
  decoded faithfully is `UNKNOWN`, not silently accepted. Conflict, validation,
  redaction, and relation records require provenance that matches their real
  inputs.
- Alternative rejected: caller prose labels or generic score fields. Those are
  not evidence of a bound execution.

## D-003: run mutations in disposable copies of real source files

- Decision: mutate a unique real source sequence, run its named invariant,
  then restore original bytes in `finally` and record three SHA-256 values.
- Alternative rejected: injecting a false predicate result into an oracle or
  modifying a fixture only. It would prove test wiring rather than a real
  production-path defense.

## D-004: separate Provider record reconstruction from Provider producer output

- Decision: each tested/receipt evidence set has distinct run, job, and
  artifact identities. An independent verifier rebuilds both JSON files and,
  when supplied, matches their digests against an external expected pair. A
  clean Git archive supplies verifier code outside the current worktree.
- Alternative rejected: trusting a producer summary or accepting only a
  syntactically valid evidence JSON. A valid-shaped substitution would survive.

## D-005: preserve hygiene defects rather than rewriting history

- Decision: retain the fact that seven bytecode files existed in an earlier
  commit, remove them in a normal follow-up commit, and make topology report
  transient versus retained generated files.
- Alternative rejected: amend or rebase. Route policy forbids history rewrite
  and review needs the negative evidence.

## Pending decisions

1. Whether a future issuer service warrants AMED-C architecture review.
2. Whether QCLAW E44 needs a compatibility proposal after independent E57
   acceptance. No E44 path is touched here.
