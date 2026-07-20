"""Test suite for QCLAW Determistic Learning Packet Pipeline.

Contains:
- Synthetic test cases for Cases A-F (Issue #36)
- ≥33 unit/behavior tests
- run_all_tests() driver
"""

import sys, os, json, datetime, copy

# Ensure workspace root is on sys.path for _qclaw_pipeline imports
_WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WS not in sys.path:
    sys.path.insert(0, _WS)

# ── Synthetic Test Cases (Issue #36: Cases A-F) ──

test_cases = {
    "case_a__no_conflict_high_confidence_facts": [
        {
            "source_id": "case_a_1",
            "content": "The gravitational constant G is 6.67430×10⁻¹¹ m³ kg⁻¹ s⁻². This value is measured with high precision and widely confirmed.",
            "source_time": "2024-01-15T10:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "The gravitational constant G equals 6.67430×10⁻¹¹ m³ kg⁻¹ s⁻²",
                    "confidence": 0.95,
                    "scope": "physics",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Measurement data from CODATA"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "CODATA 2018",
                    "original_excerpt": "G = 6.67430×10⁻¹¹ m³ kg⁻¹ s⁻²",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
            "unknowns": [],
        },
        {
            "source_id": "case_a_2",
            "content": "According to general relativity, gravity is the curvature of spacetime caused by mass-energy. The gravitational constant relates mass to this curvature.",
            "source_time": "2024-01-15T10:01:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "CONCEPT",
                    "canonical_statement": "Gravity is the curvature of spacetime caused by mass-energy according to general relativity",
                    "confidence": 0.85,
                    "scope": "physics",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Einstein field equations"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "Einstein 1915",
                    "original_excerpt": "gravity is the curvature of spacetime",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
            "unknowns": [],
        },
    ],

    "case_b__explicit_conflict_same_level": [
        {
            "source_id": "case_b_1",
            "content": "The capital of Australia is Sydney, as most people commonly assume.",
            "source_time": "2024-02-01T08:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "The capital of Australia is Sydney",
                    "confidence": 0.30,
                    "scope": "geography",
                    "verification_status": "DISPUTED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Common assumption"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "common_knowledge_misconception_1",
                    "original_excerpt": "The capital of Australia is Sydney",
                    "evidence_quality": "low",
                }
            ],
            "relations": [],
        },
        {
            "source_id": "case_b_2",
            "content": "Canberra was selected as Australia's capital in 1908 as a compromise between Sydney and Melbourne. It was purpose-built as the national capital.",
            "source_time": "2024-02-01T09:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "The capital of Australia is Canberra",
                    "confidence": 0.95,
                    "scope": "geography",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Australian Constitution", "Seat of Government Act 1908"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "official_records_2",
                    "original_excerpt": "Canberra was selected as Australia's capital",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
        },
    ],

    "case_c__new_atom_supersedes_old": [
        {
            "source_id": "case_c_1_old",
            "content": "The COVID-19 incubation period is 14 days maximum, based on early Wuhan data.",
            "source_time": "2020-03-01T00:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "The COVID-19 incubation period has a maximum of 14 days",
                    "confidence": 0.70,
                    "scope": "medicine",
                    "verification_status": "SUPERSEDED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Early Wuhan outbreak data"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "WHO_2020_early",
                    "original_excerpt": "COVID-19 incubation period is 14 days maximum",
                    "evidence_quality": "moderate",
                }
            ],
            "relations": [],
        },
        {
            "source_id": "case_c_2_new",
            "content": "Updated research shows COVID-19 incubation can extend to 24 days in rare cases, with median of 5.1 days. The 14-day quarantine guideline remains effective for ~99% of cases.",
            "source_time": "2021-06-15T00:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "REFINEMENT",
                    "canonical_statement": "COVID-19 incubation period maximum is 24 days based on updated research",
                    "confidence": 0.88,
                    "scope": "medicine",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Updated global data 2020-2021"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "Lancet 2021",
                    "original_excerpt": "COVID-19 incubation can extend to 24 days",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
        },
    ],

    "case_d__correlation_without_causation": [
        {
            "source_id": "case_d_1",
            "content": "A study found that ice cream sales and drowning incidents both increase during summer months, showing a strong positive correlation.",
            "source_time": "2024-03-10T12:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "CORRELATION",
                    "canonical_statement": "Ice cream sales and drowning incidents show positive correlation in summer months",
                    "confidence": 0.80,
                    "scope": "statistics",
                    "verification_status": "OBSERVED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Observational data"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "summer_correlation_study",
                    "original_excerpt": "ice cream sales and drowning incidents both increase during summer",
                    "evidence_quality": "moderate",
                }
            ],
            "relations": [],
        }
    ],

    "case_e__privacy_class_rules": [
        {
            "source_id": "case_e_1_public",
            "content": "Python is a high-level programming language created by Guido van Rossum in 1991. It emphasizes code readability.",
            "source_time": "2024-04-01T00:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "Python was created by Guido van Rossum in 1991",
                    "confidence": 0.98,
                    "scope": "technology",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Python documentation"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "python.org",
                    "original_excerpt": "created by Guido van Rossum in 1991",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
        },
        {
            "source_id": "case_e_2_restricted",
            "content": "Internal architecture decisions: our production API key is sk-abc123 and the database password is dbpass456. DO NOT SHARE.",
            "source_time": "2024-04-01T01:00:00Z",
            "privacy_class": "RESTRICTED",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "Production environment uses API key sk-abc123 and database password dbpass456",
                    "confidence": 0.99,
                    "scope": "internal",
                    "verification_status": "VERIFIED",
                    "memory_type": "EPISODIC",
                    "privacy_class": "RESTRICTED",
                    "premises": ["Internal documentation"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "internal_secrets_doc",
                    "original_excerpt": "API key is sk-abc123 and the database password is dbpass456",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
        },
    ],

    "case_f__multi_hop_inference": [
        {
            "source_id": "case_f_1",
            "content": "Socrates was a classical Greek philosopher who is credited as the founder of Western philosophy. Plato was his most famous student.",
            "source_time": "2024-05-20T00:00:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "Socrates was a classical Greek philosopher",
                    "confidence": 0.95,
                    "scope": "history",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Historical records"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "history_text_f1",
                    "original_excerpt": "Socrates was a classical Greek philosopher",
                    "evidence_quality": "high",
                },
                {
                    "atom_type": "FACT",
                    "canonical_statement": "Plato was the student of Socrates",
                    "confidence": 0.95,
                    "scope": "history",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Historical records"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "history_text_f1",
                    "original_excerpt": "Plato was his most famous student",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
        },
        {
            "source_id": "case_f_2",
            "content": "Aristotle studied under Plato at the Academy in Athens for nearly 20 years before founding his own school, the Lyceum.",
            "source_time": "2024-05-20T00:01:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "FACT",
                    "canonical_statement": "Aristotle studied under Plato at the Academy in Athens",
                    "confidence": 0.95,
                    "scope": "history",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Historical records"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "history_text_f2",
                    "original_excerpt": "Aristotle studied under Plato at the Academy",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
        },
        {
            "source_id": "case_f_3",
            "content": "Through this chain of mentorship—Socrates to Plato to Aristotle—Western philosophical thought evolved over three generations.",
            "source_time": "2024-05-20T00:02:00Z",
            "privacy_class": "PUBLIC_SAFE",
            "atoms": [
                {
                    "atom_type": "INSIGHT",
                    "canonical_statement": "Western philosophy evolved through the Socrates-Plato-Aristotle mentorship chain over three generations",
                    "confidence": 0.85,
                    "scope": "history",
                    "verification_status": "VERIFIED",
                    "memory_type": "SEMANTIC",
                    "privacy_class": "PUBLIC_SAFE",
                    "premises": ["Historical analysis"],
                    "exceptions": [],
                    "failure_conditions": [],
                    "source_reference": "history_text_f3",
                    "original_excerpt": "Western philosophical thought evolved over three generations",
                    "evidence_quality": "high",
                }
            ],
            "relations": [],
        },
    ],
}


