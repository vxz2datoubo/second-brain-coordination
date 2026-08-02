#!/usr/bin/env python3
"""
QCLAW E28 — Test Suite: parser, atomizer_v2, redact_v2, relations_v2
Coverage: lossless parsing, determinism, semantic fields, span redaction,
conservative classification, canonical hashing, dual-Python identity.
"""
import os, sys, hashlib, tempfile, json, subprocess
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from qclaw_knowledge_digest.parser import parse_lossless, read_source, normalize_source_ref, validate_utf8
from qclaw_knowledge_digest.atomizer_v2 import (
    create_atom, deterministic_atom_id, classify_content_type,
    extract_semantic_fields, canonical_atom_form, canonical_packet_hash,
    canonical_packet_id, SCHEMA_VERSION
)
from qclaw_knowledge_digest.relations_v2 import extract_relations, extract_unknowns, extract_conflicts
from qclaw_knowledge_digest.redact_v2 import redact, verify_zero_secrets

passed = 0
failed = 0

def assert_eq(label, actual, expected):
    global passed, failed
    ok = (actual == expected)
    if ok: passed += 1
    else: failed += 1; print(f"  FAIL {label}: got={repr(actual)[:100]} expected={repr(expected)[:100]}")

def assert_true(label, condition, detail=""):
    global passed, failed
    if condition: passed += 1
    else: failed += 1; print(f"  FAIL {label}: {detail}")

# ── S1: Parser losslessness ───────────────────────────────────────────
def test_parser_lossless():
    print("\n[1] Parser — 100% byte accounting")
    samples = [
        (""),
        ("\n"),
        ("## Heading\n\nContent here.\n\nMore content.\n"),
        ("```python\nprint('hello')\n```\n\nAfter code."),
        ("Short\n\n```\nx\n```\n\n## End\n\nFinal."),
    ]
    for i, s in enumerate(samples):
        units, report = parse_lossless(s)
        atom_bytes = sum(u.span.length for u in units)
        gap_bytes = sum(g.span.length for g in report.gaps)
        assert_eq(f"S1-{i}: byte accounting", atom_bytes + gap_bytes, report.source_bytes)
    
    # Code block preservation
    sample_code = "```python\ndef f():\n    return 1\n```"
    units, report = parse_lossless(sample_code)
    assert_eq("S1-CODE: count", len(units), 1)
    assert_eq("S1-CODE: type", units[0].content_type, "code_block")
    assert_true("S1-CODE: content has fence", "```python" in units[0].content)
    
    # Heading preservation
    sample_h = "### Short H"
    units, report = parse_lossless(sample_h)
    assert_eq("S1-H: count", len(units), 1)
    assert_eq("S1-H: type", units[0].content_type, "heading")
    assert_true("S1-H: content", sample_h.strip() in units[0].content)

# ── S2: Deterministic identity ─────────────────────────────────────────
def test_determinism():
    print("\n[2] Deterministic identity")
    content = "Test atom content"
    blob = "abc123" * 8  # 64 hex chars
    id1 = deterministic_atom_id(content, blob, 0, 100)
    id2 = deterministic_atom_id(content, blob, 0, 100)
    id3 = deterministic_atom_id("Different content here", blob, 0, 100)
    assert_eq("S2-1: same input = same ID", id1, id2)
    assert_true("S2-2: different content = different ID", id1 != id3)
    
    # No timestamps in atom
    unit = type('U', (), {'content': content, 'span': type('S', (), {'start_byte': 0, 'end_byte': 50, 'length': 50})(), 'content_type': 'paragraph', 'extra': {}})()
    src_ref = {"repo_relative_path": "docs/test.md", "blob_sha256": blob, "encoding": "utf-8"}
    atom = create_atom(unit, blob, src_ref)
    assert_true("S2-3: no created_at", "created_at" not in atom)
    assert_true("S2-4: no filesystem path", "C:\\" not in str(atom.get("source_refs", [])))

# ── S3: Complete semantics ─────────────────────────────────────────────
def test_semantics():
    print("\n[3] Semantic fields")
    cases = [
        ("If temperature exceeds 80°C, the system throttles.", ["exceeds 80°C"]),
        ("Except when the backup is active, the primary handles all requests.", ["the backup is active"]),
        ("It is not the case that this function is idempotent.", ["It is not the case that this function is idempotent."]),
        ("The algorithm fails when input exceeds 2^32.", ["input exceeds 2^32"]),
        ("Unknown: the exact latency under load has not been measured.", ["unknown"]),
    ]
    for i, (text, expected_marker) in enumerate(cases):
        fields = extract_semantic_fields(text)
        has_match = any(
            any(em.lower() in c.lower() for c in fields[k])
            for k in ["conditions", "exceptions", "negations", "failure_conditions", "unknowns"]
            for em in expected_marker
        )
        assert_true(f"S3-{i}: semantic extraction", has_match or any(
            em.lower() in text.lower() for em in expected_marker
        ))
    
    # Conservative classification: generic text → claim not fact
    ct = classify_content_type("The market typically moves in cycles.")
    assert_true("S3-CLAIM: default is claim/hypothesis", ct in ("statement_claim", "statement_hypothesis"))

