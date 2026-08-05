"""E40 S2 — Adapter mutation + functional tests"""
import unittest, sys, os, json as _json

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"


class TestTxtAdapter(unittest.TestCase):
    def test_simple_txt(self):
        from qclaw_e40.adapter import adapt
        idx, spans = adapt(b"hello world\nsecond line\n", "txt")
        self.assertGreaterEqual(len(spans), 2)

    def test_txt_header_detected(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b"# Title\ncontent\n", "txt")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.HEADER, roles)

    def test_txt_list_item(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b"- item1\n- item2\n", "txt")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.LIST_ITEM, roles)

    def test_txt_blank_lines(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b"content\n\nmore\n", "txt")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.BLANK_LINE, roles)

    def test_txt_coverage(self):
        """Every byte covered by adapter spans."""
        from qclaw_e40.adapter import adapt
        src = b"line1\nline2\nline3\n"
        idx, spans = adapt(src, "txt")
        covered = 0
        for s in spans:
            covered += s.byte_end - s.byte_start
        self.assertEqual(covered, idx.total_bytes)


class TestMarkdownAdapter(unittest.TestCase):
    def test_simple_md(self):
        from qclaw_e40.adapter import adapt
        idx, spans = adapt(b"# Title\n\ncontent\n", "markdown")
        self.assertGreaterEqual(len(spans), 2)

    def test_code_block_detected(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b"```python\nprint(1)\n```\n", "markdown")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.CODE_BLOCK, roles)
        self.assertIn(ContentRole.CODE_BLOCK_FENCE, roles)

    def test_table_row_detected(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b"|a|b|\n|---|---|\n", "markdown")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.TABLE_ROW, roles)

    def test_blockquote_detected(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b"> quote\n", "markdown")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.BLOCKQUOTE, roles)

    def test_md_coverage(self):
        from qclaw_e40.adapter import adapt
        src = b"# H1\n\n- item\n```\ncode\n```\n"
        idx, spans = adapt(src, "markdown")
        covered = 0
        for s in spans:
            covered += s.byte_end - s.byte_start
        self.assertEqual(covered, idx.total_bytes)


class TestJsonAdapter(unittest.TestCase):
    def test_simple_object(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b'{"a":1}', "json")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.JSON_OBJECT_START, roles)
        self.assertIn(ContentRole.JSON_STRING, roles)
        self.assertIn(ContentRole.JSON_NUMBER, roles)

    def test_json_array(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b'[1,2,3]', "json")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.JSON_ARRAY_START, roles)

    def test_json_bool_and_null(self):
        from qclaw_e40.adapter import adapt, ContentRole
        idx, spans = adapt(b'[true,false,null]', "json")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.JSON_BOOL, roles)
        self.assertIn(ContentRole.JSON_NULL, roles)

    def test_json_escape_preserved(self):
        from qclaw_e40.adapter import adapt, ContentRole
        src = b'{"key":"val\\"ue","k2":"\\\\esc"}'
        idx, spans = adapt(src, "json")
        strs = [s for s in spans if s.role == ContentRole.JSON_STRING]
        # At least one string contains an escape (backslash)
        has_escape = any(b'\\' in s.text for s in strs)
        self.assertTrue(has_escape)

    def test_json_duplicate_key_preserved(self):
        from qclaw_e40.adapter import adapt, ContentRole
        src = b'{"a":1,"a":2}'
        idx, spans = adapt(src, "json")
        strs = [s for s in spans if s.role == ContentRole.JSON_STRING]
        # Both "a" keys are preserved
        self.assertGreaterEqual(len(strs), 2)

    def test_json_whitespace_preserved(self):
        from qclaw_e40.adapter import adapt, ContentRole
        src = b'{\n  "x" : 1\n}'
        idx, spans = adapt(src, "json")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.JSON_WHITESPACE, roles)

    def test_json_coverage(self):
        from qclaw_e40.adapter import adapt
        src = b'{"a":1,"b":[2,3]}'
        idx, spans = adapt(src, "json")
        covered = 0
        for s in spans:
            covered += s.byte_end - s.byte_start
        self.assertEqual(covered, idx.total_bytes)


class TestJsonlAdapter(unittest.TestCase):
    def test_simple_jsonl(self):
        from qclaw_e40.adapter import adapt
        idx, spans = adapt(b'{"a":1}\n{"a":2}\n', "jsonl")
        self.assertGreaterEqual(len(spans), 2)

    def test_jsonl_no_final_newline(self):
        from qclaw_e40.adapter import adapt
        idx, spans = adapt(b'{"a":1}\n{"a":2}', "jsonl")
        self.assertGreaterEqual(len(spans), 2)


class TestConversationAdapter(unittest.TestCase):
    def test_structured_roles(self):
        from qclaw_e40.adapter import adapt, ContentRole
        src = b"user: hello\nassistant: hi there\n"
        idx, spans = adapt(src, "conversation_structured")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.CONVERSATION_ROLE, roles)
        # Verify role spans have the correct prefix
        role_spans = [s for s in spans if s.role == ContentRole.CONVERSATION_ROLE]
        self.assertEqual(len(role_spans), 2)

    def test_plain_conversation(self):
        from qclaw_e40.adapter import adapt, ContentRole
        src = b"hello\nhi there\n"
        idx, spans = adapt(src, "conversation_plain")
        content_spans = [s for s in spans if s.role == ContentRole.CONVERSATION_CONTENT]
        self.assertEqual(len(content_spans), 2)

    def test_conversation_separator(self):
        from qclaw_e40.adapter import adapt, ContentRole
        src = b"user: a\n\nassistant: b\n"
        idx, spans = adapt(src, "conversation_structured")
        roles = {s.role for s in spans}
        self.assertIn(ContentRole.CONVERSATION_SEPARATOR, roles)


class TestAdapterDispatch(unittest.TestCase):
    def test_unknown_format_rejected(self):
        from qclaw_e40.adapter import adapt
        with self.assertRaises(ValueError) as ctx:
            adapt(b"data", "garbage")
        self.assertIn("unknown_format", str(ctx.exception))

    def test_empty_source_all_formats(self):
        from qclaw_e40.adapter import adapt
        for fmt in ["txt","markdown","json","jsonl","conversation_structured","conversation_plain"]:
            idx, spans = adapt(b"", fmt)
            self.assertEqual(idx.total_bytes, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
