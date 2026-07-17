"""
syncer.py - WorkBuddy 会话同步引擎
零外部依赖。纯 Python stdlib 实现。

功能:
- 扫描 WorkBuddy 历史会话 (sessions/*.json + projects/*.md)
- 提取对话知识点并摄入知识图谱
- 同步长期记忆文件 (MEMORY.md, memory/*.md)
- 增量同步 (只处理上次同步后的新内容)
- 同步状态持久化 (sync-state.json)

使用方式:
    from core.graph import KnowledgeGraph
    from core.digest import TextDigester
    from core.syncer import WorkBuddySyncer

    syncer = WorkBuddySyncer(graph, digester, data_dir)
    new = syncer.scan()        # 扫描
    added = syncer.ingest(ids) # 摄入
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


class WorkBuddySyncer:
    """WorkBuddy 会话同步器 — 被动积累知识

    数据源:
    - ~/.workbuddy/sessions/*.json      (WorkBuddy 会话记录)
    - ~/.workbuddy/projects/*/*.md      (项目历史会话)
    - ~/.workbuddy/MEMORY.md            (跨项目长期记忆)
    - ~/.workbuddy/memory/*.md          (长期记忆文件)
    - {workspace}/.workbuddy/memory/*.md (项目日记)
    """

    def __init__(self, graph, digester, data_dir: Path):
        self.graph = graph          # KnowledgeGraph 实例
        self.digester = digester    # TextDigester 实例
        self.data_dir = data_dir
        self.wb_home = Path.home() / ".workbuddy"
        self.state_path = data_dir / "sync-state.json"
        self.state = self._load_state()

    # ========== 状态管理 ==========
    def _load_state(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "last_session_sync": "1970-01-01T00:00:00",
                "last_memory_sync": "1970-01-01T00:00:00",
                "synced_sessions": [],
                "total_nodes_synced": 0
            }

    def _save_state(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def get_state(self) -> dict:
        """获取当前同步状态"""
        return dict(self.state)

    # ========== 扫描 ==========
    def scan(self, since: str = None) -> list[dict]:
        """扫描自上次同步以来的新会话。

        Args:
            since: ISO时间戳，默认使用上次同步时间

        Returns:
            [{"id": ..., "path": ..., "modified": ..., "size": ...}, ...]
        """
        if since is None:
            since = self.state.get("last_session_sync", "1970-01-01T00:00:00")
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            since_dt = datetime(1970, 1, 1)

        new_sessions = []

        # 1. 扫描 sessions/ 目录 (JSON 格式)
        sessions_dir = self.wb_home / "sessions"
        if sessions_dir.exists():
            for f in sorted(sessions_dir.glob("*.json")):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > since_dt:
                    new_sessions.append({
                        "id": f.stem,
                        "path": str(f),
                        "type": "session",
                        "modified": mtime.isoformat(),
                        "size": f.stat().st_size
                    })

        # 2. 扫描 projects/ 目录 (按项目组织)
        projects_dir = self.wb_home / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                for md_file in sorted(project_dir.glob("*.md")):
                    mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                    if mtime > since_dt:
                        new_sessions.append({
                            "id": f"{project_dir.name}/{md_file.stem}",
                            "path": str(md_file),
                            "type": "project",
                            "modified": mtime.isoformat(),
                            "size": md_file.stat().st_size
                        })

        return new_sessions

    # ========== 摄入 ==========
    def ingest_sessions(self, session_ids: list[str]) -> int:
        """摄入指定会话，提取知识点存入图谱。

        Returns: 新增节点数
        """
        added = 0

        for sid in session_ids:
            # 尝试 JSON 格式 (sessions/)
            json_path = self.wb_home / "sessions" / f"{sid}.json"
            if json_path.exists():
                count = self._ingest_json_session(json_path, sid)
                added += count
                continue

            # 尝试 Markdown 格式 (projects/)
            if "/" in sid:
                parts = sid.split("/", 1)
                md_path = self.wb_home / "projects" / parts[0] / f"{parts[1]}.md"
                if md_path.exists():
                    count = self._ingest_md_session(md_path, sid)
                    added += count

        # 更新状态
        self.state["last_session_sync"] = datetime.now().isoformat()
        self.state["synced_sessions"] = list(set(
            self.state.get("synced_sessions", []) + session_ids
        ))
        self.state["total_nodes_synced"] += added
        self._save_state()

        return added

    def _ingest_json_session(self, path: Path, session_id: str) -> int:
        """摄入 WorkBuddy JSON 会话文件

        支持两种格式:
        1. 完整会话 (含 messages) → 提取对话内容
        2. 元数据会话 (仅含 pid/sessionId/cwd) → 创建轻量时间线节点
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return 0

        messages = session_data.get("messages", [])
        if messages:
            # 格式1: 完整会话 → 提取对话
            user_texts = []
            for msg in messages:
                if msg.get("role") != "user":
                    continue
                content = msg.get("content", "")
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            user_texts.append(part.get("text", ""))
                elif isinstance(content, str):
                    user_texts.append(content)

            full_text = "\n".join(user_texts)
            if len(full_text) >= 50:
                segments = [s.strip() for s in full_text.split("\n\n") if len(s.strip()) >= 50]
                added = 0
                for seg in segments:
                    title = seg[:80].strip().replace("\n", " ")
                    self.digester.digest(seg, title, f"workbuddy-session:{session_id}")
                    added += 1
                return added
            return 0

        # 格式2: 元数据会话 → 创建时间线节点
        cwd = session_data.get("cwd", "")
        kind = session_data.get("kind", "")
        started_raw = session_data.get("startedAt")
        started = ""
        if started_raw:
            try:
                if isinstance(started_raw, (int, float)):
                    from datetime import datetime as dt2
                    started = dt2.fromtimestamp(started_raw / 1000).isoformat()[:19]
                else:
                    started = str(started_raw)[:19]
            except:
                started = str(started_raw)[:19]
        url = session_data.get("url", "")

        text_parts = [f"WorkBuddy会话记录 (ID: {session_id})"]
        if cwd:
            text_parts.append(f"工作目录: {cwd}")
        if kind:
            text_parts.append(f"会话类型: {kind}")
        if started:
            text_parts.append(f"开始时间: {started}")
        if url:
            text_parts.append(f"端点: {url}")

        # 从 cwd 推断项目名称
        import re
        project = "unknown"
        if cwd:
            parts = cwd.replace("\\", "/").split("/")
            # 取最后一个有意义的部分
            for p in reversed(parts):
                if p and not p.startswith(":") and len(p) > 1:
                    project = p
                    break

        title = f"会话: {project} ({started[:10] if started else '?'})"
        self.digester.digest("\n".join(text_parts), title, f"workbuddy-session:{session_id}")
        return 1

    def _ingest_md_session(self, path: Path, session_id: str) -> int:
        """摄入 Markdown 格式会话"""
        try:
            text = path.read_text(encoding="utf-8")
        except IOError:
            return 0

        if len(text.strip()) < 50:
            return 0

        self.digester.digest(text, f"会话: {session_id}", f"workbuddy-project:{session_id}")
        return 1

    # ========== 记忆同步 ==========
    def sync_memory_files(self) -> int:
        """同步 WorkBuddy 长期记忆文件。

        同步来源:
        1. ~/.workbuddy/MEMORY.md (跨项目记忆)
        2. ~/.workbuddy/memory/*.md (长期记忆文件)
        3. {workspace}/.workbuddy/memory/*.md (项目记忆)

        Returns: 新增节点数
        """
        added = 0

        # 1. 跨项目记忆
        memory_md = self.wb_home / "MEMORY.md"
        added += self._ingest_file(memory_md, "WorkBuddy 跨项目记忆", "workbuddy-memory")

        # 2. 长期记忆文件
        memory_dir = self.wb_home / "memory"
        if memory_dir.exists():
            for md_file in sorted(memory_dir.glob("*.md")):
                added += self._ingest_file(
                    md_file,
                    f"记忆: {md_file.stem}",
                    f"workbuddy-memory:{md_file.name}"
                )

        # 3. 项目记忆 (当前 workspace)
        project_memory = self.data_dir.parent / ".workbuddy" / "memory"
        if project_memory.exists():
            for md_file in sorted(project_memory.glob("*.md")):
                added += self._ingest_file(
                    md_file,
                    f"项目记忆: {md_file.stem}",
                    f"project-memory:{md_file.name}"
                )

        self.state["last_memory_sync"] = datetime.now().isoformat()
        self.state["total_nodes_synced"] += added
        self._save_state()

        return added

    def _ingest_file(self, path: Path, title: str, source: str) -> int:
        """摄入单个文件到知识图谱"""
        if not path.exists():
            return 0
        try:
            text = path.read_text(encoding="utf-8")
        except IOError:
            return 0

        if len(text.strip()) < 50:
            return 0

        self.digester.digest(text, title, source)
        return 1

    # ========== 数据源信息 ==========
    def get_sources(self) -> dict:
        """获取已同步的数据源分布"""
        self.graph.reload()
        sources = {}
        for node in self.graph.data.get("nodes", {}).values():
            src = node.get("source", "unknown")
            if src.startswith("workbuddy-") or src.startswith("project-"):
                sources[src] = sources.get(src, 0) + 1

        return {
            "sources": sources,
            "synced_sessions": self.state.get("synced_sessions", []),
            "total_synced": self.state.get("total_nodes_synced", 0),
            "last_session_sync": self.state.get("last_session_sync", ""),
            "last_memory_sync": self.state.get("last_memory_sync", "")
        }