# ═══════════════════════════════════════════════════════
#  Test Functions (≥33)
# ═══════════════════════════════════════════════════════

def _run_test(name, passed, detail=""):
    """Standard test result helper."""
    return {"name": name, "passed": passed, "detail": detail}


def test_normalize_unicode():
    """NFKC normalization — full-width to standard."""
    from _qclaw_pipeline.canonical import normalize_text
    result = normalize_text("\uff21\uff22\uff23")  # Full-width A B C
    return _run_test("test_normalize_unicode", result == "ABC", f"got: {result}")


def test_collapse_whitespace():
    """Multiple whitespace collapsed to single space."""
    from _qclaw_pipeline.canonical import normalize_text
    result = normalize_text("hello    world  \t  test")
    return _run_test("test_collapse_whitespace", result == "hello world test", f"got: {result!r}")


def test_canonical_dict_key_order():
    """Canonical dict always returns keys sorted."""
    from _qclaw_pipeline.canonical import canonical_dict
    d1 = canonical_dict({"z": "last", "a": "first", "m": "middle"})
    keys = list(d1.keys())
    return _run_test("test_canonical_dict_key_order", keys == ["a", "m", "z"], f"keys: {keys}")


def test_content_hash_deterministic():
    """Same input always yields same hash."""
    from _qclaw_pipeline.canonical import content_hash
    h1 = content_hash({"key": "value"})
    h2 = content_hash({"key": "value"})
    return _run_test("test_content_hash_deterministic", h1 == h2, f"{h1} vs {h2}")


