"""Literal post-receipt external-anchor validation."""

from __future__ import annotations

from typing import Mapping

from .core import AuthorityError
from .provider import DualProviderEvidence


def required_anchor_values(*, completion_signal: str, receipt_head: str, provider_evidence: DualProviderEvidence) -> tuple[str, ...]:
    if not completion_signal or not receipt_head:
        raise AuthorityError("anchor requires the literal completion signal and receipt head")
    tested = provider_evidence.tested_provider_evidence
    receipt = provider_evidence.receipt_provider_evidence
    return (
        completion_signal,
        receipt_head,
        str(tested.run_id),
        str(receipt.run_id),
        tested.digest(),
        receipt.digest(),
    )


def verify_literal_post_receipt_anchor(
    text: str,
    *,
    completion_signal: str,
    receipt_head: str,
    provider_evidence: DualProviderEvidence,
) -> None:
    if not isinstance(text, str) or not text:
        raise AuthorityError("post-receipt anchor must be nonempty literal text")
    if any(ord(character) < 32 and character not in "\n\r\t" for character in text):
        raise AuthorityError("post-receipt anchor contains a control character")
    if "\\b" in text or "\\f" in text or "\\u" in text or "\\x" in text:
        raise AuthorityError("post-receipt anchor must not encode identifiers with escape sequences")
    missing = [value for value in required_anchor_values(completion_signal=completion_signal, receipt_head=receipt_head, provider_evidence=provider_evidence) if value not in text]
    if missing:
        raise AuthorityError("post-receipt anchor omits a required literal identity")
