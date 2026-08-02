# E43 Research Ledger

agent_id: `CODEX`

research_trigger: `L1_REUSE_AND_QUICK_CHECK`

## Repository evidence reviewed

- Canonical route, task brief, forecast, lease/freshness, visibility, AMED,
  PMA-BIG, WPDCR, and PDER governance files on remote main `925cc111...`.
- Issue #134 and all visible comments.
- Frozen PR #133, its accepted tested/receipt heads, and GPT's review finding.
- Selected E42 source blobs and synthetic test surface.

## Findings used by implementation

1. **VERIFIED_REPOSITORY:** E42 allowed a verified invocation receipt to be
   classified before the durable record reached a terminal state.
2. **VERIFIED_REPOSITORY:** E42's transport identity was a caller-provided
   string guarded only by process-local factories.
3. **VERIFIED_REPOSITORY:** recovery required the crashed holder itself.
4. **INFERENCE:** one-shot challenge consumption plus a separate recovery
   identity is the smallest compatible correction that preserves E42 CAS and
   provenance primitives.

## Scope decision

No external research was needed: the task is an internal trust-contract repair,
and no claim is made about live GitHub, application, CLI, callback, or provider
behavior.