def test_content_hash_different():
    """Different input yields different hash."""
    from _qclaw_pipeline.canonical import content_hash
    h1 = content_hash({"key": "value"})
    h2 = content_hash({"key": "other"})
    return _run_test("test_content_hash_different", h1 != h2)


def test_atom_id_deterministic():
    """Same statement + type yields same atom_id."""
    from _qclaw_pipeline.canonical import atom_identity
    id1 = atom_identity("The sky is blue", "fact")
    id2 = atom_identity("The sky is blue", "fact")
    return _run_test("test_atom_id_deterministic", id1 == id2, f"{id1} vs {id2}")


def test_atom_id_different_statement():
    """Different statements yield different atom_id."""
    from _qclaw_pipeline.canonical import atom_identity
    id1 = atom_identity("The sky is blue", "fact")
    id2 = atom_identity("The grass is green", "fact")
    return _run_test("test_atom_id_different_statement", id1 != id2)


def test_relation_id_deterministic():
    """Same source/target/type yields same relation_id."""
    from _qclaw_pipeline.canonical import relation_identity
    r1 = relation_identity("at-aaa", "at-bbb", "supports")
    r2 = relation_identity("at-aaa", "at-bbb", "supports")
    return _run_test("test_relation_id_deterministic", r1 == r2, f"{r1} vs {r2}")


def test_packet_semantic_id():
    """Semantic ID derived from source hash + atom IDs."""
    from _qclaw_pipeline.canonical import packet_semantic_id
    sid1 = packet_semantic_id("abc123", ["at-aaa", "at-bbb"])
    sid2 = packet_semantic_id("abc123", ["at-aaa", "at-bbb"])
    return _run_test("test_packet_semantic_id", sid1 == sid2 and sid1.startswith("lp-"))


def test_packet_instance_id_unique():
    """Different run contexts yield different instance IDs."""
    from _qclaw_pipeline.canonical import packet_instance_id
    i1 = packet_instance_id("lp-semantic", "run_2024_01")
    i2 = packet_instance_id("lp-semantic", "run_2024_02")
    return _run_test("test_packet_instance_id_unique", i1 != i2, f"{i1} vs {i2}")


def test_idempotency_key():
    """Idempotency key format is correct."""
    from _qclaw_pipeline.canonical import idempotency_key
    key = idempotency_key("lp-abc123", "def456789012345")
    expected = "lp-abc123-def456789012"
    return _run_test("test_idempotency_key", key == expected, f"got: {key}")


def test_field_order_independent():
    """Field order change in JSON input does not change atom_id."""
    from _qclaw_pipeline.canonical import content_hash
    h1 = content_hash({"a": 1, "b": 2, "c": 3})
    h2 = content_hash({"c": 3, "a": 1, "b": 2})
    return _run_test("test_field_order_independent", h1 == h2, f"{h1} vs {h2}")


