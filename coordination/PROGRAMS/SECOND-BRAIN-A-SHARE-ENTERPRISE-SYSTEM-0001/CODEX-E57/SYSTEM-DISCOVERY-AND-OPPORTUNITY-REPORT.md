# E57 System Discovery and Opportunity Report

## Verified local discoveries

1. Issuance cannot truthfully be modeled as frozen dataclass construction.
   The verifier must consult an authority state unavailable to normal
   consumers. E57 uses a child-process ledger for the deliberately narrow
   ordinary-import threat model.
2. Provider evidence needs two different protections: exact job/artifact
   structural binding and a separately supplied expected digest. Neither one
   replaces the other.
3. A clean source archive is valuable because a correct verifier run in a
   modified worktree is weaker evidence than the same verifier reconstructed
   from the declared Git head.
4. Generated-file hygiene is a history question as well as a final-tree
   question. The route must report transient cache files even after removal.

## High-value opportunities, not current claims

- **AMED-C issuer service:** a separately deployed issuer with constrained IPC
  could support a stronger operational boundary. It requires GPT architecture
  review, lifecycle design, and separate deployment evidence.
- **Reusable Provider verifier:** the downloaded-byte plus clean-archive
  pattern can be generalized only after an owner defines a canonical cross-task
  provider contract. E57 does not create that authority.
- **Semantic format expansion:** Markdown AST support can be added only with
  explicit raw/decoded ownership rules. Current complex Markdown remains
  `UNKNOWN` by design.

## Non-opportunities rejected in this task

- Do not infer production security from local process tests.
- Do not grant QCLAW E44 authority from an unaccepted E57 Draft PR.
- Do not use market, account, credential, or private configuration evidence.
