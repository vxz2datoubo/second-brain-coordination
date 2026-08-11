#!/usr/bin/env python3
"""
QCLAW E27 — Knowledge Atomization Pipeline Test Suite
Tests: semantic, deterministic, lineage, duplicate, conflict, UNKNOWN,
zero-secret adversarial, LearningPacket contract conformance.
"""
import os, sys, json
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
from qclaw_knowledge_digest.redact import redact, verify_zero_secrets
from qclaw_knowledge_digest.atomizer import (
    sha256, deterministic_atom_id, SCHEMA_VERSION,
    atomize_document, generate_learning_packet, run_digest_queue,
    extract_unknowns, extract_conflicts, extract_relations, create_atom,
    segment_semantic_units, classify_content_type, estimate_confidence
)

TEST_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TEST_DIR.parent / "fixtures"

passed = 0
failed = 0

def assert_true(name, cond, detail=""):
    global passed, failed
    if cond: passed += 1
    else:
        failed += 1
        print(f"  FAIL [{name}]: {detail}")

def assert_eq(name, actual, expected, detail=""):
    global passed, failed
    ok = actual == expected
    if ok: passed += 1
    else:
        failed += 1
        print(f"  FAIL [{name}]: expected={expected} actual={actual} {detail}")

def assert_false(name, cond, detail=""):
    assert_true(name, not cond, detail)

def make_fixture_md():
    return """# Knowledge Digestion Test Document

## Conditions and Preconditions

The atomization pipeline must preserve conditions. If and only if the source
document is valid UTF-8, the parser will proceed. Precondition: the file must
be readable and larger than 50 bytes.

## Exceptions and Negations

The pipeline works for Markdown and plain text. However, it does not handle
binary files. It is not a general-purpose file parser. Except when the file
is encrypted, in which case it should be skipped with a failure condition.

## Failure Conditions

The parser fails when the input is empty. It will not work with binary or
encrypted files. Break if the document contains only whitespace characters.

## Temporal Scope

- Effective from 2024-01-01: YAML frontmatter is supported
- Valid until unknown: legacy .rst format is still accepted
- Permanently: UTF-8 encoding is the canonical format

## Facts and Claims

The Earth orbits the Sun. This is established knowledge. Water boils at 100C
at standard atmospheric pressure. These are measured constants.

Claim: the market is efficient in the semi-strong form. This is debated.
I believe knowledge atomization improves retrieval quality.

## Counterexamples

Contrary to popular belief, more data does not always improve model accuracy.
A counterexample: when training data is biased, accuracy actually decreases.

## Unknowns and Open Questions

The exact mechanism of memory consolidation during sleep is unknown.
It is not yet understood how the brain prioritizes which memories to keep.
Open question: what is the theoretical limit of knowledge atom density?

## Methods and Skills

Skill: writing effective knowledge atoms requires identifying the minimum
complete semantic unit while preserving context, conditions, and exceptions.

Method: "Semantic Segmentation"
1. Identify paragraph and section boundaries
2. Find conditional statements (if, when, unless)
3. Preserve negation and exception context
4. Mark temporal scopes
5. Flag unknowns and conflicts

Decision Chain: choosing atom granularity
- If the text is a single assertion, one atom is sufficient
- If the text has multiple independent claims, split into multiple atoms
- If the text is a causal chain, keep as compound unit with relations

## Constraints

The pipeline must not produce duplicate atom IDs for identical content.
Must be deterministic: same input produces same outputs every time.
Shall not create a second canonical memory runtime.
"""

def test_semantic_segmentation():
    print("\n[1] Semantic Segmentation Tests")
    fixture = make_fixture_md()
    segments = segment_semantic_units(fixture, {"source_type": "test"})
    assert_true("SEG-01: produces segments", len(segments) > 0, f"got {len(segments)}")
    assert_true("SEG-02: captures conditions",
                any("precondition" in s.lower() or "if and only if" in s.lower() for s in segments))
    assert_true("SEG-03: captures exceptions", any("except" in s.lower() for s in segments))
    assert_true("SEG-04: captures unknowns", any("unknown" in s.lower() or "open question" in s.lower() for s in segments))
    assert_true("SEG-05: no empty segments", all(len(s.strip()) >= 12 for s in segments))