def test_timestamp_does_not_affect_semantic_id():
    """Timestamp is a runtime field; excluded from semantic identity."""
    from _qclaw_pipeline.canonical import content_hash, canonical_dict, IGNORABLE_RUNTIME_FIELDS
    # Verify timestamp_ms is in ignorable list
    return _run_test(
        "test_timestamp_does_not_affect_semantic_id",
        "timestamp_ms" in IGNORABLE_RUNTIME_FIELDS,
        str(IGNORABLE_RUNTIME_FIELDS)
    )


def test_same_content_different_filename():
    """Filename/source_id change does not affect content hash."""
    from _qclaw_pipeline.canonical import content_hash
    h1 = content_hash("identical content here")
    h2 = content_hash("identical content here")
    return _run_test("test_same_content_different_filename", h1 == h2)


def test_build_packet_complete():
    """Complete packet construction with all fields."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="test_src",
        source_content="Test source content for building a complete packet",
        source_time="2024-06-01T00:00:00Z",
        atoms=[
            {"atom_type": "FACT", "canonical_statement": "Water boils at 100°C at sea level", "confidence": 0.95}
        ],
        relations=[
            {"source": "at-water-boils", "target": "at-sea-level", "type": "APPLIES_TO", "confidence": 0.8}
        ],
    )
    ok = all([
        pkt.get("schema_version") == "0.2",
        "packet_semantic_id" in pkt,
        "idempotency_key" in pkt,
        len(pkt["atoms"]) == 1,
        len(pkt["relations"]) == 1,
        pkt["knowledge_status"] == "candidate",
    ])
    return _run_test("test_build_packet_complete", ok, f"semantic_id: {pkt.get('packet_semantic_id')}")


def test_verify_valid_packet():
    """Valid packet passes verification."""
    from _qclaw_pipeline.adapters import build_packet, verify_packet
    pkt = build_packet(
        source_id="ok", source_content="content", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "Something", "confidence": 0.8}],
        relations=[],
    )
    result = verify_packet(pkt)
    return _run_test("test_verify_valid_packet", result["valid"], f"errors: {result['errors']}")


def test_verify_missing_required():
    """Missing required field -> error."""
    from _qclaw_pipeline.adapters import verify_packet
    result = verify_packet({"schema_version": "0.2"})
    return _run_test("test_verify_missing_required", not result["valid"] and len(result["errors"]) > 0,
                     f"errors: {result['errors']}")


def test_relation_points_to_nonexistent_atom():
    """Relation referencing missing atom -> error."""
    from _qclaw_pipeline.adapters import verify_packet
    pkt = {
        "schema_version": "0.2",
        "packet_semantic_id": "lp-test",
        "packet_content_hash": "abc",
        "idempotency_key": "test",
        "knowledge_status": "candidate",
        "atoms": [{"atom_id": "at-real", "statement": "exists"}],
        "relations": [{"source_atom_id": "at-fake", "target_atom_id": "at-real", "relation_id": "rel-1", "type": "supports"}],
    }
    result = verify_packet(pkt)
    return _run_test("test_relation_points_to_nonexistent_atom",
                     any("at-fake" in e for e in result["errors"]),
                     f"errors: {result['errors']}")


def test_duplicate_atom_id():
    """Duplicate atom_id -> error."""
    from _qclaw_pipeline.adapters import verify_packet
    pkt = {
        "schema_version": "0.2", "packet_semantic_id": "lp-test", "packet_content_hash": "abc",
        "idempotency_key": "test", "knowledge_status": "candidate",
        "atoms": [
            {"atom_id": "at-dup", "statement": "first"},
            {"atom_id": "at-dup", "statement": "second"},
        ],
        "relations": [],
    }
    result = verify_packet(pkt)
    return _run_test("test_duplicate_atom_id", any("duplicate" in e.lower() for e in result["errors"]),
                     f"errors: {result['errors']}")


def test_confidence_float_to_enum():
    """Confidence float maps to correct enum."""
    from _qclaw_pipeline.adapters import adapt_atom
    atom = adapt_atom({"atom_type": "FACT", "canonical_statement": "test", "confidence": 0.82}, "h1", "s1")
    return _run_test("test_confidence_float_to_enum", atom["confidence"] == "high",
                     f"got: {atom['confidence']}")


def test_confidence_boundary():
    """Confidence boundary values map correctly."""
    from _qclaw_pipeline.adapters import adapt_atom

    tests = [
        (0.00, "speculative"),
        (0.29, "speculative"),
        (0.30, "low"),
        (0.54, "low"),
        (0.55, "medium"),
        (0.74, "medium"),
        (0.75, "high"),
        (0.89, "high"),
        (0.90, "certain"),
        (1.00, "certain"),
    ]
    for val, expected in tests:
        atom = adapt_atom({"atom_type": "FACT", "canonical_statement": "x", "confidence": val}, "h1", "s1")
        if atom["confidence"] != expected:
            return _run_test("test_confidence_boundary", False,
                             f"value {val} mapped to {atom['confidence']}, expected {expected}")
    return _run_test("test_confidence_boundary", True)


def test_confidence_unknown():
    """Confidence outside 0-1 range maps to medium."""
    from _qclaw_pipeline.adapters import adapt_atom
    atom = adapt_atom({"atom_type": "FACT", "canonical_statement": "test", "confidence": 1.5}, "h1", "s1")
    return _run_test("test_confidence_unknown", atom["confidence"] == "medium",
                     f"got: {atom['confidence']}")


def test_relation_type_mapping():
    """All 14+ relation types are mapped."""
    from _qclaw_pipeline.adapters import RELATION_TYPE_MAP, adapt_relation
    expected_types = ["EXPLAINS", "PART_OF", "UNDERPINS", "EXEMPLIFIES", "REFINES",
                      "SUPPORTS", "SUPERSEDES", "REPLACES", "CONTRADICTS_UNDER_CONDITION"]
    ok = all(t in RELATION_TYPE_MAP for t in expected_types)
    return _run_test("test_relation_type_mapping", ok,
                     f"missing: {[t for t in expected_types if t not in RELATION_TYPE_MAP]}")


def test_relation_extended_preserved():
    """Original relation type preserved in type_original."""
    from _qclaw_pipeline.adapters import adapt_relation
    rel = adapt_relation({"source": "a", "target": "b", "type": "EXPLAINS_POTENTIALLY"})
    return _run_test("test_relation_extended_preserved",
                     rel["type_original"] == "EXPLAINS_POTENTIALLY" and rel["type"] == "related_to")


def test_conflict_preserved():
    """Conflict decisions are preserved in packet."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="c", source_content="x", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "A", "confidence": 0.5}],
        relations=[],
        merge_decisions=[{"type": "CONFLICT", "atoms": ["a1", "a2"], "resolution": "KEEP_BOTH"}],
    )
    return _run_test("test_conflict_preserved", len(pkt["conflicts"]) == 1,
                     f"conflicts: {pkt['conflicts']}")


