# REALTIME-DATA-MULTI-ROUTE-INTEGRATION-PLAN-0009

## Mode

Project plan only. No business source code changes, no TdxQuant calls, no TDX MCP calls, no access to `F:\tongdaxin`, no Git operations, no trading or account interfaces.

## Objective

Plan a unified realtime and near-realtime A-share market data ingestion architecture for the SuperBrain mother system. The plan must connect TdxQuant native Python, TQ-Python Skill, TQ-Local HTTP, TDX MCP, WeStock, vipdoc historical files, and future regulated raw L2 sources into one governed raw -> normalized -> feature -> signal pipeline.

## Current Verified Premises

- Old TdxQuant can provide five-level snapshots.
- `subscribe_hq` callback is an update notification only: payload observed as `Code/ErrorId`, not price/volume/tick data.
- v1.0.4 `get_more_info` has verified 86 fields.
- 13 L2 aggregate fields are verified before upgrade: `L2TicNum`, `L2OrderNum`, `TotalBVol`, `TotalSVol`, `BCancel`, `SCancel`, `Zjl`, `Zjl_HB`, `OpenAmo`, `OpenZTBuy`, `Wtb`, `FzAmo`, `VOpenZAF`.
- Ten-level depth, raw trade tick, raw order event, order queue, single cancel event, and auction trajectory remain unverified.
- WorkBuddy is performing official TQ upgrade A/B testing; 0008 post-upgrade evidence is not yet available in this repository snapshot.

## Deliverable

This directory contains architecture maps, schemas, semantic rules, collection design, failover rules, upgrade decision gates, milestones, acceptance criteria, risks, status, and handoff notes.

