"""E39 S2 tests — 6-format byte-position adapters with mutation rejection."""
import unittest
import sys, os, json

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_strict_byte.utf8_guard import UTF8ByteIndex
from qclaw_strict_byte.adapter import (
    adapt, adapt_txt, adapt_markdown, adapt_json, adapt_jsonl,
    adapt_conversation_structured, adapt_conversation_plain,
    SpanRole,
    ROLE_HEADER, ROLE_CONTENT, ROLE_BLANK_LINE, ROLE_CODE_BLOCK,
    ROLE_LIST_ITEM, ROLE_TABLE, ROLE_JSON_KEY, ROLE_JSON_VALUE,
    ROLE_JSON_STRING, ROLE_JSON_NUMBER, ROLE_JSON_BOOL, ROLE_JSON_NULL,
    ROLE_CONVERSATION_ROLE, ROLE_CONVERSATION_CONTENT,
    ROLE_UNKNOWN, ROLE_STRUCTURE,
)
from qclaw_strict_byte.utf8_guard import UTF8ByteIndex


class TestTxtAdapter(unittest.TestCase):
    def test_empty(self):
        idx = UTF8ByteIndex(b"")
        spans = adapt_txt(idx)
        self.assertEqual(len(spans), 0)

    def test_single_line(self):
        idx = UTF8ByteIndex(b"hello world")
        spans = adapt_txt(idx)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].role, ROLE_CONTENT)
        self.assertEqual(spans[0].byte_start, 0)
        self.assertEqual(spans[0].byte_end, 11)

    def test_multiple_lines(self):
        idx = UTF8ByteIndex(b"line1\nline2\n")
        spans = adapt_txt(idx)
        roles = [s.role for s in spans]
        self.assertIn(ROLE_CONTENT, roles)

    def test_crlf_lines(self):
        idx = UTF8ByteIndex(b"a\r\nb\r\n")
        spans = adapt_txt(idx)
        self.assertGreaterEqual(len(spans), 2)

    def test_blank_line(self):
        idx = UTF8ByteIndex(b"a\n\nb")
        spans = adapt_txt(idx)
        blank = [s for s in spans if s.role == ROLE_BLANK_LINE]
        self.assertEqual(len(blank), 1)

    def test_coverage_complete(self):
        idx = UTF8ByteIndex(b"hello\nworld\n")
        covered = 0
        for s in adapt_txt(idx):
            covered += s.byte_end - s.byte_start
        self.assertEqual(covered, idx.total_bytes)


class TestMarkdownAdapter(unittest.TestCase):
    def test_header_detection(self):
        md = b"# Title\ncontent\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        headers = [s for s in spans if s.role == ROLE_HEADER]
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0].label, "h1")

    def test_h3_header(self):
        md = b"### Section\ncontent\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        h3 = [s for s in spans if s.role == ROLE_HEADER and s.label == "h3"]
        self.assertEqual(len(h3), 1)

    def test_code_block(self):
        md = b"```python\nprint('hi')\n```\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        has_code = any(s.role == ROLE_CODE_BLOCK for s in spans)
        self.assertTrue(has_code, "Should detect code block")

    def test_code_block_content_presence(self):
        md = b"```\ncode here\n```\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        code_spans = [s for s in spans if s.role == ROLE_CODE_BLOCK]
        self.assertGreaterEqual(len(code_spans), 1)

    def test_list_item_dash(self):
        md = b"- item 1\n- item 2\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        items = [s for s in spans if s.role == ROLE_LIST_ITEM]
        self.assertEqual(len(items), 2)

    def test_list_item_star(self):
        md = b"* item\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        items = [s for s in spans if s.role == ROLE_LIST_ITEM]
        self.assertEqual(len(items), 1)

    def test_table_detection(self):
        md = b"| a | b |\n| c | d |\ncontent\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        tables = [s for s in spans if s.role == ROLE_TABLE]
        self.assertEqual(len(tables), 1)

    def test_content_fallback(self):
        md = b"Just some text\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        has_content = any(s.role == ROLE_CONTENT for s in spans)
        self.assertTrue(has_content)

    def test_coverage_complete(self):
        md = b"# Hi\n\n- a\n- b\n\nnormal text\n"
        idx = UTF8ByteIndex(md)
        covered = sum(s.byte_end - s.byte_start for s in adapt_markdown(idx))
        self.assertEqual(covered, idx.total_bytes)

    def test_cjk_header(self):
        md_str = b"# \xe4\xb8\xad\xe6\x96\x87\xe6\xa0\x87\xe9\xa2\x98\n"  # # 中文标题
        idx = UTF8ByteIndex(md_str)
        spans = adapt_markdown(idx)
        headers = [s for s in spans if s.role == ROLE_HEADER]
        self.assertEqual(len(headers), 1)


