# D0-D6 Enterprise Construction Plan

## Scope and non-goals

This is an executable **plan**, not a simulator. Its system purpose is to turn four A-share participant families into falsifiable, latent-type hypotheses whose simulated actions remain constrained by versioned market rules, inventory and observation capability. It is permanently `research_only / NO_TRADE` until a separately approved promotion task says otherwise.

No phase may infer real identity from market traces, activate a source, run a replay/backtest, train MARL, access an account or emit an order solely because this plan exists.

## Shared construction rules

1. Reuse `<CORE_CONTRACTS>` for provenance and decision objects, `<FOUNDATION_GOVERNANCE>` for market-data capability, and `<TRADING_DOMAIN>` for downstream validation.
2. Every state-bearing object carries `rule_snapshot_ref`, `available_at`, lineage, UNKNOWN flags and a forbidden-downstream-use field.
3. Every candidate metric declares unit, horizon, inputs, confounders, calibration method, invalidation condition and abstention behavior. Missing evidence blocks promotion rather than defaulting to zero.
4. Each future phase uses a dedicated branch/worktree, a tested head and a receipt-only head. Rollback is a normal revert of its phase commit; never rewrite history to hide a failed experiment.

## Phase task graph

| Phase | Task ID | Objective | Inputs | Outputs | Owner / reviewer | Prerequisites | Effort | Acceptance / stop / rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D0 | MAGE-D0-PLAN | Preserve public-safe contracts, UNKNOWNs, release plan and evidence chain. | Approved blueprints, repository audit, frozen candidate inputs. | This package, completeness matrix, tree-equality receipt. | Codex / GPT | Active route only. | Complete | Parse, allowlist and path scan pass; stop on secret/path/runtime scope; revert D0 commits. |
| D1 | MAGE-D1-SYNTHETIC-RULES | Implement deterministic synthetic state transitions for one instrument and two latent archetypes. | D0 contracts, synthetic rule snapshot, generated fixtures. | Pure state reducer, fixtures, invariants, no-trade outputs. | Codex / GPT | Separate task; D0 gates accepted. | Medium | 12 fixtures and 20 invariants pass; stop on need for real data; revert D1 commits. |
| D2 | MAGE-D2-DATA-ADMISSION | Admit only permitted, point-in-time, versioned historical data and rule/status snapshots. | License evidence, source manifests, security/rule snapshots. | Admission manifest, availability tests, rejected-source log. | WorkBuddy + Codex / GPT | D1 complete; user/data approval where needed. | High | No future leakage; license and semantics proved; stop on ambiguity; revoke manifest. |
| D3 | MAGE-D3-REPLAY-CALIBRATION | Calibrate synthetic mechanisms against approved replay without identity promotion. | D1 engine, D2 manifest, baselines, preregistration. | Calibration report, abstentions, coverage and error ledger. | Codex / independent reviewer | D2 accepted. | High | Temporal/OOS gates and costs pass; stop on leakage/data gaps; revert derived artifacts. |
| D4 | MAGE-D4-OPPONENT | Add bounded Bayesian/Level-k candidate models with registered priors and baselines. | D3 calibration, confidence diagnostics, compute budget. | Candidate posterior and opponent-model comparison. | Codex / GPT | D3 promotion. | High | Beats baselines only under preregistered metrics; stop on instability; retire model. |
| D5 | MAGE-D5-SELFPLAY | Evaluate self-play only for synthetic robustness, not market truth. | D4 model, synthetic scenarios, independent seeds. | Seed ledger, exploitability report, failure inventory. | Codex / independent reviewer | D4 accepted and compute approval. | Very high | Reproducibility and stress gates pass; cancellation threshold enforced; delete generated runs per retention policy. |
| D6 | MAGE-D6-MARL-GATE | Decide whether MARL is justified; it is not a default endpoint. | D5 evidence, cost ledger, independent validation proposal. | Go/no-go ADR or rejection report. | GPT / user | D5 accepted; separate authorization. | Very high | Requires net value case, budget and user gate; otherwise reject/defer with no implementation. |

## D0 completion contract

The D0 exit condition is not “documentation exists.” It is: all requirements map to a file and acceptance gate; public output contains no physical local paths or credential values; the plan supplies independently assignable task inputs/outputs/owners/rollback; and remote/publication provenance is explicit without rewriting Git history. GPT is the only approver for D1.
