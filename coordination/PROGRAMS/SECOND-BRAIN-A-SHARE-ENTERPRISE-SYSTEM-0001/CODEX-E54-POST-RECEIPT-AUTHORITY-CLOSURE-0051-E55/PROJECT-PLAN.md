# E55 Project Plan: clean authority-closure successor

## Route identity

- Task: `CODEX-E54-POST-RECEIPT-SOURCE-ADMISSION-VERIFIED-RECORD-RELATION-EVIDENCE-RECEIPT-PARENT-ARTIFACT-BINDING-HYGIENE-AND-PROVIDER-RECERTIFICATION-0051-E55`
- Route epoch: `57`; Issue: `#179`; planned Draft PR branch: `codex/e54-post-receipt-authority-closure-0051-e55`.
- Canonical base: `71221117b2e15a5437bed27b95fced5e00d11157` from `vxz2datoubo/second-brain-coordination`.
- Frozen input: E54 Issue `#170`, Draft PR `#174`, receipt `1c0bdc3b337828f6e9734823cef73d06e7cd3a20`; E52 Issue `#166` / PR `#167`; parallel QCLAW E42 Issue `#177`.
- E54 is untrusted as a final authority. Only exact selected path/blob/content material may be reused after an E55 selection ledger exists. No whole-branch integration, source-branch mutation, merge, rebase, amend, force push, or history rewrite is allowed.

## Fundamental goal

Produce a public-safe, synthetic-only candidate that closes E54's remaining authority bypasses: controlled source admission, exact escaped JSON ownership, verified packet records, semantically admitted relation evidence, observed Git receipt ancestry, externally fetched Provider artifact binding, complete history hygiene, and mutation evidence. The result stays `research_only / NO_TRADE`, requires GPT review, and grants neither canonical authority nor merge approval.

## Non-negotiable boundaries

- Do not read or modify model/provider/reasoning/default/thread/subagent/workspace/session/private configuration.
- Do not access or publish credentials, accounts, market data, orders, positions, funds, or trading functions.
- Use only synthetic public-safe fixtures and public repository evidence.
- Do not change frozen E52/E53/E54/QCLAW branches or `main`.
- Preserve all failures, rejected alternatives, UNKNOWNs, retries, and execution attribution uncertainty.

## Work packages and gates

### Q0: provenance and recoverable controls

Create `E54-SOURCE-SELECTION.yaml` before any code copy. Each candidate path records the E54 commit, source path, Git blob SHA-1, content SHA-256, destination, selection decision, reason, and untrusted status. Create task controls, impact forecast, UNKNOWN registry, AMED/WPDCR/PDER ledgers, receipt allowlist, and rollback instructions. Gate: no copied production source is present before the ledger is machine-valid.

### Q1-Q3: source admission and exact content ownership

Build a controlled issuance design for retained source bytes. Reverification must apply strict UTF-8, allowed format, source-id policy, exact digest, and a versioned raw-plus-decoded blocked-content policy. Replace quote scanning with a tokenizer that keeps JSON/JSONL keys, quotes, delimiters, backslashes, Unicode escape syntax, structural brackets, and line terminators structural. Gate: direct construction, object allocation, copied-state mutation, Unicode-escaped blocked content, malformed data, duplicate keys, and partial/key boundary attacks fail closed.

### Q4-Q5: verified graph records and relation evidence

Replace arbitrary packet subrecord strings/maps with immutable factory-issued, evidence-bound unknown, conflict, redaction, and validation records in verified registries. Require relation evidence to originate from an admitted semantic span or registered evidence record; structural punctuation is inadmissible. Gate: full packet graph rebuild rejects forged records, stale registries, foreign sources, endpoints, or structural evidence.

### Q6-Q7: receipt topology, Provider binding, and history hygiene

Implement a fail-closed verifier that compares observed Git base-plan-tested-receipt ancestry, exact route values, the actual receipt parent, and exact receipt-only path set. Bind independently fetched GitHub run/job/artifact metadata and downloaded artifact bytes to the receipt head, workflow, branch, six version/seed pairs, compare job, names, IDs, and digests. Expand every-commit, merge-parent, rename/copy, generated/transient, and final-tree hygiene checks. Gate: shape-only artifact or parent data cannot pass.

### Q8: copied-production mutation evidence

Mutate actual copied E55 production files in isolated copies. Each mutation records exact anchor, replacement count, source hashes, counterexample identity, command/hash, duration, mutated/restored exits, mutated/restored stdout/stderr hashes, byte-exact restoration, and restored-green result. Gate: every required remaining bypass has a real killed mutant.

### Q9-Q10: exact-head Provider recertification and delivery

Run the Draft workflow `.github/workflows/codex-e55-authority-closure.yml` on Python 3.11 and 3.13 with seeds `0`, `1`, and `777`. Each job runs complete tests and mutations, publishes canonical and environment artifacts, and a compare job validates exactly six canonical inner files. After a green tested head, create exactly one nonempty receipt-only commit, rerun the receipt head, independently download and verify artifacts, publish the external anchor, and deliver a review-grade report. No post-receipt commit is permitted.

## Architecture choices

E55 will use a compact task-local `e55_authority` candidate package rather than patching the frozen E54 branch or claiming a new global canonical system. It will rewrite selected E54 ideas where review exposed ordinary-caller bypasses. Alternatives rejected up front: trusting frozen E54 Provider green, copying its branch, using raw quote scanning, self-referential receipt metadata, or treating artifact IDs as proof of provenance.

## Validation and rollback

Validation includes strict serialization tests, adversarial Unicode/escape and credential-marker corpus tests, graph reconstruction, Git fixture topology tests, mocked independently fetched Provider metadata/bytes, full copied-production mutation evidence, commit-range hygiene, public-safe scans, and both exact-head Provider matrices. Rollback is disposal or closure of the isolated Draft E55 branch after GPT review. No frozen source object or `main` file is modified.