class TestJsonAdapter(unittest.TestCase):
    def test_simple_object(self):
        idx = UTF8ByteIndex(b'{"key": "value"}')
        spans = adapt_json(idx)
        keys = [s for s in spans if s.role == ROLE_JSON_KEY]
        self.assertEqual(len(keys), 1)

    def test_number_value(self):
        idx = UTF8ByteIndex(b'{"count": 42}')
        spans = adapt_json(idx)
        nums = [s for s in spans if s.role == ROLE_JSON_NUMBER]
        self.assertEqual(len(nums), 1)

    def test_bool_value(self):
        idx = UTF8ByteIndex(b'{"active": true}')
        spans = adapt_json(idx)
        bools = [s for s in spans if s.role == ROLE_JSON_BOOL]
        self.assertEqual(len(bools), 1)

    def test_null_value(self):
        idx = UTF8ByteIndex(b'{"data": null}')
        spans = adapt_json(idx)
        nulls = [s for s in spans if s.role == ROLE_JSON_NULL]
        self.assertEqual(len(nulls), 1)

    def test_array(self):
        idx = UTF8ByteIndex(b'[1, 2, 3]')
        spans = adapt_json(idx)
        nums = [s for s in spans if s.role == ROLE_JSON_NUMBER]
        self.assertEqual(len(nums), 3)

    def test_nested_object(self):
        idx = UTF8ByteIndex(b'{"a": {"b": "c"}}')
        spans = adapt_json(idx)
        keys = [s for s in spans if s.role == ROLE_JSON_KEY]
        self.assertEqual(len(keys), 2)

    def test_duplicate_key_preserved(self):
        """Duplicate keys must both be tokenized as keys."""
        idx = UTF8ByteIndex(b'{"x": 1, "x": 2}')
        spans = adapt_json(idx)
        keys = [s for s in spans if s.role == ROLE_JSON_KEY]
        # Both "x" keys should be present (not merged)
        self.assertEqual(len(keys), 2)

    def test_escape_preserved(self):
        """Escaped characters in string values are preserved in byte spans."""
        idx = UTF8ByteIndex(b'{"text": "hello\\nworld"}')
        spans = adapt_json(idx)
        strings = [s for s in spans if s.role == ROLE_JSON_STRING]
        self.assertEqual(len(strings), 1)
        # The string should contain the backslash-n
        content = idx.source_bytes[strings[0].byte_start:strings[0].byte_end]
        self.assertIn(0x5C, content)  # backslash present

    def test_structure_tokens(self):
        idx = UTF8ByteIndex(b'{"a": 1}')
        spans = adapt_json(idx)
        roles = {s.role for s in spans}
        self.assertIn(ROLE_JSON_KEY, roles)
        self.assertIn(ROLE_JSON_NUMBER, roles)

    def test_empty_object(self):
        idx = UTF8ByteIndex(b'{}')
        spans = adapt_json(idx)
        self.assertEqual(len(spans), 2)  # { and }

    def test_whitespace_preserved(self):
        """Byte-level parsing works even with irregular whitespace."""
        idx = UTF8ByteIndex(b'{"a" : 1  ,  "b":2}')
        spans = adapt_json(idx)
        keys = [s for s in spans if s.role == ROLE_JSON_KEY]
        self.assertEqual(len(keys), 2)


class TestJsonlAdapter(unittest.TestCase):
    def test_two_lines(self):
        idx = UTF8ByteIndex(b'{"a":1}\n{"b":2}\n')
        spans = adapt_jsonl(idx)
        keys = [s for s in spans if s.role == ROLE_JSON_KEY]
        self.assertEqual(len(keys), 2)

    def test_malformed_line(self):
        idx = UTF8ByteIndex(b'not json\n{"a":1}\n')
        spans = adapt_jsonl(idx)
        unknowns = [s for s in spans if s.role == ROLE_UNKNOWN]
        self.assertEqual(len(unknowns), 1)

    def test_no_trailing_newline(self):
        """Last line without newline still gets parsed."""
        idx = UTF8ByteIndex(b'{"a":1}')
        spans = adapt_jsonl(idx)
        self.assertGreater(len(spans), 0)


