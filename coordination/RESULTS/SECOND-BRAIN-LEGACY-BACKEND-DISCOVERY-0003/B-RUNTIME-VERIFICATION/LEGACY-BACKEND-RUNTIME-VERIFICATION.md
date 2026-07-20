# Legacy Backend Runtime Verification Report

- **Task**: SECOND-BRAIN-LEGACY-BACKEND-DISCOVERY-0003B
- **Phase**: B / RUNTIME_VERIFICATION
- **Agent**: WORKBUDDY
- **Date**: 2026-07-20 10:30 CST
- **Input**: CANDIDATE-ENDPOINTS.yaml (Phase A, GPT-verified via Issue #24)

---

## Executive Summary

**1 of 5 candidates is actively listening.** SB-HTTP-8766 (localhost:8766) is the sole confirmed running second-brain backend. Three candidates are not running. One (SB-MCP-STDIO) cannot be verified via TCP alone.

| Status | Count | Candidates |
|--------|-------|------------|
| LISTENING | 1 | SB-HTTP-8766 |
| NOT_LISTENING | 3 | SB-DEEP-HTTP-8767, SB-LEGACY-HTTP-MCP-8767, SB-CHATGPT-BRIDGE-8799 |
| UNKNOWN | 1 | SB-MCP-STDIO (stdio MCP) |

---

## Detailed Findings

### 1. SB-HTTP-8766 — **LISTENING** ✅

**This is the sole confirmed active candidate at check time (2026-07-20 10:30 CST).** Classification as canonical backend or otherwise is deferred to phase C.

| Property | Value |
|----------|-------|
| Address | 0.0.0.0:8766 |
| PID | 24344 |
| Process | python.exe (WorkBuddy managed Python 3.13.12) |
| Startup | `python -u F:\aidanao\server.py` |
| Working Dir | F:\aidanao |
| Running Since | 2026-07-18 14:29 CST |
| Bind | 0.0.0.0 (may be LAN-reachable if no firewall rule; firewall not verified) |

**Health Checks:**

| Path | Method | Status | Summary |
|------|--------|--------|---------|
| `/` | GET | 200 | HTML web UI |
| `/health` | GET | 200 | Error HTML (no dedicated health endpoint) |
| `/api/retrieve/search` | POST | 200 | JSON API functional |
| `/api/digest/text` | POST | 404 | Not implemented on this version |
| `/api/events/upcoming` | GET | 200 | Events API |

**API Capabilities:**
- REST JSON API for knowledge retrieval (`/api/retrieve/search`)
- Calendar/events endpoint (`/api/events/upcoming`)
- Web UI served at root

**Data Directory:** `F:/aidanao/data/` — contains knowledge-graph.json, category-index.json, super_brain_v01.sqlite.

**Evidence Level:** VERIFIED_FACT — port listening, process confirmed, HTTP responses validated.

---

### 2. SB-DEEP-HTTP-8767 — **NOT LISTENING** ❌

Port 8767 has no listener. Source file `F:/aidanao/deep_server.py` exists (16,767 bytes, 2026-07-06) but no process is running on this port.

**Blocker:** Port conflict with SB-LEGACY-HTTP-MCP-8767 — both declare port 8767. Cannot coexist.

**Evidence Level:** PARTIAL_EVIDENCE — source exists, runtime absent.

---

### 3. SB-LEGACY-HTTP-MCP-8767 — **NOT LISTENING** ❌

Port 8767 has no listener. Source file `F:/aidanao/mcp/brain_server.py` exists (5,282 bytes, 2026-07-04) but no process is running.

**Blocker:** Port conflict with SB-DEEP-HTTP-8767. Both declare port 8767.

**Evidence Level:** PARTIAL_EVIDENCE — source exists, runtime absent.

---

### 4. SB-MCP-STDIO — **UNKNOWN** ⚠️

Cannot verify via TCP — this is a stdio MCP server. Source file `F:/aidanao/mcp/brain_bridge.py` exists (53,545 bytes, 2026-07-14).

**Key finding:** This is an adapter, not a standalone backend. It forwards to `http://localhost:8766` for knowledge operations.

**API Capabilities (from source):**
- MCP tools: search_knowledge, get_knowledge_node, list_categories, get_stats
- MCP resources: knowledge://categories, knowledge://search/{query}

**Evidence Level:** PARTIAL_EVIDENCE — source verified, runtime unverified. Would require MCP initialize handshake over stdin/stdout.

---

### 5. SB-CHATGPT-BRIDGE-8799 — **NOT LISTENING** ❌

Port 8799 has no listener. Source file `F:/aidanao/chatgpt_bridge/bridge.py` exists (4,550 bytes, 2026-07-12). FastAPI/uviicorn bridge for ChatGPT → Second Brain ingestion.

**Evidence Level:** PARTIAL_EVIDENCE — source exists, runtime absent. Adapter only; depends on SB-HTTP-8766.

---

## Historical Path Clue: F:/ai

The `F:/ai` directory exists and contains:
- `F:/ai/second-brain-coordination` — cloned coordination repo
- `F:/ai/qclaw-output` — QClaw output archives
- `F:/ai/tdx-l2` — TDX Level-2 data
- Timestamped directories (2026-07-13 through 2026-07-17)

References to `F:/ai` in `F:/aidanao/core/qclaw.py` (lines 216, 349) are confirmed as historical artifacts. The active project root is `F:/aidanao`. No active service runs from `F:/ai` on any candidate port.

**Evidence Level:** VERIFIED_FACT — directory exists, no active service.

---

## Conclusions

1. **SB-HTTP-8766 is the sole confirmed active candidate at check time.** The other 4 candidates were not listening at 2026-07-20 10:30 CST; classification of their status (maintained, archived, migratable, etc.) is deferred to Issue #26 phase C.
2. Port 8767 has a static conflict: two different services declare the same port. Neither is running.
3. SB-MCP-STDIO (brain_bridge.py) is an MCP adapter, not a standalone backend — it proxies to SB-HTTP-8766.
4. SB-CHATGPT-BRIDGE-8799 is offline and is an integration adapter only.
5. F:/ai historical references are harmless artifacts; no migration risk.
6. For phase C (capability mapping), SB-HTTP-8766 is the primary target. SB-MCP-STDIO may be verified if an MCP client is available.

---

## Commands Executed

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8766,8767,8799
Get-Process -Id <pid> | Select Path,StartTime
Get-WmiObject Win32_Process -Filter "ProcessId=<pid>" | Select CommandLine
Test-Path <file_path>
Get-ChildItem F:/ai -Directory
```

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8766/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8766/health
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8766/api/retrieve/search -H "Content-Type: application/json" -d '{"query":"test"}'
curl -s -o /dev/null -w "%{http_code}" http://localhost:8767/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8799/
```
