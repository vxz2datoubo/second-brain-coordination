"""Codex MCP Bridge — 把 Codex CLI 注册为 WorkBuddy MCP 连接器

让 WorkBuddy 可以通过 MCP 工具协议调用 Codex, 而不用直接调命令行.

提供 4 个工具:
  1. codex_run         - 执行一次性任务
  2. codex_resume      - 续接上次会话
  3. codex_review      - 代码 review
  4. codex_doctor      - 健康检查

MCP 协议: stdin/stdout JSON-RPC 2.0
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# 路径常量
CODEX_BIN = r"C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\codex.cmd"
DEFAULT_OUTPUT_DIR = Path("F:/aidanao/qclaw-output/codex-runs")
DEFAULT_BRAIN_URL = "http://localhost:8766"

# 沙箱策略
SANDBOX_MAP = {
    "readonly": "read-only",
    "workspace-write": "workspace-write",
    "danger": "danger-full-access",
}


def _run_codex(args: list, timeout: int = 600) -> dict:
    """调 codex 命令, 返回结构化结果"""
    start = time.time()
    try:
        proc = subprocess.run(
            [CODEX_BIN] + args,
            capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_sec": round(time.time() - start, 2),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"timeout after {timeout}s"}
    except FileNotFoundError as e:
        return {"success": False, "error": f"codex not found: {e}"}


def codex_run(
    prompt: str,
    cwd: str = "F:/aidanao",
    sandbox: str = "workspace-write",
    model: str = "gpt-5.5",
    ephemeral: bool = True,
    timeout: int = 600,
) -> str:
    """执行 Codex 任务 (WorkBuddy MCP 入口)"""
    if sandbox not in SANDBOX_MAP:
        return f"❌ 非法沙箱: {sandbox}, 必须是 {list(SANDBOX_MAP.keys())}"

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = DEFAULT_OUTPUT_DIR / f"codex-{ts}.md"

    args = ["exec", prompt, "-C", cwd, "-s", SANDBOX_MAP[sandbox],
            "-m", model, "--json", "-o", str(out_file)]
    if ephemeral:
        args.append("--ephemeral")
    args.append("--skip-git-repo-check")

    result = _run_codex(args, timeout=timeout)

    if not result["success"]:
        return f"❌ Codex 失败 (exit={result.get('exit_code')})\nstderr: {result.get('stderr', '')[:500]}"

    # 解析 session_id
    session_id = None
    for line in result["stdout"].splitlines():
        if line.strip().startswith("{"):
            try:
                evt = json.loads(line)
                if evt.get("type") == "session_configured":
                    session_id = evt.get("session_id")
                    break
            except json.JSONDecodeError:
                pass

    # 读 output_file 内容
    out_content = ""
    if out_file.exists():
        out_content = out_file.read_text(encoding="utf-8", errors="replace")[:2000]

    # 自动摄入第二大脑
    brain_id = None
    if out_file.exists():
        try:
            text = f"""任务: {prompt}
工作目录: {cwd}
沙箱: {sandbox}
执行时长: {result['duration_sec']}s
Session: {session_id or '(无)'}

---
{out_content}
"""
            data = json.dumps({
                "title": f"Codex任务 | {datetime.now().strftime('%m-%d %H:%M')}",
                "text": text[:4000],
                "tags": "Codex,智能体,任务",
                "source": "codex-mcp-bridge",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{DEFAULT_BRAIN_URL}/api/digest/text",
                data=data, headers={"Content-Type": "application/json"},
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
            brain_id = resp.get("node", {}).get("id")
        except Exception as e:
            brain_id = f"摄入失败: {e}"

    return json.dumps({
        "success": True,
        "duration_sec": result["duration_sec"],
        "session_id": session_id,
        "output_file": str(out_file),
        "brain_node_id": brain_id,
        "preview": out_content[:500],
    }, ensure_ascii=False, indent=2)


def codex_resume(cwd: str = "F:/aidanao", last: bool = True) -> str:
    """续接上一个 Codex 会话"""
    args = ["exec", "resume"]
    if last:
        args.append("--last")
    args += ["-C", cwd]
    result = _run_codex(args, timeout=600)
    if not result["success"]:
        return f"❌ Resume 失败: {result.get('stderr', '')[:500]}"
    return f"✅ Codex resume 完成\n{result['stdout'][:2000]}"


def codex_review(cwd: str = "F:/aidanao") -> str:
    """对工作目录做 code review"""
    result = _run_codex(["review", "-C", cwd], timeout=600)
    if not result["success"]:
        return f"❌ Review 失败: {result.get('stderr', '')[:500]}"
    return f"✅ Codex review 完成\n{result['stdout'][:3000]}"


def codex_doctor() -> str:
    """健康检查"""
    result = _run_codex(["doctor"], timeout=30)
    out_raw = result.get("stdout", "")
    stderr = result.get("stderr", "")
    if not out_raw:
        return f"""Codex Doctor (无输出)
