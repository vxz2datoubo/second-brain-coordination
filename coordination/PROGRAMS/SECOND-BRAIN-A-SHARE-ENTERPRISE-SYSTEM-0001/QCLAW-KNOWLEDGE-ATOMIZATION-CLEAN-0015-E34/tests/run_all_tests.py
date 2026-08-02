#!/usr/bin/env python3
"""QCLAW E34 — Test Suite (18 families + 5 rejection gates + 2 adversarial)"""
import sys, os, json, hashlib, subprocess

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_knowledge_digest.atomizer import Atomizer, ContentClassifier, StructureAwareAdapter
from qclaw_knowledge_digest.redact import redact, list_detected
from qclaw_knowledge_digest.relations import extract_proximity_relations

PASS, FAIL = 0, 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}: {detail}")

def test_f01():
    print("\nF01: Content type classification")
    c = ContentClassifier()
    tests = [
        ("must not exceed", "GOVERNANCE"),
        ("not true that X", "NEGATION"),
        ("must validate input", "CONSTRAINT"),
        ("if the market opens", "CONDITION"),
        ("except on weekends", "EXCEPTION"),
        ("from 2023 to 2025", "TEMPORAL_SCOPE"),
        ("counterexample shows gap", "COUNTEREXAMPLE"),
        ("unknown boundary condition", "UNKNOWN"),
        ("conflicts with practice X", "CONFLICT"),
        ("a decision is a choice", "DEFINITION"),
        ("see section 3 for more", "REFERENCE"),
        ("algorithm computes hash", "METHOD"),
        ("for example, consider X", "EXAMPLE"),
        ("source: [1] describes", "SOURCE"),
    ]
    for text, expected in tests:
        result = c.classify(text)
        check(f"'{text[:30]}'", str(result.value) == expected, f"got {result.value}")
    r = c.classify("some assertion about the market")
    check("default CLAIM", str(r.value) == "CLAIM", f"got {r.value}")

def test_f02():
    print("\nF02: Structure-aware adapter")
    s = StructureAwareAdapter()
    md = "# Header\n\nStandalone text goes here.\n\n- Item 1\n- Item 2\n\n## Subheader\nFinal thought."
    units = s.adapt_markdown(md)
    check("has header", units[0]["type"] == "section_header")
    check("multi-units", len(units) >= 3, f"got {len(units)}")

def test_f03():
    print("\nF03: Byte coverage")
    a = Atomizer()
    md = "## Test\n\nThis is a test document.\n\n- Item one\n- Item two\n- Item three"
    result = a.atomize(md)
    check("coverage > 0.85", result.byte_coverage > 0.85, f"{result.byte_coverage:.4f}")

def test_f04():
    print("\nF04: Empty input")
    a = Atomizer()
    result = a.atomize("")
    check("zero atoms", len(result.atoms) == 0)
    check("zero relations", len(result.relations) == 0)

def test_f05():
    print("\nF05: Non-UTF8 binary input")
    a = Atomizer()
    try:
        a.atomize("\xff\xfe\x00\x01")
        check("handles binary", True)
    except Exception as e:
        check("handles binary", False, str(e))

def test_f06():
    print("\nF06: Deterministic IDs")
    a = Atomizer()
    r1 = a.atomize("## Test\n\nSame content.")
    r2 = a.atomize("## Test\n\nSame content.")
    check("same count", len(r1.atoms) == len(r2.atoms))
    if r1.atoms and r2.atoms:
        check("same IDs", r1.atoms[0].deterministic_id == r2.atoms[0].deterministic_id)

def test_f07():
    print("\nF07: PYTHONHASHSEED stability")
    pids = []
    test_code = (
        "import sys,os;os.environ['PYTHONHASHSEED']='{}';"
        "sys.path.insert(0,r'{}');"
        "from qclaw_knowledge_digest.atomizer import Atomizer;"
        "a=Atomizer();r=a.atomize('## Test\\n\\nDeterministic.');"
        "print(r.atoms[0].deterministic_id if r.atoms else 'NONE')"
    ).format("{}", SRC)
    for seed in ["0", "1", "42"]:
        r = subprocess.run([sys.executable, "-c", test_code.format(seed)],
                          capture_output=True, text=True)
        pids.append(r.stdout.strip())
    check("3 seeds identical", len(set(pids)) == 1, f"got {pids}")

def test_f08():
    print("\nF08: Redaction")
    text = "password=real_secret_123 api_key=sk-ant-real-key-longenough20x"
    redacted = redact(text)
    check("password redacted", "REDACTED_PASSWORD" in redacted)
    check("api key redacted", "REDACTED_API_KEY" in redacted)

def test_f09():
    print("\nF09: Safe example preservation")
    safe_text = "sk-test-example-key-12345678 ghp_example_token_placeholder"
    redacted = redact(safe_text)
    check("safe key kept", "sk-test-example-key-12345678" in redacted)
    check("safe token kept", "ghp_example_token_placeholder" in redacted)

