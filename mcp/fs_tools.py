"""WorkBuddy 文件系统辅助工具 MCP 服务器

为 WorkBuddy 和 Codex 提供文件系统操作、知识图谱读写、第二大脑交互等工具。

注册为 MCP 连接器后，WorkBuddy 可以在不直接跑命令的情况下:
  - 扫描文件系统结构
  - 读取知识图谱
  - 写入第二大脑
  - 列出产出目录

协议: stdin/stdout JSON-RPC 2.0
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 路径常量
BRAIN_URL = "http://localhost:8766"
WORKSPACE_ROOT = Path("F:/aidanao")


# ============================================================
# 工具实现
# ============================================================

def scan_filesystem(path_str: str = "F:/aidanao", depth: int = 2, pattern: str = "") -> str:
    """扫描文件系统结构，返回可读的树状描述"""
    root = Path(path_str)
    if not root.exists():
        return f"❌ 路径不存在: {path_str}"

    result = []
    limit = depth if depth > 0 else 99

    def walk(p: Path, level: int):
        if level > limit:
            return
        try:
            entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        except PermissionError:
            result.append("  " * level + "  ⚠️ (无权限)")
            return

        for entry in entries:
            if entry.name.startswith(".") or entry.name == "__pycache__":
                continue
            if pattern and pattern not in entry.name:
                continue
            prefix = "  " * level
            if entry.is_dir():
                result.append(f"{prefix}📁 {entry.name}/")
                walk(entry, level + 1)
            else:
                size = entry.stat().st_size
                if size < 1024:
                    sz = f"{size}B"
                elif size < 1024 * 1024:
                    sz = f"{size/1024:.0f}KB"
                else:
                    sz = f"{size/1024/1024:.1f}MB"
                result.append(f"{prefix}📄 {entry.name} ({sz})")

    walk(root, 0)
    return "\n".join(result) if result else "(空)"


def read_file(file_path: str, max_chars: int = 50000) -> str:
    """读取文件内容"""
    p = Path(file_path)
    if not p.exists():
        return f"❌ 文件不存在: {file_path}"
    if not p.is_file():
        return f"❌ 不是文件: {file_path}"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... (截断, 共{len(content)}字符, 仅显示前{max_chars})"
        return content
    except Exception as e:
        return f"❌ 读取失败: {e}"


def list_recent_outputs(count: int = 20) -> str:
    """列出 qclaw-output 和 codex-runs 最近产出"""
    results = []

    for base_name in ["qclaw-output", "qclaw-output/codex-runs"]:
        base = WORKSPACE_ROOT / base_name
        if not base.exists():
            continue
        files = sorted(base.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:count]
        if not files:
            continue
        results.append(f"📂 {base_name}/")
        for f in files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%m-%d %H:%M")
            size = f.stat().st_size
            results.append(f"  {mtime}  {size:>6}B  {f.name}")

    return "\n".join(results) if results else "(空)"


def read_knowledge_graph() -> str:
    """读取知识图谱结构（节点数量、分类统计、前N个节点）"""
    kg_path = WORKSPACE_ROOT / "data" / "knowledge-graph.json"
    if not kg_path.exists():
        return "❌ 知识图谱文件不存在"

    try:
        data = json.loads(kg_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"❌ 读取失败: {e}"

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # 分类统计
    categories = {}
    for n in nodes:
        cat = n.get("category", "uncategorized")
        categories[cat] = categories.get(cat, 0) + 1

    cat_lines = "\n".join(f"  {k}: {v}个" for k, v in sorted(categories.items()))

    # 前20个节点
    top = nodes[:20]
    top_lines = "\n".join(
        f"  {n.get('id','?')}  [{n.get('category','?')}]  {n.get('title','?')[:60]}"
        for n in top
    )

    return (
        f"知识图谱概览\n"
        f"  节点总数: {len(nodes)}\n"
        f"  关系边: {len(edges)}\n"
        f"  \n分类分布:\n{cat_lines}\n"
        f"  \n前{len(top)}个节点:\n{top_lines}"
    )


def search_knowledge_graph(query: str, max_results: int = 10) -> str:
    """在知识图谱中搜索节点（按标题和内容匹配）"""
    kg_path = WORKSPACE_ROOT / "data" / "knowledge-graph.json"
    if not kg_path.exists():
        return "❌ 知识图谱文件不存在"

    try:
        data = json.loads(kg_path.read_text(encoding="utf-8"))
    except Exception:
        return "❌ 读取失败"

    q = query.lower()
    hits = []
    for n in data.get("nodes", []):
        if q in n.get("title", "").lower() or q in n.get("content", "").lower():
            hits.append(f"  {n['id']}  [{n.get('category','?')}]  {n['title'][:80]}")

    if not hits:
        return f"未找到匹配 '{query}' 的节点"

    hits = hits[:max_results]
    return f"搜索 '{query}' 找到 {len(hits)} 个节点:\n" + "\n".join(hits)


def write_to_brain(title: str, text: str, source: str = "codex-fs-tools", tags: str = "Codex") -> str:
    """写入第二大脑知识库 (POST /api/digest/text)"""
    import urllib.request

    try:
        data = json.dumps({
            "title": title,
            "text": text[:5000],
            "tags": tags,
            "source": source,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{BRAIN_URL}/api/digest/text",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        node_id = resp.get("node", {}).get("id", "?")
        return f"✅ 已写入第二大脑 (node: {node_id})"
    except Exception as e:
        return f"❌ 写入失败: {e}"


def search_brain(query: str, max_results: int = 5) -> str:
    """搜索第二大脑知识库 (GET /api/retrieve/search)"""
    import urllib.request
    import urllib.parse

    try:
        url = f"{BRAIN_URL}/api/retrieve/search?q={urllib.parse.quote(query)}&top_k={max_results}"
        req = urllib.request.Request(url)
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())

        results = resp.get("results", [])
        if not results:
            return f"未找到匹配 '{query}' 的结果"

        lines = [f"搜索 '{query}' 找到 {len(results)} 条:"]
        for r in results:
            title = r.get("title", r.get("node", {}).get("title", "?"))
            score = r.get("score", 0)
            node_id = r.get("node", {}).get("id", "?")
            snippet = r.get("snippet", "")[:120]
            lines.append(f"\n  [{score:.2f}] {node_id}  {title}")
            if snippet:
                lines.append(f"         {snippet}")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ 搜索失败: {e}"


def health_check() -> str:
    """检查第二大脑服务器是否运行"""
    import urllib.request

    status = []
    status.append(f"⚙️ Codex: 已安装")

    # 检查第二大脑
    try:
        resp = urllib.request.urlopen(f"{BRAIN_URL}/", timeout=3)
        status.append(f"🧠 第二大脑: ✅ ({resp.status})")
    except Exception:
        status.append("🧠 第二大脑: ❌ 未运行")

    # 检查知识图谱文件
    kg_path = WORKSPACE_ROOT / "data" / "knowledge-graph.json"
    if kg_path.exists():
        size = kg_path.stat().st_size
        try:
            data = json.loads(kg_path.read_text(encoding="utf-8"))
            nodes = len(data.get("nodes", []))
            edges = len(data.get("edges", []))
            status.append(f"📊 知识图谱: ✅ ({nodes}节点 / {edges}边 / {size//1024}KB)")
        except Exception:
            status.append(f"📊 知识图谱: ⚠️ 文件存在但解析失败")
    else:
        status.append("📊 知识图谱: ❌ 文件不存在")

    # 检查产出目录
    out_dir = WORKSPACE_ROOT / "qclaw-output"
    if out_dir.exists():
        md_files = len(list(out_dir.rglob("*.md")))
        status.append(f"📝 产出目录: ✅ ({md_files}个md文件)")
    else:
        status.append("📝 产出目录: ❌ 不存在")

    return "\n".join(status)


# ============================================================
# MCP 工具注册
# ============================================================
TOOLS = [
    {
        "name": "fs_scan",
        "description": "扫描文件系统结构 (树状). 支持 depth 控制层级, pattern 过滤文件名.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "F:/aidanao", "description": "扫描路径"},
                "depth": {"type": "integer", "default": 2, "description": "扫描深度"},
                "pattern": {"type": "string", "default": "", "description": "文件名过滤关键词"},
            },
        },
    },
    {
        "name": "fs_read",
        "description": "读取文件内容. 支持限制读取字符数.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件绝对路径"},
                "max_chars": {"type": "integer", "default": 50000, "description": "最大字符数"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "fs_list_outputs",
        "description": "列出 qclaw-output 和 codex-runs 最近产出文件 (按修改时间排序).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 20, "description": "最近N个文件"},
            },
        },
    },
    {
        "name": "brain_read_graph",
        "description": "读取知识图谱结构: 节点数、分类分布、关系边数、前N个节点列表.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "brain_search_graph",
        "description": "在知识图谱中搜索节点 (按标题和内容关键词).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_write",
        "description": "写入第二大脑知识库. 内容自动截断到5000字符.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "知识标题"},
                "text": {"type": "string", "description": "知识内容"},
                "source": {"type": "string", "default": "codex-fs-tools"},
                "tags": {"type": "string", "default": "Codex"},
            },
            "required": ["title", "text"],
        },
    },
    {
        "name": "brain_search",
        "description": "搜索第二大脑知识库 (RAG检索, 按相关性排序).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fs_health",
        "description": "健康检查: Codex 安装状态、第二大脑运行状态、知识图谱完整性.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

HANDLERS = {
    "fs_scan": lambda **kw: scan_filesystem(**kw),
    "fs_read": lambda **kw: read_file(**kw),
    "fs_list_outputs": lambda **kw: list_recent_outputs(**kw),
    "brain_read_graph": lambda **kw: read_knowledge_graph(),
    "brain_search_graph": lambda **kw: search_knowledge_graph(**kw),
    "brain_write": lambda **kw: write_to_brain(**kw),
    "brain_search": lambda **kw: search_brain(**kw),
    "fs_health": lambda **kw: health_check(),
}


# ============================================================
# MCP 协议处理
# ============================================================
def handle_request():
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id", 0)

        if method == "initialize":
            respond(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "workbuddy-fs-tools", "version": "1.0.0"},
            })
        elif method == "tools/list":
            respond(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            tool_name = req["params"]["name"]
            args = req["params"].get("arguments", {})
            handler = HANDLERS.get(tool_name)
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
