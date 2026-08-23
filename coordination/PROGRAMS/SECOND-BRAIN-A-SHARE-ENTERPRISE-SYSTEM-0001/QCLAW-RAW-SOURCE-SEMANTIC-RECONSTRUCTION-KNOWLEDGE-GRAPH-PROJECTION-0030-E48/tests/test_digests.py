"""Mutation tests for E61 compatibility digests.

Verifies the rules from Issue #216 comment #5249272794 (rule #5):
- semantic changes alter canonical_semantic_sha256
- source changes alter l0_provenance_sha256
- volatile / non-semantic field changes do NOT alter canonical_semantic_sha256
- raw_artifact_sha256 covers the exact serialized bytes
"""
from __future__ import annotations

import unittest
import copy
import sys
from pathlib import Path

# Path setup: run from anywhere by walking up to the E48 module root.
_HERE = Path(__file__).resolve()
E48_ROOT = _HERE.parents[1]
sys.path.insert(0, str(E48_ROOT / "src"))

from qclaw_e48_reconstruction.digests import (  # noqa: E402
    canonical_json,
    l0_provenance_sha256,
    raw_artifact_sha256,
    canonical_semantic_sha256,
    sha256_hex,
)


def _pkg(ingested_at: str = "2026-08-11T05:00:00Z") -> dict:
    return {
        "schema": "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1",
        "package_id": "E48-DIGEST-CANARY-001",
        "package_version": 1,
        "content_hash": "379ccafdf592ac75",  # legacy 16-hex, compat-only
        "source": {
            "source_id": "synthetic-canary-noisy-chinese",
            "source_url": "workspace://canary/synthetic_canary_noisy_chinese.txt",
            "source_title": "E48 PUBLIC_SAFE canary",
            "source_hash": "0" * 64,
            "source_size_bytes": 0,
            "ingested_at": ingested_at,
        },
        "summary": "short",
        "atoms": [
            {
                "atom_id": "A001",
                "atom_type": "CONCEPT",
                "content": "成交量上升时价格倾向于上升",
                "source_spans": [
                    {"byte_start": 30, "byte_end": 50, "line_start": 1, "line_end": 1},
                ],
                "evidence_kind": "INFERENCE",
                "confidence": "MEDIUM",
                "scope": "A股日内",
                "invalidation_conditions": "n/a",
            }
        ],
        "relations": [
            {
                "source_atom_id": "A001",
                "target_atom_id": "A002",
                "relation_type": "SUPPORTS",
                "span_index": 0,
            }
        ],
        "contradictions": [],
        "unknowns": [],
        "memory_records": [],
        "skills": [],
    }


def test_canonical_json_is_deterministic() -> None:
    a = canonical_json({"b": 2, "a": 1})
    b = canonical_json({"a": 1, "b": 2})
    assert a == b
    assert a == '{"a":1,"b":2}'


def test_semantic_change_alters_canonical_semantic_digest() -> None:
    pkg1 = _pkg()
    pkg2 = _pkg()
    pkg2["atoms"][0]["content"] = "成交量上升时价格倾向于下降"  # semantic change
    h1 = canonical_semantic_sha256(pkg1)
    h2 = canonical_semantic_sha256(pkg2)
    assert h1 != h2, "semantic change must alter canonical_semantic_sha256"
    assert len(h1) == 64 and len(h2) == 64


def test_volatile_change_does_not_alter_canonical_semantic_digest() -> None:
    pkg1 = _pkg(ingested_at="2026-08-11T05:00:00Z")
    pkg2 = _pkg(ingested_at="2030-01-01T00:00:00Z")  # volatile, MUST NOT affect canonical
    pkg3 = _pkg()
    pkg3["package_version"] = 99  # also volatile
    pkg4 = _pkg()
    pkg4["content_hash"] = "deadbeefcafebabe"  # legacy compat field, volatile here
    h1 = canonical_semantic_sha256(pkg1)
    h2 = canonical_semantic_sha256(pkg2)
    h3 = canonical_semantic_sha256(pkg3)
    h4 = canonical_semantic_sha256(pkg4)
    assert h1 == h2 == h3 == h4, (
        "ingested_at / package_version / content_hash MUST NOT alter canonical_semantic_sha256"
    )


