"""Bounded Windows descendant-process ownership for E59 synthetic tests.

This module deliberately does not kill by executable name. A PID is eligible
for cleanup only after it was observed below an owned root and still matches the
same creation time at the moment of termination. Job Object support is optional:
the audited fallback is a retained descendant identity registry.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Iterator, Sequence


class ProcessLifecycleError(RuntimeError):
    """Ownership, containment, or cleanup evidence is insufficient."""


class ResourceViolation(ProcessLifecycleError):
    """A request would exceed a task or shared resource budget."""


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    pid: int
    ppid: int
    creation_time: str
    executable: str
    command_digest: str
    root_pid: int
    discovered_from: str

    def matches(self, current: "ProcessIdentity") -> bool:
        return self.pid == current.pid and self.creation_time == current.creation_time


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    event: str
    pid: int | None
    detail: str
    monotonic_ns: int


def _digest_command(command: Sequence[str]) -> str:
    encoded = json.dumps(list(command), ensure_ascii=True, separators=(",", ":"), sort_keys=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _windows_snapshot(pids: set[int] | None = None) -> dict[int, ProcessIdentity]:
    """Return a minimum, redaction-safe ToolHelp process snapshot on Windows.

    Non-Windows test environments return an empty snapshot. The command line is
    hashed immediately and is never exposed by this runtime's reports.
    """

    if os.name != "nt":
        return {}
    # Do not enumerate arbitrary process command lines. Apart from being an
    # unreliable JSON boundary on Windows, they can contain unrelated users'
    # secrets. ToolHelp plus GetProcessTimes avoids both the privacy problem
    # and the expensive PowerShell/CIM process-table startup on every event.
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    snapshot_handle = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid = ctypes.c_void_p(-1).value
    if snapshot_handle == invalid:
        raise ProcessLifecycleError("TOOLHELP_SNAPSHOT_FAILED")
    snapshot: dict[int, ProcessIdentity] = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        has_entry = kernel32.Process32FirstW(snapshot_handle, ctypes.byref(entry))
        while has_entry:
            pid = int(entry.th32ProcessID)
            if pids is None or pid in pids:
                creation_time = f"UNAVAILABLE:{pid}"
                # Full scans are used only to learn a parent-child topology.
                # Querying times for every desktop process made discovery slow
                # enough to hide short-lived roots. Identity-sensitive callers
                # pass an explicit PID set and receive creation times below.
                if pids is not None:
                    process_handle = kernel32.OpenProcess(0x1000, False, pid)
                    if process_handle:
                        try:
                            created = wintypes.FILETIME()
                            exited = wintypes.FILETIME()
                            kernel_time = wintypes.FILETIME()
                            user_time = wintypes.FILETIME()
                            if kernel32.GetProcessTimes(process_handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel_time), ctypes.byref(user_time)):
                                creation_time = str((int(created.dwHighDateTime) << 32) | int(created.dwLowDateTime))
                        finally:
                            kernel32.CloseHandle(process_handle)
                snapshot[pid] = ProcessIdentity(
                    pid=pid,
                    ppid=int(entry.th32ParentProcessID),
                    creation_time=creation_time,
                    executable=str(entry.szExeFile or "UNKNOWN"),
                    command_digest=sha256(f"SAFE_SNAPSHOT_NO_COMMAND_LINE:{pid}:{creation_time}".encode("ascii")).hexdigest(),
                    root_pid=pid,
                    discovered_from="TOOLHELP",
                )
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            has_entry = kernel32.Process32NextW(snapshot_handle, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot_handle)
    return snapshot


def resource_snapshot() -> dict[str, object]:
    """Small public-safe preflight snapshot; no command line or absolute path."""

    processes = _windows_snapshot()
    python_count = sum(1 for item in processes.values() if Path(item.executable).name.lower().startswith("python"))
    available_ram_gib: float | None = None
    cpu_percent: float | None = None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        def filetime_value(value: wintypes.FILETIME) -> int:
            return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
        kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
        memory = MEMORYSTATUSEX()
        memory.dwLength = ctypes.sizeof(memory)
        if kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            available_ram_gib = round(int(memory.ullAvailPhys) / 1024 / 1024 / 1024, 2)

        kernel32.GetSystemTimes.argtypes = [
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        ]
        kernel32.GetSystemTimes.restype = wintypes.BOOL

        def system_times() -> tuple[int, int] | None:
            idle = wintypes.FILETIME()
            kernel = wintypes.FILETIME()
            user = wintypes.FILETIME()
            if not kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                return None
            return filetime_value(idle), filetime_value(kernel) + filetime_value(user)

        before = system_times()
        time.sleep(0.05)
        after = system_times()
        if before is not None and after is not None:
            idle_delta = after[0] - before[0]
            total_delta = after[1] - before[1]
            if total_delta > 0:
                cpu_percent = round(max(0.0, min(100.0, 100.0 * (total_delta - idle_delta) / total_delta)), 2)
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_process_count": python_count,
        "available_ram_gib": available_ram_gib,
        "cpu_percent": cpu_percent,
    }


class ResourceGate:
    """Filesystem-backed shared gate for bounded local E59 heavy work.

    The lock is intentionally cross-process. It is not a deployment service,
    and it records only public-safe counts and task labels. Stale locks are not
    silently removed; a human or later audited recovery must decide.
    """

    _ROOT = Path(tempfile.gettempdir()) / "second-brain-e59-resource-gate"
    _LOCK = _ROOT / "SECOND_BRAIN_LOCAL_HEAVY_TEST_LOCK"
    _STATE = _ROOT / "state.json"

    def __init__(
        self,
        task_id: str,
        *,
        max_task_processes: int = 6,
        max_shared_processes: int = 8,
        max_task_cpu_workers: int = 3,
        max_shared_cpu_workers: int = 4,
        mutex_wait_seconds: float = 30.0,
        cpu_throttle_percent: float = 70.0,
        cpu_throttle_sustain_seconds: float = 15.0,
    ) -> None:
        self.task_id = task_id
        self.max_task_processes = max_task_processes
        self.max_shared_processes = max_shared_processes
        self.max_task_cpu_workers = max_task_cpu_workers
        self.max_shared_cpu_workers = max_shared_cpu_workers
        self.mutex_wait_seconds = mutex_wait_seconds
        self.cpu_throttle_percent = cpu_throttle_percent
        self.cpu_throttle_sustain_seconds = cpu_throttle_sustain_seconds
        self._held = False
        self._owner_pid: int | None = None
        self._cpu_above_threshold_since: float | None = None
        self._last_snapshot: dict[str, object] | None = None
        self._sampled_at = 0.0

    def acquire(self) -> None:
        self._ROOT.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.mutex_wait_seconds
        while True:
            try:
                self._LOCK.mkdir()
                break
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise ResourceViolation("HEAVY_STAGE_MUTEX_UNAVAILABLE") from exc
                # A valid external holder is never removed or bypassed. Waiting
                # is bounded so a stale/unknown lock still fails closed.
                time.sleep(0.05)
        self._held = True
        self._owner_pid = os.getpid()
        try:
            snapshot = self._environment_snapshot(force=True)
            self._write_state(
                {
                    "task_id": self.task_id,
                    "owner_pid": self._owner_pid,
                    "owned_processes": 0,
                    "cpu_workers": 0,
                    "snapshot": snapshot,
                }
            )
        except BaseException:
            self.release()
            raise

    def _environment_snapshot(self, *, force: bool = False) -> dict[str, object]:
        now = time.monotonic()
        # Native sampling is bounded and avoids PowerShell/CIM startup. Refresh
        # often enough to distinguish a sustained overload from one transient
        # desktop spike, as required by the shared resource protocol.
        if force or self._last_snapshot is None or now - self._sampled_at >= 1:
            self._last_snapshot = resource_snapshot()
            self._sampled_at = now
        return self._last_snapshot

    @classmethod
    def recover_legacy_abandoned_lock(cls) -> bool:
        """Remove only the first-run lock lacking an owner identity.

        This recovery is intentionally narrower than automatic stale-lock
        eviction. It is for the E59 pre-ownership-format canary interruption:
        it refuses to act when any Python process exists and it refuses any
        state that has an owner PID. A future owner-aware recovery requires an
        exact PID/creation-time proof and is not silently inferred here.
        """

        if not cls._LOCK.exists():
            return False
        try:
            state = json.loads(cls._STATE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            # A process can die between state unlink and lock-directory rmdir.
            # It is recoverable only after the no-foreign-Python proof below.
            state = {}
        except json.JSONDecodeError as exc:
            raise ProcessLifecycleError("LOCK_STATE_NOT_RECOVERABLE") from exc
        owner_pid = state.get("owner_pid")
        if owner_pid is not None and _windows_snapshot({int(owner_pid)}).get(int(owner_pid)) is not None:
            raise ProcessLifecycleError("OWNER_AWARE_LOCK_OWNER_STILL_EXISTS")
        foreign_python = [
            item
            for item in _windows_snapshot().values()
            if item.pid != os.getpid() and item.executable.lower().startswith("python")
        ]
        if foreign_python:
            raise ProcessLifecycleError("LEGACY_LOCK_RECOVERY_REQUIRES_NO_FOREIGN_PYTHON_PROCESSES")
        cls._STATE.unlink(missing_ok=True)
        for _ in range(10):
            try:
                cls._LOCK.rmdir()
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise ProcessLifecycleError("LEGACY_LOCK_DIRECTORY_STILL_IN_USE")
        try:
            cls._ROOT.rmdir()
        except OSError:
            pass
        return True

    def _write_state(self, state: dict[str, object]) -> None:
        self._STATE.write_text(json.dumps(state, ensure_ascii=True, sort_keys=True), encoding="utf-8")

    def admit(self, owned_processes: int, cpu_workers: int = 0) -> None:
        if not self._held:
            raise ResourceViolation("HEAVY_STAGE_MUTEX_NOT_HELD")
        snapshot = self._environment_snapshot()
        available = snapshot["available_ram_gib"]
        cpu = snapshot["cpu_percent"]
        if available is not None and available < 8:
            raise ResourceViolation("AVAILABLE_RAM_BELOW_8_GIB")
        if cpu is not None and cpu > self.cpu_throttle_percent:
            if self._cpu_above_threshold_since is None:
                self._cpu_above_threshold_since = time.monotonic()
            if time.monotonic() - self._cpu_above_threshold_since >= self.cpu_throttle_sustain_seconds:
                raise ResourceViolation("CPU_THROTTLE_REQUIRED")
        else:
            self._cpu_above_threshold_since = None
        if owned_processes > self.max_task_processes or owned_processes > self.max_shared_processes:
            raise ResourceViolation("PROCESS_CAP_EXCEEDED")
        if cpu_workers > self.max_task_cpu_workers or cpu_workers > self.max_shared_cpu_workers:
            raise ResourceViolation("CPU_WORKER_CAP_EXCEEDED")
        self._write_state(
                {
                    "task_id": self.task_id,
                    "owner_pid": self._owner_pid,
                    "owned_processes": owned_processes,
                    "cpu_workers": cpu_workers,
                    "cpu_above_threshold_since_monotonic": self._cpu_above_threshold_since,
                    "snapshot": snapshot,
            }
        )

    def release(self) -> None:
        if not self._held:
            return
        try:
            self._STATE.unlink(missing_ok=True)
            for _ in range(10):
                try:
                    self._LOCK.rmdir()
                    break
                except OSError:
                    time.sleep(0.05)
            else:
                raise ProcessLifecycleError("HEAVY_STAGE_LOCK_RELEASE_FAILED")
        finally:
            self._held = False
            self._owner_pid = None

    def __enter__(self) -> "ResourceGate":
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()


class OwnedProcessTree:
    """Own one root and every verified descendant visible under it.

    The root is launched below-normal on Windows. Discovery accumulates verified
    identities while ancestors still exist, so a later root exit cannot make a
    previously observed grandchild unowned. Cleanup performs identity rechecks.
    """

    def __init__(self, task_id: str, *, gate: ResourceGate | None = None) -> None:
        self.task_id = task_id
        self.gate = gate or ResourceGate(task_id)
        self._owns_gate = gate is None
        self._roots: dict[int, subprocess.Popen[str]] = {}
        self._owned: dict[int, ProcessIdentity] = {}
        self.events: list[LifecycleEvent] = []
        self.peak_owned_processes = 0
        self.cleaned_pids: set[int] = set()
        self.unrelated_terminated = 0
        self._closed = False

    def __enter__(self) -> "OwnedProcessTree":
        if self._owns_gate:
            self.gate.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.cleanup("context_exit")
        if self._owns_gate:
            self.gate.release()
        self._closed = True

    def _record(self, event: str, pid: int | None, detail: str) -> None:
        self.events.append(LifecycleEvent(event, pid, detail, time.monotonic_ns()))

    def spawn(self, command: Sequence[str], *, purpose: str, env: dict[str, str] | None = None) -> int:
        if self._closed:
            raise ProcessLifecycleError("TREE_IS_CLOSED")
        expected = len(self._owned) + 1
        self.gate.admit(expected)
        creationflags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0) if os.name == "nt" else 0
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
            env=env,
        )
        time.sleep(0.05)
        snapshot = _windows_snapshot({process.pid})
        item = snapshot.get(process.pid)
        if item is None:
            process.kill()
            raise ProcessLifecycleError("ROOT_IDENTITY_NOT_VISIBLE")
        root = ProcessIdentity(
            pid=item.pid,
            ppid=item.ppid,
            creation_time=item.creation_time,
            executable=item.executable,
            command_digest=_digest_command(command),
            root_pid=item.pid,
            discovered_from="ROOT_SPAWN",
        )
        self._roots[process.pid] = process
        self._owned[root.pid] = root
        self._record("spawn", root.pid, purpose)
        self._refresh_peak()
        return root.pid

    def _refresh_peak(self) -> None:
        self.peak_owned_processes = max(self.peak_owned_processes, len(self._owned))
        self.gate.admit(len(self._owned))

    def discover_descendants(self) -> tuple[ProcessIdentity, ...]:
        snapshot = _windows_snapshot()
        changed = True
        while changed:
            changed = False
            owned_pids = set(self._owned)
            for item in snapshot.values():
                if item.pid in owned_pids or item.ppid not in owned_pids:
                    continue
                # Re-read only the candidate PID so its creation time is
                # trustworthy before it becomes an owned descendant.
                identified = _windows_snapshot({item.pid}).get(item.pid)
                if identified is None or identified.ppid != item.ppid:
                    continue
                parent = self._owned[item.ppid]
                descendant = ProcessIdentity(
                    pid=identified.pid,
                    ppid=identified.ppid,
                    creation_time=identified.creation_time,
                    executable=identified.executable,
                    command_digest=identified.command_digest,
                    root_pid=parent.root_pid,
                    discovered_from="OBSERVED_DESCENDANT",
                )
                self._owned[item.pid] = descendant
                self._record("discover_descendant", item.pid, f"root={descendant.root_pid}")
                changed = True
        self._refresh_peak()
        return tuple(self._owned.values())

    def wait_for_descendants(self, root_pid: int, *, minimum: int, timeout_seconds: float) -> tuple[ProcessIdentity, ...]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            self.discover_descendants()
            descendants = [item for item in self._owned.values() if item.root_pid == root_pid and item.pid != root_pid]
            if len(descendants) >= minimum:
                return tuple(descendants)
            time.sleep(0.05)
        raise ProcessLifecycleError("DESCENDANT_DISCOVERY_TIMEOUT")

    def wait(self, root_pid: int, *, timeout_seconds: float) -> int:
        process = self._roots[root_pid]
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            self._record("timeout", root_pid, "wait timeout")
            raise
        self.discover_descendants()
        self._record("root_exit", root_pid, str(return_code))
        if return_code != 0:
            raise ProcessLifecycleError(f"ROOT_EXIT_{return_code}")
        return return_code

    def _identity_is_live(self, owned: ProcessIdentity, snapshot: dict[int, ProcessIdentity] | None = None) -> bool:
        current = (snapshot if snapshot is not None else _windows_snapshot({owned.pid})).get(owned.pid)
        return current is not None and owned.matches(current)

    def _request_termination(self, owned: ProcessIdentity, *, force: bool) -> None:
        process = self._roots.get(owned.pid)
        if process is not None and process.poll() is None:
            if force:
                process.kill()
            else:
                process.terminate()
        elif os.name == "nt":
            # The immediately preceding batch identity check is the authorization.
            command = ["taskkill", "/PID", str(owned.pid), "/T"]
            if force:
                command.append("/F")
            try:
                subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
            except subprocess.TimeoutExpired:
                # The process identity remains in the current cleanup batch. A
                # single slow taskkill request must not abandon verified roots,
                # descendants, descriptor cleanup, or the later force pass.
                self._record("termination_request_timeout", owned.pid, "force" if force else "soft")
        else:
            os.kill(owned.pid, 9 if force else 15)

    def cleanup(self, reason: str) -> int:
        if self._closed and not self._owned:
            return 0
        self.discover_descendants()
        targets = sorted(self._owned.values(), key=lambda item: (item.root_pid, item.pid), reverse=True)
        current = _windows_snapshot({item.pid for item in targets})
        live = [item for item in targets if self._identity_is_live(item, current)]
        # One identity batch immediately precedes all soft requests; we do not
        # repeatedly scan every desktop process for each descendant.
        for owned in live:
            self._request_termination(owned, force=False)
        time.sleep(0.2)
        after_soft = _windows_snapshot({item.pid for item in live})
        remaining = [item for item in live if self._identity_is_live(item, after_soft)]
        for owned in remaining:
            self._request_termination(owned, force=True)
        deadline = time.monotonic() + 2.0
        final = _windows_snapshot({item.pid for item in live})
        while remaining and time.monotonic() < deadline:
            time.sleep(0.1)
            final = _windows_snapshot({item.pid for item in live})
            remaining = [item for item in live if self._identity_is_live(item, final)]
        failed = [item.pid for item in live if self._identity_is_live(item, final)]
        reap_failure: ProcessLifecycleError | None = None
        for process in self._roots.values():
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired as exc:
                    reap_failure = ProcessLifecycleError(f"ROOT_REAP_TIMEOUT:{process.pid}")
            finally:
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
        if failed:
            for pid in failed:
                self._record("cleanup_failed", pid, reason)
            raise ProcessLifecycleError(f"OWNED_PROCESS_CLEANUP_FAILED:{','.join(map(str, failed))}")
        if reap_failure is not None:
            raise reap_failure
        for owned in targets:
            self.cleaned_pids.add(owned.pid)
            self._record("cleanup", owned.pid, reason)
        count = len(self._owned)
        self._owned.clear()
        return count

    @property
    def active_owned_count(self) -> int:
        current = _windows_snapshot(set(self._owned))
        return sum(1 for item in self._owned.values() if self._identity_is_live(item, current))

    def report(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "peak_task_owned_processes": self.peak_owned_processes,
            "spawned_pid_count": len([event for event in self.events if event.event == "spawn"]),
            "discovered_descendant_count": len([event for event in self.events if event.event == "discover_descendant"]),
            "cleaned_pid_count": len(self.cleaned_pids),
            "postflight_task_owned_process_count": self.active_owned_count,
            "orphan_count": self.active_owned_count,
            "unrelated_terminated": self.unrelated_terminated,
            "events": [asdict(event) for event in self.events],
        }


def descendant_root_program(*, grandchildren: int, root_exit_first: bool, sleep_seconds: float = 10.0) -> list[str]:
    """Return a public-safe child command that creates bounded Python grandchildren."""

    if grandchildren < 1 or grandchildren > 2:
        raise ValueError("grandchildren must be between 1 and 2")
    code = (
        "import subprocess,sys,time; "
        f"children=[subprocess.Popen([sys.executable,'-c','import time; time.sleep({sleep_seconds})']) for _ in range({grandchildren})]; "
        "print(','.join(str(p.pid) for p in children), flush=True); "
        + ("time.sleep(0.75); raise SystemExit(0)" if root_exit_first else f"time.sleep({sleep_seconds})")
    )
    return [sys.executable, "-c", code]
