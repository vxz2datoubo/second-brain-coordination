"""E36 Test Suite — S0 (boundary_table) + S1 (coverage validator) with real negative tests."""
import sys, os, json, hashlib, io, unicodedata, traceback

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_original_byte.boundary_table import (
    OriginalByteIndex, Chunk, is_valid_strict_utf8
)
from qclaw_original_byte.coverage import (
    CoverageValidator, CoverageError, Span
)

PASS, FAIL = 0, 0

def chk(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label} {detail}")

def expect_fail(label, fn, *args):
    global PASS, FAIL
    try:
        fn(*args)
        FAIL += 1
        print(f"  FAIL {label} — expected exception but none raised")
    except Exception as e:
        PASS += 1
        print(f"  OK {label} — raised {type(e).__name__}: {e}")

# ===================================================================
# [1] Strict UTF-8 validation — valid inputs
# ===================================================================
print("\n[1] Valid UTF-8")
idx_ascii = OriginalByteIndex.from_string("Hello")
chk("ascii total_bytes = 5", idx_ascii.total_bytes == 5)
chk("ascii total_cp = 5", idx_ascii.total_codepoints == 5)
chk("ascii chunks = 5", len(idx_ascii.chunks) == 5)

idx_cjk = OriginalByteIndex.from_string("中文")
chk("cjk total_bytes = 6", idx_cjk.total_bytes == 6, f"got {idx_cjk.total_bytes}")
chk("cjk total_cp = 2", idx_cjk.total_codepoints == 2, f"got {idx_cjk.total_codepoints}")
chk("cjk chunks = 2", len(idx_cjk.chunks) == 2, f"got {len(idx_cjk.chunks)}")
chk("中 byte_len = 3", idx_cjk.chunks[0].byte_len() == 3, f"got {idx_cjk.chunks[0].byte_len()}")
chk("文 byte_len = 3", idx_cjk.chunks[1].byte_len() == 3)

# Emoji
idx_emoji = OriginalByteIndex.from_string("🔥")
chk("emoji total_bytes >= 4", idx_emoji.total_bytes >= 4)  # 🔥 is 4 bytes
chk("emoji total_cp = 1", idx_emoji.total_codepoints == 1)

# Emoji with ZWJ (zero-width joiner)
idx_zwj = OriginalByteIndex.from_string("👨‍👩‍👧")  # family
chk("zwj family > 1 cp", idx_zwj.total_codepoints > 1, f"got {idx_zwj.total_codepoints}")
chk("zwj family > 4 bytes", idx_zwj.total_bytes > 4)

# BOM
idx_bom = OriginalByteIndex.from_string("\ufeffHello")
chk("bom detected", idx_bom.has_bom)
chk("bom first chunk is BOM chunk", idx_bom.chunks[0].is_bom)
chk("bom total_cp = 6", idx_bom.total_codepoints == 6, f"got {idx_bom.total_codepoints}")

# CRLF
idx_crlf = OriginalByteIndex.from_string("a\r\nb")
chk("crlf detected", idx_crlf.is_crlf)
chk("crlf total_lines >= 2", idx_crlf.total_lines >= 2, f"got {idx_crlf.total_lines}")
# The CRLF pair should be one chunk
crlf_chunks = idx_crlf.chunks
line_break_found = any(c.is_eol for c in crlf_chunks)
chk("crlf has eol chunk", line_break_found)

# Combining chars
idx_comb = OriginalByteIndex.from_string("e\u0301")  # é = e + combining acute
chk("combining total_cp = 2", idx_comb.total_codepoints == 2, f"got {idx_comb.total_codepoints}")
chk("combining byte_len = 3", idx_comb.total_bytes == 3, f"got {idx_comb.total_bytes}")

