# INITIAL COMMIT PLAN

## Goal

Create a first Git baseline that captures stable source, tests, and approved docs without dragging in runtime state, secrets, or large binary payloads.

## Recommended Initial Include Scope

1. root control files
   - `F:/aidanao/AGENTS.md`
   - `F:/aidanao/SYSTEM_MANUAL.md`
   - `F:/aidanao/AUTO_EVOLUTION.md`
   - `F:/aidanao/MCP_TOOLS.md`
   - `F:/aidanao/server.py`

2. mother-system code
   - `F:/aidanao/brain_core/`
   - `F:/aidanao/apps/`
   - selected `F:/aidanao/core/` files after secret review

3. trading code
   - `F:/aidanao/daytrade_system/` except live secret-bearing files until sanitized
   - `F:/aidanao/mcp/` except secret-bearing token defaults until sanitized

4. tests
   - `F:/aidanao/tests/`

5. approved docs
   - `F:/aidanao/docs/`
   - selected blueprint and governance markdown

## Recommended Initial Exclude Scope

1. runtime state
   - `F:/aidanao/data/`
   - `F:/aidanao/bulletin/super-second-brain-v01-board.md`
   - `F:/aidanao/second-brain/daily_log.md`

2. generated / archival content
   - `F:/aidanao/backups/`
   - `F:/aidanao/qclaw-output/`
   - `F:/aidanao/handoff/`
   - `F:/aidanao/coordination/RESULTS/`

3. local dependencies and binaries
   - `.venv/`
   - `codex_siliconflow_proxy/.venv/`
   - `tools/dreamina/dreamina.exe`

## Blockers Before Safe Initial Commit

1. remove or exclude hardcoded secrets in:
   - `core/tushare_bridge.py`
   - `core/qclaw.py`
   - `daytrade_system/live/tdx_mcp_client.py`
   - `mcp/tdx_live_bridge.py`

2. decide whether `second-brain/rules.md` and `second-brain/lessons.md` are source-controlled knowledge or mutable runtime state

3. decide whether live bulletin markdown is:
   - excluded entirely, or
   - replaced by a sanitized seed template

## Recommended Commit Order

1. commit baseline scaffolding and governance docs
2. commit mother-system code and tests
3. commit trading code after secret cleanup
4. add curated sample fixtures later, in a separate commit

## Explicit Non-Goals

- do not commit SQLite, JSONL, raw market dumps, or long-running audit logs in the first baseline
- do not commit credential-bearing connectors before sanitation
