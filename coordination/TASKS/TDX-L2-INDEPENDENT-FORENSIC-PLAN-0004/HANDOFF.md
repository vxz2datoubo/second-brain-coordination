# HANDOFF

## Summary

This plan round completed an independent read-only review plan for TongDaXin L2 access routes. No code, TongDaXin files, runtime data, Git state, client state, or trading functions were modified.

## Most Important Verified Facts

- WorkBuddy raw JSONL evidence exists and should remain the primary evidence base, not the summary reports alone.
- Current local `tqcenter.py` exists, so old "TdxQuant missing" claims are stale.
- TDX MCP raw captures support five-depth snapshots plus changing L2-adjacent aggregate fields.
- TDX MCP raw captures do not support ten-depth, raw trades, raw orders, queues, cancellation events, or auction trajectories.
- Local file evidence is not exhausted by `.l2d/.tick` search; cache and DB objects require copy-first forensic analysis.

## Recommended Next Task

Run `TDX-L2-INDEPENDENT-FORENSIC-RUN-0005` in goal mode after approval.

Suggested order:

1. Local file inventory and delta monitor.
2. TdxQuant read-only import/init/snapshot probe.
3. Short `subscribe_hq` callback capture for `300418.SZ`.
4. Expand to `300058.SZ`, `600519.SH`, `510300.SH`.
5. Formula test for L2 aggregate functions.

## User / ChatGPT Approval Needed

- Approve whether to run the TdxQuant runtime probe during a live trading window.
- Approve whether Codex may copy changing TongDaXin files into an independent evidence directory for analysis.
- Approve whether to install or use a PE export parser if DLL export inspection is required.
- Confirm WorkBuddy is not simultaneously writing to the same evidence directory.

## Output Directory

`F:\aidanao\coordination\TASKS\TDX-L2-INDEPENDENT-FORENSIC-PLAN-0004\`

