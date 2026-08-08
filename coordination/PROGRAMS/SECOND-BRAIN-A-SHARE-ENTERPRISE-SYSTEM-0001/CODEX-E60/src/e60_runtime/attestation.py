"""Fail-closed synthetic attestation and Source/Span verification for E60.

The only verification material in this runtime is a public, synthetic fixture
key. Test signing material lives outside this package. The raw-RSA envelope is
intentionally labelled non-production: it makes authority substitution tests
executable without claiming a deployed PKI or protection from code mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .provider_evidence import ProviderEvidenceAggregate, canonical_json_bytes


_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_HEX_40 = re.compile(r"^[0-9a-f]{40}$")
_PUBLIC_MODULUS = int(
    "4860328296384066339081332229486435989775165605120886380697317341049670319131444432990037230279525616568637811580412731556012931985943462985444097595156577"
)
_PUBLIC_EXPONENT = 65537
_KEY_ID = "E60-SYNTHETIC-TEST-ONLY-RSA-RAW-SHA256-V1"
_DOMAIN = "SYNTHETIC_EXTERNAL_ATTESTATION_ONLY"
_SYNTHETIC_FIXTURE_ACCEPTANCE_REF = "SYNTHETIC_FIXTURE_NO_EXTERNAL_REVIEW"
_GITHUB_PR_COMMENT_REF = re.compile(r"^GITHUB_PR_COMMENT:[1-9][0-9]*$")


class AttestationError(ValueError):
    """A candidate did not satisfy the E60 fail-closed attestation contract."""


def _canonical(value: object) -> bytes:
    return canonical_json_bytes(value)


def _require_hex(value: object, *, length: int, field: str) -> str:
    text = str(value)
    matcher = _HEX_40 if length == 40 else _HEX_64
    if not matcher.fullmatch(text):
        raise AttestationError(f"{field.upper()}_MALFORMED")
    return text


def _verify_signature(payload: Mapping[str, object], signature_hex: object) -> bool:
    """Verify the synthetic fixture envelope with runtime public material only."""

    try:
        signature = int(str(signature_hex), 16)
    except ValueError:
        return False
    if signature < 0 or signature >= _PUBLIC_MODULUS:
        return False
    digest = sha256(_canonical(payload)).digest()
    recovered = pow(signature, _PUBLIC_EXPONENT, _PUBLIC_MODULUS).to_bytes(
        (_PUBLIC_MODULUS.bit_length() + 7) // 8,
        "big",
    )[-len(digest):]
    return hmac.compare_digest(recovered, digest)


def runtime_identity_digest() -> str:
    """Hash the complete runtime package, excluding generated artifacts.

    A signed attestation binds this exact package manifest.  The function is
    intentionally deterministic: a new private bootstrap module, a modified
    verifier, or any other Python source change makes a previously attested
    runtime ineligible before a verifier instance is created.
    """

    package_root = Path(__file__).resolve().parent
    digest = sha256()
    for source in sorted(package_root.rglob("*.py"), key=lambda item: item.relative_to(package_root).as_posix()):
        relative = source.relative_to(package_root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(sha256(source.read_bytes()).digest())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ExternalAttestation:
    """External record binding source identity, exact Git heads, and Provider facts."""

    authority_id: str
    source_digest: str
    runtime_identity_digest: str
    tested_head: str
    tested_parent: str
    tested_tree: str
    receipt_head: str
    receipt_parent: str
    receipt_tree: str
    provider_evidence_aggregate_digest: str
    reviewer_acceptance_ref: str
    lifecycle: str
    signature_hex: str

    @property
    def attestation_id(self) -> str:
        return sha256(_canonical(self.payload())).hexdigest()

    def payload(self) -> dict[str, str]:
        return {
            "authority_id": self.authority_id,
            "source_digest": self.source_digest,
            "runtime_identity_digest": self.runtime_identity_digest,
            "tested_head": self.tested_head,
            "tested_parent": self.tested_parent,
            "tested_tree": self.tested_tree,
            "receipt_head": self.receipt_head,
            "receipt_parent": self.receipt_parent,
            "receipt_tree": self.receipt_tree,
            "provider_evidence_aggregate_digest": self.provider_evidence_aggregate_digest,
            "reviewer_acceptance_ref": self.reviewer_acceptance_ref,
            "lifecycle": self.lifecycle,
            "domain": _DOMAIN,
            "key_id": _KEY_ID,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "ExternalAttestation":
        required = {
            "authority_id", "source_digest", "runtime_identity_digest", "tested_head",
            "tested_parent", "tested_tree", "receipt_head", "receipt_parent", "receipt_tree",
            "provider_evidence_aggregate_digest", "reviewer_acceptance_ref",
            "lifecycle", "signature_hex", "domain", "key_id",
        }
        if set(value) != required:
            raise AttestationError("EXTERNAL_ATTESTATION_FIELD_SET_MISMATCH")
        if value["domain"] != _DOMAIN or value["key_id"] != _KEY_ID:
            raise AttestationError("EXTERNAL_ATTESTATION_DOMAIN_MISMATCH")
        lifecycle = str(value["lifecycle"])
        if lifecycle not in {
            "PENDING_EXTERNAL",
            "SYNTHETIC_FIXTURE_ACCEPTED",
            "ACCEPTED_EXTERNAL",
        }:
            raise AttestationError("EXTERNAL_ATTESTATION_LIFECYCLE_INVALID")
        if lifecycle == "PENDING_EXTERNAL" and str(value["reviewer_acceptance_ref"]) != "PENDING_EXTERNAL":
            raise AttestationError("EXTERNAL_ATTESTATION_PENDING_CONTRADICTION")
        if (
            lifecycle == "SYNTHETIC_FIXTURE_ACCEPTED"
            and str(value["reviewer_acceptance_ref"]) != _SYNTHETIC_FIXTURE_ACCEPTANCE_REF
        ):
            raise AttestationError("EXTERNAL_ATTESTATION_SYNTHETIC_FIXTURE_CONTRADICTION")
        if (
            lifecycle == "ACCEPTED_EXTERNAL"
            and not _GITHUB_PR_COMMENT_REF.fullmatch(str(value["reviewer_acceptance_ref"]))
        ):
            raise AttestationError("EXTERNAL_ATTESTATION_ACCEPTANCE_REFERENCE_INVALID")
        item = cls(
            authority_id=str(value["authority_id"]),
            source_digest=_require_hex(value["source_digest"], length=64, field="source_digest"),
            runtime_identity_digest=_require_hex(value["runtime_identity_digest"], length=64, field="runtime_identity_digest"),
            tested_head=_require_hex(value["tested_head"], length=40, field="tested_head"),
            tested_parent=_require_hex(value["tested_parent"], length=40, field="tested_parent"),
            tested_tree=_require_hex(value["tested_tree"], length=40, field="tested_tree"),
            receipt_head=_require_hex(value["receipt_head"], length=40, field="receipt_head"),
            receipt_parent=_require_hex(value["receipt_parent"], length=40, field="receipt_parent"),
            receipt_tree=_require_hex(value["receipt_tree"], length=40, field="receipt_tree"),
            provider_evidence_aggregate_digest=_require_hex(
                value["provider_evidence_aggregate_digest"],
                length=64,
                field="provider_evidence_aggregate_digest",
            ),
            reviewer_acceptance_ref=str(value["reviewer_acceptance_ref"]),
            lifecycle=lifecycle,
            signature_hex=str(value["signature_hex"]),
        )
        if not item.authority_id:
            raise AttestationError("EXTERNAL_ATTESTATION_REQUIRED_ID_MISSING")
        if item.receipt_parent != item.tested_head:
            raise AttestationError("EXTERNAL_ATTESTATION_RECEIPT_NOT_DIRECT_CHILD")
        if not _verify_signature(item.payload(), item.signature_hex):
            raise AttestationError("EXTERNAL_ATTESTATION_SIGNATURE_INVALID")
        return item


@dataclass(frozen=True, slots=True)
class SourceSpanGrant:
    """A signed capability; raw source bytes never constitute a valid grant."""

    attestation_id: str
    source_digest: str
    start_byte: int
    end_byte: int
    decoded_digest: str
    signature_hex: str

    def payload(self) -> dict[str, object]:
        return {
            "attestation_id": self.attestation_id,
            "source_digest": self.source_digest,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "decoded_digest": self.decoded_digest,
            "domain": _DOMAIN,
            "key_id": _KEY_ID,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "SourceSpanGrant":
        required = {"attestation_id", "source_digest", "start_byte", "end_byte", "decoded_digest", "signature_hex"}
        if set(value) != required:
            raise AttestationError("SOURCE_SPAN_GRANT_FIELD_SET_MISMATCH")
        try:
            start, end = int(value["start_byte"]), int(value["end_byte"])
        except (TypeError, ValueError) as exc:
            raise AttestationError("SOURCE_SPAN_GRANT_RANGE_MALFORMED") from exc
        if start < 0 or end <= start:
            raise AttestationError("SOURCE_SPAN_GRANT_RANGE_INVALID")
        item = cls(
            attestation_id=_require_hex(value["attestation_id"], length=64, field="attestation_id"),
            source_digest=_require_hex(value["source_digest"], length=64, field="source_digest"),
            start_byte=start,
            end_byte=end,
            decoded_digest=_require_hex(value["decoded_digest"], length=64, field="decoded_digest"),
            signature_hex=str(value["signature_hex"]),
        )
        if not _verify_signature(item.payload(), item.signature_hex):
            raise AttestationError("SOURCE_SPAN_GRANT_SIGNATURE_INVALID")
        return item


class CanonicalVerifier:
    """Verification-only consumer of a valid, externally attested capability."""

    __slots__ = ("_attestation",)

    def __init__(self, attestation: ExternalAttestation, provider_evidence: ProviderEvidenceAggregate) -> None:
        if not isinstance(attestation, ExternalAttestation):
            raise AttestationError("CANONICAL_VERIFIER_REQUIRES_EXTERNAL_ATTESTATION")
        if attestation.lifecycle not in {"SYNTHETIC_FIXTURE_ACCEPTED", "ACCEPTED_EXTERNAL"}:
            raise AttestationError("CANONICAL_VERIFIER_REQUIRES_ACCEPTED_ATTESTATION")
        if not hmac.compare_digest(attestation.runtime_identity_digest, runtime_identity_digest()):
            raise AttestationError("EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH")
        if not isinstance(provider_evidence, ProviderEvidenceAggregate):
            raise AttestationError("CANONICAL_VERIFIER_REQUIRES_PROVIDER_EVIDENCE_AGGREGATE")
        if not hmac.compare_digest(attestation.provider_evidence_aggregate_digest, provider_evidence.digest):
            raise AttestationError("EXTERNAL_ATTESTATION_PROVIDER_EVIDENCE_DIGEST_MISMATCH")
        if (
            provider_evidence.tested_head != attestation.tested_head
            or provider_evidence.tested_parent != attestation.tested_parent
            or provider_evidence.tested_tree != attestation.tested_tree
        ):
            raise AttestationError("EXTERNAL_ATTESTATION_PROVIDER_EVIDENCE_TOPOLOGY_MISMATCH")
        self._attestation = attestation

    @property
    def attestation_id(self) -> str:
        return self._attestation.attestation_id

    def verify_source_span(self, candidate: object) -> bool:
        if not isinstance(candidate, SourceSpanGrant):
            return False
        return (
            candidate.attestation_id == self._attestation.attestation_id
            and candidate.source_digest == self._attestation.source_digest
            and _verify_signature(candidate.payload(), candidate.signature_hex)
        )

    def verify_evidence(self, candidate: object) -> bool:
        if not isinstance(candidate, Mapping):
            return False
        grant = candidate.get("source_span")
        proposition = candidate.get("proposition")
        if not isinstance(grant, SourceSpanGrant) or not isinstance(proposition, Mapping):
            return False
        return self.verify_source_span(grant) and {"subject", "predicate", "object", "polarity"} <= set(proposition)
