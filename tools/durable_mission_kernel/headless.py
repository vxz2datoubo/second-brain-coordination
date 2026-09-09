"""B5 — WorkBuddy headless adapter + runtime/model attestation + context rollover.

The adapter is an *interface* for driving bounded headless episodes. It records
runtime/model attestation (version, model id) and supports context rollover by
serializing a checkpoint that a subsequent episode can resume from.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class RuntimeAttestation:
    python_version: str
    platform: str
    machine: str
    model_id: Optional[str] = None
    model_profile: str = "DEEP_ENGINEERING"
    kernel_version: str = "0.1.0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "machine": self.machine,
            "model_id": self.model_id,
            "model_profile": self.model_profile,
            "kernel_version": self.kernel_version,
        }


def attest_runtime(model_id: Optional[str] = None,
                   model_profile: str = "DEEP_ENGINEERING") -> RuntimeAttestation:
    """Capture a fresh runtime/model attestation (never persisted with secrets)."""
    return RuntimeAttestation(
        python_version=platform.python_version(),
        platform=sys.platform,
        machine=platform.machine(),
        model_id=model_id,
        model_profile=model_profile,
    )


@dataclass
class ContextRollover:
    """A serializable context-rollover checkpoint for episode handoff."""

    mission_id: str
    state: str
    state_seq: int
    verified_facts: dict[str, Any] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    next_action: Optional[str] = None
    exact_git_head: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "mission_id": self.mission_id,
                "state": self.state,
                "state_seq": self.state_seq,
                "verified_facts": self.verified_facts,
                "unresolved": self.unresolved,
                "counter_evidence": self.counter_evidence,
                "next_action": self.next_action,
                "exact_git_head": self.exact_git_head,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str) -> "ContextRollover":
        d = json.loads(raw)
        return cls(**d)


class HeadlessAdapter:
    """Minimal headless episode adapter.

    The adapter intentionally does NOT reimplement the WorkBuddy SDK; it models the
    bounded interface the kernel needs (launch, checkpoint, rollover) so the rest of
    the kernel can be tested deterministically. SDK capability verification is a
    separate, explicitly-bounded probe.
    """

    def __init__(self, mission_id: str, attestation: RuntimeAttestation):
        self.mission_id = mission_id
        self.attestation = attestation

    def launch_episode(self, episode_id: str, resume_from: Optional[ContextRollover] = None) -> dict[str, Any]:
        """Return the episode's launch record (attestation + resume pointer)."""
        return {
            "episode_id": episode_id,
            "mission_id": self.mission_id,
            "attestation": self.attestation.as_dict(),
            "resume_from": None if resume_from is None else resume_from.to_json(),
        }

    def rollover(self, state: str, state_seq: int, next_action: str,
                 verified_facts: dict[str, Any] | None = None,
                 exact_git_head: str | None = None) -> ContextRollover:
        return ContextRollover(
            mission_id=self.mission_id,
            state=state,
            state_seq=state_seq,
            verified_facts=verified_facts or {},
            next_action=next_action,
            exact_git_head=exact_git_head,
        )
