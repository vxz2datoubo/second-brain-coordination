"""Control Tower reader — reads the canonical ACTIVE-* / LANES state.

IMPORTANT: The Control Tower is the execution authority. This module only
READS its current state (route/claim/lease/lane) and projects a summary.
It never grants authority, never dispatches.

Preferred source: run the existing control_tower.py projection if present,
otherwise parse the canonical YAML directly.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.coordination import (
    build_collisions, read_active_tasks, read_claims, read_lanes,
)
from ..schemas import (
    ControlTowerSummary, Freshness, Meta, SourceRef, TaskState, TrustBadge,
)


def read_summary(coord: Path) -> ControlTowerSummary:
    lanes_doc, _ = read_lanes(coord)
    tasks, _ = read_active_tasks(coord)
    claims, claim_meta = read_claims(coord)
    collisions, collision_meta = build_collisions(coord)
    lanes = lanes_doc.get("program_lanes") or []

    # Build state histogram from real task states (never invented).
    counts: dict[str, int] = {
        "READY": 0, "RUNNING": 0, "REVIEW": 0, "BLOCKED": 0,
        "DONE": 0, "PAUSED": 0, "PLANNED": 0, "OWNER_GATE": 0,
        "OUTCOME_UNKNOWN": 0, "STALLED": 0, "DISPATCHED": 0,
        "CANONICALIZATION": 0,
    }
    for t in tasks:
        key = t.state.value
        if key in counts:
            counts[key] += 1
        else:
            counts.setdefault(key, 0)
            counts[key] += 1

    lane_rows = []
    for lane in lanes:
        lane_rows.append({
            "lane_id": lane.get("lane_id"),
            "desired_state": lane.get("desired_state"),
            "observed_state": lane.get("observed_state"),
            "phase": lane.get("current_phase"),
            "next_gate": lane.get("next_gate"),
            "executor": lane.get("implementation_owner"),
            "route": lane.get("active_execution_route"),
            "trading_authorized": lane.get("trading_authorized"),
        })

    route_rows = [{
        "agent": t.executor, "task_id": t.task_id, "epoch": t.route_epoch,
        "status": t.raw_status, "execution_allowed": t.execution_allowed,
        "issue": t.issue, "pr": t.pr,
    } for t in tasks]

    sources = [
        SourceRef(kind="control_tower",
                  path="coordination/ACTIVE-PROGRAM-LANES.yaml"),
        SourceRef(kind="control_tower",
                  path="coordination/CONTROL-TOWER/"),
    ] + list(claim_meta.sources) + list(collision_meta.sources)
    warnings: list[str] = []
    if not lanes:
        warnings.append("no program lanes readable")
    warnings.extend(claim_meta.warnings)
    warnings.extend(collision_meta.warnings)

    return ControlTowerSummary(
        counts=counts,
        lanes=lane_rows,
        routes=route_rows,
        claims=claims,
        collisions=collisions,
        meta=Meta(
            freshness=Freshness.FRESH if lanes or tasks else Freshness.UNKNOWN,
            authority="CONTROL_TOWER",
            trust=TrustBadge.DERIVED,
            projection_status="COMPLETE" if (lanes or tasks) else "UNAVAILABLE",
            sources=sources,
            warnings=warnings,
        ),
    )


def main_projection_head(coord: Path) -> str | None:
    """Read the autogen snapshot header (as_of) from PROGRAM-CONTROL-TOWER.md."""
    path = coord / "coordination/PROGRAM-CONTROL-TOWER.md"
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re.search(r"as_of:\s*`?([0-9T:\-+\.]+)`?", text)
    return m.group(1) if m else None
