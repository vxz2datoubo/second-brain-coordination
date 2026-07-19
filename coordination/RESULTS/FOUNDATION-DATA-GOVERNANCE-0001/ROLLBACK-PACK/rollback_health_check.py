from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROW_IDS = {
    "sources": "src_1e9ff3b54a7289",
    "evidence": "ev_1e9ff3b54a7289",
    "atoms": "atom_1e9ff3b54a7289",
    "skill_registry_entries": "skill_1bdd0c7030a5b9",
    "module_status_records": "mod_1bdd0c7030a5b9",
    "evolution_logs": "evo_1ee9927b18704b",
    "bulletin_state_records": "bstate_0f066f14d29c4e",
}

MARKERS = {
    "service_import": "FoundationDataGovernanceV01",
    "cli_command": "foundation-data-governance-report",
    "board_event": "foundation_data_governance_v2_registered",
}


def contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def db_presence(path: Path) -> dict[str, int]:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    rows: dict[str, int] = {}
    for table, key in ROW_IDS.items():
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE id=?", (key,))
        rows[table] = cur.fetchone()[0]
    conn.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="F:/aidanao")
    parser.add_argument("--mode", choices=["pre", "post"], default="pre")
    args = parser.parse_args()

    root = Path(args.root)
    pre = args.mode == "pre"

    print("service_import:", contains(root / "brain_core/service.py", MARKERS["service_import"]))
    print("cli_command:", contains(root / "apps/cli/brainctl.py", MARKERS["cli_command"]))
    print("board_event:", contains(root / "bulletin/super-second-brain-v01-board.md", MARKERS["board_event"]))
    print("db_rows:", db_presence(root / "data/super_brain_v01.sqlite"))

    if pre:
        print("expectation: markers and DB rows should exist before rollback")
    else:
        print("expectation: markers and DB rows should be absent after rollback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
