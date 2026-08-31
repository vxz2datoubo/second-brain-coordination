# R174 implementation report

agent_id: `CODEX`

## Outcome

R174 was reimplemented from canonical baseline
`c8cbf8d8f3086f0c96daa877c608ed5db9b4a775`. No implementation file was
copied, cherry-picked, or imported from frozen PR #525 or any historical frozen
candidate.

The delivery closes all four findings from independent review `5068184475`:

1. Python capability checks use the standard-library AST and resolve import
   aliases, from-import aliases, and constant dynamic imports. Network/provider
   modules and environment-variable reads fail closed.
2. Browser checks reject HTTP(S) and protocol-relative active loads, CSS URLs,
   `srcset`, SVG references, meta refresh, inline browser networking, and remote
   JavaScript imports.
3. The JSON policy's four scan roots are mechanically bound to the exact
   `pull_request.paths` set. Missing and extra trigger paths both fail.
4. Traversal checks every descendant with no-follow metadata before suffix
   filtering. File links, directory links, junction/reparse points, and links to
   both inside and outside the repository fail closed.
5. Legacy migration stages a lossless v2 envelope, re-reads and fingerprints the
   v1 source, and only then uses a create-only hard-link publication. A race
   leaves no v2 target; a pre-existing target is never replaced or removed.

## Adjacent lifecycle hardening

- CLI command: `creativectl migrate --slot <safe-slot>`.
- Legacy event hashes and replay are verified before migration.
- Original legacy bytes remain unchanged.
- Repeated identical migration is idempotent.
- Unsafe slots, corrupt ledgers, duplicate keys, save-directory links, target
  corruption, and target metadata drift fail closed.
- The verifier is repository-local and has no optional executable dependency.
- GitHub CI checks out and asserts the exact PR head, runs one Python 3.11
  creative suite, writes a machine receipt, checks whitespace, and enforces the
  R174 path allowlist.

## Boundaries retained

No credential/account introspection, provider/model call, deployment, customer
data, real media, trading, canonical knowledge write, self-review, Ready,
acceptance, merge, force-push, rebase, amend, reset, or history rewrite was
performed.

## Rollback

Before merge, close the R174 PR and delete only the R174 branch. After an
authorized merge, revert the R174 delivery commits in reverse order. Do not
rewrite branch history and do not mutate frozen PR #525.