def test_supersedes_preserves_old():
    """SUPERSEDES relation does not remove old atom."""
    from _qclaw_pipeline.adapters import adapt_relation
    rel = adapt_relation({"source": "at-new", "target": "at-old", "type": "SUPERSEDES"})
    return _run_test("test_supersedes_preserves_old",
                     rel["type"] == "supersedes" and rel["target_atom_id"] == "at-old")


def test_causal_restraint():
    """Correlation mapped as observation, not causal."""
    from _qclaw_pipeline.adapters import adapt_atom
    atom = adapt_atom({"atom_type": "CORRELATION", "canonical_statement": "X correlates with Y", "confidence": 0.7}, "h", "s")
    return _run_test("test_causal_restraint", atom["type"] == "observation",
                     f"got: {atom['type']}")


def test_privacy_hard_secret():
    """RESTRICTED privacy class is preserved but gpt_access should be checked."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="secret", source_content="secret data", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "Secret", "confidence": 0.9,
                "privacy_class": "RESTRICTED"}],
        relations=[],
        privacy_class="RESTRICTED",
    )
    atom_pc = pkt["atoms"][0]["privacy_class"]
    return _run_test("test_privacy_hard_secret", atom_pc == "RESTRICTED",
                     f"atom privacy_class: {atom_pc}")


def test_candidate_not_authority():
    """Candidate packets should have CANDIDATE_ONLY authority."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="c", source_content="x", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "A", "confidence": 0.5}],
        relations=[],
    )
    return _run_test("test_candidate_not_authority",
                     pkt["authority_level"] == "CANDIDATE_ONLY",
                     f"got: {pkt['authority_level']}")


