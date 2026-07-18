"""
CODEX-GITHUB-DISPATCHER-0001 — State Manager
SQLite idempotency DB + ETag cursor + single-instance file lock.
"""
import os
import sqlite3
import threading
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "SecondBrain" / "CodexDispatcher"
DB_PATH = STATE_DIR / "dispatcher_state.sqlite"
LOCK_PATH = STATE_DIR / "dispatcher.lock"
LOG_DIR = STATE_DIR / "logs"


def ensure_dirs():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def init_db():
    ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idempotency (
            key TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            status TEXT NOT NULL,
            comment_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cursor_state (
            id INTEGER PRIMARY KEY CHECK (id=1),
            last_comment_id INTEGER NOT NULL DEFAULT 0,
            last_etag TEXT,
            last_checked_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("INSERT OR IGNORE INTO cursor_state (id, last_comment_id) VALUES (1, 0)")
    conn.commit()
    return conn


def is_idempotency_key_used(conn: sqlite3.Connection, key: str) -> bool:
    row = conn.execute("SELECT 1 FROM idempotency WHERE key=?", (key,)).fetchone()
    return row is not None


def mark_idempotency_key(conn: sqlite3.Connection, key: str, task_id: str, status: str, comment_id: int):
    conn.execute(
        "INSERT OR REPLACE INTO idempotency (key, task_id, status, comment_id) VALUES (?,?,?,?)",
        (key, task_id, status, comment_id),
    )
    conn.commit()


def get_cursor(conn: sqlite3.Connection) -> tuple[int, str | None]:
    row = conn.execute("SELECT last_comment_id, last_etag FROM cursor_state WHERE id=1").fetchone()
    return (row[0], row[1]) if row else (0, None)


def update_cursor(conn: sqlite3.Connection, comment_id: int, etag: str | None = None):
    conn.execute(
        "UPDATE cursor_state SET last_comment_id=?, last_etag=?, last_checked_at=datetime('now') WHERE id=1",
        (comment_id, etag),
    )
    conn.commit()


class SingleInstanceLock:
    def __init__(self):
        self._fd = None

    def acquire(self) -> bool:
        import msvcrt
        try:
            self._fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_RDWR)
            msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
            return True
        except (OSError, IOError):
            if self._fd:
                os.close(self._fd)
                self._fd = None
            return False

    def release(self):
        if self._fd:
            try:
                import msvcrt
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            os.close(self._fd)
            self._fd = None
