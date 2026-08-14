# Lane B · A-share Trading-System Remediation · Proposal Workspace

Status: `HELD_PROPOSAL_ONLY` until the Control Tower foundation receives an explicit GPT release decision.

This directory is the only durable write surface reserved for Lane B while it is in proposal-only mode. It does **not** authorize edits to W2-W13 runtime/domain authorities, current cognitive-loop runtime, Agent ACTIVE routes, accounts, orders or funds.

## Allowed proposal outputs

- `DEFECT-LEDGER.yaml` — confirmed defects, suspected defects, evidence gaps and provenance.
- `ROOT-CAUSE-MAP.md` — mechanism/root-cause alternatives, strongest counterevidence and falsification signals.
- `FIRST-REMEDIATION-SLICE.yaml` — one bounded candidate repair with exact affected modules and success/stop conditions.
- `EVAL-PLAN.md` — PIT/OOS/walk-forward/shadow/cost/slippage/T+1/regime validation plan as applicable.
- `IMPLEMENTATION-CLAIM-CANDIDATE.yaml` — proposed exact implementation write paths/interfaces/authority/resource class for future Control Tower rescan.
- current first-party/official evidence research retained with evidence level and time scope.

## Proposal-only analysis requirements

- separate confirmed fact, report, hypothesis, model inference and unknown;
- do not convert price movement into post-hoc causal explanation without evidence;
- when detailed real-time/order-flow data is unavailable, mark the relevant conclusion `DATA_INSUFFICIENT` rather than fabricate a mechanism;
- preserve W2 point-in-time/time-rule authority, W12 probability authority and W7 final risk-veto boundary;
- remain `RESEARCH_AND_DECISION_SUPPORT / NO_TRADE`.

## Forbidden in proposal-only mode

- no runtime/source edits outside this directory;
- no new executable Agent route;
- no second probability/risk/knowledge authority;
- no autonomous account/order/fund/trading action;
- no weakening of T+1, liquidity, transaction-cost, slippage or validation gates.

## Upgrade rule

Before implementation, freeze one bounded remediation slice and submit a new Work Claim with exact route binding, write paths, interfaces including frozen/mutable state, authority claims and resource class. Run the Control Tower collision/WIP/dependency scan and create a fresh durable authorization witness. Without that result, remain proposal-only.