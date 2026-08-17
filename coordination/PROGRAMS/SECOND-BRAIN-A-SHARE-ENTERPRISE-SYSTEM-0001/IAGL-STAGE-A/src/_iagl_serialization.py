from __future__ import annotations

from _iagl_primitives import *
from _iagl_events import *
from _iagl_models import *

def _slice_to_json(slice_: ImprovementSlice) -> str:
    value = asdict(slice_)
    value["priority"] = int(slice_.priority)
    for name in ("changed_paths", "source_signal_refs", "allowed_tools", "allowed_data_classes", "stop_conditions"):
        value[name] = list(value[name])
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _slice_from_json(raw: str) -> ImprovementSlice:
    value = json.loads(raw)
    value["priority"] = Priority(value["priority"])
    for name in ("changed_paths", "source_signal_refs", "allowed_tools", "allowed_data_classes", "stop_conditions"):
        value[name] = tuple(value[name])
    return ImprovementSlice(**value)


def _slice_digest(slice_: ImprovementSlice) -> str:
    return digest(_slice_to_json(slice_))


def _event_to_json(event: NormalizedEvent) -> str:
    value = asdict(event)
    value["priority_hint"] = int(event.priority_hint)
    value["class_priority_hint"] = int(event.class_priority_hint)
    value["risk_markers"] = list(event.risk_markers)
    return json.dumps(value, sort_keys=True)


def _event_from_json(raw: str) -> NormalizedEvent:
    data = json.loads(raw)
    data["priority_hint"] = Priority(data["priority_hint"])
    data["class_priority_hint"] = Priority(data["class_priority_hint"])
    data["risk_markers"] = tuple(data["risk_markers"])
    return NormalizedEvent(**data)


def _snapshot_to_json(snapshot: ReconciliationSnapshot) -> str:
    value = asdict(snapshot)
    value["governance_mode"] = snapshot.governance_mode.value
    for name in ("allowed_write_paths", "allowed_tools", "allowed_data_classes", "allowed_risk_classes", "allowed_writeback_plans", "active_p2_event_keys", "active_p2_classes"):
        value[name] = list(value[name])
    value["p0_dispositions"] = [asdict(item) for item in snapshot.p0_dispositions]
    value["p2_resolutions"] = [asdict(item) for item in snapshot.p2_resolutions]
    return json.dumps(value, sort_keys=True)


def _snapshot_from_json(raw: str) -> ReconciliationSnapshot:
    data = json.loads(raw)
    data["governance_mode"] = GovernanceMode(data["governance_mode"])
    for name in ("allowed_write_paths", "allowed_tools", "allowed_data_classes", "allowed_risk_classes", "allowed_writeback_plans", "active_p2_event_keys", "active_p2_classes"):
        data[name] = tuple(data[name])
    data["p0_dispositions"] = tuple(P0Disposition(**item) for item in data.get("p0_dispositions", ()))
    data["p2_resolutions"] = tuple(P2Resolution(**item) for item in data.get("p2_resolutions", ()))
    return ReconciliationSnapshot(**data)



__all__ = tuple(name for name in globals() if not name.startswith("__"))
