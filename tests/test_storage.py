from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from brain_core.contracts import SourceRecord
from brain_core.storage import BrainStore


class BrainStoreTests(unittest.TestCase):
    def make_store(self) -> BrainStore:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        return BrainStore(root)

    def test_connect_configures_wal_and_busy_timeout(self):
        store = self.make_store()

        with store.connect() as conn:
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

        self.assertEqual(str(journal_mode).lower(), "wal")
        self.assertGreaterEqual(int(busy_timeout), 15000)

    def test_list_records_retries_locked_connection_once(self):
        store = self.make_store()
        store.save(
            "sources",
            SourceRecord(
                source_type="manual",
                title="alpha",
                uri="memory://source/1",
            ),
        )

        original_connect = store.connect
        attempts = {"count": 0}

        @contextmanager
        def flaky_connect():
            if attempts["count"] == 0:
                attempts["count"] += 1
                raise sqlite3.OperationalError("database is locked")
            with original_connect() as conn:
                yield conn

        store.connect = flaky_connect  # type: ignore[assignment]
        rows = store.list_records("sources", limit=5)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["uri"], "memory://source/1")
        self.assertEqual(attempts["count"], 1)


if __name__ == "__main__":
    unittest.main()