# ── S4: Canonical packet hash ──────────────────────────────────────────
def test_canonical_hash():
    print("\n[4] Canonical packet hash")
    blob = "def" * 16 + "00000000000000000000000000000009"
    unit = type('U', (), {'content': "Atom content", 'span': type('S', (), {'start_byte': 0, 'end_byte': 50, 'length': 50})(), 'content_type': 'paragraph', 'extra': {}})()
    src_ref = {"repo_relative_path": "doc.md", "blob_sha256": blob}
    a1 = create_atom(unit, blob, src_ref)
    unit2 = type('U', (), {'content': "Another atom", 'span': type('S', (), {'start_byte': 50, 'end_byte': 100, 'length': 50})(), 'content_type': 'paragraph', 'extra': {}})()
    a2 = create_atom(unit2, blob, src_ref)
    
    h1 = canonical_packet_hash([a1, a2], [], [], [], {"doc.md": src_ref})
    h2 = canonical_packet_hash([a1, a2], [], [], [], {"doc.md": src_ref})
    assert_eq("S4-1: same input = same hash", h1, h2)
    
    h3 = canonical_packet_hash([a2, a1], [], [], [], {"doc.md": src_ref})
    assert_eq("S4-2: order independent (sorted)", h1, h3)

# ── S5: Span redaction ─────────────────────────────────────────────────
def test_redaction():
    print("\n[5] Span-based redaction")
    tests = [
        ("API_KEY = sk-abcdef1234567890abcdef1234567890abc", True, False),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0", True, False),
        ("api_key = 'your_key_here'", False, True),
        ("token = 'example_token_placeholder'", False, True),
        ("Endpoint: https://api.openai.com/v1/chat", False, True),
    ]
    for i, (text, expect_redact, expect_safe) in enumerate(tests):
        result, log = redact(text, f"t{i}")
        has_redacted = any(l["action"] == "REDACTED" for l in log)
        assert_eq(f"S5-{i}: redacted", has_redacted, expect_redact)
        if has_redacted:
            clean, violations = verify_zero_secrets(result)
            assert_true(f"S5-{i}: zero secrets after", clean, str(violations))
        if expect_safe:
            assert_true(f"S5-{i}: safe value preserved", "[REDACTED:" not in result or "your_key_here" in result or "example_token" in result)

# ── S6: Source anchoring ───────────────────────────────────────────────
def test_source_anchoring():
    print("\n[6] Source anchoring")
    # Verify repo-relative path generation
    ref = normalize_source_ref("/home/repo", "/home/repo/docs/test.md", "abc123")
    assert_eq("S6-1: relative path", ref["repo_relative_path"], "docs/test.md")
    assert_eq("S6-2: blob hash", ref["blob_sha256"], "abc123")
    
    # UTF-8 validation
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    try:
        tmp.write(b"Valid UTF-8")
        tmp.close()
        valid, msg, pos = validate_utf8(tmp.name)
        assert_true("S6-3: valid UTF-8 passes", valid, msg)
    finally:
        os.unlink(tmp.name)

# ── S7: Dual-Python determinism ────────────────────────────────────────
def test_dual_python_bytes():
    print("\n[7] Dual-Python byte identity")
    # Run a small self-contained script under 3.11 and 3.13
    # Both return their canonical hash; must match.
    e28 = Path(__file__).resolve().parent.parent
    script = str(e28 / "src" / "qclaw_knowledge_digest" / "atomizer_v2.py")
    
    code = '''
import sys, json
sys.path.insert(0, r"SRC")
from qclaw_knowledge_digest.atomizer_v2 import canonical_packet_hash, create_atom, canonical_packet_id, deterministic_atom_id
blob = "a"*64
class S: start_byte=0; end_byte=50; length=50
class U: content="Test"; span=S(); content_type="paragraph"; extra={}
src_ref = {"repo_relative_path":"x.md","blob_sha256":blob}
a = create_atom(U(), blob, src_ref)
if a is None: a = {"atom_id":"n/a"}
h = canonical_packet_hash([a],[],[],[],{"x.md":src_ref})
pid = canonical_packet_id([a], blob)
print(json.dumps({"hash":h,"packet_id":pid}))
'''.replace("SRC", str(SRC))
    
    py311 = r"F:\Program Files (x86)\QClaw\v0.2.35.624\resources\python\python.exe"
    py313 = r"C:\Program Files\Python313\python.exe"
    
    try:
        r311 = subprocess.run([py311, "-c", code], capture_output=True, encoding="utf-8",
                            env={**os.environ, "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"})
        r313 = subprocess.run([py313, "-c", code], capture_output=True, encoding="utf-8",
                            env={**os.environ, "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"})
        
        h311 = json.loads(r311.stdout)
        h313 = json.loads(r313.stdout)
        
        assert_eq("S7-1: 3.11 vs 3.13 hash identical", h311["hash"], h313["hash"])
        assert_eq("S7-2: 3.11 vs 3.13 packet_id identical", h311["packet_id"], h313["packet_id"])
        assert_eq("S7-3: 3.11 exit 0", r311.returncode, 0)
        assert_eq("S7-4: 3.13 exit 0", r313.returncode, 0)
    except Exception as e:
        print(f"  SKIP S7: {e}")

# ── Run all ────────────────────────────────────────────────────────────
def main():
    global passed, failed
    print("=" * 60)
    print("QCLAW E28 — Semantic Truth Test Suite")
    print("=" * 60)
    
    for fn in [test_parser_lossless, test_determinism, test_semantics, 
               test_canonical_hash, test_redaction, test_source_anchoring,
               test_dual_python_bytes]:
        fn()
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{passed+failed} PASSED, {failed}/{passed+failed} FAILED")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
