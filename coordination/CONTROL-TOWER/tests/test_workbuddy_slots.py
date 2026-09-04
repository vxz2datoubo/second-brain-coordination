from __future__ import annotations

"""Compatibility shim for the retained WorkBuddy slot regression corpus.

The predecessor test corpus is kept byte-identical in
``_workbuddy_slots_tests_v1.py``.  This shim upgrades only its synthetic legacy
projection fixture so the retained tests exercise the successor requirement
that the singular compatibility projection bind authority-bearing references.
"""

import _workbuddy_slots_tests_v1 as _v1

_ORIGINAL_LEGACY = _v1._legacy


def _legacy(slot):
    payload = _ORIGINAL_LEGACY(slot)
    payload.update(
        {
            "repository": "vxz2datoubo/second-brain-coordination",
            "target_agent": "WORKBUDDY",
            "canonical_route": slot["canonical_route"],
            "work_claim": slot["work_claim"],
            "task_lease": slot["task_lease"],
            "executor_reservation": slot["executor_reservation"],
            "prewrite_snapshot": slot["prewrite_snapshot"],
            "executable_batch": slot["executable_batch"],
            "authorized_paths": list(slot["write_paths"]),
        }
    )
    return payload


_v1._legacy = _legacy
for _name in dir(_v1):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_v1, _name)
globals()["_legacy"] = _legacy
