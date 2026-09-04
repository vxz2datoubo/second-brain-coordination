---
name: trading-system-relay
description: Map and verify the second-brain A-share trading system handoff between GPT, Codex and WorkBuddy, including GitHub-to-local reproducibility, capability evidence, numeric contracts, knowledge gaps and model fallback. Use for architecture, delivery and research replay; preserve existing task, market and knowledge authorities.
---

# Trading system relay

agent_id: CODEX

This is a user-requested candidate skill, not a canonical task route or production permission. Keep `research_only / NO_TRADE`.

## Read and map before changing

1. Read the current repository `AGENTS.md`, remote `main` SHA, relevant charter and task routes. A dirty local checkout is not the remote truth. Existing short-command routes still apply to “读取任务”; a new user architecture request must not preempt unrelated active work.
2. Use [architecture](references/architecture.md) for deployment, relay, fallback, department contracts and acceptance gates. Inventory each requirement as REUSE, ADAPT, WRAP, NEW_CANDIDATE, REFERENCE_ONLY or UNKNOWN, with a file/ref and an observable test. A document or skill catalog entry does not prove executable capability.
3. Use [knowledge map](references/knowledge-map.md) for the four user knowledge bands and source-to-method mapping. Reuse EPISTEMIC-0013, PEOS, Gap Compiler and W3; never create a second memory or infer user mastery from silence.
4. Use [research ledger](references/research-ledger.md) for official sources, limitations, counterevidence and triggers to recheck. New external knowledge is candidate evidence until tested, not an automatic skill or blueprint promotion.

## Establish execution, not a narrative

- GitHub holds versioned software, approved contracts and public-safe evidence. A runner executes software. GPT may initiate or interpret that run only through an available, authorized tool; repository reading alone proves neither execution nor write access.
- Reuse the repository's `PHASE-2-OFFLINE-VERTICAL-SLICE/run_demo.py` through the sibling `../../scripts/prove_replay.py` verifier. Read its `--help`. Use only its synthetic fixture. Set `-X utf8` on Windows. Require a new output directory, source commit, source and input hashes, fixed as-of, runtime version, two actual subprocess runs and artifact equality.
- A PASS here means synthetic offline execution, including safe abstention when the calendar is absent. It does not certify live data, complete trading, profitability, GPT cloud execution or WB deployment.
- For cross-machine acceptance, rerun the same exact commit on another runner and compare `artifact_hashes`; keep host/time/challenge separate. Verify a remote Actions run's `head_sha`, status and artifact against its actual URL. A checksum detects changes, not who honestly ran the code.
- Test a GPT session with a fresh caller challenge and read-only repo fetch first. Test a real execution tool next, if available. If absent, record `READ_ONLY_VERIFIED / EXECUTION_UNVERIFIED`; do not simulate a tool result in prose.

## Freeze meaning without freezing the market

Apply [numeric contract](references/numeric-contract.md). Hard-lock schemas, units, temporal meaning, provenance, evidence requirements and `NO_TRADE`. Version exchange rules by effective time. Learn strategy parameters only from preregistered training slices. Keep uncertainty, null and inferred fields explicit. Never turn a vendor bucket or OHLCV proxy into investor identity.

## Handoff and fallback

Use existing route/claim/lease authorities. A handoff records source_agent, target_agent, reviewer, review_status, exact commit, allowed paths, acceptance commands, evidence, blockers and next action. Reviewer assignment is not review completion. Preserve other agents' files and never self-merge.

Default: GPT direction → CODEX architecture/contracts/tests → WORKBUDDY implementation and local operation. On Codex quota exhaustion: GPT direction plus detailed architecture → WORKBUDDY implementation → distinct review. Record actual product/model only from runtime evidence; do not assume the user-described Flash model name or price is verified.

Deliver a self-contained Chinese report with agent_id, evidence grades, implemented vs proposed boundaries, failures, scope effects, unknown owners and next gates. The result must remain usable when every LLM is offline.
