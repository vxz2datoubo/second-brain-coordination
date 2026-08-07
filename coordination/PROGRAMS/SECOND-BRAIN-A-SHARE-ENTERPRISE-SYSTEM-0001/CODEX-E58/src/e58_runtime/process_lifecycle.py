"""Bounded task-owned subprocess lifecycle management for E58.

The registry never discovers and kills arbitrary Python processes. It owns only
children it starts, records a command digest instead of command text, places
Windows children in a Job Object configured for kill-on-close, and cleans every
registered child on normal or exceptional context-manager exit.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import threading
import time
from typing import Sequence


class ProcessLifecycleError(RuntimeError):
    """A task-owned process cannot be created, verified, or cleaned safely."""


class ResourceBudgetViolation(ProcessLifecycleError):
    """A requested worker would exceed E58's local resource budget."""


@dataclass(frozen=True, slots=True)
class ResourceBudget:
    max_task_python_processes: int = 6
    max_cpu_bound_workers: int = 3
    p0_canary_workers: int = 2

    def __post_init__(self) -> None:
        if not 1 <= self.max_task_python_processes <= 6:
            raise ValueError("max_task_python_processes must be within E58's hard cap")
        if not 1 <= self.max_cpu_bound_workers <= 3:
            raise ValueError("max_cpu_bound_workers must be within E58's hard cap")
        if not 1 <= self.p0_canary_workers <= 2:
            raise ValueError("p0_canary_workers must be one or two")


@dataclass(frozen=True, slots=True)
class OwnedProcess:
    pid: int
    created_monotonic: float
    command_digest: str
    purpose: str
    expected_exit: int | None


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    event: str
    pid: int
    purpose: str
    monotonic_time: float
    exit_code: int | None


_THREAD_LIMIT_ENV = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "TOKENIZERS_PARALLELISM": "false",
    "LOKY_MAX_CPU_COUNT": "2",
}


class _JobObjectBasicLimit(ctypes.Structure):
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


