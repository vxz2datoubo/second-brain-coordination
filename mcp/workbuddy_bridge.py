"""workbuddy_bridge.py — WorkBuddy MCP 服务器 (stdio)

将 WorkBuddy 暴露为 MCP 工具，供 MaiBot Planner 调用执行文件/代码任务。

WorkBuddy 定位：执行层（文件读写、脚本运行、本地自动化），
          与 Codex（架构审查）和 QClaw（分析算力）互补。

协议: JSON-RPC 2.0 over stdin/stdout
暴露 6 个工具:
  wb_file_read    — 读取文件内容
  wb_file_write   — 写入文件
  wb_file_list    — 列出目录
  wb_run_python   — 运行 Python 脚本
  wb_run_shell    — 运行 PowerShell 命令
  wb_status       — WorkBuddy 健康检查

启动方式 (bot_config.toml):
  [[mcp.servers]]
  name = "workbuddy-bridge"
  transport = "stdio"
  command = "python"
  args = ["-u", "F:/aidanao/mcp/workbuddy_bridge.py"]
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ============ 安全边界 ============
ALLOWED_ROOTS = [
    Path("F:/aidanao"),
    Path("F:/aidanao/qclaw-output"),
    Path("C:/Users/Administrator/.qclaw/workspace"),
    Path.home() / "Downloads",
]
ALLOWED_WRITE_ROOTS = [
    Path("F:/aidanao/qclaw-output"),
    Path("F:/aidanao/mcp/output"),
    Path.home() / "Downloads",
]

PYTHON_BIN = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"

def _is_allowed(path: Path, write: bool = False) -> bool:
    """安全校验：路径是否在允许范围内"""
    try:
        resolved = path.resolve()
    except Exception:
        return False
    roots = ALLOWED_WRITE_ROOTS if write else ALLOWED_ROOTS
    return any(str(resolved).startswith(str(r.resolve())) for r in roots)


# ============ 工具实现 ============

def wb_file_read(path: str, offset: int = 0, limit: int = 100) -> str:
    """读取文件内容"""
    p = Path(path)
    if not _is_allowed(p):
        return f"❌ 安全限制: 不允许读取 {path}"
    if not p.exists():
        return f"❌ 文件不存在: {path}"
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total = len(lines)
        chunk = lines[offset:offset + limit]
        preview = "\n".join(chunk)
        return f"📄 {p.name} ({total} 行, 显示 {offset+1}-{min(offset+limit, total)})\n{preview}"
    except Exception as e:
        return f"❌ 读取失败: {e}"


def wb_file_write(path: str, content: str, mode: str = "overwrite") -> str:
    """写入文件"""
    p = Path(path)
    if not _is_allowed(p, write=True):
        return f"❌ 安全限制: 不允许写入 {path}"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append" and p.exists():
            existing = p.read_text(encoding="utf-8", errors="replace")
            content = existing + "\n" + content
        p.write_text(content, encoding="utf-8")
        size = len(content.encode("utf-8"))
        return f"✅ 已写入 {p} ({size} bytes)"
    except Exception as e:
        return f"❌ 写入失败: {e}"


def wb_file_list(directory: str = "F:/aidanao", pattern: str = "*", depth: int = 1) -> str:
    """列出目录内容"""
    p = Path(directory)
    if not _is_allowed(p):
        return f"❌ 安全限制: 不允许访问 {directory}"
    if not p.exists():
        return f"❌ 目录不存在: {directory}"
    try:
        if depth == 1:
            items = sorted(p.glob(pattern))
        else:
            items = sorted(p.rglob(pattern))[:200]
        lines = [f"{'📁' if i.is_dir() else '📄'} {i.relative_to(p)}" for i in items[:100]]
        return f"📂 {p} ({len(items)} 项)\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ 列目录失败: {e}"


def wb_run_python(script: str, cwd: str = "F:/aidanao", timeout: int = 60) -> str:
    """运行 Python 脚本片段"""
    import tempfile
    cwd_p = Path(cwd)
    if not _is_allowed(cwd_p):
        return f"❌ 安全限制: 不允许在 {cwd} 执行"
    try:
        tmp = Path(tempfile.gettempdir()) / f"wb_mcp_{datetime.now().strftime('%H%M%S%f')}.py"
        tmp.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            [PYTHON_BIN, "-u", str(tmp)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(cwd_p),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        tmp.unlink(missing_ok=True)
        output = proc.stdout + proc.stderr
        if proc.returncode != 0:
            return f"❌ 退出码 {proc.returncode}\n{output[:2000]}"
        return f"✅ 执行成功\n{output[:2000]}"
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return f"❌ 超时 ({timeout}s)"
    except Exception as e:
        return f"❌ 异常: {e}"


def wb_run_shell(command: str, cwd: str = "F:/aidanao", timeout: int = 30) -> str:
    """运行 PowerShell 命令（受限白名单）"""
    # 安全白名单：禁止 rm/del/format 等危险操作
    DANGEROUS = ["rm ", "del ", "format ", "shutdown", "restart", "> /dev", "> nul", "| sh", "| bash"]
    cmd_lower = command.lower()
    for d in DANGEROUS:
        if d in cmd_lower:
            return f"❌ 安全限制: 禁止执行危险命令 ({d})"

    cwd_p = Path(cwd)
    if not _is_allowed(cwd_p):
        return f"❌ 安全限制: 不允许在 {cwd} 执行"

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(cwd_p),
        )
        output = proc.stdout + proc.stderr
        if proc.returncode != 0:
            return f"❌ 退出码 {proc.returncode}\n{output[:2000]}"
        return f"✅ 执行成功\n{output[:2000]}"
    except subprocess.TimeoutExpired:
        return f"❌ 超时 ({timeout}s)"
    except Exception as e:
        return f"❌ 异常: {e}"


def wb_status() -> str:
    """WorkBuddy 健康检查"""
    checks = {}
    # 检查 Python
    try:
        r = subprocess.run([PYTHON_BIN, "--version"], capture_output=True, text=True, timeout=5)
        checks["python"] = f"✅ {r.stdout.strip()}"
    except Exception:
        checks["python"] = "❌ 未找到"

    # 检查磁盘空间
    try:
        import shutil
        for drive, label in [("F:", "F盘"), ("C:", "C盘")]:
            usage = shutil.disk_usage(drive)
            free_gb = usage.free / (1024**3)
            checks[f"disk_{label}"] = f"{'✅' if free_gb > 5 else '⚠️'} {free_gb:.1f}G 可用"
    except Exception:
        checks["disk"] = "❌"

    # 检查关键目录
    for name, p in [("ai_dir", "F:/aidanao"), ("output_dir", "F:/aidanao/qclaw-output")]:
        checks[name] = f"{'✅' if Path(p).exists() else '❌'} {p}"

    lines = [f"{k}: {v}" for k, v in checks.items()]
    return "🛠️ WorkBuddy 状态\n" + "\n".join(lines)


# ============ MCP 协议 ============

TOOLS = [
    {
        "name": "wb_file_read",
        "description": "读取文件内容（UTF-8）。受限目录：仅允许 F:/aidanao、workspace、Downloads。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件绝对路径"},
                "offset": {"type": "integer", "default": 0, "description": "起始行号(0-based)"},
                "limit": {"type": "integer", "default": 100, "description": "最大返回行数"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "wb_file_write",
        "description": "写入文件。受限目录：仅允许 F:/aidanao/qclaw-output、F:/aidanao/mcp/output、Downloads。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件绝对路径（自动创建父目录）"},
                "content": {"type": "string", "description": "文件内容"},
                "mode": {"type": "string", "enum": ["overwrite", "append"], "default": "overwrite"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "wb_file_list",
        "description": "列出目录内容。受限目录：仅允许 F:/aidanao、workspace、Downloads。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "default": "F:/aidanao"},
                "pattern": {"type": "string", "default": "*", "description": "glob 模式"},
                "depth": {"type": "integer", "default": 1, "enum": [1, 2]},
            },
        },
    },
    {
        "name": "wb_run_python",
        "description": "在 WorkBuddy Python 3.13 环境中执行脚本片段（临时文件 + 自动清理）。适合小段数据分析/文件处理。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "Python 脚本内容"},
                "cwd": {"type": "string", "default": "F:/aidanao", "description": "工作目录"},
                "timeout": {"type": "integer", "default": 60, "description": "超时秒数"},
            },
            "required": ["script"],
        },
    },
    {
        "name": "wb_run_shell",
        "description": "运行 PowerShell 命令（有安全白名单，禁止 rm/del/format 等危险操作）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "PowerShell 命令"},
                "cwd": {"type": "string", "default": "F:/aidanao"},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["command"],
        },
    },
    {
        "name": "wb_status",
        "description": "WorkBuddy 健康检查：Python 版本、磁盘空间、关键目录状态。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

HANDLERS = {
    "wb_file_read": wb_file_read,
    "wb_file_write": wb_file_write,
    "wb_file_list": wb_file_list,
    "wb_run_python": wb_run_python,
    "wb_run_shell": wb_run_shell,
    "wb_status": wb_status,
}


def handle_request():
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method", "")
        rid = req.get("id")

        if method == "initialize":
            respond(rid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "workbuddy-bridge", "version": "1.0.0"},
            })
        elif rid is None:
            continue
        elif method == "tools/list":
            respond(rid, {"tools": TOOLS})
        elif method == "tools/call":
            name = req["params"]["name"]
            args = req["params"].get("arguments", {})
            handler = HANDLERS.get(name)
            if handler:
                try:
                    result = handler(**args)
                except Exception as e:
                    result = f"❌ {name} 异常: {e}"
            else:
                result = f"未知工具: {name}"
            respond(rid, {"content": [{"type": "text", "text": result}]})
        else:
            respond(rid, {"error": f"unsupported method: {method}"})


def respond(rid, result):
    print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    handle_request()