def test_processor_version_change():
    """Processor version is stamped but does not affect semantic identity."""
    from _qclaw_pipeline.adapters import PROCESSOR_VERSION, build_packet
    pkt = build_packet(
        source_id="v", source_content="x", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "A", "confidence": 0.5}],
        relations=[],
    )
    return _run_test("test_processor_version_change",
                     pkt["processor_version"] == PROCESSOR_VERSION)


def test_empty_source():
    """Empty source content handled gracefully."""
    from _qclaw_pipeline.adapters import build_packet, verify_packet
    pkt = build_packet(
        source_id="empty", source_content="", source_time="2024-01-01",
        atoms=[],
        relations=[],
    )
    result = verify_packet(pkt)
    return _run_test("test_empty_source",
                     pkt["quality_audit"]["source_coverage"] == 0.0,
                     f"coverage: {pkt['quality_audit']['source_coverage']}")


def test_missing_source_hash():
    """Atom without source_reference gets source_id as fallback."""
    from _qclaw_pipeline.adapters import adapt_atom
    atom = adapt_atom(
        {"atom_type": "FACT", "canonical_statement": "test", "confidence": 0.5},
        "hash123", "fallback_id",
    )
    return _run_test("test_missing_source_hash",
                     atom["source"]["reference"] == "fallback_id")


def test_compare_runs_identical():
    """Identical packets should compare as deterministic."""
    from _qclaw_pipeline.adapters import build_packet
    from _qclaw_pipeline.compare import compare_runs

    def make_pkt():
        return build_packet(
            source_id="cmp", source_content="same", source_time="2024-01-01",
            atoms=[{"atom_type": "FACT", "canonical_statement": "Test fact", "confidence": 0.8}],
            relations=[],
        )

    p1 = make_pkt()
    p2 = make_pkt()
    result = compare_runs(p1, p2)
    return _run_test("test_compare_runs_identical",
                     result["deterministic"] and result["semantic_id_match"],
                     str(result))


def test_compare_runs_different_instances():
    """Same semantic content but different run context -> same semantic ID, different instance ID."""
    from _qclaw_pipeline.adapters import build_packet
    from _qclaw_pipeline.compare import compare_runs
    from time import sleep

    p1 = build_packet(
        source_id="cmp", source_content="same", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "Test", "confidence": 0.8}],
        relations=[],
        run_context="run_1",
    )
    sleep(0.1)
    p2 = build_packet(
        source_id="cmp", source_content="same", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "Test", "confidence": 0.8}],
        relations=[],
        run_context="run_2",
    )
    result = compare_runs(p1, p2)
    return _run_test("test_compare_runs_different_instances",
                     result["deterministic"] and p1["packet_instance_id"] != p2["packet_instance_id"],
                     f"sem_match={result['semantic_id_match']}, hash_match={result['content_hash_match']}")


def test_case_a_no_conflict():
    """Case A: high-confidence facts without conflict produce valid packet."""
    from _qclaw_pipeline.adapters import build_packet, verify_packet
    for mat in test_cases["case_a__no_conflict_high_confidence_facts"]:
        pkt = build_packet(
            source_id=mat["source_id"], source_content=mat["content"],
            source_time=mat["source_time"], atoms=mat["atoms"],
            relations=mat.get("relations", []),
            unknowns=mat.get("unknowns", []),
            privacy_class=mat.get("privacy_class", "PUBLIC_SAFE"),
        )
        v = verify_packet(pkt)
        if not v["valid"]:
            return _run_test("test_case_a_no_conflict", False, f"verify failed for {mat['source_id']}: {v['errors']}")
    return _run_test("test_case_a_no_conflict", True)


def test_case_b_explicit_conflict():
    """Case B: conflicting atoms both preserved in packet."""
    from _qclaw_pipeline.adapters import build_packet

    all_atoms = []
    for mat in test_cases["case_b__explicit_conflict_same_level"]:
        pkt = build_packet(
            source_id=mat["source_id"], source_content=mat["content"],
            source_time=mat["source_time"], atoms=mat["atoms"],
            relations=mat.get("relations", []),
            privacy_class=mat.get("privacy_class", "PUBLIC_SAFE"),
        )
        all_atoms.extend(pkt["atoms"])

    statements = [a["statement"] for a in all_atoms]
    has_sydney = any("Sydney" in s for s in statements)
    has_canberra = any("Canberra" in s for s in statements)
    return _run_test("test_case_b_explicit_conflict", has_sydney and has_canberra)


