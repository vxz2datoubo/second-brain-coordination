# A-share Microstructure Simulator Plan

Status: `Future Roadmap`; D0 implements no simulator.

The rules-based MVP must consume a versioned `RuleSnapshotRef` and represent call-auction, continuous-auction, midday, closing, halt and post-close phases. It must model price limits, suspension, valid/invalid orders, partial fills, no fills, transaction costs, slippage assumptions, fresh and seasoned inventory, and cross-day settlement effects. Rule values, time windows and board/security differences are loaded from governed snapshots rather than hard-coded as permanent truths.

The MVP is synthetic first. Promotion to empirical replay requires approved point-in-time market data, security-status and corporate-action snapshots, explicit availability times, permitted licensing, deterministic replay tests and cost/capacity assumptions. It is never an order-management system.
