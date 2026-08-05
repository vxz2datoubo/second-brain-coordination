# E53 adversarial validation design

## Product boundary

The authority is intentionally narrower than an adversary with arbitrary
Python object-memory access.  Its enforced public contract is that an ordinary
caller cannot construct an accepted atom, relation or packet from declared
metadata.  Acceptance requires the exact object instance issued by the active
factory plus recomputation from the retained `SourceEvidence` bytes.

## Control violations

| Mutation | Actual copied source | Exact replacement | Bad input | Required observation |
| --- | --- | --- | --- | --- |
| `MUT-UTF8-STRICT` | `src/e53_authority/utf8_index.py` | strict UTF-8 decoder -> Latin-1 decoder | isolated byte `0xED` | copied real product suite exits nonzero; mutant is killed |
| `MUT-ATOM-LEDGER` | `src/e53_authority/atoms.py` | exact candidate-span guard -> `if False` | subspan `0:1` of `alpha\n` | copied real product suite exits nonzero; mutant is killed |
| `MUT-JSON-NAN` | `src/e53_authority/packet.py` | validation normalization plus JSON finite guard weakened together | `NaN` canonical value | copied real product suite exits nonzero; mutant is killed |

The harness copies only the E53 source package into a temporary directory,
checks that each target anchor occurs exactly once, runs the copied real
product test suite so the target gate fails nonzero, restores the copied source
from the original E53 worktree and reruns that suite green.  No repository code
is mutated during the test.

## Counterexample corpus

The fixed corpus contains valid text, blank line, invalid `0xED`, truncated
UTF-8, valid/invalid JSON, valid/invalid JSONL and an unsupported declared
format.  Its seed-equivalent deterministic digest is produced by
`e53_authority.corpus.corpus_digest`.  Markdown structural-heading ownership,
redaction ownership, explicit relations, FACT lexical promotion, duplicated
identities, caller-field mismatch, `NaN`, relation endpoint failure, missing
artifacts and post-receipt topology are separate product tests.

## Non-credit rules

Tests fail on rejected result mismatch; none receive credit for imports,
printing, existence, documentation or unconditional truth assertions.  The
timeout probe launches a busy child only to prove kill/reap behavior and ends
it after 0.1 seconds; it is not a duration-padding mechanism.
