"""QClaw MCP Bridge — 把 QClaw API 注册为 WorkBuddy MCP 连接器

v2 改造: 不再硬编码 token/port, 复用 core.qclaw.QClawBridge 的动态探测
和统一 token 解析 (避免重启后 token 失联)。
"""
import json
import sys
from core.qclaw import QClawBridge

# 全局单例 — MCP stdin 循环中只初始化一次, 避免每次调用都重启健康检查
_qclaw = None

def _get_qclaw():
    global _qclaw
    if _qclaw is None:
        _qclaw = QClawBridge()
    return _qclaw

def handle_request():
    """MCP stdin/stdout 协议处理"""
    for line in sys.stdin:
        req = json.loads(line)
        method = req.get("method", "")
        req_id = req.get("id", 0)

        if method == "initialize":
            respond(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "qclaw-bridge", "version": "2.0.0"}
            })

        elif method == "tools/list":
            respond(req_id, {
                "tools": [{
                    "name": "qclaw_ask",
                    "description": "调用 QClaw 本地算力分析问题。QClaw 是桌面 AI，已配置为 WorkBuddy 纯算力引擎。",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "分析任务描述"},
                            "max_tokens": {"type": "integer", "default": 1500, "description": "最大输出 token 数"}
                        },
                        "required": ["prompt"]
                    }
                }, {
                    "name": "qclaw_analyze_douyin",
                    "description": "用 QClaw 深度分析抖音视频内容: 事实核查/评论洞察/市场机会",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "video_url": {"type": "string", "description": "抖音视频链接"},
                            "video_data": {"type": "string", "description": "已提取的视频页面数据(JSON)"}
                        },
                        "required": ["video_url", "video_data"]
                    }
                }]
            })

        elif method == "tools/call":
            tool_name = req["params"]["name"]
            args = req["params"].get("arguments", {})

            if tool_name == "qclaw_ask":
                result = call_qclaw(args["prompt"], args.get("max_tokens", 1500))
            elif tool_name == "qclaw_analyze_douyin":
                result = analyze_douyin(args["video_url"], args["video_data"])
            else:
                result = f"未知工具: {tool_name}"

            respond(req_id, {"content": [{"type": "text", "text": result}]})

def call_qclaw(prompt, max_tokens=1500):
    """v2: 复用 QClawBridge, 动态 token + 动态端口, 不再硬编码
    QClawBridge.ask() 内部自带 system 提示词, 这里只传 user prompt.
    """
    qc = _get_qclaw()
    content, _ = qc.ask(prompt, max_tokens=max_tokens)
    return content

def analyze_douyin(video_url, video_data):
    return call_qclaw(f"分析抖音视频: {video_url}\n数据: {video_data[:3000]}", 2000)

def respond(req_id, result):
    print(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}), flush=True)

if __name__ == "__main__":
    import json
    handle_request()