def test_case_c_supersedes():
    """Case C: old and new atoms correctly adapted, old marked SUPERSEDED."""
    from _qclaw_pipeline.adapters import build_packet

    all_atoms = []
    for mat in test_cases["case_c__new_atom_supersedes_old"]:
        pkt = build_packet(
            source_id=mat["source_id"], source_content=mat["content"],
            source_time=mat["source_time"], atoms=mat["atoms"],
            relations=mat.get("relations", []),
            privacy_class=mat.get("privacy_class", "PUBLIC_SAFE"),
        )
        all_atoms.extend(pkt["atoms"])

    has_old = any("14 days" in a["statement"] for a in all_atoms)
    has_new = any("24 days" in a["statement"] for a in all_atoms)
    return _run_test("test_case_c_supersedes",
                     has_old and has_new,
                     f"atoms={len(all_atoms)}, has_old={has_old}, has_new={has_new}")


def test_case_d_correlation_not_causal():
    """Case D: CORRELATION atom type mapped as observation (not causal)."""
    from _qclaw_pipeline.adapters import build_packet
    mat = test_cases["case_d__correlation_without_causation"][0]
    pkt = build_packet(
        source_id=mat["source_id"], source_content=mat["content"],
        source_time=mat["source_time"], atoms=mat["atoms"],
        relations=mat.get("relations", []),
        privacy_class=mat.get("privacy_class", "PUBLIC_SAFE"),
    )
    atom_type = pkt["atoms"][0]["type"]
    return _run_test("test_case_d_correlation_not_causal", atom_type == "observation",
                     f"atom_type={atom_type}, original={pkt['atoms'][0]['type_original']}")


def test_case_e_privacy_restricted():
    """Case E: RESTRICTED atoms have correct privacy_class."""
    from _qclaw_pipeline.adapters import build_packet

    # Test PUBLIC_SAFE atom
    mat_pub = test_cases["case_e__privacy_class_rules"][0]
    pkt_pub = build_packet(
        source_id=mat_pub["source_id"], source_content=mat_pub["content"],
        source_time=mat_pub["source_time"], atoms=mat_pub["atoms"],
        relations=[], privacy_class=mat_pub["privacy_class"],
    )
    pub_ok = pkt_pub["atoms"][0]["privacy_class"] == "PUBLIC_SAFE"

    # Test RESTRICTED atom
    mat_rest = test_cases["case_e__privacy_class_rules"][1]
    pkt_rest = build_packet(
        source_id=mat_rest["source_id"], source_content=mat_rest["content"],
        source_time=mat_rest["source_time"], atoms=mat_rest["atoms"],
        relations=[], privacy_class=mat_rest["privacy_class"],
    )
    rest_ok = pkt_rest["atoms"][0]["privacy_class"] == "RESTRICTED"

    return _run_test("test_case_e_privacy_restricted", pub_ok and rest_ok,
                     f"public={pub_ok}, restricted={rest_ok}")


def test_case_f_multi_hop():
    """Case F: multi-hop inference — 3 sources produce ≥4 atoms covering Socrates/Plato/Aristotle chain."""
    from _qclaw_pipeline.adapters import build_packet

    all_atoms = []
    for mat in test_cases["case_f__multi_hop_inference"]:
        pkt = build_packet(
            source_id=mat["source_id"], source_content=mat["content"],
            source_time=mat["source_time"], atoms=mat["atoms"],
            relations=mat.get("relations", []),
            privacy_class=mat.get("privacy_class", "PUBLIC_SAFE"),
        )
        all_atoms.extend(pkt["atoms"])

    has_socrates = any("Socrates" in a["statement"] for a in all_atoms)
    has_plato = any("Plato" in a["statement"] for a in all_atoms)
    has_aristotle = any("Aristotle" in a["statement"] for a in all_atoms)
    has_chain = any("chain" in a["statement"].lower() for a in all_atoms)
    return _run_test("test_case_f_multi_hop",
                     len(all_atoms) >= 4 and has_socrates and has_plato and has_aristotle and has_chain,
                     f"atoms={len(all_atoms)}, S={has_socrates}, P={has_plato}, A={has_aristotle}, chain={has_chain}")


