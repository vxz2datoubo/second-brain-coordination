"""source_policy — E50 source policy enforcement.

PUBLIC_SAFE_GENERALIZATION_ONLY:
  - No private/high-value user source ingestion during E50.
  - Allowed: synthetic fixtures, public-domain non-sensitive text, sanitized ASR/OCR/chat.
  - Private tags must close the input (fail-closed).

D1: source ingestion / privacy / provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceClass(str, Enum):
    """Required source classes per E50 task brief."""
    CLEAN_ARTICLE = "clean_article"
    NOISY_ASR = "noisy_asr"
    CHAT_DIALOGUE = "chat_dialogue"
    OCR_TYPO_HEAVY = "ocr_typo_heavy"
    CONTRADICTION_PAIR = "contradiction_pair"
    METHOD_SKILL = "method_skill"
    # Adversarial (D10)
    PROMPT_INJECTION = "prompt_injection"
    ADVERSARIAL_MUTATION = "adversarial_mutation"
    # D6: User declared (still public-safe since marked explicitly; private inference denied)
    USER_DECLARED = "user_declared"


class PrivateSourceRefused(Exception):
    """Raised when a private source is submitted to an E50 PUBLIC_SAFE audit."""


@dataclass(frozen=True)
class SourcePolicy:
    """Frozen policy: refuse any source marked private=True; refuse any source
    lacking source_class; refuse any source marked as private_user_high_value."""
    allow_private: bool = False
    allowed_source_classes: frozenset = frozenset({
        SourceClass.CLEAN_ARTICLE,
        SourceClass.NOISY_ASR,
        SourceClass.CHAT_DIALOGUE,
        SourceClass.OCR_TYPO_HEAVY,
        SourceClass.CONTRADICTION_PAIR,
        SourceClass.METHOD_SKILL,
        SourceClass.PROMPT_INJECTION,
        SourceClass.ADVERSARIAL_MUTATION,
        SourceClass.USER_DECLARED,
    })

    def check(self, source_class, is_private: bool = False, source_uri: str = "") -> None:
        """Fail-closed policy enforcement.

        - If is_private=True, refuse (E50 never ingests private sources).
        - If source_class not in allowed classes, refuse.
        - If source_uri is empty, refuse (no silent default).
        """
        if is_private:
            raise PrivateSourceRefused(
                f"Source marked private=True refused by E50 policy (source_uri={source_uri!r})."
            )
        if source_class is None:
            raise PrivateSourceRefused(
                "Source missing source_class; refusing by default (no silent default)."
            )
        if source_class not in self.allowed_source_classes:
            raise PrivateSourceRefused(
                f"Source class {source_class.value!r} not in E50 allowed set."
            )
        if not source_uri:
            raise PrivateSourceRefused(
                "Source missing source_uri; refusing by default (no silent default)."
            )


DEFAULT_POLICY = SourcePolicy()


def refuse_if_private(source_class, is_private: bool, source_uri: str = "") -> None:
    """Module-level convenience."""
    DEFAULT_POLICY.check(source_class, is_private=is_private, source_uri=source_uri)