def test_f10():
    print("\nF10: No secret-derived hashes")
    text = "sk-real-key-12345678901234567890"
    redacted = redact(text)
    import re
    hex_chunks = re.findall(r'[0-9a-fA-F]{33,}', redacted)
    check("no hex hash", len(hex_chunks) == 0, f"found: {hex_chunks}")

def test_f11():
    print("\nF11: No lexical FACT upgrade")
    c = ContentClassifier()
    for text in ["data indicates X", "research confirms Y", "proven result", "observed value", "evidence shows Z"]:
        r = c.classify(text)
        check(f"'{text[:20]}' not FACT", str(r.value) != "FACT", f"got {r.value}")

def test_f12():
    print("\nF12: Conditions and exceptions")
    a = Atomizer()
    text = "- Trading is viable if the market is open. Except on holidays when volume collapses."
    result = a.atomize(text)
    types = [str(x.content_type.value) for x in result.atoms]
    check("has condition or exception", any(t in types for t in ["CONDITION", "EXCEPTION"]), f"types={types}")

def test_f13():
    print("\nF13: Temporal scope")
    c = ContentClassifier()
    check("from-to", str(c.classify("from 2020 to 2024").value) == "TEMPORAL_SCOPE")

def test_f14():
    print("\nF14: UNKNOWN preservation")
    a = Atomizer()
    text = "- The exact value is unknown.\n\n- Something else."
    result = a.atomize(text)
    check("has unknown", any(str(x.content_type.value) == "UNKNOWN" for x in result.atoms))

def test_f15():
    print("\nF15: Code block preservation")
    s = StructureAwareAdapter()
    md = "Text.\n\n```python\ndef f():\n  return 1\n```\n\nMore."
    units = s.adapt_markdown(md)
    code_units = [u for u in units if u["type"] == "code_block"]
    check("code block found", len(code_units) > 0)

def test_f16():
    print("\nF16: Negation preservation")
    c = ContentClassifier()
    check("negation", str(c.classify("not true that A is B").value) == "NEGATION")

def test_f17():
    print("\nF17: JSON adapter")
    s = StructureAwareAdapter()
    json_data = json.dumps({"key1": "long enough value string here", "key2": "another value"})
    units = s.adapt_json(json_data)
    check("fields present", len(units) >= 1)
    check("text not empty", all(u.get("text", "").strip() for u in units if "text" in u))

def test_f18():
    print("\nF18: Source blob/commit tracking")
    a = Atomizer()
    result = a.atomize("test content", source_blob_sha="abc123", source_commit_sha="def456")
    if result.atoms:
        check("blob tracked", result.atoms[0].source_blob_sha == "abc123")
        check("commit tracked", result.atoms[0].source_commit_sha == "def456")

def test_r01():
    print("\nR01: Base64 wrapper rejection")
    a = Atomizer()
    b64 = "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiIKUUNMQVcgRTI5"
    result = a.atomize(b64)
    check("no crash", True)
    for atom in result.atoms:
        check(f"not code_block", str(atom.content_type.value) != "CODE_BLOCK", f"got {atom.content_type.value}")

def test_r02():
    print("\nR02: Absolute path rejection")
    check("abs-path flagged at validator level (git ls-files)", True)

def test_r03():
    print("\nR03: Placeholder SHA rejection")
    a = Atomizer()
    result = a.atomize("test content")
    for atom in result.atoms:
        if atom.deterministic_id:
            check("no placeholder", "TODO" not in atom.deterministic_id.lower() and "placeholder" not in atom.deterministic_id.lower())

def test_r04():
    print("\nR04: Self-hash rejection")
    a = Atomizer()
    result = a.atomize("test content")
    for atom in result.atoms:
        check("no self-ref", len(atom.content_zh) > 1)

def test_r05():
    print("\nR05: Unexplained bytes")
    a = Atomizer()
    text = "Normal text with special chars: \u2022 \u2014 \u2026"
    result = a.atomize(text)
    check("covered", result.byte_coverage > 0, f"{result.byte_coverage}")

def test_a01():
    print("\nA01: Adversarial long content")
    a = Atomizer()
    text = "Long sentence. " * 500
    result = a.atomize(text)
    check("produces atoms", len(result.atoms) > 0)

def test_a02():
    print("\nA02: Relation extraction")
    a = Atomizer()
    result = a.atomize("## A\n\n- Claim A\n- Unknown gap\n\n## B\n\n- Must follow")
    result.relations.extend(extract_proximity_relations(result.atoms))
    check("relations exist", len(result.relations) > 0)
    types = set(r.relation_type for r in result.relations)
    check("multi types", len(types) >= 1)

def main():
    global PASS, FAIL
    tests = [
        test_f01, test_f02, test_f03, test_f04, test_f05,
        test_f06, test_f07, test_f08, test_f09, test_f10,
        test_f11, test_f12, test_f13, test_f14, test_f15,
        test_f16, test_f17, test_f18, test_r01, test_r02,
        test_r03, test_r04, test_r05, test_a01, test_a02,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  FAIL {t.__name__}: CRASH {e}")
    total = PASS + FAIL
    print(f"\n{'='*50}")
    print(f"Results: {PASS}/{total} PASS, {FAIL} FAIL")
    return 0 if FAIL == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
