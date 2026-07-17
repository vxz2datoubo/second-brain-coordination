from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


FOUNDATION_FILE = Path("brain_core/foundation_data_governance.py")
FOUNDATION_DOC = Path("docs/governance/FOUNDATION-DATA-GOVERNANCE-0001.md")
MEMORY_DOC = Path("docs/governance/MEMORY-AUTHORITY-BOUNDARY.md")
FOUNDATION_TEST = Path("tests/test_foundation_data_governance.py")
SERVICE_FILE = Path("brain_core/service.py")
CLI_FILE = Path("apps/cli/brainctl.py")
BOARD_FILE = Path("bulletin/super-second-brain-v01-board.md")
DB_FILE = Path("data/super_brain_v01.sqlite")
AUDIT_FILE = Path("data/audit/events.jsonl")

SERVICE_SNIPPETS = [
    "from .foundation_data_governance import FoundationDataGovernanceV01\n",
    "        self.foundation_data_governance = FoundationDataGovernanceV01(\n            self.store, self.board, self.evolution, self.root, self.trading\n        )\n",
    "\n    def foundation_data_governance_report(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:\n        return self.foundation_data_governance.report(payload or {})\n",
    '                "foundation_data_governance_v2": "Implemented",\n',
]

CLI_SNIPPETS = [
    '    foundation_report = sub.add_parser("foundation-data-governance-report")\n    foundation_report.add_argument("--symbol", default="300418")\n    foundation_report.add_argument("--timeframe", default="1d")\n    foundation_report.add_argument("--data-path", default="")\n    foundation_report.add_argument("--no-writeback", action="store_true")\n',
    '    elif args.command == "foundation-data-governance-report":\n        emit(brain.foundation_data_governance_report({\n            "symbol": args.symbol,\n            "timeframe": args.timeframe,\n            "data_path": args.data_path,\n            "writeback": not args.no_writeback,\n        }))\n',
]

BOARD_LINES_TO_REMOVE = [
    "- Foundation data-governance v2 baseline 已接入母系统（对象模型 / 分层 / 适配器 / 能力协商 / 质量治理）",
    "- [2026-07-15T21:33:56+00:00] foundation_data_governance_v2_registered: Foundation data-governance baseline registered for the mother system: object model bindings, layer boundaries, capability negotiation, quality governance, and A-share adapter isolation are now explicit.",
]

ROW_IDS = {
    "bulletin_state_records": "bstate_0f066f14d29c4e",
    "evolution_logs": "evo_1ee9927b18704b",
    "module_status_records": "mod_1bdd0c7030a5b9",
    "skill_registry_entries": "skill_1bdd0c7030a5b9",
    "atoms": "atom_1e9ff3b54a7289",
    "evidence": "ev_1e9ff3b54a7289",
    "sources": "src_1e9ff3b54a7289",
}

AUDIT_SUFFIX = [
    '"event_type": "sources.save", "payload": {"id": "src_1e9ff3b54a7289"',
    '"event_type": "evidence.save", "payload": {"id": "ev_1e9ff3b54a7289"',
    '"event_type": "atoms.save", "payload": {"id": "atom_1e9ff3b54a7289"',
    '"event_type": "skill_registry_entries.save", "payload": {"id": "skill_1bdd0c7030a5b9"',
    '"event_type": "module_status_records.save", "payload": {"id": "mod_1bdd0c7030a5b9"',
    '"event_type": "evolution_logs.save", "payload": {"id": "evo_1ee9927b18704b"',
    '"event_type": "bulletin_state_records.save", "payload": {"id": "bstate_0f066f14d29c4e"',
]


def strip_snippets(path: Path, snippets: list[str], write: bool) -> list[str]:
    text = path.read_text(encoding="utf-8")
    missing = []
    for snippet in snippets:
        if snippet not in text:
            missing.append(snippet.splitlines()[0][:80])
            continue
        text = text.replace(snippet, "")
    if write and not missing:
        path.write_text(text, encoding="utf-8")
    return missing


def rollback_board(path: Path, write: bool) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    removed = []
    kept = []
    for line in lines:
        if line in BOARD_LINES_TO_REMOVE:
            removed.append(line)
            continue
        kept.append(line)
    if write and removed:
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return removed


def rollback_db(path: Path, write: bool) -> dict[str, int]:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    result: dict[str, int] = {}
    for table, key in ROW_IDS.items():
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE id=?", (key,))
        result[table] = cur.fetchone()[0]
    if write:
        for table, key in ROW_IDS.items():
            cur.execute(f"DELETE FROM {table} WHERE id=?", (key,))
        conn.commit()
    conn.close()
    return result


def rollback_audit(path: Path, write: bool) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    tail = lines[-7:]
    ok = len(tail) == 7 and all(fragment in line for fragment, line in zip(AUDIT_SUFFIX, tail))
    if write and ok:
        kept = lines[:-7]
        path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="F:/aidanao")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    write = bool(args.write)

    print(f"mode={'WRITE' if write else 'DRY_RUN'}")

    print("service_missing:", strip_snippets(root / SERVICE_FILE, SERVICE_SNIPPETS, write))
    print("cli_missing:", strip_snippets(root / CLI_FILE, CLI_SNIPPETS, write))
    print("board_removed:", len(rollback_board(root / BOARD_FILE, write)))
    print("db_rows_found:", rollback_db(root / DB_FILE, write))
    print("audit_tail_matches:", rollback_audit(root / AUDIT_FILE, write))

    for rel in [FOUNDATION_FILE, FOUNDATION_DOC, MEMORY_DOC, FOUNDATION_TEST]:
        path = root / rel
        exists = path.exists()
        print(f"new_file:{rel} exists={exists}")
        if write and exists:
            path.unlink()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
