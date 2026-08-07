"""Independent reconstruction of two downloaded Provider evidence files."""

from __future__ import annotations

from hashlib import sha256
import hmac
import json
from pathlib import Path
from typing import Mapping

from .core import AuthorityError, canonical_bytes
from .provider import DualProviderEvidence, E57_PROVIDER_CONTRACT, provider_evidence_from_mapping, verify_dual_provider_evidence


def _verify_expected_pair(tested_digest: str | None, receipt_digest: str | None) -> None:
    if tested_digest is None or receipt_digest is None:
        raise AuthorityError("both external Provider evidence digests are required")
    for label, digest in (("tested", tested_digest), ("receipt", receipt_digest)):
        if digest is not None and (len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest)):
            raise AuthorityError(f"external {label} Provider evidence digest is malformed")


def verify_evidence_files(
    *,
    tested_path: Path,
    receipt_path: Path,
    tested_head: str,
    receipt_head: str,
    expected_tested_evidence_digest: str | None = None,
    expected_receipt_evidence_digest: str | None = None,
) -> Mapping[str, object]:
    _verify_expected_pair(expected_tested_evidence_digest, expected_receipt_evidence_digest)
    try:
        tested_bytes = tested_path.read_bytes()
        receipt_bytes = receipt_path.read_bytes()
        tested = provider_evidence_from_mapping(json.loads(tested_bytes))
        receipt = provider_evidence_from_mapping(json.loads(receipt_bytes))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AuthorityError("downloaded Provider evidence file is malformed") from exc
    pair = DualProviderEvidence(tested, receipt)
    verify_dual_provider_evidence(pair, E57_PROVIDER_CONTRACT, tested_head=tested_head, receipt_head=receipt_head)
    if not hmac.compare_digest(tested.digest(), expected_tested_evidence_digest):
        raise AuthorityError("downloaded tested Provider evidence differs from its external anchor")
    if not hmac.compare_digest(receipt.digest(), expected_receipt_evidence_digest):
        raise AuthorityError("downloaded receipt Provider evidence differs from its external anchor")
    result = {
        "schema": "e57-dual-provider-verification-v1",
        "tested_evidence_file_sha256": sha256(tested_bytes).hexdigest(),
        "receipt_evidence_file_sha256": sha256(receipt_bytes).hexdigest(),
        "tested_evidence_digest": tested.digest(),
        "receipt_evidence_digest": receipt.digest(),
        "tested_head": tested_head,
        "receipt_head": receipt_head,
        "tested_run_id": tested.run_id,
        "receipt_run_id": receipt.run_id,
    }
    result["verification_sha256"] = sha256(canonical_bytes(result)).hexdigest()
    return result
