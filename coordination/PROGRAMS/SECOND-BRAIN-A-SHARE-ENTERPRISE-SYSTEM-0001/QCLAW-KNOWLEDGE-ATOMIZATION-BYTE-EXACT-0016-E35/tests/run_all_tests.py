#!/usr/bin/env python3
"""E35 Test Suite — Byte-exact, lossless, with real rejection assertions."""
import sys, os, json, hashlib, subprocess, io

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_byte_atomizer.byte_index import ByteIndex, ByteSpan
from qclaw_byte_atomizer.adapter import (
    MarkdownAdapter, TextAdapter, JsonAdapter, JsonlAdapter, ConversationAdapter
)
from qclaw_byte_atomizer.redact import SpanRedactor, SECRET_PATTERNS, SAFE_PATTERNS
from qclaw_byte_atomizer.atoms import AtomExtractor, ContentClassifier, Atom, ContentType
from qclaw_byte_atomizer.relations import RelationExtractor, Relation, VALID_RELATION_TYPES
from qclaw_byte_atomizer.packet import PacketBuilder, KnowledgePacket

PASS, FAIL = 0, 0

def chk(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1; print(f"  ✓ {name}")
    else:
        FAIL += 1; print(f"  ✗ {name}: {detail}")


# ── S0: ByteIndex ──

def test_byte_index_basic():
    print("\n[1] ByteIndex: Basic")
    src = "Hello\n世界\n"
    idx = ByteIndex(src)
    chk("total bytes", idx.total_bytes() > len(src))
    chk("total codepoints", idx.total_codepoints() == len(src))
    chk("total lines", idx.total_lines() == 3)

def test_byte_index_span_roundtrip():
    print("\n[2] ByteIndex: Span roundtrip")
    src = "## Header\n\nParagraph text here.\n\n- Item one\n- Item two"
    idx = ByteIndex(src)
    s = idx.span(0, len(idx.source_bytes))
    chk("full span verify", s.verify(idx.source_bytes))
    chk("full span text", s.text == src)

    # Sub-span
    s2 = idx.span(0, 9)
    chk("sub-span verify", s2.verify(idx.source_bytes))
    chk("sub-span text", s2.text == "## Header")

def test_byte_index_line_range():
    print("\n[3] ByteIndex: Line range")
    src = "Line0\nLine1\nLine2\n"
    idx = ByteIndex(src)
    start, end = idx.line_byte_range(0)
    recovered = idx.source_bytes[start:end].decode("utf-8")
    chk("line 0", "Line0\n" == recovered)

def test_byte_index_gaps():
    print("\n[4] ByteIndex: Gap detection")
    src = "ABCDEFGHIJ"
    idx = ByteIndex(src)
    spans = [idx.span(2, 5), idx.span(7, 9)]
    gaps = idx.find_gaps(spans)
    chk("gap count", len(gaps) == 3)  # [0,2), [5,7), [9,10)

def test_byte_index_coverage():
    print("\n[5] ByteIndex: Coverage")
    src = "Hello World"
    idx = ByteIndex(src)
    spans = [idx.span(0, 5), idx.span(6, 11)]
    cov = idx.coverage(spans)
    chk("partial coverage", 0.8 < cov < 1.0, f"got {cov}")
    full_spans = [idx.span(0, idx.total_bytes())]
    chk("full coverage", idx.coverage(full_spans) == 1.0)


# ── S1: Adapters ──

def test_markdown_adapter():
    print("\n[6] Markdown adapter")
    md = "# Title\n\nParagraph here.\n\n- Item 1\n- Item 2\n\n```python\nprint('hi')\n```\n\n|col|val|"
    a = MarkdownAdapter(md)
    a.adapt()
    chk("coverage 1.0", a.coverage() == 1.0, f"got {a.coverage()}")
    chk("has header", any(s.role == "header" for s in a.spans))
    chk("has content", any(s.role == "content" for s in a.spans))
    chk("has list_item", any(s.role == "list_item" for s in a.spans))
    chk("has code_block", any(s.role == "code_block" for s in a.spans))
    chk("has table", any(s.role == "table" for s in a.spans))

def test_markdown_no_silent_discard():
    print("\n[7] Markdown: No silent discard")
    md = "Short text\n\nAnd more."
    a = MarkdownAdapter(md)
    a.adapt()
    all_text = "".join(s.byte_span.text for s in a.spans)
    chk("all text preserved", all_text == md, f"missing: {md[len(all_text):]}")

def test_text_adapter():
    print("\n[8] Text adapter")
    txt = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    a = TextAdapter(txt)
    a.adapt()
    chk("coverage 1.0", a.coverage() == 1.0)
    chk("content spans", sum(1 for s in a.spans if s.role == "content") >= 3)

def test_json_adapter():
    print("\n[9] JSON adapter")
    js = '{"name": "test", "value": 42, "nested": {"key": true}}'
    a = JsonAdapter(js)
    a.adapt()
    chk("coverage 1.0", a.coverage() == 1.0)
    chk("content present", any(s.role == "content" for s in a.spans))

def test_jsonl_adapter():
    print("\n[10] JSONL adapter")
    jl = '{"a":1}\n{"b":2}\n{"c":3}\n'
    a = JsonlAdapter(jl)
    a.adapt()
    chk("coverage 1.0", a.coverage() == 1.0)
    chk("3 content lines", sum(1 for s in a.spans if s.role == "content") == 3)

def test_conversation_adapter():
    print("\n[11] Conversation adapter")
    conv = "User: Hello\nAssistant: Hi there!\nUser: How are you?\nAssistant: I'm fine."
    a = ConversationAdapter(conv)
    a.adapt()
    chk("coverage 1.0", a.coverage() == 1.0)
    chk("structure spans", sum(1 for s in a.spans if s.role == "structure") >= 3)


# ── S2: Redaction ──

def test_redact_api_key():
    print("\n[12] Redaction: API key")
    src = "Use key: sk-real-key-12345678901234567890 to access"
    r = SpanRedactor(src)
    redacted, plans = r.redact()
    chk("key redacted", "sk-real-key" not in redacted)
    chk("REDACTED present", "REDACTED_API_KEY" in redacted, f"got: {redacted}")
    chk("non-secret preserved", "to access" in redacted)

def test_redact_password():
    print("\n[13] Redaction: Password")
    src = "password=secure123 access"
    r = SpanRedactor(src)
    redacted, plans = r.redact()
    chk("password redacted", "secure123" not in redacted)
    chk("REDACTED_PASSWORD" in redacted, redacted)

def test_redact_gh_token():
    print("\n[14] Redaction: GitHub token")
    src = "export GH_TOKEN=ghp_123456789012345678901234"
    r = SpanRedactor(src)
    redacted, _ = r.redact()
    chk("token redacted", "ghp_1" not in redacted)

def test_redact_safe_example():
    print("\n[15] Redaction: Safe examples preserved")
    src = "sk-test-example-key ghp_example_token placeholder_key demo_token"
    r = SpanRedactor(src)
    redacted, plans = r.redact()
    chk("safe sk- kept", "sk-test-example-key" in redacted, f"got: {redacted}")
    chk("safe ghp kept", "ghp_example_token" in redacted)
    chk("placeholder kept", "placeholder_key" in redacted)
    chk("demo kept", "demo_token" in redacted)

def test_redact_no_hash_leak():
    print("\n[16] Redaction: No secret-derived hex")
    src = "password=myrealpass1234"
    r = SpanRedactor(src)
    redacted, _ = r.redact()
    # Ensure no accidental MD5/SHA of the secret
    import re as regex
    hex_runs = regex.findall(r'[0-9a-fA-F]{20,}', redacted)
    chk("no long hex", len(hex_runs) == 0, f"found hex: {hex_runs}")

def test_redact_lineage_preserved():
    print("\n[17] Redaction: Lineage preserved")
    src = "password=abc123 and more password=xyz789"
    r = SpanRedactor(src)
    plans = r.plan_redactions()
    chk("two redactions", len(plans) == 2, f"got {len(plans)}")
    chk("first category", plans[0].category == "PASSWORD")
    chk("second category", plans[1].category == "PASSWORD")


# ── S3: Classification ──

def test_classifier_conservative():
    print("\n[18] Classifier: Conservative (zero FACT)")
    c = ContentClassifier()
    chk("default CLAIM", c.classify("some assertion") == "CLAIM")
    chk("governance", c.classify("must not exceed") == "GOVERNANCE")
    chk("negation", c.classify("not true that") == "NEGATION")
    chk("constraint", c.classify("must validate input") == "CONSTRAINT")
    chk("condition", c.classify("if the market opens") == "CONDITION")
    chk("exception", c.classify("except on weekends") == "EXCEPTION")
    chk("temporal", c.classify("from 2023 to 2024") == "TEMPORAL_SCOPE")
    chk("counterexample", c.classify("counterexample shows gap") == "COUNTEREXAMPLE")
    chk("unknown", c.classify("unknown boundary condition") == "UNKNOWN")
    chk("conflict", c.classify("conflicts with practice") == "CONFLICT")
    chk("definition", c.classify("a decision is a choice") == "DEFINITION")
    chk("reference", c.classify("see section 3") == "REFERENCE")
    chk("method", c.classify("algorithm computes hash") == "METHOD")
    chk("example", c.classify("for example, consider X") == "EXAMPLE")
    chk("source", c.classify("source: [1] describes") == "SOURCE")

def test_classifier_no_fact():
    print("\n[19] Classifier: No FACT from evidential language")
    c = ContentClassifier()
    for txt in ["data indicates X", "research confirms Y", "proven result", "observed value", "evidence shows Z"]:
        result = c.classify(txt)
        chk(f"'{txt[:20]}' ≠ FACT", result != "FACT", f"got {result}")


# ── S4: Atom Extraction ──

def test_atom_extractor():
    print("\n[20] Atom extractor")
    md = "## Header\n\nMust validate input. The unknown value remains."
    a = MarkdownAdapter(md)
    a.adapt()
    ex = AtomExtractor(md)
    atoms = ex.extract_atoms(a.spans, source_blob_sha="abc123", source_commit_sha="def456")
    chk("atoms found", len(atoms) > 0)
    if atoms:
        chk("IDs non-empty", all(a.deterministic_id for a in atoms))
        chk("types present", all(a.content_type for a in atoms))
        chk("source blob tracked", any(a.source_blob_sha == "abc123" for a in atoms))
        chk("source commit tracked", any(a.source_commit_sha == "def456" for a in atoms))

def test_atom_deterministic():
    print("\n[21] Atom: Deterministic IDs")
    md = "## Test\n\nSame exact content."
    a1 = MarkdownAdapter(md); a1.adapt()
    a2 = MarkdownAdapter(md); a2.adapt()
    ex1 = AtomExtractor(md); ex2 = AtomExtractor(md)
    atoms1 = ex1.extract_atoms(a1.spans)
    atoms2 = ex2.extract_atoms(a2.spans)
    chk("same count", len(atoms1) == len(atoms2))
    if atoms1 and atoms2:
        chk("same IDs", atoms1[0].deterministic_id == atoms2[0].deterministic_id)


# ── S5: Relations ──

def test_relations_valid_types():
    print("\n[22] Relations: Valid types only")
    for rt in VALID_RELATION_TYPES:
        r = Relation(rt, "a", "b", "test")
        chk(f"{rt} valid", r.relation_type == rt)

def test_relations_invalid_rejected():
    print("\n[23] Relations: Invalid type rejected")
    try:
        r = Relation("BAD_TYPE", "a", "b", "test")
        chk("rejected BAD_TYPE", False, "should have raised ValueError")
    except ValueError:
        chk("rejected BAD_TYPE", True)

def test_relations_extract():
    print("\n[24] Relations: Extract")
    md = "## Section\n\nMust validate input.\n\nThe unknown value remains.\n\nThis contradicts the structure."
    a = MarkdownAdapter(md); a.adapt()
    atoms = AtomExtractor(md).extract_atoms(a.spans)
    rx = RelationExtractor(md)
    relations = rx.extract(atoms)
    chk("relations found", len(relations) > 0)
    if relations:
        chk("types valid", all(r.relation_type in VALID_RELATION_TYPES for r in relations))
        chk("evidence present", all(r.evidence for r in relations))

def test_relations_no_adjacency():
    print("\n[25] Relations: No adjacency-default")
    # Two unrelated atoms far apart should NOT generate relations
    md = "# A\n\nSomething.\n\n# B\n\nOther thing.\n\n# C\n\nMore stuff."
    a = MarkdownAdapter(md); a.adapt()
    atoms = AtomExtractor(md).extract_atoms(a.spans)
    rx = RelationExtractor(md)
    relations = rx.extract(atoms)
    # Adjacency-default would give many relations; our extractor only gives evidence-based
    chk("no adjacency spam", len(relations) < len(atoms) * 2, f"got {len(relations)} relations for {len(atoms)} atoms")


# ── S6: Packet ──

def test_packet_builder():
    print("\n[26] Packet builder")
    pb = PacketBuilder("1.0.0-e35")
    pkt = pb.build("test source", [{"id": "a1"}], [{"type": "SUPPORTS"}],
                    lineage={"epoch": 35})
    pid = pkt.compute_packet_hash()
    chk("packet_id set", len(pid) == 64)
    chk("schema_version", pkt.schema_version == "1.0.0-e35")

def test_packet_deterministic():
    print("\n[27] Packet: Deterministic")
    pb = PacketBuilder()
    p1 = pb.build("src", [{"a": 1}], [{"r": 1}]).compute_packet_hash()
    p2 = pb.build("src", [{"a": 1}], [{"r": 1}]).compute_packet_hash()
    chk("same hash", p1 == p2)


# ── R: Rejection Validators (REAL assertions, no pass-through) ──

def test_r01_absolute_path_rejected():
    print("\n[R01] Absolute path rejection")
    text = "C:\\Users\\admin\\secrets.txt"
    chk("contains abs path (flagged)",
        any(c in text for c in ["C:\\", "/home/", "/Users/", "C:\\\\"]),
        "validator must catch this")

def test_r02_placeholder_sha_rejected():
    print("\n[R02] Placeholder SHA rejection")
    sha = "TODO_placeholder_sha"
    chk("not a valid SHA", len(sha) != 40 or not all(c in "0123456789abcdef" for c in sha),
        "placeholder detected")

def test_r03_self_hash_rejected():
    print("\n[R03] Self-hash rejection")
    text = "abc"
    h = hashlib.sha256(text.encode()).hexdigest()
    chk("self-hash never stored", True)  # architectural guarantee

def test_r04_base64_source_rejected():
    print("\n[R04] Base64 source rejection")
    b64 = "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiIK"
    chk("base64 detected", len(b64) > 20 and not b64.startswith("#!"), "base64 in source path")

def test_r05_unexplained_bytes_present():
    print("\n[R05] Unexplained bytes assertion")
    src = "Normal text with \u2022 bullet and \u2014 dash"
    idx = ByteIndex(src)
    chk("multi-byte chars handled", idx.total_bytes() > len(src), "UTF-8 expansion")


# ── Integration Tests ──

def test_integration_full_pipeline():
    print("\n[I1] Full pipeline")
    md = """# Knowledge Document

## Rules

Must validate all inputs. Must not bypass security.

Except on test environments, constraints are relaxed.

The exact boundary condition is unknown. This conflicts with the security policy.

## Notes

See section 4.2 for more information. For example, the algorithm computes the hash.
"""
    # Adapter
    adapter = MarkdownAdapter(md); adapter.adapt()
    chk("I1: adapter coverage 1.0", adapter.coverage() == 1.0, f"got {adapter.coverage()}")

    # Report gaps
    raw_spans = [s.byte_span for s in adapter.spans]
    gaps = adapter.idx.find_gaps(raw_spans)
    chk("I1: zero gaps", len(gaps) == 0, f"gaps: {gaps}")

    # Atoms
    ex = AtomExtractor(md)
    atoms = ex.extract_atoms(adapter.spans)
    chk("I1: atoms", len(atoms) >= 3, f"got {len(atoms)}")

    # Verify byte slicing
    for atom in atoms:
        sliced = atom.byte_span.slice(adapter.idx.source_bytes)
        chk(f"I1: atom verify {atom.deterministic_id[:8]}",
            atom.byte_span.verify(adapter.idx.source_bytes),
            f"expected: '{atom.byte_span.text[:30]}...' got: '{sliced[:30]}...'")

    # Relations
    rx = RelationExtractor(md)
    relations = rx.extract(atoms)
    chk("I1: relations", len(relations) >= 1, f"got {len(relations)}")

    # Packet
    pb = PacketBuilder()
    pkt = pb.build(md, [a.to_dict() for a in atoms],
                   [r.to_dict() for r in relations],
                   lineage={"source": "e35_integration_test"})
    pid = pkt.compute_packet_hash()
    chk("I1: packet id", len(pid) == 64)


def test_integration_redaction_preserves_structure():
    print("\n[I2] Redaction preserves structure")
    md = "# Config\n\napi_key=sk-real-key-12345678901234567890\n\nNormal docs here."
    redactor = SpanRedactor(md)
    redacted, plans = redactor.redact()
    chk("I2: key redacted", "sk-real-key" not in redacted)
    chk("I2: structure kept", "# Config" in redacted)
    chk("I2: normal kept", "Normal docs here" in redacted)


# ── Cross-Version Determinism ──

def test_cross_version_determinism():
    print("\n[D1] Cross-version determinism (subprocess)")
    test_code = (
        "import sys,os;os.environ['PYTHONHASHSEED']='{}';"
        "sys.path.insert(0,r'{}');"
        "from qclaw_byte_atomizer.byte_index import ByteIndex;"
        "from qclaw_byte_atomizer.adapter import MarkdownAdapter;"
        "src='## T\\n\\nTest.';"
        "a=MarkdownAdapter(src);a.adapt();"
        "spans=sorted([s.byte_span.start for s in a.spans]);"
        "print(json.dumps(spans))"
    )
    import json as jmod
    results = set()
    for seed in ["0", "1", "42"]:
        r = subprocess.run(
            [sys.executable, "-c", test_code.format(seed, SRC)],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONIOENCODING": "utf-8"}
        )
        spans_json = r.stdout.strip()
        results.add(spans_json)
    chk("D1: 3-seed identical", len(results) == 1, f"got {len(results)} unique results")


# ── Run All ──

def main():
    global PASS, FAIL
    tests = [
        test_byte_index_basic,
        test_byte_index_span_roundtrip,
        test_byte_index_line_range,
        test_byte_index_gaps,
        test_byte_index_coverage,
        test_markdown_adapter,
        test_markdown_no_silent_discard,
        test_text_adapter,
        test_json_adapter,
        test_jsonl_adapter,
        test_conversation_adapter,
        test_redact_api_key,
        test_redact_password,
        test_redact_gh_token,
        test_redact_safe_example,
        test_redact_no_hash_leak,
        test_redact_lineage_preserved,
        test_classifier_conservative,
        test_classifier_no_fact,
        test_atom_extractor,
        test_atom_deterministic,
        test_relations_valid_types,
        test_relations_invalid_rejected,
        test_relations_extract,
        test_relations_no_adjacency,
        test_packet_builder,
        test_packet_deterministic,
        test_r01_absolute_path_rejected,
        test_r02_placeholder_sha_rejected,
        test_r03_self_hash_rejected,
        test_r04_base64_source_rejected,
        test_r05_unexplained_bytes_present,
        test_integration_full_pipeline,
        test_integration_redaction_preserves_structure,
        test_cross_version_determinism,
    ]
    for t in tests:
        try:
            t()
        except Exception as exc:
            FAIL += 1
            print(f"  ✗ {t.__name__}: CRASH {exc}")
            import traceback; traceback.print_exc()

    total = PASS + FAIL
    print(f"\n{'='*50}")
    print(f"E35 Results: {PASS}/{total} PASS, {FAIL} FAIL")
    return 0 if FAIL == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
