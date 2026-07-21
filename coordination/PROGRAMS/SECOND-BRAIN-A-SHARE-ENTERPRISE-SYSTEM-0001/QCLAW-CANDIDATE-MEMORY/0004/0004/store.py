"""Candidate Memory Library — SQLite Storage Engine

Work Package A: implements atoms, relations, conflicts, unknowns, sources,
packets, revisions, audit, skills, credential_refs, and FTS retrieval_terms.

4-axis independence: knowledge_status / gpt_access / transport_visibility / authority_level
"""

import sqlite3
import json
import os
import hashlib
import datetime
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

SCHEMA_VERSION = "0.2"


# ── Create Tables ─────────────────────────────────────────────────────

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS atoms (
    id TEXT PRIMARY KEY,
    atom_type TEXT NOT NULL,
    canonical_statement TEXT NOT NULL,
    scope TEXT,
    confidence REAL,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    memory_type TEXT DEFAULT 'SEMANTIC',
    privacy_class TEXT DEFAULT 'INTERNAL',
    evidence_quality TEXT,
    premises TEXT DEFAULT '[]',
    exceptions TEXT DEFAULT '[]',
    failure_conditions TEXT DEFAULT '[]',
    source_reference TEXT,
    original_excerpt TEXT,
    processor_version TEXT,
    base_knowledge_revision TEXT,
    knowledge_status TEXT DEFAULT 'NEW',
    gpt_access TEXT DEFAULT 'FULL_SEMANTIC_ACCESS',
    transport_visibility TEXT DEFAULT 'LOCAL',
    authority_level TEXT DEFAULT 'CANDIDATE_ONLY',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    relation_type TEXT NOT NULL,
    from_atom_id TEXT NOT NULL,
    to_atom_id TEXT NOT NULL,
    confidence REAL,
    context TEXT,
    privacy_class TEXT DEFAULT 'INTERNAL',
    knowledge_status TEXT DEFAULT 'NEW',
    created_at TEXT NOT NULL,
    FOREIGN KEY (from_atom_id) REFERENCES atoms(id),
    FOREIGN KEY (to_atom_id) REFERENCES atoms(id)
);

CREATE TABLE IF NOT EXISTS conflicts (
    id TEXT PRIMARY KEY,
    atom_id_a TEXT NOT NULL,
    atom_id_b TEXT NOT NULL,
    conflict_type TEXT DEFAULT 'DIRECT',
    resolution_status TEXT DEFAULT 'UNRESOLVED',
    resolution_note TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY (atom_id_a) REFERENCES atoms(id),
    FOREIGN KEY (atom_id_b) REFERENCES atoms(id)
);