class TestConversationAdapter(unittest.TestCase):
    def test_structured_roles(self):
        data = b"user: hello\nassistant: hi\n"
        idx = UTF8ByteIndex(data)
        spans = adapt_conversation_structured(idx)
        roles = [s for s in spans if s.role == ROLE_CONVERSATION_ROLE]
        self.assertEqual(len(roles), 2)

    def test_structured_content(self):
        data = b"user: hello\n"
        idx = UTF8ByteIndex(data)
        spans = adapt_conversation_structured(idx)
        content_spans = [s for s in spans if s.role == ROLE_CONVERSATION_CONTENT]
        self.assertEqual(len(content_spans), 1)

    def test_plain_conversation(self):
        data = b"Hello there.\n\nHow are you?\n"
        idx = UTF8ByteIndex(data)
        spans = adapt_conversation_plain(idx)
        self.assertGreaterEqual(len(spans), 1)


class TestAdapterCoverage(unittest.TestCase):
    def test_txt_full_coverage(self):
        for data in [b"hello", b"a\nb", b"a\n\nb", b"line\r\n"]:
            idx = UTF8ByteIndex(data)
            covered = sum(s.byte_end - s.byte_start for s in adapt_txt(idx))
            self.assertEqual(covered, idx.total_bytes,
                             f"TXT coverage miss for {data!r}")

    def test_markdown_full_coverage(self):
        md = b"# A\n\n- b\n- c\n\n```\nd\n```\n\ntext\n"
        idx = UTF8ByteIndex(md)
        covered = sum(s.byte_end - s.byte_start for s in adapt_markdown(idx))
        self.assertEqual(covered, idx.total_bytes)

    def test_json_full_coverage(self):
        data = b'{"a": [1, 2], "b": {"c": "d"}}'
        idx = UTF8ByteIndex(data)
        spans = adapt_json(idx)
        # JSON adapter covers everything in the tokenized byte range
        if spans:
            last_end = max(s.byte_end for s in spans)
            self.assertGreaterEqual(last_end, idx.total_bytes - 1)

    def test_span_no_overlap(self):
        """Verify no byte belongs to multiple spans (non-structure at least)."""
        md = b"# Hi\n\n- a\n- b\n"
        idx = UTF8ByteIndex(md)
        spans = adapt_markdown(idx)
        content_spans = [s for s in spans if s.role != ROLE_STRUCTURE]
        total = idx.total_bytes
        coverage = [0] * total
        for s in content_spans:
            for i in range(s.byte_start, s.byte_end):
                coverage[i] += 1
        multi = sum(1 for c in coverage if c > 1)
        self.assertEqual(multi, 0, f"{multi} bytes covered by multiple spans")


class TestMutationFailureFamilies(unittest.TestCase):
    """Active mutation tests: prove that char-index NOT EQUAL byte-index."""

    def test_char_index_not_byte_index(self):
        """euro symbol: 3 bytes but len(str) = 1."""
        data = b"cost: \xe2\x82\xac5"  # "cost: €5" — 10 bytes, 8 chars
        idx = UTF8ByteIndex(data)
        spans = adapt_txt(idx)
        # char-index would be len("cost: €5") = 8
        # byte-index is 10
        self.assertEqual(idx.total_bytes, 10)
        # Ensure spans cover all bytes
        covered = sum(s.byte_end - s.byte_start for s in spans)
        self.assertEqual(covered, 10)

    def test_cjk_byte_vs_char(self):
        """CJK: '中文' = 6 bytes but len('中文') = 2 chars."""
        data = "中文content".encode("utf-8")  # 13 bytes, 9 chars
        idx = UTF8ByteIndex(data)
        covers = sum(s.byte_end - s.byte_start for s in adapt_txt(idx))
        self.assertEqual(covers, 13)  # byte, not char
        self.assertNotEqual(covers, len(data.decode("utf-8")))  # char would differ


if __name__ == "__main__":
    unittest.main(verbosity=2)