- Exit: {result.get('exit_code', '?')}
- Success: {result.get('success', False)}
- Error: {result.get('error', '')}
- Stderr: {str(stderr)[:500]}
"""
    ok = out_raw.count("\u2713")  # ✓
    # Count warnings and failures
    lines = out_raw.split("\n")
    warn = sum(1 for l in lines if "⚠" in l)
    fail = sum(1 for l in lines if "\u2717" in l)  # ✗
    return f"""Codex Doctor
- Exit: {result['exit_code']}
- 健康: {ok} ok / {warn} warn / {fail} fail
- 可达: {result['success']}
- 版本: 0.139.0

⚠️ 已知: ChatGPT API endpoint websocket 超时 (HTTPS fallback 仍可工作)
✗ 已知: 部分 provider 不可达

详情 (前 1500 字):
{out_raw[:1500] if out_raw else stderr[:500]}
"""


# === MCP 协议处理 ===
TOOLS = [
    {
        "name": "codex_run",
        "description": "执行 Codex 任务 (智能体模式, 高于 QClaw 算力层). 用于复杂多步任务: 代码生成/重构/分析/审查. 输出自动存入第二大脑.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "任务描述"},
                "cwd": {"type": "string", "default": "F:/aidanao", "description": "工作目录"},
                "sandbox": {"type": "string", "enum": ["readonly", "workspace-write", "danger"], "default": "workspace-write", "description": "沙箱策略"},
                "model": {"type": "string", "default": "gpt-5.5", "description": "模型名 (不支持的模型会报错, 用 gpt-5.5)"},
                "timeout": {"type": "integer", "default": 600, "description": "超时秒数"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "codex_resume",
        "description": "续接上一个 Codex 会话 (--last 模式)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "F:/aidanao"},
            },
        },
    },
    {
        "name": "codex_review",
        "description": "对工作目录做 code review (Codex 智能体模式)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "F:/aidanao"},
            },
        },
    },
    {
        "name": "codex_doctor",
        "description": "检查 Codex 安装和健康状态",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle_request():
    """MCP stdin/stdout JSON-RPC 2.0 处理"""
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method", "")
        req_id = req.get("id")
        is_notification = req_id is None

        if method == "initialize":
            requested_protocol = req.get("params", {}).get("protocolVersion")
            respond(req_id, {
                "protocolVersion": requested_protocol or "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "codex-bridge", "version": "1.0.0"},
            })
        elif is_notification:
            continue
        elif method == "tools/list":
            respond(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            tool_name = req["params"]["name"]
            args = req["params"].get("arguments", {})
            handlers = {
                "codex_run": codex_run,
                "codex_resume": codex_resume,
                "codex_review": codex_review,
                "codex_doctor": codex_doctor,
            }
            handler = handlers.get(tool_name)
            if handler:
                try:
                    result_text = handler(**args)
                except Exception as e:
                    result_text = f"❌ 异常: {e}"
            else:
                result_text = f"未知工具: {tool_name}"
            respond(req_id, {"content": [{"type": "text", "text": result_text}]})
        else:
            respond(req_id, {"error": f"unsupported method: {method}"})


def respond(req_id, result):
    print(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}), flush=True)


if __name__ == "__main__":
    handle_request()