CREATE TABLE IF NOT EXISTS unknowns (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    scope TEXT,
    raised_by_sources TEXT DEFAULT '[]',
    related_atom_ids TEXT DEFAULT '[]',
    status TEXT DEFAULT 'OPEN',
    resolution_note TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    source_type TEXT DEFAULT 'SYNTHETIC',
    title TEXT,
    description TEXT,
    location TEXT,
    content_hash TEXT,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS packets (
    id TEXT PRIMARY KEY,
    instance_id TEXT UNIQUE,
    content_hash TEXT,
    source_id TEXT,
    processor_version TEXT,
    authority_level TEXT DEFAULT 'CANDIDATE_ONLY',
    packet_status TEXT DEFAULT 'VALID',
    ingested_at TEXT NOT NULL,
    json_blob TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS packet_atoms (
    packet_id TEXT NOT NULL,
    atom_id TEXT NOT NULL,
    PRIMARY KEY (packet_id, atom_id),
    FOREIGN KEY (packet_id) REFERENCES packets(id),
    FOREIGN KEY (atom_id) REFERENCES atoms(id)
);

CREATE TABLE IF NOT EXISTS packet_relations (
    packet_id TEXT NOT NULL,
    relation_id TEXT NOT NULL,
    PRIMARY KEY (packet_id, relation_id),
    FOREIGN KEY (packet_id) REFERENCES packets(id),
    FOREIGN KEY (relation_id) REFERENCES relations(id)
);

CREATE TABLE IF NOT EXISTS revisions (
    revision_id TEXT PRIMARY KEY,
    parent_revision_id TEXT,
    packet_set_hash TEXT,
    created_at TEXT NOT NULL,
    snapshot_manifest TEXT DEFAULT '{}',
    FOREIGN KEY (parent_revision_id) REFERENCES revisions(revision_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    revision_id TEXT,
    packet_id TEXT,
    atom_id TEXT,
    detail TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_structures (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'SKILL',
    content TEXT,
    related_atom_ids TEXT DEFAULT '[]',
    packet_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credential_refs (
    id TEXT PRIMARY KEY,
    purpose TEXT NOT NULL,
    system TEXT NOT NULL,
    local_location TEXT NOT NULL,
    checksum TEXT,
    rotation_rule TEXT,
    last_rotated TEXT,
    valid_until TEXT,
    related_atom_ids TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS retrieval_fts USING fts5(
    term, atom_id, weight
);

CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms(atom_type);
CREATE INDEX IF NOT EXISTS idx_atoms_scope ON atoms(scope);
CREATE INDEX IF NOT EXISTS idx_atoms_confidence ON atoms(confidence);
CREATE INDEX IF NOT EXISTS idx_atoms_privacy ON atoms(privacy_class);
CREATE INDEX IF NOT EXISTS idx_atoms_verification ON atoms(verification_status);
CREATE INDEX IF NOT EXISTS idx_atoms_created ON atoms(created_at);
CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_atom_id);
CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_atom_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(resolution_status);
CREATE INDEX IF NOT EXISTS idx_unknowns_status ON unknowns(status);
CREATE INDEX IF NOT EXISTS idx_packets_ingested ON packets(ingested_at);
CREATE INDEX IF NOT EXISTS idx_packet_atoms_atom ON packet_atoms(atom_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);
"""


# ── Store Class ────────────────────────────────────────────────────────

class MemoryStore:
    """SQLite-backed candidate memory library."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._rev_counter: int = 0

    # ── Lifecycle ──

    def connect(self):
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(CREATE_TABLES)
        self._conn.commit()
        return self

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self):
        """Context manager for atomic operations."""
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Store not connected. Call .connect() first.")
        return self._conn

    def now(self) -> str:
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Atoms ──────────────────────────────────────────────────────

    def insert_atom(self, atom: Dict[str, Any]) -> str:
        """Insert a new atom. Returns atom id."""
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO atoms
                (id, atom_type, canonical_statement, scope, confidence,
                 verification_status, memory_type, privacy_class, evidence_quality,
                 premises, exceptions, failure_conditions, source_reference,
                 original_excerpt, processor_version, base_knowledge_revision,
                 knowledge_status, gpt_access, transport_visibility, authority_level,
                 created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                atom["id"], atom["atom_type"], atom["canonical_statement"],
                atom.get("scope"), atom.get("confidence"),
                atom.get("verification_status", "UNVERIFIED"),
                atom.get("memory_type", "SEMANTIC"),
                atom.get("privacy_class", "INTERNAL"),
                atom.get("evidence_quality"),
                json.dumps(atom.get("premises", [])),
                json.dumps(atom.get("exceptions", [])),
                json.dumps(atom.get("failure_conditions", [])),
                atom.get("source_reference"),
                atom.get("original_excerpt"),
                atom.get("processor_version"),
                atom.get("base_knowledge_revision"),
                atom.get("knowledge_status", "NEW"),
                atom.get("gpt_access", "FULL_SEMANTIC_ACCESS"),
                atom.get("transport_visibility", "LOCAL"),
                atom.get("authority_level", "CANDIDATE_ONLY"),
                now, now,
            ))
        return atom["id"]

    def get_atom(self, atom_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM atoms WHERE id=?", (atom_id,)).fetchone()
        if not row:
            return None
        return self._atom_row_to_dict(row)

    def atom_exists(self, atom_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM atoms WHERE id=?", (atom_id,)).fetchone()
        return row is not None

    def get_atoms_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"SELECT * FROM atoms WHERE id IN ({placeholders})", ids
        ).fetchall()
        return [self._atom_row_to_dict(r) for r in rows]

    def update_atom(self, atom_id: str, updates: Dict[str, Any]) -> bool:
        """Update atom fields. Returns True if row was updated."""
        if not updates:
            return False
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values())
        values.append(atom_id)
        values.append(self.now())
        self.conn.execute(
            f"UPDATE atoms SET {set_clause}, updated_at=? WHERE id=?",
            values
        )
        c = self.conn.cursor()
        c.execute("SELECT changes()")
        return c.fetchone()[0] > 0

    def _atom_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for field in ("premises", "exceptions", "failure_conditions"):
            d[field] = json.loads(d[field]) if d.get(field) else []
        return d

    # ── Relations ──────────────────────────────────────────────────

    def insert_relation(self, rel: Dict[str, Any]) -> str:
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO relations
                (id, relation_type, from_atom_id, to_atom_id, confidence,
                 context, privacy_class, knowledge_status, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                rel["id"], rel["relation_type"], rel["from_atom_id"],
                rel["to_atom_id"], rel.get("confidence"),
                rel.get("context"), rel.get("privacy_class", "INTERNAL"),
                rel.get("knowledge_status", "NEW"), now,
            ))
        return rel["id"]

    def get_relation(self, rel_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM relations WHERE id=?", (rel_id,)).fetchone()
        return dict(row) if row else None

    def get_relations_from(self, atom_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM relations WHERE from_atom_id=?", (atom_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_relations_to(self, atom_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM relations WHERE to_atom_id=?", (atom_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_relations_around(self, atom_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM relations WHERE from_atom_id=? OR to_atom_id=?",
            (atom_id, atom_id)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Conflicts ──────────────────────────────────────────────────────

    def insert_conflict(self, conflict: Dict[str, Any]) -> str:
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO conflicts
                (id, atom_id_a, atom_id_b, conflict_type, resolution_status,
                 resolution_note, created_at, resolved_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                conflict["id"], conflict["atom_id_a"], conflict["atom_id_b"],
                conflict.get("conflict_type", "DIRECT"),
                conflict.get("resolution_status", "UNRESOLVED"),
                conflict.get("resolution_note"),
                now, conflict.get("resolved_at"),
            ))
        return conflict["id"]

    def get_unresolved_conflicts(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM conflicts WHERE resolution_status='UNRESOLVED'"
        ).fetchall()
        return [dict(r) for r in rows]

    def resolve_conflict(self, conflict_id: str, resolution: str, note: str = ""):
        now = self.now()
        self.conn.execute(
            "UPDATE conflicts SET resolution_status=?, resolution_note=?, resolved_at=? WHERE id=?",
            (resolution, note, now, conflict_id)
        )
        self.conn.commit()

    # ── Unknowns ───────────────────────────────────────────────────────

    def insert_unknown(self, unknown: Dict[str, Any]) -> str:
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO unknowns
                (id, question, scope, raised_by_sources, related_atom_ids,
                 status, resolution_note, created_at, resolved_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                unknown["id"], unknown["question"], unknown.get("scope"),
                json.dumps(unknown.get("raised_by_sources", [])),
                json.dumps(unknown.get("related_atom_ids", [])),
                unknown.get("status", "OPEN"),
                unknown.get("resolution_note"),
                now, unknown.get("resolved_at"),
            ))
        return unknown["id"]

    def get_open_unknowns(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM unknowns WHERE status='OPEN'"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Sources ────────────────────────────────────────────────────────

    def insert_source(self, src: Dict[str, Any]) -> str:
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO sources
                (id, source_type, title, description, location, content_hash, ingested_at)
                VALUES (?,?,?,?,?,?,?)
            """, (
                src["id"], src.get("source_type", "SYNTHETIC"),
                src.get("title"), src.get("description"),
                src.get("location"), src.get("content_hash"), now,
            ))
        return src["id"]

    # ── Packets ────────────────────────────────────────────────────────

    def insert_packet(self, packet: Dict[str, Any]) -> str:
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO packets
                (id, instance_id, content_hash, source_id, processor_version,
                 authority_level, packet_status, ingested_at, json_blob)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                packet["id"], packet["instance_id"], packet["content_hash"],
                packet.get("source_id"), packet.get("processor_version"),
                packet.get("authority_level", "CANDIDATE_ONLY"),
                packet.get("packet_status", "VALID"), now,
                json.dumps(packet),
            ))
            # Junction tables
            for aid in packet.get("atom_ids", []):
                c.execute(
                    "INSERT OR IGNORE INTO packet_atoms (packet_id, atom_id) VALUES (?,?)",
                    (packet["id"], aid)
                )
            for rid in packet.get("relation_ids", []):
                c.execute(
                    "INSERT OR IGNORE INTO packet_relations (packet_id, relation_id) VALUES (?,?)",
                    (packet["id"], rid)
                )
        return packet["id"]

    def get_packet(self, packet_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM packets WHERE id=?", (packet_id,)).fetchone()
        return dict(row) if row else None

    def get_all_packet_ids(self) -> List[str]:
        rows = self.conn.execute("SELECT id FROM packets ORDER BY ingested_at").fetchall()
        return [r["id"] for r in rows]

    # ── Revisions ──────────────────────────────────────────────────────

    def create_revision(self, parent_revision_id: Optional[str] = None) -> str:
        now = self.now()
        all_pids = sorted(self.get_all_packet_ids())
        pset_hash = hashlib.sha256(json.dumps(all_pids, sort_keys=True).encode()).hexdigest()

        revision_id = hashlib.sha256(f"{pset_hash}|{now}|{self._rev_counter}".encode()).hexdigest()
        self._rev_counter += 1
        with self.transaction() as c:
            c.execute("""
                INSERT INTO revisions (revision_id, parent_revision_id, packet_set_hash, created_at)
                VALUES (?,?,?,?)
            """, (revision_id, parent_revision_id, pset_hash, now))
        return revision_id

    def get_latest_revision(self) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM revisions ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_revision(self, rev_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM revisions WHERE revision_id=?", (rev_id,)
        ).fetchone()
        return dict(row) if row else None

    # ── Audit ──────────────────────────────────────────────────────────

    def audit(self, event_type: str, detail: str = "",
              revision_id: str = "", packet_id: str = "", atom_id: str = ""):
        now = self.now()
        self.conn.execute(
            "INSERT INTO audit_events (event_type, revision_id, packet_id, atom_id, detail, timestamp) "
            "VALUES (?,?,?,?,?,?)",
            (event_type, revision_id, packet_id, atom_id, detail, now)
        )
        self.conn.commit()

    def get_audit_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Skills / Structures ────────────────────────────────────────────

    def insert_skill(self, skill: Dict[str, Any]) -> str:
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO skill_structures
                (id, name, type, content, related_atom_ids, packet_id, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (
                skill["id"], skill["name"], skill.get("type", "SKILL"),
                skill.get("content"),
                json.dumps(skill.get("related_atom_ids", [])),
                skill.get("packet_id"), now,
            ))
        return skill["id"]

    # ── Credential Refs ────────────────────────────────────────────────

    def insert_credential_ref(self, ref: Dict[str, Any]) -> str:
        now = self.now()
        with self.transaction() as c:
            c.execute("""
                INSERT OR IGNORE INTO credential_refs
                (id, purpose, system, local_location, checksum, rotation_rule,
                 last_rotated, valid_until, related_atom_ids, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                ref["id"], ref["purpose"], ref["system"], ref["local_location"],
                ref.get("checksum"), ref.get("rotation_rule"),
                ref.get("last_rotated"), ref.get("valid_until"),
                json.dumps(ref.get("related_atom_ids", [])), now,
            ))
        return ref["id"]

    # ── FTS Retrieval ──────────────────────────────────────────────────

    def index_atom_terms(self, atom_id: str, terms: List[Tuple[str, float]]):
        """Index terms for an atom. terms = [(term_str, weight), ...]"""
        with self.transaction() as c:
            c.execute("DELETE FROM retrieval_fts WHERE atom_id=?", (atom_id,))
            for term, weight in terms:
                c.execute(
                    "INSERT INTO retrieval_fts (term, atom_id, weight) VALUES (?,?,?)",
                    (term.lower(), atom_id, weight)
                )

    def search_fts(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Full-text search. Returns atoms matching the query."""
        # FTS5 query — use MATCH
        try:
            rows = self.conn.execute(
                "SELECT DISTINCT a.* FROM retrieval_fts f "
                "JOIN atoms a ON a.id = f.atom_id "
                "WHERE retrieval_fts MATCH ? "
                "ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
            return [self._atom_row_to_dict(r) for r in rows]
        except sqlite3.OperationalError:
            # FTS5 parse error — try LIKE fallback
            rows = self.conn.execute(
                "SELECT DISTINCT a.* FROM retrieval_fts f "
                "JOIN atoms a ON a.id = f.atom_id "
                "WHERE f.term LIKE ? "
                "ORDER BY f.weight DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [self._atom_row_to_dict(r) for r in rows]

    # ── Stats & Diagnostics ────────────────────────────────────────────

    def stats(self) -> Dict[str, int]:
        tables = ["atoms", "relations", "conflicts", "unknowns", "sources",
                   "packets", "revisions", "audit_events", "skill_structures",
                   "credential_refs"]
        result = {}
        for t in tables:
            row = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()
            result[t] = row["cnt"]
        return result

    def integrity_check(self) -> Dict[str, Any]:
        """Run integrity checks: orphan relations, invalid references."""
        issues = []

        # Orphan relations
        orphan_rels = self.conn.execute("""
            SELECT r.id, r.from_atom_id, r.to_atom_id FROM relations r
            WHERE r.from_atom_id NOT IN (SELECT id FROM atoms)
               OR r.to_atom_id NOT IN (SELECT id FROM atoms)
        """).fetchall()
        for r in orphan_rels:
            issues.append(f"Orphan relation {r['id']}: from={r['from_atom_id']} to={r['to_atom_id']}")

        # Stale conflicts
        orphan_conflicts = self.conn.execute("""
            SELECT c.id FROM conflicts c
            WHERE c.atom_id_a NOT IN (SELECT id FROM atoms)
               OR c.atom_id_b NOT IN (SELECT id FROM atoms)
        """).fetchall()
        for c in orphan_conflicts:
            issues.append(f"Orphan conflict {c['id']}")

        # Duplicate atoms by canonical statement
        dupes = self.conn.execute("""
            SELECT canonical_statement, COUNT(*) as cnt FROM atoms
            GROUP BY canonical_statement HAVING cnt > 1
        """).fetchall()
        for d in dupes:
            issues.append(f"Duplicate statement (count={d['cnt']}): {d['canonical_statement'][:80]}")

        return {
            "integrity_ok": len(issues) == 0,
            "issues": issues,
            "stats": self.stats(),
        }

    # ── Bulk Import ────────────────────────────────────────────────────

    def import_packet_dict(self, pkt: Dict[str, Any]) -> Dict[str, Any]:
        """Import a full packet dict (as from pipeline output). Returns import summary."""
        summary = {"atoms": 0, "relations": 0, "unknowns": 0, "conflicts": 0, "skills": 0, "duplicates": 0}

        # Source first
        if pkt.get("source"):
            src = pkt["source"]
            if isinstance(src, str):
                src = {"id": src, "source_type": "SYNTHETIC"}
            src.setdefault("id", src.get("source_id", hashlib.sha256(str(src).encode()).hexdigest()[:16]))
            self.insert_source(src)

        # Packet
        pkt_id = pkt.get("semantic_id") or pkt.get("packet_id") or pkt.get("id")
        if not pkt_id:
            pkt_id = hashlib.sha256(json.dumps(pkt, sort_keys=True, default=str).encode()).hexdigest()
        pkt.setdefault("id", pkt_id)
        pkt.setdefault("instance_id", pkt.get("instance_id") or hashlib.sha256(f"{pkt_id}|{self.now()}".encode()).hexdigest())
        pkt.setdefault("content_hash", pkt.get("content_hash") or hashlib.sha256(json.dumps(pkt, sort_keys=True, default=str).encode()).hexdigest())

        atom_ids = []
        relation_ids = []

        # Atoms
        for atom in pkt.get("atoms", []):
            aid = atom.get("id")
            if not aid:
                aid = hashlib.sha256(json.dumps(atom, sort_keys=True, default=str).encode()).hexdigest()
                atom["id"] = aid
            if self.atom_exists(aid):
                summary["duplicates"] += 1
            else:
                self.insert_atom(atom)
                summary["atoms"] += 1
            atom_ids.append(aid)

        # Relations
        for rel in pkt.get("relations", []):
            rid = rel.get("id")
            if not rid:
                rid = hashlib.sha256(json.dumps(rel, sort_keys=True, default=str).encode()).hexdigest()
                rel["id"] = rid
            self.insert_relation(rel)
            summary["relations"] += 1
            relation_ids.append(rid)

        # Unknowns
        for unk in pkt.get("unknowns", []):
            uid = unk.get("id")
            if not uid:
                uid = hashlib.sha256(unk["question"].encode()).hexdigest()
                unk["id"] = uid
            self.insert_unknown(unk)
            summary["unknowns"] += 1

        # Conflicts (explicit)
        for con in pkt.get("conflicts", []):
            cid = con.get("id")
            if not cid:
                cid = hashlib.sha256(f"{con.get('atom_id_a','')}|{con.get('atom_id_b','')}".encode()).hexdigest()
                con["id"] = cid
            self.insert_conflict(con)
            summary["conflicts"] += 1

        # Skills / Structures
        for sk in pkt.get("skills", []) + pkt.get("structures", []):
            sid = sk.get("id")
            if not sid:
                sid = hashlib.sha256(json.dumps(sk, sort_keys=True, default=str).encode()).hexdigest()
                sk["id"] = sid
            self.insert_skill(sk)
            summary["skills"] += 1

        # Packet record
        pkt["atom_ids"] = atom_ids
        pkt["relation_ids"] = relation_ids
        self.insert_packet(pkt)

        self.audit("INGEST", f"Imported packet {pkt_id}: {summary['atoms']} new atoms, {summary['duplicates']} duplicates", packet_id=pkt_id)
        return summary
