from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from workbuddy_slots import WorkBuddySlot, workbuddy_slot_is_executable


@dataclass(frozen=True)
class WorkBuddySlotSelection:
    status: str
    code: str
    requested_worker_slot_id: str | None
    requested_task_id: str | None
    selected_worker_slot_id: str | None
    selected_task_id: str | None
    candidate_worker_slot_ids: tuple[str, ...]
    execution_authority_granted: bool
    runtime_exclusivity_proven: bool
    detail: str


def _result(
    *,
    status: str,
    code: str,
    requested_worker_slot_id: str | None,
    requested_task_id: str | None,
    candidates: Iterable[WorkBuddySlot],
    selected: WorkBuddySlot | None = None,
    detail: str,
) -> WorkBuddySlotSelection:
    candidate_ids = tuple(str(slot.worker_slot_id) for slot in candidates if slot.worker_slot_id)
    return WorkBuddySlotSelection(
        status=status,
        code=code,
        requested_worker_slot_id=requested_worker_slot_id,
        requested_task_id=requested_task_id,
        selected_worker_slot_id=str(selected.worker_slot_id) if selected and selected.worker_slot_id else None,
        selected_task_id=str(selected.task_id) if selected and selected.task_id else None,
        candidate_worker_slot_ids=candidate_ids,
        execution_authority_granted=False,
        runtime_exclusivity_proven=False,
        detail=detail,
    )


def select_workbuddy_slot(
    slots: Iterable[WorkBuddySlot],
    *,
    requested_worker_slot_id: str | None = None,
    requested_task_id: str | None = None,
) -> WorkBuddySlotSelection:
    """Resolve one execution target without minting execution or runtime-lock authority.

    Structural/authorization validation must happen before this selector is used. This
    function only resolves identity among slots that are already executable according
    to the governed slot lifecycle. It deliberately does not infer executor-instance
    ownership from ACTIVE Claim/Lease state.
    """

    executable = [slot for slot in slots if workbuddy_slot_is_executable(slot)]

    if requested_worker_slot_id is not None and not str(requested_worker_slot_id).strip():
        return _result(
            status="BLOCKED",
            code="INVALID_WORKBUDDY_SLOT_SELECTOR",
            requested_worker_slot_id=requested_worker_slot_id,
            requested_task_id=requested_task_id,
            candidates=executable,
            detail="requested_worker_slot_id must be a non-empty exact slot id.",
        )
    if requested_task_id is not None and not str(requested_task_id).strip():
        return _result(
            status="BLOCKED",
            code="INVALID_WORKBUDDY_TASK_SELECTOR",
            requested_worker_slot_id=requested_worker_slot_id,
            requested_task_id=requested_task_id,
            candidates=executable,
            detail="requested_task_id must be a non-empty exact task id.",
        )

    matches = list(executable)
    if requested_worker_slot_id is not None:
        matches = [slot for slot in matches if slot.worker_slot_id == requested_worker_slot_id]
    if requested_task_id is not None:
        matches = [slot for slot in matches if slot.task_id == requested_task_id]

    if requested_worker_slot_id is not None or requested_task_id is not None:
        if len(matches) == 1:
            return _result(
                status="SELECTED",
                code="EXPLICIT_WORKBUDDY_SLOT_SELECTED",
                requested_worker_slot_id=requested_worker_slot_id,
                requested_task_id=requested_task_id,
                candidates=executable,
                selected=matches[0],
                detail="Explicit selector resolved exactly one executable WorkBuddy slot.",
            )
        if not matches:
            return _result(
                status="BLOCKED",
                code="REQUESTED_WORKBUDDY_SLOT_NOT_EXECUTABLE_OR_NOT_FOUND",
                requested_worker_slot_id=requested_worker_slot_id,
                requested_task_id=requested_task_id,
                candidates=executable,
                detail="No executable slot matches the supplied exact selector(s).",
            )
        return _result(
            status="BLOCKED",
            code="AMBIGUOUS_EXPLICIT_WORKBUDDY_SLOT_SELECTION",
            requested_worker_slot_id=requested_worker_slot_id,
            requested_task_id=requested_task_id,
            candidates=matches,
            detail="Explicit selector still resolves multiple executable slots; fail closed.",
        )

    if len(executable) == 1:
        return _result(
            status="SELECTED",
            code="SOLE_EXECUTABLE_WORKBUDDY_SLOT_SELECTED",
            requested_worker_slot_id=None,
            requested_task_id=None,
            candidates=executable,
            selected=executable[0],
            detail="Exactly one executable slot exists, so bare task-read semantics are unambiguous.",
        )
    if not executable:
        return _result(
            status="BLOCKED",
            code="NO_EXECUTABLE_WORKBUDDY_SLOT",
            requested_worker_slot_id=None,
            requested_task_id=None,
            candidates=(),
            detail="No executable WorkBuddy slot exists after governed validation.",
        )
    return _result(
        status="BLOCKED",
        code="AMBIGUOUS_WORKBUDDY_SLOT_SELECTION",
        requested_worker_slot_id=None,
        requested_task_id=None,
        candidates=executable,
        detail="Multiple executable slots exist and no execution-context slot binding was supplied; guessing is forbidden.",
    )


def selection_witness(selection: WorkBuddySlotSelection) -> dict[str, Any]:
    return asdict(selection)