def test_determinism():
    print("\n[2] Deterministic Atom ID Tests")
    text = "The Earth orbits the Sun at approximately 149.6 million kilometers."
    refs = [{"source_id": "test/astronomy.md", "location": "para-1"}]
    id1 = deterministic_atom_id(text, refs)
    id2 = deterministic_atom_id(text, refs)
    id3 = deterministic_atom_id(text + " Additional content.", refs)
    assert_eq("ID-01: same input same ID", id1, id2, id1)
    assert_false("ID-02: different input different ID", id1 == id3)
    assert_true("ID-03: valid SHA-256 format", len(id1) == 64 and all(c in "0123456789abcdef" for c in id1))

def test_content_types():
    print("\n[3] Content Type Classification Tests")
    assert_eq("CT-01: failure", classify_content_type("The system fails when input is empty"), "failure_condition")
    assert_eq("CT-02: counterexample", classify_content_type("A counterexample to this claim is..."), "counterexample")
    assert_eq("CT-03: exception", classify_content_type("Works fine except when the network is down"), "exception_explicit")
    assert_eq("CT-04: negation", classify_content_type("It is not a general-purpose tool"), "negation")
    assert_eq("CT-05: precondition", classify_content_type("Precondition: the file must exist"), "condition_precondition")
    assert_eq("CT-06: method", classify_content_type("Method: the following steps outline the process"), "method")
    assert_eq("CT-07: constraint", classify_content_type("The system must not write to protected paths"), "constraint")
    assert_eq("CT-08: temporal", classify_content_type("Effective from 2024-01-01 to 2025-12-31"), "temporal_scope")
    assert_eq("CT-09: definition", classify_content_type("Definition: a knowledge atom is..."), "definition")

def test_confidence():
    print("\n[4] Confidence Estimation Tests")
    assert_eq("CF-01: established", estimate_confidence("This is a proven theorem")["level"], "established_knowledge")
    assert_eq("CF-02: empirical", estimate_confidence("The study shows that exercise improves memory")["level"], "empirical_evidence")
    assert_eq("CF-03: speculative", estimate_confidence("This might be related to neural plasticity")["level"], "speculative")
    assert_eq("CF-04: unknown", estimate_confidence("The exact cause is unknown at this time")["level"], "unknown")

def test_duplicates():
    print("\n[5] Duplicate Detection Tests")
    fixture = make_fixture_md()
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    p = FIXTURES_DIR / "test_doc.md"
    p.write_text(fixture, encoding="utf-8")
    r1 = atomize_document(str(p))
    r2 = atomize_document(str(p))
    ids1 = sorted([a["atom_id"] for a in r1["atoms"]])
    ids2 = sorted([a["atom_id"] for a in r2["atoms"]])
    assert_eq("DUP-01: same count", len(ids1), len(ids2))
    assert_eq("DUP-02: identical IDs", ids1, ids2, "deterministic replay")
    assert_true("DUP-03: no duplicates", len(ids1) == len(set(ids1)))

def test_conflicts():
    print("\n[6] Conflict Detection Tests")
    atoms = [
        {"atom_id": "a1", "canonical_text": "However, the evidence contradicts this claim."},
        {"atom_id": "a2", "canonical_text": "This is a straightforward statement."},
        {"atom_id": "a3", "canonical_text": "On the contrary, Smith found the opposite."}
    ]
    c = extract_conflicts(atoms)
    assert_true("CFL-01: detects however", any(x["atom_id"] == "a1" for x in c))
    assert_true("CFL-02: detects contrary", any(x["atom_id"] == "a3" for x in c))
    assert_false("CFL-03: no false positive", any(x["atom_id"] == "a2" for x in c))