class _JobObjectIoCounters(ctypes.Structure):
    _fields_ = [(field, ctypes.c_ulonglong) for field in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _JobObjectExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobObjectBasicLimit),
        ("IoInfo", _JobObjectIoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _WindowsJobObject:
    """Minimal Job Object wrapper that kills only assigned children on close."""

    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    def __init__(self) -> None:
        self._handle: int | None = None
        self.mode = "process_group_fallback"
        self.fallback_reason: str | None = "non_windows"
        if os.name != "nt":
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32 = kernel32
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            self._raise("CreateJobObjectW")
        limit = _JobObjectExtendedLimit()
        limit.BasicLimitInformation.LimitFlags = self._JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(handle, self._JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(limit), ctypes.sizeof(limit)):
            kernel32.CloseHandle(handle)
            self._raise("SetInformationJobObject")
        self._handle = int(handle)
        self.mode = "job_object"
        self.fallback_reason = None

    def _raise(self, operation: str) -> None:
        raise ProcessLifecycleError(f"Windows Job Object operation failed: {operation} ({ctypes.get_last_error()})")

    def assign(self, pid: int) -> None:
        if self._handle is None:
            return
        process_access = 0x0001 | 0x0400 | 0x00100000
        process = self._kernel32.OpenProcess(process_access, False, pid)
        if not process:
            self._raise("OpenProcess")
        try:
            if not self._kernel32.AssignProcessToJobObject(self._handle, process):
                error = ctypes.get_last_error()
                if error == 5:
                    # Desktop hosts can already be constrained by an outer Job.
                    # The child was created in its own process group and remains
                    # controlled by this registry's Popen handle.
                    self._kernel32.CloseHandle(self._handle)
                    self._handle = None
                    self.mode = "process_group_fallback"
                    self.fallback_reason = "assign_access_denied_outer_job"
                    return
                self._raise("AssignProcessToJobObject")
        finally:
            self._kernel32.CloseHandle(process)

    def close(self) -> None:
        if self._handle is not None:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None


class HeavyStageMutex:
    """Cross-agent named mutex for one local heavy E58 stage at a time."""

    _process_lock = threading.Lock()

    def __init__(self, name: str = "Local\\SECOND_BRAIN_LOCAL_HEAVY_TEST_LOCK") -> None:
        self._acquired = False
        self._handle: int | None = None
        self._fallback = threading.Lock()
        if os.name == "nt":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel32.WaitForSingleObject.restype = wintypes.DWORD
            kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
            kernel32.ReleaseMutex.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            self._kernel32 = kernel32
            handle = kernel32.CreateMutexW(None, False, name)
            if not handle:
                raise ProcessLifecycleError(f"CreateMutexW failed ({ctypes.get_last_error()})")
            self._handle = int(handle)

    def acquire(self, timeout_seconds: float = 0.0) -> None:
        if self._acquired:
            raise ProcessLifecycleError("heavy-stage mutex cannot be re-entered")
        if not self._process_lock.acquire(timeout=timeout_seconds):
            raise ResourceBudgetViolation("heavy-stage mutex is held")
        if self._handle is None:
            if not self._fallback.acquire(timeout=timeout_seconds):
                self._process_lock.release()
                raise ResourceBudgetViolation("heavy-stage mutex is held")
        else:
            result = self._kernel32.WaitForSingleObject(self._handle, max(0, int(timeout_seconds * 1000)))
            if result not in (0, 0x80):
                self._process_lock.release()
                raise ResourceBudgetViolation("heavy-stage mutex is held")
        self._acquired = True

    def release(self) -> None:
        if not self._acquired:
            return
        if self._handle is None:
            self._fallback.release()
        else:
            self._kernel32.ReleaseMutex(self._handle)
        self._acquired = False
        self._process_lock.release()

    def close(self) -> None:
        self.release()
        if self._handle is not None:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> "HeavyStageMutex":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class OwnedProcessRegistry:
    """Own, cap, record, and clean only subprocesses started by this registry."""

    def __init__(self, task_id: str, agent_id: str = "CODEX", budget: ResourceBudget | None = None) -> None:
        self.task_id = task_id
        self.agent_id = agent_id
        self.budget = budget or ResourceBudget()
        self._job = _WindowsJobObject()
        self._owned: dict[int, tuple[subprocess.Popen[bytes], OwnedProcess]] = {}
        self._events: list[LifecycleEvent] = []
        self._peak = 0
        self._closed = False

    @property
    def active_count(self) -> int:
        return len(self._owned)

    @property
    def peak_owned_processes(self) -> int:
        return self._peak

    @property
    def events(self) -> tuple[LifecycleEvent, ...]:
        return tuple(self._events)

    @property
    def active_processes(self) -> tuple[OwnedProcess, ...]:
        return tuple(owned for _, owned in self._owned.values())

    @property
    def containment_mode(self) -> str:
        return self._job.mode

    @property
    def containment_fallback_reason(self) -> str | None:
        return self._job.fallback_reason

    def _record(self, event: str, owned: OwnedProcess, exit_code: int | None = None) -> None:
        self._events.append(LifecycleEvent(event, owned.pid, owned.purpose, time.monotonic(), exit_code))

    @staticmethod
    def _command_digest(command: Sequence[str]) -> str:
        return sha256(json.dumps(list(command), ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def spawn(self, command: Sequence[str], *, purpose: str, expected_exit: int | None = 0) -> int:
        if self._closed:
            raise ProcessLifecycleError("registry is closed")
        if not command or not purpose:
            raise ValueError("command and purpose are required")
        if self.active_count >= self.budget.max_task_python_processes:
            raise ResourceBudgetViolation("task-owned Python process cap would be exceeded")
        environment = dict(os.environ)
        environment.update(_THREAD_LIMIT_ENV)
        kwargs: dict[str, object] = {"env": environment, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00004000
        else:
            kwargs["start_new_session"] = True
        process = subprocess.Popen(list(command), **kwargs)
        owned = OwnedProcess(process.pid, time.monotonic(), self._command_digest(command), purpose, expected_exit)
        try:
            self._job.assign(process.pid)
        except Exception:
            process.kill()
            process.wait(timeout=5)
            raise
        self._owned[process.pid] = (process, owned)
        self._peak = max(self._peak, self.active_count)
        self._record("spawn", owned)
        return process.pid

    def wait(self, pid: int, timeout_seconds: float | None = None) -> int:
        process, owned = self._owned[pid]
        exit_code = process.wait(timeout=timeout_seconds)
        self._owned.pop(pid)
        self._record("exit", owned, exit_code)
        if owned.expected_exit is not None and exit_code != owned.expected_exit:
            raise ProcessLifecycleError(f"owned process {pid} exited {exit_code}, expected {owned.expected_exit}")
        return exit_code

    def cleanup(self, reason: str) -> int:
        cleaned = 0
        for pid, (process, owned) in tuple(self._owned.items()):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            exit_code = process.returncode
            self._owned.pop(pid, None)
            self._record(f"cleanup:{reason}", owned, exit_code)
            cleaned += 1
        self._job.close()
        return cleaned

    def close(self) -> int:
        if self._closed:
            return 0
        self._closed = True
        return self.cleanup("context_exit")

    def __enter__(self) -> "OwnedProcessRegistry":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