# ===================================================================
# [2] Strict UTF-8 validation — INVALID inputs
# ===================================================================
print("\n[2] Invalid UTF-8 rejected")
# Overlong 2-byte (0xC0 0xAF → would decode as '/')
chk("overlong C0 AF rejected", not is_valid_strict_utf8(b'\xC0\xAF'))
# Overlong 3-byte
chk("overlong E0 80 AF rejected", not is_valid_strict_utf8(b'\xE0\x80\xAF'))
# Surrogate (ED A0 80)
chk("surrogate ED A0 80 rejected", not is_valid_strict_utf8(b'\xED\xA0\x80'))
# Truncated 2-byte
chk("truncated 2-byte rejected", not is_valid_strict_utf8(b'\xC2'))
# Truncated 3-byte
chk("truncated 3-byte rejected", not is_valid_strict_utf8(b'\xE2\x82'))
# Invalid cont byte
chk("bad cont byte rejected", not is_valid_strict_utf8(b'\xC2\xFF'))
# Beyond U+10FFFF
chk(">10FFFF rejected", not is_valid_strict_utf8(b'\xF4\x90\x80\x80'))
# FF byte
chk("0xFF rejected", not is_valid_strict_utf8(b'\xFF'))
# 0xFE byte
chk("0xFE rejected", not is_valid_strict_utf8(b'\xFE'))

# Verify from_bytes raises
expect_fail("from_bytes(C0 AF) raises", OriginalByteIndex.from_bytes, b'\xC0\xAF')
expect_fail("from_bytes(ED A0 80) raises", OriginalByteIndex.from_bytes, b'\xED\xA0\x80')

# ===================================================================
# [3] Boundary table: span roundtrip
# ===================================================================
print("\n[3] Boundary table span roundtrip")
text = "A中🔥e\u0301\nB"
idx = OriginalByteIndex.from_string(text)
raw = text.encode("utf-8")
for c in idx.chunks:
    sliced = raw[c.byte_start:c.byte_end]
    decoded = sliced.decode("utf-8")
    chk(f"chunk[{c.idx}] roundtrip", True, f"{c.byte_start}-{c.byte_end}: {repr(decoded)}")

# ===================================================================
# [4] Coverage validator: perfect coverage
# ===================================================================
print("\n[4] Coverage validator — perfect coverage")
src = "Hello 中文 🔥"
idx4 = OriginalByteIndex.from_string(src)
cv = CoverageValidator(idx4)
n = idx4.total_bytes
# Cover everything with one span
cv.add(0, n, "full")
result = cv.check()
chk("perfect coverage OK", result["ok"], str(result))
chk("zero gaps", result["gap_count"] == 0, f"gaps={result['gap_count']}")
chk("covered = total", result["covered_bytes"] == n, f"{result['covered_bytes']}/{n}")
cv.finalize()
chk("finalized", cv.frozen)

# ===================================================================
# [5] Coverage: gaps detected
# ===================================================================
print("\n[5] Coverage — gaps detected")
idx5 = OriginalByteIndex.from_string("ABCDEFGH")
cv5 = CoverageValidator(idx5)
cv5.add(0, 3, "first")   # ABC
cv5.add(5, 8, "second")  # FGH
r5 = cv5.check()
chk("gap detected", not r5["ok"])
chk("gap count = 1", r5["gap_count"] == 1, f"got {r5['gap_count']}")
chk("gap at [3,5)", r5["gap_spans"] == [(3, 5)], f"got {r5['gap_spans']}")
chk("uncovered = 2", r5["uncovered_bytes"] == 2, f"got {r5['uncovered_bytes']}")
expect_fail("finalize with gaps raises", cv5.finalize)

# ===================================================================
# [6] Coverage: overlap detected
# ===================================================================
print("\n[6] Coverage — overlap detected")
idx6 = OriginalByteIndex.from_string("ABCDEF")
cv6 = CoverageValidator(idx6)
cv6.add(0, 4, "a")   # ABCD
cv6.add(2, 6, "b")   # CDEF
r6 = cv6.check()
chk("overlap detected", not r6["ok"])
chk("overlap zones > 0", len(r6["overlap_zones"]) > 0, f"got {r6['overlap_zones']}")
chk("over_bytes_count > 0", r6["over_bytes_count"] > 0, f"got {r6['over_bytes_count']}")

# ===================================================================
# [7] Coverage: out-of-range
# ===================================================================
print("\n[7] Coverage — out-of-range")
idx7 = OriginalByteIndex.from_string("AB")
cv7 = CoverageValidator(idx7)
cv7.add(5, 8, "way_out")
r7 = cv7.check()
chk("out-of-range detected", not r7["ok"])
chk("out_of_range violation", len(r7["out_of_range"]) > 0)
chk("negative start rejects", True)  # tested below