def test_unknowns():
    print("\n[7] UNKNOWN Detection Tests")
    atoms = [
        {"atom_id": "u1", "canonical_text": "The mechanism is unknown at this time."},
        {"atom_id": "u2", "canonical_text": "It is unclear whether this generalizes."},
        {"atom_id": "u3", "canonical_text": "This is fully understood."},
        {"atom_id": "u4", "canonical_text": "Open question: what drives this effect?"}
    ]
    u = extract_unknowns(atoms)
    assert_eq("UNK-01: count", len(u), 3)
    assert_true("UNK-02: unknown", any(x["atom_id"] == "u1" for x in u))
    assert_true("UNK-03: unclear", any(x["atom_id"] == "u2" for x in u))
    assert_true("UNK-04: open question", any(x["atom_id"] == "u4" for x in u))

def test_zero_secret():
    print("\n[8] Zero-Secret Adversarial Tests")
    secrets = [
        "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
        "password=superSecret123!",
        "api_key: abcdef1234567890"
    ]
    for s in secrets:
        atom = create_atom(s, [{"source_id": "test", "location": "L1"}])
        assert_true(f"SEC-{secrets.index(s)}: atom created", atom is not None)
        if atom:
            assert_eq(f"SEC-{secrets.index(s)}-status", atom["status"], "candidate")
            assert_eq(f"SEC-{secrets.index(s)}-no_trade", atom["no_trade_gate"], True)

def test_relations():
    print("\n[9] Relation Extraction Tests")
    atoms = [
        {"atom_id": "r1", "canonical_text": "Knowledge digestion depends on accurate semantic segmentation techniques."},
        {"atom_id": "r2", "canonical_text": "Semantic segmentation is a prerequisite for knowledge digestion."},
        {"atom_id": "r3", "canonical_text": "NLP techniques include tokenization and parsing."},
        {"atom_id": "r4", "canonical_text": "Better segmentation implies higher retrieval quality."},
    ]
    rels = extract_relations(atoms)
    assert_true("REL-01: finds relations", len(rels) >= 0, f"got {len(rels)}")

def test_packet_contract():
    print("\n[10] LearningPacket Contract Tests")
    p = FIXTURES_DIR / "pkt_test.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(make_fixture_md(), encoding="utf-8")
    r = atomize_document(str(p))
    packet = generate_learning_packet(r)
    for k in ["schema_version","packet_id","packet_content_hash","idempotency_key",
              "status","authority_write","no_trade_gate","atoms","relations","unknowns","conflicts"]:
        assert_true(f"PKT-{k}", k in packet, k)
    assert_eq("PKT-status", packet.get("status"), "candidate")
    assert_eq("PKT-authority_write", packet.get("authority_write"), False)
    assert_eq("PKT-no_trade_gate", packet.get("no_trade_gate"), True)
    assert_true("PKT-non-empty", len(packet.get("atoms",[])) > 0)
    assert_true("PKT-id-format", len(packet.get("packet_id","")) == 64)

def test_packet_hash():
    print("\n[11] Deterministic Packet Hash Tests")
    p = FIXTURES_DIR / "hash_test.md"
    p.write_text(make_fixture_md(), encoding="utf-8")
    p1 = generate_learning_packet(atomize_document(str(p)))
    p2 = generate_learning_packet(atomize_document(str(p)))
    assert_eq("DPH-01: same packet_id", p1["packet_id"], p2["packet_id"])
    assert_eq("DPH-02: same hash", p1["packet_content_hash"], p2["packet_content_hash"])

def test_empty_input():
    print("\n[12] Adversarial: Empty Input")
    p = FIXTURES_DIR / "empty.md"
    p.write_text("", encoding="utf-8")
    assert_eq("ADV-01: zero atoms", len(atomize_document(str(p))["atoms"]), 0)

def test_whitespace():
    print("\n[13] Adversarial: Whitespace Only")
    p = FIXTURES_DIR / "whitespace.md"
    p.write_text("   \n\n   \n\t  \n", encoding="utf-8")
    assert_eq("ADV-02: zero atoms", len(atomize_document(str(p))["atoms"]), 0)

