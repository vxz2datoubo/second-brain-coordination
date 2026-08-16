"""Read-only host discovery with fixed commands and injectable test runners."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import subprocess
from typing import Callable

from .models import CapabilityStatus

Runner = Callable[[tuple[str, ...]], tuple[int, str, str]]


def _default_runner(command: tuple[str, ...]) -> tuple[int, str, str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
    return completed.returncode, completed.stdout, completed.stderr


@dataclass(frozen=True)
class DiscoverySnapshot:
    codex_desktop: CapabilityStatus
    codex_cli: CapabilityStatus
    docker: CapabilityStatus
    listeners: tuple[int, ...]
    evidence_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["codex_desktop"] = self.codex_desktop.value
        data["codex_cli"] = self.codex_cli.value
        data["docker"] = self.docker.value
        return data


class ReadOnlyDiscovery:
    """Uses a fixed allowlist of inventory commands; it never starts or stops anything."""

    _COMMANDS = {
        "listeners": ("netstat.exe", "-ano", "-p", "tcp"),
        "codex": ("where.exe", "codex"),
        "docker": ("where.exe", "docker"),
    }

    def __init__(self, runner: Runner = _default_runner) -> None:
        self._runner = runner

    @staticmethod
    def _status(exit_code: int) -> CapabilityStatus:
        return CapabilityStatus.SUPPORTED if exit_code == 0 else CapabilityStatus.UNKNOWN

    def snapshot(self) -> DiscoverySnapshot:
        codex_exit, _, _ = self._runner(self._COMMANDS["codex"])
        docker_exit, _, _ = self._runner(self._COMMANDS["docker"])
        listen_exit, listen_stdout, _ = self._runner(self._COMMANDS["listeners"])
        listeners: list[int] = []
        if listen_exit == 0:
            for line in listen_stdout.splitlines():
                if "LISTENING" not in line.upper():
                    continue
                match = re.search(r":(\d+)\s+", line)
                if match:
                    listeners.append(int(match.group(1)))
        return DiscoverySnapshot(
            codex_desktop=CapabilityStatus.UNKNOWN,
            codex_cli=self._status(codex_exit),
            docker=self._status(docker_exit),
            listeners=tuple(sorted(set(listeners))),
            evidence_notes=(
                "desktop UI and App Automation are intentionally UNKNOWN without a visible local verification",
                "all discovery commands are fixed read-only inventory commands",
            ),
        )
