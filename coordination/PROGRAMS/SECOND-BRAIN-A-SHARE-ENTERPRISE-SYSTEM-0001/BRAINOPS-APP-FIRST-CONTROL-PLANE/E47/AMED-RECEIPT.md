# E47 AMED Receipt

## Authority and route

- source_agent: `CODEX`
- target_agent: `GPT`
- reviewer: `GPT`
- route epoch: `49`
- active issue: `#150`
- parent issue: `#31`
- draft PR: `#151`
- frozen source PR: `#146`
- frozen source substantive SHA: `dcf0e099fb2abc50fbb04fb95a1a7c39d4f38231`
- tested SHA: `f6835949b111134dea5734217a2074d169f897d3`
- tested tree: `9c8b33bef8ffd8fae9b8144e5e1d823950e967db`

## Delivered implementation

1. A seven-stage synthetic lifecycle with request-bound, durable receipts.
2. Claim and lease cross-record recovery that applies only a missing matching
   mutation after a post-apply response loss.
3. A chained journal for effect, invocation, terminal and terminal-commit
   transitions, including response-loss and reconciliation phases.
4. A product-level pre-receipt gate and an exact-head 3.11/3.13 workflow.
5. Selected E46 imports pinned by path and blob ID, with E46 kept frozen.

## Negative and recovery proof

The focused E47 tests inject post-apply response loss for effect authorization,
claim invocation, lease invocation, terminal attestation, claim terminal CAS,
lease terminal commit, and the journal itself. Exact retries recover from the
durable record; changed request/binding/evidence attempts fail closed; no test
uses a live authority, GitHub App, Codex App, CLI, canary, market, account, or
trading action.

## Completion boundary

This receipt documents the tested head. The current receipt-only commit must
receive its own successful exact-head matrix before the completion signal is
sent for GPT second-pass review.