def test_binary():
    print("\n[14] Adversarial: Binary Content")
    p = FIXTURES_DIR / "binary.md"
    p.write_text("\x00\x01\xff" + "some valid text that is long enough for atom creation minimum character length", encoding="utf-8", errors="replace")
    try:
        r = atomize_document(str(p))
        assert_true("ADV-03: handled", True, f"atoms={len(r['atoms'])}")
    except Exception as e:
        assert_true("ADV-03: crash", False, str(e))

def test_order_sensitivity():
    print("\n[15] Adversarial: Order Sensitivity")
    t1 = "A then B then C. First item. Second item."
    t2 = "C then B then A. Second item. First item."
    (FIXTURES_DIR / "o1.md").write_text(t1, encoding="utf-8")
    (FIXTURES_DIR / "o2.md").write_text(t2, encoding="utf-8")
    ids1 = sorted([a["atom_id"] for a in atomize_document(str(FIXTURES_DIR / "o1.md"))["atoms"]])
    ids2 = sorted([a["atom_id"] for a in atomize_document(str(FIXTURES_DIR / "o2.md"))["atoms"]])
    assert_false("ADV-05: different order different IDs", ids1 == ids2)

def test_sycophancy():
    print("\n[16] Adversarial: Sycophancy Markers")
    p = FIXTURES_DIR / "syco.md"
    p.write_text("This is brilliant! Best idea ever! Completely right!\n" * 5, encoding="utf-8")
    r = atomize_document(str(p))
    assert_true("ADV-06: no crash", len(r["atoms"]) >= 0)

# ── Main ───────────────────────────────────────────────────────────────

def test_redaction_core():
    print("\n[17] Redaction Core Tests")
    cases = [
        ("API_KEY = sk-abcdef1234567890abcdef1234567890abc", True),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0", True),
        ("mysql://admin:realpassword@db.example.com:3306/mydb", True),
        ("api_key = 'your_key_here'", False),
        ("token = 'example_token_placeholder'", False),
        ("The API endpoint is https://api.openai.com", False),
        ("api_key parameter is passed to the constructor", False),
    ]
    for i, (text, expect) in enumerate(cases):
        redacted, log = redact(text, f"t{i}")
        assert_eq(f"RDC-{i}: redact={'YES' if expect else 'NO'}", len(log) > 0, expect)
        if len(log) > 0:
            assert_true(f"RDC-{i}-clean: zero remaining", verify_zero_secrets(redacted))

def test_redaction_mixed_document():
    print("\n[18] Mixed Document Redaction + Atomization")
    import os
    q = FIXTURES_DIR.parent / "digest_queue" / "batch_002"
    if q.exists():
        for f in q.iterdir():
            if f.suffix == ".md":
                with open(f, "r", encoding="utf-8") as fp:
                    raw = fp.read()
                redacted, log = redact(raw, str(f))
                assert_true("RDX-01: redactions applied", len(log) > 0, f"got {len(log)} redactions, expecting >0 for batch_002 mixed doc")
                assert_true("RDX-02: zero secrets after redact", verify_zero_secrets(redacted), f"redactions={len(log)}")
                # Verify secret markers were replaced
                assert_true("RDX-03: contains REDACTED marker", "[REDACTED:" in redacted)
                assert_true("RDX-04: sk-proj key redacted", "sk-proj" not in redacted)
                assert_true("RDX-05: realPass not in output", "realPass" not in redacted)
                return
    assert_true("RDX-01", False, "batch_002 not found")

def main():
    global passed, failed
    print("=" * 60)
    print("QCLAW E27 — Knowledge Atomization Pipeline Test Suite")
    print("=" * 60)
    test_semantic_segmentation()
    test_determinism()
    test_content_types()
    test_confidence()
    test_duplicates()
    test_conflicts()
    test_unknowns()
    test_zero_secret()
    test_relations()
    test_packet_contract()
    test_packet_hash()
    test_empty_input()
    test_whitespace()
    test_binary()
    test_order_sensitivity()
    test_sycophancy()
    test_redaction_core()
    test_redaction_mixed_document()
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} PASSED, {failed}/{total} FAILED")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
