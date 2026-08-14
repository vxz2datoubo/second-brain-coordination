from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml

AGENT_FILES = {
    "CODEX": "coordination/ACTIVE-CODEX-TASK.yaml",
    "QCLAW": "coordination/ACTIVE-QCLAW-TASK.yaml",
    "WORKBUDDY": "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
}
PROGRAM_REGISTRY = "coordination/ACTIVE-PROGRAM-LANES.yaml"
PROJECTION = "coordination/PROGRAM-CONTROL-TOWER.md"
PROJECTION_START = "<!-- CONTROL_TOWER_AUTOGEN:START -->"
PROJECTION_END = "<!-- CONTROL_TOWER_AUTOGEN:END -->"

NON_EXECUTABLE_STATUSES = {
    "PAUSED",
    "BLOCKED",
    "REVIEW",
    "DONE",
    "CANCELLED",
    "GPT_REVIEW_CHANGES_REQUIRED_PAUSED",
    "PAUSED_COMPUTE_UNAVAILABLE",
}


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: str
    code: str
    message: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class RouteSnapshot:
    agent: str
    task_id: str | None
    route_epoch: int | str | None
    issue: int | str | None
    pr: int | str | None
    branch: str | None
    status: str | None
    execution_allowed: bool
    completion_signal: str | None
    fingerprint: str


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping YAML at {path}")
    return data


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def normalize_route(agent: str, route: dict[str, Any]) -> RouteSnapshot:
    normalized = {
        "agent": agent,
        "task_id": _first(route, "task_id", "active_task_id"),
        "route_epoch": _first(route, "route_epoch", "epoch"),
        "issue": _first(route, "active_issue", "issue"),
        "pr": _first(route, "implementation_pr", "active_pull_request", "pull_request", "pr"),
        "branch": _first(route, "implementation_branch", "planned_branch", "frozen_branch", "branch"),
        "status": _first(route, "status"),
        "execution_allowed": bool(route.get("execution_allowed", False)),
        "completion_signal": _first(route, "completion_signal"),
    }
    fingerprint = hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return RouteSnapshot(fingerprint=fingerprint, **normalized)


def route_is_executable(route: RouteSnapshot) -> bool:
    if not route.execution_allowed:
        return False
    if route.status is None:
        return False
    return str(route.status).upper() not in NON_EXECUTABLE_STATUSES


def route_witness(route: RouteSnapshot) -> dict[str, Any]:
    return asdict(route)


def verify_route_witness(expected: dict[str, Any], current: RouteSnapshot) -> bool:
    return expected.get("fingerprint") == current.fingerprint


def _norm_path(value: str) -> str:
    value = value.replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    return str(PurePosixPath(value))


def _path_overlap(left: str, right: str) -> bool:
    a = _norm_path(left)
    b = _norm_path(right)
    if a == b:
        return True
    if a in {".", ""} or b in {".", ""}:
        return True
    a_prefix = a.rstrip("/") + "/"
    b_prefix = b.rstrip("/") + "/"
    return a.startswith(b_prefix) or b.startswith(a_prefix)


def _any_path_overlap(left: Iterable[str], right: Iterable[str]) -> bool:
    return any(_path_overlap(a, b) for a in left for b in right)


