# R135 remediation work-process evidence

agent_id: CODEX

The planned difficulty was medium. Actual D3 difficulty came from binding a local source root to a Git commit/tree/blob rather than trusting a caller label, and from adapting S0D to the accepted SQLite-backed S0C ledger without creating a second truth store. Observable evidence is the focused `7/7` suite, including the 20 mechanism-driven acceptance cases, and the fresh-connection durable replay receipt.

The hardest part was preserving a strict read-only source boundary while proving ten individual Git object bindings. The implementation now verifies repository root, exact `HEAD`, per-path tree blob, Git object bytes and checked-out payload bytes before any observation is admitted. Schema extraction is intentionally conservative: the pending-writes and unknown registries expose stable item refs; registry-level status cannot override an item; unsupported surfaces stay `UNKNOWN`.

Plan changes: GPT review `4945202126` required replacing the former in-memory ledger. S0D now emits public-safe `SignalEvent` and `SignalLink` records into R134 `DurableSignalLedger`; the S0D reducer is an explicitly non-authoritative staging summary. A real-source manifest records repo, commit, path, blob, content hash, schema, derived state and opaque ref for all ten allowlisted paths; it contains no source body.

Negative results: the first remediation head failed S0D CI because the new YAML schema parser was not installed in that workflow. The additive workflow-only commit `f3dcc50bb3ee49193e8e0e63d3e29f95d801cdff` installs `PyYAML==6.0.2`; its exact-head S0D run `31922700529` and Phase 3 run `31922700558` both passed on Python 3.11 and 3.13. Local Phase 3 was `291/291 PASS`; Phase 3 public safety was `108 files/0 issues`.

LOCAL_EXECUTION_ISSUES:

- Problem characteristic: the task-owned temporary AI Film exact-snapshot clone was ready for deletion after the receipt was generated, but the local execution safety layer rejected the explicit PowerShell `Remove-Item` command before it ran.
- Discovery and control test: the clone was verified clean and at `44c383afd2207a97caf45b1b0da6ee1dece43a76`; the blocked command made no deletion and no source mutation.
- Root-cause scope and limit: environment policy rejection; it is not attributed to Git, AI Film, credentials, or the source content. Root cause remains UNKNOWN.
- Reversible mitigation and rollback: no workaround or alternate deletion mechanism was used. Owner may remove only `F:\aidanao-worktrees\standalone-clones\r135-ai-film-readonly-source` after independently rechecking its exact path; no repository rollback is needed.

Coordination boundary: GPT is the only reviewer/merge authority. This task does not authorize AI Film writes, W3/private chat, Harness, H2/H7, S0E, production, or trading. The next acceptance gate is the documentation-head exact CI followed by GPT exact-head review; no successor is unlocked by a pass.
