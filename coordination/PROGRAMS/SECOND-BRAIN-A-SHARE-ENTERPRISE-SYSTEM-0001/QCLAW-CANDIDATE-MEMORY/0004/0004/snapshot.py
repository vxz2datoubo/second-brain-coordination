"""Candidate Memory Library — Version Snapshots & Rollback Engine

Work Package C: full-state snapshots, revision chaining, point-in-time restore,
packet-set diffing, and deterministic rollback.

Design rules:
  - Snapshots capture the COMPLETE state (all tables minus audit)
  - Revisions are chained (parent_revision_id)
  - Rollback restores to a previous revision's exact state
  - Diffs between revisions are computable
  - Old state is preserved in the revision chain
  - Every snapshot/rollback produces an audit record
"""

import json
import hashlib
import datetime
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Set
from copy import deepcopy


class SnapshotEngine:
    """Manages revision snapshots and rollback for MemoryStore."""

    def __init__(self, store):
        self.store = store

    def now(self) -> str:
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self, parent_revision_id: Optional[str] = None) -> str:
        """Create a full snapshot of current memory state. Returns revision_id."""
        rev_id = self.store.create_revision(parent_revision_id)

        # Capture full state into the revision's snapshot_manifest
        state = self._capture_state()
        manifest_json = json.dumps(state, sort_keys=True, default=str)

        self.store.conn.execute(
            "UPDATE revisions SET snapshot_manifest=? WHERE revision_id=?",
            (manifest_json, rev_id)
        )
        self.store.conn.commit()

        self.store.audit(
            "SNAPSHOT",
            f"Snapshot {rev_id[:16]}... created. "
            f"atoms={state['counts']['atoms']}, rels={state['counts']['relations']}, "
            f"conflicts={state['counts']['conflicts']}, packets={state['counts']['packets']}",
            revision_id=rev_id,
        )

        return rev_id

    def _capture_state(self) -> Dict[str, Any]:
        """Capture complete current state."""
        tables = ["atoms", "relations", "conflicts", "unknowns", "sources",
                   "packets", "packet_atoms", "packet_relations",
                   "skill_structures", "credential_refs"]

        state: Dict[str, Any] = {"tables": {}, "counts": {}}

        for table in tables:
            try:
                rows = self.store.conn.execute(f"SELECT * FROM {table}").fetchall()
                state["tables"][table] = [dict(r) for r in rows]
                state["counts"][table] = len(rows)
            except sqlite3.OperationalError as e:
                state["tables"][table] = []
                state["counts"][table] = 0

        state["snapshot_at"] = self.now()
        state["snapshot_hash"] = hashlib.sha256(
            json.dumps(state["tables"], sort_keys=True, default=str).encode()
        ).hexdigest()

        return state

    # ── Rollback ─────────────────────────────────────────────────────

    def rollback(self, revision_id: str) -> Dict[str, Any]:
        """Rollback memory state to a specific revision. Returns rollback summary."""
        rev = self.store.get_revision(revision_id)
        if not rev:
            raise ValueError(f"Revision {revision_id} not found")

        manifest = json.loads(rev.get("snapshot_manifest", "{}"))
        if not manifest or "tables" not in manifest:
            raise ValueError(f"Revision {revision_id} has no snapshot manifest")

        # Create current snapshot FIRST (undo point)
        undo_rev = self.snapshot(revision_id)

        # Clear all data tables
        self._clear_all_tables()

        # Restore from manifest — ordered by dependency (parents first)
        TABLE_RESTORE_ORDER = [
            "sources", "atoms", "unknowns",
            "relations", "packets", "conflicts",
            "packet_atoms", "packet_relations",
            "skill_structures", "credential_refs",
        ]
        restored_counts: Dict[str, int] = {}
        for table in TABLE_RESTORE_ORDER:
            rows = manifest["tables"].get(table, [])
            if not rows:
                restored_counts[table] = 0
                continue
            columns = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            col_names = ", ".join(columns)

            for row in rows:
                try:
                    self.store.conn.execute(
                        f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
                        [row[c] for c in columns]
                    )
                except sqlite3.OperationalError:
                    continue

            restored_counts[table] = len(rows)

        self.store.conn.commit()

        summary = {
            "rollback_to": revision_id,
            "rollback_from_undo": undo_rev,
            "restored_counts": restored_counts,
            "snapshot_hash": manifest.get("snapshot_hash", ""),
        }

        self.store.audit(
            "ROLLBACK",
            f"Rolled back to {revision_id[:16]}... "
            f"(undo point: {undo_rev[:16]}...)",
            revision_id=revision_id,
        )

        return summary

    def _clear_all_tables(self):
        """Clear all data tables (preserve revisions + audit)."""
        tables = ["packet_atoms", "packet_relations", "packets",
                   "skill_structures", "credential_refs",
                   "conflicts", "unknowns", "relations", "atoms", "sources",
                   "retrieval_fts"]

        for table in tables:
            try:
                self.store.conn.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                pass

        self.store.conn.commit()

    # ── Diff ──────────────────────────────────────────────────────────

    def diff(self, rev_a: str, rev_b: str) -> Dict[str, Any]:
        """Compute diff between two revisions."""
        ra = self.store.get_revision(rev_a)
        rb = self.store.get_revision(rev_b)
        if not ra or not rb:
            raise ValueError("One or both revisions not found")

        ma = json.loads(ra.get("snapshot_manifest", "{}"))
        mb = json.loads(rb.get("snapshot_manifest", "{}"))

        diff_result = {
            "revision_a": rev_a,
            "revision_b": rev_b,
            "a_time": ra["created_at"],
            "b_time": rb["created_at"],
            "tables": {},
        }

        for table in set(list(ma.get("tables", {}).keys()) + list(mb.get("tables", {}).keys())):
            rows_a = ma.get("tables", {}).get(table, [])
            rows_b = mb.get("tables", {}).get(table, [])

            ids_a = {r.get("id") for r in rows_a}
            ids_b = {r.get("id") for r in rows_b}

            diff_result["tables"][table] = {
                "added": sorted(ids_b - ids_a),
                "removed": sorted(ids_a - ids_b),
                "common": sorted(ids_a & ids_b),
                "count_a": len(ids_a),
                "count_b": len(ids_b),
            }

        return diff_result

    # ── Version Chain ─────────────────────────────────────────────────

    def get_version_chain(self) -> List[Dict[str, Any]]:
        """Get the full revision chain from oldest to newest."""
        rows = self.store.conn.execute(
            "SELECT revision_id, parent_revision_id, created_at FROM revisions ORDER BY created_at"
        ).fetchall()
        return [{
            "revision_id": r["revision_id"],
            "parent_revision_id": r["parent_revision_id"],
            "created_at": r["created_at"],
        } for r in rows]

    def get_revision_ancestors(self, revision_id: str) -> List[str]:
        """Get all ancestor revision_ids (parents chain)."""
        ancestors = []
        current = revision_id
        visited: Set[str] = set()

        while current and current not in visited:
            visited.add(current)
            rev = self.store.get_revision(current)
            if rev and rev.get("parent_revision_id"):
                parent = rev["parent_revision_id"]
                ancestors.append(parent)
                current = parent
            else:
                break

        return ancestors

    # ── Health ────────────────────────────────────────────────────────

    def verify_revision_integrity(self, revision_id: str) -> Dict[str, Any]:
        """Verify a revision's snapshot is internally consistent."""
        rev = self.store.get_revision(revision_id)
        if not rev:
            return {"valid": False, "error": "Revision not found"}

        manifest = json.loads(rev.get("snapshot_manifest", "{}"))
        if not manifest:
            return {"valid": False, "error": "Empty manifest"}

        issues = []

        # Check hash
        snapshot_hash = hashlib.sha256(
            json.dumps(manifest["tables"], sort_keys=True, default=str).encode()
        ).hexdigest()
        if snapshot_hash != manifest.get("snapshot_hash"):
            issues.append("Hash mismatch — manifest may be corrupted")

        # Check relations refer to valid atoms
        atoms_in_snapshot = {r["id"] for r in manifest["tables"].get("atoms", [])}
        for rel in manifest["tables"].get("relations", []):
            if rel["from_atom_id"] not in atoms_in_snapshot:
                issues.append(f"Relation {rel['id']} has missing from_atom: {rel['from_atom_id']}")
            if rel["to_atom_id"] not in atoms_in_snapshot:
                issues.append(f"Relation {rel['id']} has missing to_atom: {rel['to_atom_id']}")

        # Check conflicts refer to valid atoms
        for con in manifest["tables"].get("conflicts", []):
            if con.get("atom_id_a") not in atoms_in_snapshot:
                issues.append(f"Conflict {con['id']} has missing atom_id_a")
            if con.get("atom_id_b") not in atoms_in_snapshot:
                issues.append(f"Conflict {con['id']} has missing atom_id_b")

        return {
            "valid": len(issues) == 0,
            "revision_id": revision_id,
            "snapshot_hash": snapshot_hash,
            "stored_hash": manifest.get("snapshot_hash"),
            "hash_match": snapshot_hash == manifest.get("snapshot_hash"),
            "issues": issues,
        }


# ── Convenience ────────────────────────────────────────────────────────

def create_snapshot(store) -> str:
    """Create a snapshot from current store state."""
    engine = SnapshotEngine(store)
    return engine.snapshot()


def rollback_to_revision(store, revision_id: str) -> Dict[str, Any]:
    """Rollback store to a specific revision."""
    engine = SnapshotEngine(store)
    return engine.rollback(revision_id)


def diff_revisions(store, rev_a: str, rev_b: str) -> Dict[str, Any]:
    """Diff two revisions."""
    engine = SnapshotEngine(store)
    return engine.diff(rev_a, rev_b)
