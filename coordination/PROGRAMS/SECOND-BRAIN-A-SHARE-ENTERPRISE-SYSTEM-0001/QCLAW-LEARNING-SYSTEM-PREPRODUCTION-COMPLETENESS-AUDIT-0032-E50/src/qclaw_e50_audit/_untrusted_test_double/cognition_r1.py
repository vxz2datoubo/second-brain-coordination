"""cognition — D6 verified user-origin cognition mapping.

D6 pass criteria:
  - "verified user-origin" requires explicit `source_class=USER_DECLARED` on the source,
    not inferred from text content
  - inferred cognition remains `candidate / confidence / UNKNOWN`
  - no forgery path: caller cannot mark `verified_user_origin=true` without the source marker
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .source_policy import SourceClass


class CognitionOrigin(str, Enum):
    """Origin classification for cognition entries."""
    VERIFIED_USER = "verified_user"
    USER_DECLARED = "user_declared"
    INFERRED_CANDIDATE = "inferred_candidate"
    UNKNOWN = "unknown"


class VerifiedUserOriginRequired(Exception):
    """Raised when caller attempts to mark VERIFIED_USER without USER_DECLARED source."""


@dataclass(frozen=True)
class CognitionEntry:
    text: str
    origin: CognitionOrigin
    confidence: float = 1.0
    provenance: str = ""


def classify_cognition_origin(*, source_class: SourceClass, text: str,
                              claimed_verified_user: bool = False) -> CognitionEntry:
    """Map a source + text fragment to a cognition entry.

    Rules:
      - claimed_verified_user=True requires source_class in {USER_DECLARED, ...}; else raise.
      - USER_DECLARED without verified_user flag → origin=USER_DECLARED.
      - source_class in {CLEAN_ARTICLE, NOISY_ASR, CHAT_DIALOGUE, OCR_TYPO_HEAVY, METHOD_SKILL, ADVERSARIAL_MUTATION}
        → origin=INFERRED_CANDIDATE (default).
      - PROMPT_INJECTION class → origin=UNKNOWN (refuse to derive cognition).
    """
    if claimed_verified_user:
        if source_class not in {SourceClass.USER_DECLARED}:
            raise VerifiedUserOriginRequired(
                f"Cannot mark verified_user_origin=True with source_class={source_class.value!r}; "
                "must be USER_DECLARED."
            )
        return CognitionEntry(
            text=text,
            origin=CognitionOrigin.VERIFIED_USER,
            confidence=1.0,
            provenance=f"source_class={source_class.value}",
        )

    if source_class == SourceClass.PROMPT_INJECTION:
        return CognitionEntry(
            text=text,
            origin=CognitionOrigin.UNKNOWN,
            confidence=0.0,
            provenance="prompt-injection content; refused to derive cognition",
        )

    if source_class == SourceClass.USER_DECLARED:
        return CognitionEntry(
            text=text,
            origin=CognitionOrigin.USER_DECLARED,
            confidence=0.9,
            provenance="user declared but not yet verified",
        )

    # Default: public-safe source, inferred candidate only
    return CognitionEntry(
        text=text,
        origin=CognitionOrigin.INFERRED_CANDIDATE,
        confidence=0.4,
        provenance=f"source_class={source_class.value}",
    )


@dataclass
class CognitionMap:
    """Container of cognition entries."""
    entries: list = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = []

    def add(self, entry: CognitionEntry) -> None:
        self.entries.append(entry)

    def verified_user_count(self) -> int:
        return sum(1 for e in self.entries if e.origin == CognitionOrigin.VERIFIED_USER)

    def inferred_candidate_count(self) -> int:
        return sum(1 for e in self.entries if e.origin == CognitionOrigin.INFERRED_CANDIDATE)

    def unknown_count(self) -> int:
        return sum(1 for e in self.entries if e.origin == CognitionOrigin.UNKNOWN)

    def any_forgery_attempt(self) -> bool:
        """For D6: caller attempted to forge verified_user_origin without USER_DECLARED."""
        # tracked via the exception path; this is the placeholder for runtime telemetry
        return False