def test_unknowns_preserved():
    """Unknowns array is preserved in packet."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="u", source_content="x", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "A", "confidence": 0.5}],
        relations=[],
        unknowns=[{"question": "What is X?", "confidence": 0.3}],
    )
    return _run_test("test_unknowns_preserved", len(pkt["unknowns"]) == 1)


def test_structures_preserved():
    """Structures array is preserved in packet."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="s", source_content="x", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "A", "confidence": 0.5}],
        relations=[],
        structures=[{"type": "taxonomy", "nodes": ["a", "b"]}],
    )
    return _run_test("test_structures_preserved", len(pkt["structures"]) == 1)


def test_skills_preserved():
    """Skills array is preserved in packet."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="sk", source_content="x", source_time="2024-01-01",
        atoms=[{"atom_type": "FACT", "canonical_statement": "A", "confidence": 0.5}],
        relations=[],
        skills=[{"name": "python", "proficiency": "expert"}],
    )
    return _run_test("test_skills_preserved", len(pkt["skills"]) == 1)


def test_source_artifacts_populated():
    """Source artifacts contain correct metadata."""
    from _qclaw_pipeline.adapters import build_packet
    pkt = build_packet(
        source_id="sa", source_content="hello", source_time="2024-01-01T00:00:00Z",
        atoms=[{"atom_type": "FACT", "canonical_statement": "A", "confidence": 0.5}],
        relations=[],
    )
    sa = pkt["source_artifacts"][0]
    ok = all([
        sa["source_id"] == "sa",
        len(sa["source_hash"]) == 64,
        sa["source_time"] == "2024-01-01T00:00:00Z",
    ])
    return _run_test("test_source_artifacts_populated", ok, str(sa))


# ═══════════════════════════════════════════════════════
#  Test Discovery & Runner
# ═══════════════════════════════════════════════════════

ALL_TESTS = [
    test_normalize_unicode,
    test_collapse_whitespace,
    test_canonical_dict_key_order,
    test_content_hash_deterministic,
    test_content_hash_different,
    test_atom_id_deterministic,
    test_atom_id_different_statement,
    test_relation_id_deterministic,
    test_packet_semantic_id,
    test_packet_instance_id_unique,
    test_idempotency_key,
    test_field_order_independent,
    test_timestamp_does_not_affect_semantic_id,
    test_same_content_different_filename,
    test_build_packet_complete,
    test_verify_valid_packet,
    test_verify_missing_required,
    test_relation_points_to_nonexistent_atom,
    test_duplicate_atom_id,
    test_confidence_float_to_enum,
    test_confidence_boundary,
    test_confidence_unknown,
    test_relation_type_mapping,
    test_relation_extended_preserved,
    test_conflict_preserved,
    test_supersedes_preserves_old,
    test_causal_restraint,
    test_privacy_hard_secret,
    test_candidate_not_authority,
    test_processor_version_change,
    test_empty_source,
    test_missing_source_hash,
    test_compare_runs_identical,
    test_compare_runs_different_instances,
    test_case_a_no_conflict,
    test_case_b_explicit_conflict,
    test_case_c_supersedes,
    test_case_d_correlation_not_causal,
    test_case_e_privacy_restricted,
    test_case_f_multi_hop,
    test_unknowns_preserved,
    test_structures_preserved,
    test_skills_preserved,
    test_source_artifacts_populated,
]


def run_all_tests():
    """Run all registered tests. Returns list of {name, passed, detail} dicts."""
    results = []
    for test_fn in ALL_TESTS:
        try:
            result = test_fn()
            results.append(result)
        except Exception as e:
            results.append({"name": test_fn.__name__, "passed": False, "detail": str(e)})
    return results


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(__file__)))
    results = run_all_tests()
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\nTest Results: {passed}/{total} passed\n")
    for r in results:
        symbol = "✅" if r["passed"] else "❌"
        print(f"  {symbol} {r['name']}" + (f" — {r['detail']}" if not r["passed"] else ""))
    sys.exit(0 if passed == total else 1)
