#!/usr/bin/env python3
"""探针: 测试本地 connector-proxy (127.0.0.1:8505/mcp) 是否可作为 MCP JSON-RPC 端点被 Python 直连"""
import json, urllib.request, urllib.error

URL = "http://127.0.0.1:8505/mcp"

def rpc(method, params=None, sid=None, notif=False):
    body = {"jsonrpc": "2.0", "method": method}
    if not notif:
        body["id"] = 1
    if params is not None:
        body["params"] = params
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if sid:
        req.add_header("Mcp-Session-Id", sid)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        sid2 = resp.headers.get("Mcp-Session-Id", sid)
        raw = resp.read().decode("utf-8", "replace")
        return resp.status, sid2, raw
    except urllib.error.HTTPError as e:
        return e.code, None, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, None, f"ERR:{e}"

print("=== 1) initialize ===")
st, sid, raw = rpc("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "probe", "version": "0.1"},
})
print("status:", st, "sid:", sid)
print("resp:", raw[:600])

if st == 200 and sid:
    print("\n=== 2) tools/list ===")
    st2, sid2, raw2 = rpc("tools/list", {}, sid)
    print("status:", st2)
    # parse SSE or json
    if raw2.startswith("{"):
        try:
            j = json.loads(raw2)
            tools = j.get("result", {}).get("tools", [])
            print("tool count:", len(tools))
            names = [t["name"] for t in tools if "westock" in t["name"].lower() or "data_" in t["name"].lower()][:40]
            print("westock/data_ tools (sample):", names[:40])
        except Exception as e:
            print("json parse err:", e, raw2[:400])
    else:
        # SSE
        print("SSE raw[:800]:", raw2[:800])
    # initialized notification
    rpc("notifications/initialized", {}, sid, notif=True)
