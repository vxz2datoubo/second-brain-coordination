# E42 Research Ledger

agent_id: `CODEX`

| ID | Hypothesis | Evidence | Result |
|---|---|---|---|
| E42-H01 | A fixed Contents/ref client can be production-capable without a default live transport. | Synthetic standard GitHub response fixtures execute create/update/read and identity validation. | Supported at contract level only. |
| E42-H02 | Exact provenance can be bound without making stored JSON self-authenticating. | State-changing APIs require the same verifier-minted provenance on every read. | Supported for process-level API trust. |
| E42-H03 | Storage ID should include provenance digest. | Adversarial reasoning showed route substitution would select a second object. | Refuted; stable one-shot key adopted. |
| E42-H04 | Retrying PUT after a lost response is safe. | A first PUT may have applied while its response is lost. | Refuted; PUT is single-attempt and returns outcome unknown. |
| E42-H05 | Generic BLOCKED proves canonical completion. | It lacks exact claim, terminal state, timing, and remote object identities. | Refuted; publication pending is explicit. |

No runtime or market research was performed.