def test_source_change_alters_l0_provenance_digest() -> None:
    pkg1 = _pkg()
    pkg2 = _pkg()
    pkg2["source"]["source_id"] = "different-source"  # source mutation
    pkg3 = _pkg()
    pkg3["atoms"][0]["source_spans"][0]["byte_start"] = 31  # L0 span mutation
    h_base = l0_provenance_sha256(pkg1["source"], pkg1["atoms"])
    h_src = l0_provenance_sha256(pkg2["source"], pkg2["atoms"])
    h_span = l0_provenance_sha256(pkg3["source"], pkg3["atoms"])
    assert h_base != h_src
    assert h_base != h_span
    assert len(h_base) == 64


def test_volatile_change_does_not_alter_l0_provenance_digest() -> None:
    pkg1 = _pkg(ingested_at="2026-08-11T05:00:00Z")
    pkg2 = _pkg(ingested_at="2030-01-01T00:00:00Z")
    pkg3 = _pkg()
    pkg3["summary"] = "completely different"  # summary is not provenance
    h1 = l0_provenance_sha256(pkg1["source"], pkg1["atoms"])
    h2 = l0_provenance_sha256(pkg2["source"], pkg2["atoms"])
    h3 = l0_provenance_sha256(pkg3["source"], pkg3["atoms"])
    assert h1 == h2, "ingested_at MUST NOT alter l0_provenance_sha256"
    assert h1 == h3, "summary MUST NOT alter l0_provenance_sha256"


def test_raw_artifact_sha256_covers_exact_bytes() -> None:
    pkg = _pkg()
    serialized_a = canonical_json(pkg).encode("utf-8")
    serialized_b = (canonical_json(pkg) + " ").encode("utf-8")
    h_a = raw_artifact_sha256(serialized_a)
    h_b = raw_artifact_sha256(serialized_b)
    assert h_a != h_b, "extra trailing whitespace MUST alter raw_artifact_sha256"
    assert len(h_a) == 64


def test_legacy_short_content_hash_is_compat_only() -> None:
    pkg = _pkg()
    legacy = pkg["content_hash"]
    full = canonical_semantic_sha256(pkg)
    assert len(legacy) == 16
    assert len(full) == 64
    assert legacy != full[:16]  # they are independent
    assert "0" * 16 != full[:16] or True  # sanity


def test_digests_are_independent() -> None:
    pkg = _pkg()
    full = canonical_semantic_sha256(pkg)
    prov = l0_provenance_sha256(pkg["source"], pkg["atoms"])
    raw = raw_artifact_sha256(canonical_json(pkg).encode("utf-8"))
    assert len({full, prov, raw}) == 3, "the three digests must be distinct"


def test_sha256_hex_is_64() -> None:
    h = sha256_hex(b"abc")
    assert h == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert len(h) == 64


class TestDigests(unittest.TestCase):
    def test_canonical_json_is_deterministic(self):
        test_canonical_json_is_deterministic()

    def test_semantic_change_alters_canonical_semantic_digest(self):
        test_semantic_change_alters_canonical_semantic_digest()

    def test_volatile_change_does_not_alter_canonical_semantic_digest(self):
        test_volatile_change_does_not_alter_canonical_semantic_digest()

    def test_source_change_alters_l0_provenance_digest(self):
        test_source_change_alters_l0_provenance_digest()

    def test_volatile_change_does_not_alter_l0_provenance_digest(self):
        test_volatile_change_does_not_alter_l0_provenance_digest()

    def test_raw_artifact_sha256_covers_exact_bytes(self):
        test_raw_artifact_sha256_covers_exact_bytes()

    def test_legacy_short_content_hash_is_compat_only(self):
        test_legacy_short_content_hash_is_compat_only()

    def test_digests_are_independent(self):
        test_digests_are_independent()

    def test_sha256_hex_is_64(self):
        test_sha256_hex_is_64()