def _interface_map(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in item.get("interfaces", []) or []:
        if isinstance(raw, str):
            result[raw] = {"name": raw, "mode": "read", "frozen": True}
            continue
        if isinstance(raw, dict) and raw.get("name"):
            result[str(raw["name"])] = {
                "name": str(raw["name"]),
                "mode": str(raw.get("mode", "read")).lower(),
                "frozen": bool(raw.get("frozen", False)),
            }
    return result


def classify_collision(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_auth = set(left.get("authority_claims", []) or [])
    right_auth = set(right.get("authority_claims", []) or [])
    authority_overlap = sorted(left_auth & right_auth)
    if authority_overlap:
        return {"level": "O4", "reason": "AUTHORITY_COLLISION", "overlap": authority_overlap}

    left_writes = list(left.get("write_paths", []) or [])
    right_writes = list(right.get("write_paths", []) or [])
    left_reads = list(left.get("read_paths", []) or [])
    right_reads = list(right.get("read_paths", []) or [])

    if (
        _any_path_overlap(left_writes, right_writes)
        or _any_path_overlap(left_writes, right_reads)
        or _any_path_overlap(right_writes, left_reads)
    ):
        return {"level": "O3", "reason": "MUTABLE_PATH_SURFACE", "overlap": []}

    left_interfaces = _interface_map(left)
    right_interfaces = _interface_map(right)
    shared_interfaces = sorted(set(left_interfaces) & set(right_interfaces))
    if shared_interfaces:
        mutable = []
        for name in shared_interfaces:
            a = left_interfaces[name]
            b = right_interfaces[name]
            if "write" in {a["mode"], b["mode"]} and not (a["frozen"] and b["frozen"]):
                mutable.append(name)
        if mutable:
            return {"level": "O3", "reason": "MUTABLE_INTERFACE", "overlap": mutable}
        if any(
            "write" in {left_interfaces[name]["mode"], right_interfaces[name]["mode"]}
            for name in shared_interfaces
        ):
            return {"level": "O2", "reason": "FROZEN_SHARED_CONTRACT", "overlap": shared_interfaces}

    left_read_domains = set(left.get("read_domains", []) or [])
    right_read_domains = set(right.get("read_domains", []) or [])
    left_write_domains = set(left.get("write_domains", []) or [])
    right_write_domains = set(right.get("write_domains", []) or [])

    shared_contract_domains = sorted(
        (left_write_domains & (right_read_domains | right_write_domains))
        | (right_write_domains & (left_read_domains | left_write_domains))
    )
    if shared_contract_domains:
        return {"level": "O2", "reason": "SHARED_DOMAIN_CONTRACT", "overlap": shared_contract_domains}

    read_read = sorted(left_read_domains & right_read_domains)
    if read_read or _any_path_overlap(left_reads, right_reads):
        return {"level": "O1", "reason": "READ_READ", "overlap": read_read}

    return {"level": "O0", "reason": "NO_MATERIAL_OVERLAP", "overlap": []}


def _route_expected_fields(agent_state: dict[str, Any]) -> dict[str, Any]:
    source_keys = {
        "task_id": "observed_task_id",
        "route_epoch": "observed_route_epoch",
        "issue": "observed_issue",
        "pr": "observed_pr",
        "status": "observed_status",
        "execution_allowed": "execution_allowed",
    }
    return {target: agent_state[source] for target, source in source_keys.items() if source in agent_state}


def _route_actual_fields(route: RouteSnapshot) -> dict[str, Any]:
    return {
        "task_id": route.task_id,
        "route_epoch": route.route_epoch,
        "issue": route.issue,
        "pr": route.pr,
        "status": route.status,
        "execution_allowed": route.execution_allowed,
    }


def _lane_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for lane in registry.get("program_lanes", []) or []:
        if isinstance(lane, dict) and lane.get("lane_id"):
            result[str(lane["lane_id"])] = lane
    return result


def _known_stale_view_findings(
    repo_root: Path, registry: dict[str, Any], routes: dict[str, RouteSnapshot]
) -> list[Finding]:
    findings: list[Finding] = []
    for entry in registry.get("known_stale_aggregate_views", []) or []:
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        path = repo_root / str(entry["path"])
        if not path.exists():
            findings.append(
                Finding(
                    "CT-R01-STALE-VIEW",
                    "ERROR",
                    "DECLARED_STALE_VIEW_MISSING",
                    "A configured stale aggregate view path does not exist.",
                    {"path": str(entry["path"])},
                )
            )
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        missing_current = []
        for agent, route in routes.items():
            if agent in text.upper() and route.task_id and route.task_id not in text:
                missing_current.append(agent)
        if missing_current:
            findings.append(
                Finding(
                    "CT-R01-STALE-VIEW",
                    "WARN",
                    "STALE_VIEW_DETECTED",
                    "A declared historical aggregate view disagrees with current per-agent task identity.",
                    {
                        "path": str(entry["path"]),
                        "agents": missing_current,
                        "disposition": entry.get("disposition"),
                    },
                )
            )
    return findings


def scan_repository(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    registry = load_yaml(repo_root / PROGRAM_REGISTRY)
    routes: dict[str, RouteSnapshot] = {}
    findings: list[Finding] = []

    for agent, relpath in AGENT_FILES.items():
        route = normalize_route(agent, load_yaml(repo_root / relpath))
        routes[agent] = route

    observed = registry.get("observed_agent_state", {}) or {}
    for agent, route in routes.items():
        expected_raw = observed.get(agent)
        if not isinstance(expected_raw, dict):
            findings.append(
                Finding(
                    "CT-R01-STALE-VIEW",
                    "ERROR",
                    "MISSING_AGENT_PROJECTION",
                    "Program registry lacks an observed snapshot for an active agent source.",
                    {"agent": agent},
                )
            )
            continue
        expected = _route_expected_fields(expected_raw)
        actual = _route_actual_fields(route)
        drift = {
            key: {"expected": expected[key], "actual": actual[key]}
            for key in expected
            if expected[key] != actual[key]
        }
        if drift:
            findings.append(
                Finding(
                    "CT-R01-STALE-VIEW",
                    "ERROR",
                    "PROGRAM_REGISTRY_ROUTE_DRIFT",
                    "Program registry observed state is stale relative to the per-agent ACTIVE route.",
                    {"agent": agent, "drift": drift},
                )
            )

    findings.extend(_known_stale_view_findings(repo_root, registry, routes))

    lanes = _lane_by_id(registry)
    release_policy = registry.get("current_user_release_policy", {}) or {}
    held_lanes = list(release_policy.get("held_lanes", []) or [])
    for lane_id in held_lanes:
        lane = lanes.get(str(lane_id))
        if lane is None:
            findings.append(
                Finding(
                    "CT-R05-DEPENDENCY",
                    "ERROR",
                    "HELD_LANE_MISSING",
                    "A user-held lane is not present in the registry.",
                    {"lane_id": lane_id},
                )
            )
            continue
        if str(lane.get("desired_state", "")).upper() != "PAUSED":
            findings.append(
                Finding(
                    "CT-R05-DEPENDENCY",
                    "ERROR",
                    "USER_HOLD_NOT_ENFORCED",
                    "A held lane is not PAUSED.",
                    {"lane_id": lane_id, "desired_state": lane.get("desired_state")},
                )
            )
        if lane.get("active_execution_route") not in (None, {}, ""):
            findings.append(
                Finding(
                    "CT-R07-AGENT-LEASE",
                    "ERROR",
                    "HELD_LANE_HAS_EXECUTION_ROUTE",
                    "A held lane still claims an active execution route.",
                    {"lane_id": lane_id},
                )
            )
        if bool(lane.get("heavy_execution_authorized", False)):
            findings.append(
                Finding(
                    "CT-R08-RESOURCE",
                    "ERROR",
                    "HELD_LANE_HEAVY_AUTHORIZED",
                    "A held lane still has heavy execution authorization.",
                    {"lane_id": lane_id},
                )
            )

    capacity = registry.get("portfolio_capacity_policy", {}) or {}
    heavy_limit = int(capacity.get("local_heavy_stage_concurrency_max", 1))
    heavy_active = [
        lane_id
        for lane_id, lane in lanes.items()
        if bool(lane.get("heavy_execution_authorized", False))
        and str(lane.get("desired_state", "")).upper() in {"ACTIVE", "READY"}
    ]
    if len(heavy_active) > heavy_limit:
        findings.append(
            Finding(
                "CT-R08-RESOURCE",
                "ERROR",
                "HEAVY_WIP_EXCEEDED",
                "More heavy program lanes are authorized than the local heavy-stage limit.",
                {"active": heavy_active, "limit": heavy_limit},
            )
        )

    agent_lane_counts: dict[str, list[str]] = {}
    for lane_id, lane in lanes.items():
        route = lane.get("active_execution_route")
        if route in (None, {}, ""):
            continue
        owner = str(lane.get("implementation_owner") or lane.get("implementation_owner_candidate") or "UNKNOWN")
        agent_lane_counts.setdefault(owner, []).append(lane_id)
    agent_limits = {
        "CODEX": int(capacity.get("codex_active_execution_routes_max", 1)),
        "QCLAW": int(capacity.get("qclaw_active_execution_routes_max", 1)),
        "WORKBUDDY": int(capacity.get("workbuddy_active_execution_routes_max", 1)),
    }
    for agent, lane_ids in agent_lane_counts.items():
        limit = agent_limits.get(agent)
        if limit is not None and len(lane_ids) > limit:
            findings.append(
                Finding(
                    "CT-R07-AGENT-LEASE",
                    "ERROR",
                    "SAME_AGENT_DOUBLE_BOOKED",
                    "One execution agent is assigned to more active lanes than allowed.",
                    {"agent": agent, "lanes": lane_ids, "limit": limit},
                )
            )

    overlap_matrix = registry.get("cross_lane_overlap_matrix", []) or []
    for relation in overlap_matrix:
        if not isinstance(relation, dict):
            continue
        level = str(relation.get("overlap_level", ""))
        if not level.startswith(("O0", "O1", "O2", "O3", "O4")):
            findings.append(
                Finding(
                    "CT-R04-INTERFACE",
                    "ERROR",
                    "UNKNOWN_OVERLAP_LEVEL",
                    "Cross-lane overlap uses an unknown classification.",
                    {"pair": relation.get("pair"), "level": level},
                )
            )

    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    warnings = [asdict(item) for item in findings if item.severity == "WARN"]
    release_decision = "HOLD_BY_USER" if held_lanes else ("NOT_READY" if errors else "ELIGIBLE_FOR_GPT_DRY_RUN")

    return {
        "schema_version": "1.0",
        "registry_id": registry.get("registry_id"),
        "registry_as_of": registry.get("as_of"),
        "routes": {agent: route_witness(route) for agent, route in routes.items()},
        "errors": errors,
        "warnings": warnings,
        "release_decision": release_decision,
        "user_held_lanes": held_lanes,
        "foundation_structural_check": "PASS" if not errors else "FAIL",
    }


def render_projection_block(repo_root: Path) -> str:
    registry = load_yaml(repo_root / PROGRAM_REGISTRY)
    scan = scan_repository(repo_root)
    routes = scan["routes"]
    lines = [
        PROJECTION_START,
        "## 自动同步快照（机器生成区）",
        "",
        f"- Registry: `{registry.get('registry_id')}`",
        f"- as_of: `{registry.get('as_of')}`",
        f"- Foundation structural check: **{scan['foundation_structural_check']}**",
        f"- Lane release decision: **{scan['release_decision']}**",
        f"- User-held lanes: `{', '.join(scan['user_held_lanes']) if scan['user_held_lanes'] else 'NONE'}`",
        "",
        "### Agent routes",
        "",
        "| Agent | task_id | epoch | status | execution_allowed | Issue / PR |",
        "|---|---|---:|---|---|---|",
    ]
    for agent in ("CODEX", "QCLAW", "WORKBUDDY"):
        route = routes[agent]
        lines.append(
            f"| {agent} | `{route.get('task_id')}` | {route.get('route_epoch')} | `{route.get('status')}` | "
            f"`{str(route.get('execution_allowed')).lower()}` | #{route.get('issue')} / #{route.get('pr')} |"
        )
    lines.extend(
        [
            "",
            "### Program lanes",
            "",
            "| Lane | desired | observed | heavy | next gate |",
            "|---|---|---|---|---|",
        ]
    )
    for lane in registry.get("program_lanes", []) or []:
        lines.append(
            f"| `{lane.get('lane_id')}` | `{lane.get('desired_state')}` | `{lane.get('observed_state')}` | "
            f"`{str(bool(lane.get('heavy_execution_authorized', False))).lower()}` | {lane.get('next_gate')} |"
        )
    lines.extend(["", PROJECTION_END])
    return "\n".join(lines)


def projection_matches(repo_root: Path) -> bool:
    projection_path = repo_root / PROJECTION
    if not projection_path.exists():
        return False
    text = projection_path.read_text(encoding="utf-8")
    if PROJECTION_START not in text or PROJECTION_END not in text:
        return False
    start = text.index(PROJECTION_START)
    end = text.index(PROJECTION_END, start) + len(PROJECTION_END)
    current = text[start:end]
    expected = render_projection_block(repo_root)
    return current == expected


def replace_projection_block(text: str, block: str) -> str:
    if PROJECTION_START in text and PROJECTION_END in text:
        start = text.index(PROJECTION_START)
        end = text.index(PROJECTION_END, start) + len(PROJECTION_END)
        return text[:start] + block + text[end:]
    if text.startswith("#"):
        first_newline = text.find("\n")
        if first_newline != -1:
            return text[: first_newline + 1] + "\n" + block + "\n" + text[first_newline + 1 :]
    return block + "\n\n" + text
