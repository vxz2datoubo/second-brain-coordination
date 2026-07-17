"""SQLite storage and JSONL audit logging for v0.1."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterable

from .contracts import (
    AgentTrace,
    BacktestConfig,
    BacktestResult,
    BulletinStateRecord,
    DecisionRecord,
    EpisodicMemory,
    EvidenceItem,
    FeatureSet,
    FeedbackRecord,
    ForecastRecord,
    IndicatorDefinition,
    KnowledgeAtom,
    LearningEntry,
    MarketDataRecord,
    ModuleStatusRecord,
    OrderBookSnapshot,
    PriceBar,
    ReasoningTrace,
    RelationEdge,
    RiskCheckResult,
    ReviewRecord,
    RiskApproval,
    SignalRecord,
    SkillRegistryEntry,
    StrategyDefinition,
    StrategyReview,
    SelfEvolutionLog,
    SourceRecord,
    TheoryDefinition,
    TradeDecision,
    TradeJournal,
    TradePrint,
    ValidationReport,
    WritebackSnapshot,
    from_dict,
    now_iso,
    to_dict,
)


RECORD_TABLES: dict[str, type] = {
    "sources": SourceRecord,
    "evidence": EvidenceItem,
    "atoms": KnowledgeAtom,
    "relations": RelationEdge,
    "episodes": EpisodicMemory,
    "decisions": DecisionRecord,
    "forecasts": ForecastRecord,
    "reviews": ReviewRecord,
    "feedback_records": FeedbackRecord,
    "reasoning_traces": ReasoningTrace,
    "learning_entries": LearningEntry,
    "writeback_snapshots": WritebackSnapshot,
    "evolution_logs": SelfEvolutionLog,
    "agent_traces": AgentTrace,
    "risk_approvals": RiskApproval,
    "market_data_records": MarketDataRecord,
    "price_bars": PriceBar,
    "order_book_snapshots": OrderBookSnapshot,
    "trade_prints": TradePrint,
    "feature_sets": FeatureSet,
    "indicator_definitions": IndicatorDefinition,
    "theory_definitions": TheoryDefinition,
    "strategy_definitions": StrategyDefinition,
    "backtest_configs": BacktestConfig,
    "backtest_results": BacktestResult,
    "validation_reports": ValidationReport,
    "signal_records": SignalRecord,
    "trade_decisions": TradeDecision,
    "trade_journals": TradeJournal,
    "risk_check_results": RiskCheckResult,
    "strategy_reviews": StrategyReview,
    "skill_registry_entries": SkillRegistryEntry,
    "module_status_records": ModuleStatusRecord,
    "bulletin_state_records": BulletinStateRecord,
}


class AuditLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, payload: dict[str, Any]) -> None:
        row = {
            "timestamp": now_iso(),
            "event_type": event_type,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


class BrainStore:
    def __init__(
        self,
        root: Path,
        db_path: Path | None = None,
        audit_path: Path | None = None,
        sqlite_timeout_seconds: float = 15.0,
        sqlite_busy_timeout_ms: int = 15000,
        sqlite_lock_retry_attempts: int = 3,
        sqlite_lock_retry_backoff_seconds: float = 0.2,
    ):
        self.root = Path(root)
        self.data_dir = self.root / "data"
        self.db_path = db_path or self.data_dir / "super_brain_v01.sqlite"
        self.audit = AuditLog(audit_path or self.data_dir / "audit" / "events.jsonl")
        self.sqlite_timeout_seconds = float(sqlite_timeout_seconds)
        self.sqlite_busy_timeout_ms = int(sqlite_busy_timeout_ms)
        self.sqlite_lock_retry_attempts = max(1, int(sqlite_lock_retry_attempts))
        self.sqlite_lock_retry_backoff_seconds = max(0.0, float(sqlite_lock_retry_backoff_seconds))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=self.sqlite_timeout_seconds)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={self.sqlite_busy_timeout_ms}")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _run_with_lock_retry(self, operation):
        last_error: sqlite3.OperationalError | None = None
        for attempt in range(self.sqlite_lock_retry_attempts):
            try:
                return operation()
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                last_error = exc
                if attempt + 1 >= self.sqlite_lock_retry_attempts:
                    raise
                time.sleep(self.sqlite_lock_retry_backoff_seconds * (attempt + 1))
        if last_error is not None:
            raise last_error

    def _init_db(self) -> None:
        def _init() -> None:
            with self.connect() as conn:
                for table in RECORD_TABLES:
                    conn.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table} (
                            id TEXT PRIMARY KEY,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            data TEXT NOT NULL
                        )
                        """
                    )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                    ("schema_version", "v0.1"),
                )

        self._run_with_lock_retry(_init)

    def save(self, table: str, record: Any, audit: bool = True) -> dict[str, Any]:
        if table not in RECORD_TABLES:
            raise ValueError(f"Unknown table: {table}")
        data = to_dict(record)
        record_id = data.get("id")
        if not record_id:
            raise ValueError("record.id is required")
        created_at = data.get("created_at") or data.get("captured_at") or data.get("extracted_at") or data.get("reviewed_at") or now_iso()
        updated_at = data.get("updated_at") or data.get("created_at") or now_iso()
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        def _save() -> None:
            with self.connect() as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO {table}(id, created_at, updated_at, data) VALUES (?, ?, ?, ?)",
                    (record_id, created_at, updated_at, payload),
                )

        self._run_with_lock_retry(_save)
        if audit:
            self.audit.append(f"{table}.save", {"id": record_id, "table": table})
        return data

    def save_many(self, table: str, records: Iterable[Any]) -> list[dict[str, Any]]:
        return [self.save(table, r) for r in records]

    def get(self, table: str, record_id: str) -> dict[str, Any] | None:
        def _get():
            with self.connect() as conn:
                return conn.execute(f"SELECT data FROM {table} WHERE id = ?", (record_id,)).fetchone()

        row = self._run_with_lock_retry(_get)
        if not row:
            return None
        return json.loads(row["data"])

    def update_data(self, table: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if "id" not in data:
            data["id"] = record_id
        data["updated_at"] = now_iso()
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        def _update() -> None:
            with self.connect() as conn:
                conn.execute(
                    f"UPDATE {table} SET updated_at = ?, data = ? WHERE id = ?",
                    (data["updated_at"], payload, record_id),
                )

        self._run_with_lock_retry(_update)
        self.audit.append(f"{table}.update", {"id": record_id, "table": table})
        return data

    def list_records(self, table: str, limit: int = 100, newest: bool = True) -> list[dict[str, Any]]:
        order = "DESC" if newest else "ASC"
        def _list():
            with self.connect() as conn:
                return conn.execute(
                    f"SELECT data FROM {table} ORDER BY created_at {order} LIMIT ?",
                    (int(limit),),
                ).fetchall()

        rows = self._run_with_lock_retry(_list)
        return [json.loads(r["data"]) for r in rows]

    def count(self, table: str) -> int:
        def _count():
            with self.connect() as conn:
                return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()

        row = self._run_with_lock_retry(_count)
        return int(row["n"])

    def counts(self) -> dict[str, int]:
        return {table: self.count(table) for table in RECORD_TABLES}

    def all_atoms(self) -> list[KnowledgeAtom]:
        return [from_dict(KnowledgeAtom, d) for d in self.list_records("atoms", limit=100000)]

    def all_evidence(self) -> list[EvidenceItem]:
        return [from_dict(EvidenceItem, d) for d in self.list_records("evidence", limit=100000)]

    def legacy_status(self) -> dict[str, Any]:
        graph_path = self.data_dir / "knowledge-graph.json"
        if not graph_path.exists():
            return {"knowledge_graph": "not_found"}
        try:
            with graph_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "knowledge_graph": "read_only",
                "nodes": len(data.get("nodes", {})),
                "edges": len(data.get("edges", {})),
            }
        except Exception as exc:
            return {"knowledge_graph": "unreadable", "error": str(exc)}

    def get_meta(self, key: str, default: Any = None) -> Any:
        def _get_meta():
            with self.connect() as conn:
                return conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()

        row = self._run_with_lock_retry(_get_meta)
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return row["value"]

    def set_meta(self, key: str, value: Any) -> None:
        payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
        def _set_meta() -> None:
            with self.connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                    (key, payload),
                )

        self._run_with_lock_retry(_set_meta)
