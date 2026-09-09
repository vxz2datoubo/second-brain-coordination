"""B4 — Windows Job Object hard process-tree containment + orphan reaper.

Provides *hard* containment via the Windows Job Object API (KILL_ON_JOB_CLOSE +
TerminateJobObject), an ownership registry, and a soft orphan reaper as
defense-in-depth.

The hard boundary ``NO_SILENT_DOWNGRADE_FROM_JOB_OBJECT_HARD_CONTAINMENT_TO_BARE_
PROCESS_EXECUTION`` is enforced: if Job Objects are unavailable, the provider
reports ``BLOCKED``/``PARTIAL`` with exact evidence instead of degrading to bare
process execution and calling it "hard containment".
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Optional


class ContainmentError(RuntimeError):
    """Raised when hard containment cannot be established or applied."""


# ---------------------------------------------------------------------------
# Windows API bindings (ctypes)
# ---------------------------------------------------------------------------
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001
_PROCESS_QUERY_INFORMATION = 0x0400
_SYNCHRONIZE = 0x00100000


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _kernel32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k.SetInformationJobObject.restype = wintypes.BOOL
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.AssignProcessToJobObject.restype = wintypes.BOOL
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k.TerminateJobObject.restype = wintypes.BOOL
    k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.CloseHandle.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.TerminateProcess.restype = wintypes.BOOL
    k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    return k


_k32 = None


def _get_k32():
    global _k32
    if _k32 is None:
        _k32 = _kernel32()
    return _k32


# ---------------------------------------------------------------------------
# Containment primitives
# ---------------------------------------------------------------------------
class WindowsJobObject:
    """A hard process-tree containment boundary backed by a Windows Job Object."""

    def __init__(self, name: Optional[str] = None, kill_on_close: bool = True):
        if sys.platform != "win32":
            raise ContainmentError("Job Object containment requires Windows")
        self._handle = _get_k32().CreateJobObjectW(None, name)
        if not self._handle:
            raise ContainmentError("CreateJobObjectW failed")
        if kill_on_close:
            info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            ok = _get_k32().SetInformationJobObject(
                self._handle,
                _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
            if not ok:
                self.close()
                raise ContainmentError("SetInformationJobObject(KILL_ON_JOB_CLOSE) failed")

    def assign(self, pid: int) -> None:
        hproc = _get_k32().OpenProcess(
            _PROCESS_SET_QUOTA | _PROCESS_TERMINATE | _PROCESS_QUERY_INFORMATION,
            False,
            pid,
        )
        if not hproc:
            raise ContainmentError(f"OpenProcess failed for pid {pid}")
        try:
            ok = _get_k32().AssignProcessToJobObject(self._handle, hproc)
            if not ok:
                raise ContainmentError(f"AssignProcessToJobObject failed for pid {pid}")
        finally:
            _get_k32().CloseHandle(hproc)

    def terminate(self, exit_code: int = 1) -> bool:
        if not self._handle:
            return False
        return bool(_get_k32().TerminateJobObject(self._handle, exit_code))

    def close(self) -> None:
        if self._handle:
            _get_k32().CloseHandle(self._handle)
            self._handle = None


@dataclass
class OwnershipRegistry:
    """Tracks which PIDs are owned by a mission (for the soft orphan reaper)."""

    owner: str
    pids: set[int] = field(default_factory=set)

    def register(self, pid: int) -> None:
        self.pids.add(pid)

    def unregister(self, pid: int) -> None:
        self.pids.discard(pid)

    def snapshot(self) -> set[int]:
        return set(self.pids)


def is_process_alive(pid: int) -> bool:
    """Best-effort liveness check for a PID on Windows."""
    if sys.platform != "win32":
        return False
    hproc = _get_k32().OpenProcess(_SYNCHRONIZE | _PROCESS_QUERY_INFORMATION, False, pid)
    if not hproc:
        return False
    try:
        return bool(_get_k32().WaitForSingleObject(hproc, 0) == 0x00000102)  # WAIT_TIMEOUT
    finally:
        _get_k32().CloseHandle(hproc)


class SoftOrphanReaper:
    """Defense-in-depth reaper: only touches PIDs *owned* by the mission."""

    def __init__(self, registry: OwnershipRegistry):
        self._registry = registry

    def reap_owned(self) -> list[int]:
        """Terminate owned PIDs that are still alive. Returns the reaped PIDs.

        Never kills unrelated processes by name — only PIDs explicitly owned.
        """
        reaped = []
        for pid in self._registry.snapshot():
            if is_process_alive(pid):
                _get_k32().TerminateProcess(
                    _get_k32().OpenProcess(_PROCESS_TERMINATE, False, pid), 1
                )
                reaped.append(pid)
            self._registry.unregister(pid)
        return reaped


# ---------------------------------------------------------------------------
# Capability probe + no-silent-downgrade provider
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ContainmentReport:
    mode: str  # "HARD_JOB_OBJECT" | "PARTIAL" | "BLOCKED"
    supported: bool
    evidence: str


def probe_support() -> ContainmentReport:
    """Probe whether hard Job Object containment is available on this machine."""
    if sys.platform != "win32":
        return ContainmentReport(
            mode="BLOCKED",
            supported=False,
            evidence="non-Windows platform: Job Object hard containment unavailable",
        )
    try:
        job = WindowsJobObject(kill_on_close=True)
        job.close()
        return ContainmentReport(
            mode="HARD_JOB_OBJECT",
            supported=True,
            evidence="Job Object created + KILL_ON_JOB_CLOSE applied successfully",
        )
    except ContainmentError as e:
        return ContainmentReport(
            mode="PARTIAL",
            supported=False,
            evidence=f"Job Object probe failed: {e}",
        )


def build_provider() -> tuple[WindowsJobObject, ContainmentReport]:
    """Return (job, report). On failure the job is None and report is non-hard.

    This is the *only* supported path; there is no bare-process fallback that
    would silently violate the hard-containment invariant.
    """
    report = probe_support()
    if not report.supported:
        return None, report
    try:
        return WindowsJobObject(kill_on_close=True), report
    except ContainmentError as e:
        return None, ContainmentReport(mode="PARTIAL", supported=False, evidence=str(e))