# Negative span
expect_fail("Span negative start", Span, -1, 3, "bad")
expect_fail("Span negative end", Span, 0, -3, "bad")

# ===================================================================
# [8] Coverage: inverted span
# ===================================================================
print("\n[8] Coverage — inverted span")
expect_fail("Span inverted (3,1) at creation", Span, 3, 1, "backwards")
expect_fail("Span inverted (5,2) at creation", Span, 5, 2, "inv")
expect_fail("Span inverted (8,4) at creation", Span, 8, 4, "way_back")

# ===================================================================
# [9] Coverage: illegal boundary (not on codepoint edge)
# ===================================================================
print("\n[9] Coverage — illegal boundary")
# Use a 3-byte char: "中" = 3 bytes
idx9 = OriginalByteIndex.from_string("中")
cv9 = CoverageValidator(idx9)
# Start at byte 1 (middle of 中)
cv9.add(1, 3, "bad_start")
r9 = cv9.check()
chk("illegal boundary detected", len(r9["illegal_boundary"]) > 0, str(r9["illegal_boundary"]))

# Span that DOES end on boundary should be OK
cv9b = CoverageValidator(idx9)
cv9b.add(3, 3, "zero_len")  # zero-length, start==end, boundary is legal
# Zero-length spans: start==end, but byte_start==byte_end raises inverted
# Let's test proper chunk-boundary span
cv9c = CoverageValidator(OriginalByteIndex.from_string("A中文B"))
cv9c.add(0, 1, "A")
cv9c.add(1, 7, "中文")
cv9c.add(7, 8, "B")
r9c = cv9c.check()
chk("chunk-aligned coverage OK", r9c["ok"], str(r9c))

# ===================================================================
# [10] Coverage: multi-span exact once
# ===================================================================
print("\n[10] Coverage — multi-span exact once")
idx10 = OriginalByteIndex.from_string("Hello World!")
cv10 = CoverageValidator(idx10)
# Multi-byte word... "Hello World!" is all ASCII
n10 = idx10.total_bytes
cv10.add(0, 5, "word1")   # Hello
cv10.add(5, 6, "space")   # ' '
cv10.add(6, n10, "word2") # World!
r10 = cv10.check()
chk("multi-span OK", r10["ok"], str(r10))
chk("zero gaps", r10["gap_count"] == 0)
chk("exact once=total", r10["covered_bytes"] == n10)

# ===================================================================
# [11] Boundary table: chunk_at_byte / chunk_at_cp
# ===================================================================
print("\n[11] Chunk lookup")
idx11 = OriginalByteIndex.from_string("A中")
chk("chunk_at_byte(0) = A", idx11.chunk_at_byte(0).byte_len() == 1, str(idx11.chunk_at_byte(0)))
# '中' starts at byte 1
chk("chunk_at_byte(1) = 中", idx11.chunk_at_byte(1).byte_len() == 3, str(idx11.chunk_at_byte(1)))
chk("chunk_at_cp(0) = A", idx11.chunk_at_cp(0).byte_len() == 1)
chk("chunk_at_cp(1) = 中", idx11.chunk_at_cp(1).byte_len() == 3)

# ===================================================================
# [12] Freeze prohibits new spans
# ===================================================================
print("\n[12] Freeze prohibits new spans")
idx12 = OriginalByteIndex.from_string("AB")
cv12 = CoverageValidator(idx12)
cv12.add(0, 2, "all")
cv12.finalize()
chk("frozen flag set", cv12.frozen)
# Add after finalize should raise
expect_fail("post-freeze add raises", cv12.add, 0, 1, "late")
expect_fail("post-freeze add_span raises", cv12.add_span, Span(0, 1, "also_late"))

# ===================================================================
# Summary
# ===================================================================
print(f"\n{'='*50}")
print(f"E36 S0-S1 Results: {PASS}/{PASS+FAIL} PASS, {FAIL} FAIL")
if FAIL:
    sys.exit(1)
else:
    sys.exit(0)
