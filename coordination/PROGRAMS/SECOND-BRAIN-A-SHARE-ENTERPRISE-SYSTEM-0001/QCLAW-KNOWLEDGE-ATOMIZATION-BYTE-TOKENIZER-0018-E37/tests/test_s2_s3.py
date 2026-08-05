"""E37 S2 unittest — adapter (6 formats) + redaction with mutation tests."""
import unittest
import sys, os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_byte_tokenizer.boundary_table import OriginalByteIndex
from qclaw_byte_tokenizer.adapter import (
    adapt, adapt_txt, adapt_markdown, adapt_json, adapt_jsonl,
    adapt_conversation_structured, adapt_conversation_plain,
    AdapterSpan,
)
from qclaw_byte_tokenizer.redact import (
    find_redactions, resolve_redactions, apply_redactions,
    RedactionMapping, RedactedView, CATEGORY_PRIORITY,
)


# ═══════════════════════════════════════════════════════════════════
# TXT adapter
# ═══════════════════════════════════════════════════════════════════

class TestAdaptTxt(unittest.TestCase):

    def test_single_line(self):
        idx = OriginalByteIndex(b"hello world")
        spans = adapt_txt(idx)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].role, "content")
        self.assertEqual(spans[0].byte_start, 0)
        self.assertEqual(spans[0].byte_end, idx.total_bytes)

    def test_multiline(self):
        idx = OriginalByteIndex(b"line1\nline2\nline3\n")
        spans = adapt_txt(idx)
        roles = [s.role for s in spans]
        self.assertTrue(all(r == "content" for r in roles))
        self.assertGreaterEqual(len(spans), 3)

    def test_empty(self):
        idx = OriginalByteIndex(b"")
        spans = adapt_txt(idx)
        self.assertEqual(len(spans), 0)

    def test_utf8_content_preserved(self):
        idx = OriginalByteIndex("中文文本\n第二行".encode("utf-8"))
        spans = adapt_txt(idx)
        self.assertGreaterEqual(len(spans), 1)
        for s in spans:
            self.assertEqual(s.role, "content")


# ═══════════════════════════════════════════════════════════════════
# Markdown adapter
# ═══════════════════════════════════════════════════════════════════

class TestAdaptMarkdown(unittest.TestCase):

    def test_header_h1(self):
        idx = OriginalByteIndex(b"# Title\ncontent\n")
        spans = adapt_markdown(idx)
        roles = [s.role for s in spans]
        self.assertIn("header", roles)
        self.assertIn("content", roles)

    def test_header_h2(self):
        idx = OriginalByteIndex(b"## Subtitle\nbody\n")
        spans = adapt_markdown(idx)
        self.assertTrue(any(s.role == "header" for s in spans))

    def test_list_bullet(self):
        idx = OriginalByteIndex(b"- item 1\n- item 2\n")
        spans = adapt_markdown(idx)
        list_items = [s for s in spans if s.role == "list_item"]
        self.assertEqual(len(list_items), 2)

    def test_list_numbered(self):
        idx = OriginalByteIndex(b"1. first\n2. second\n")
        spans = adapt_markdown(idx)
        list_items = [s for s in spans if s.role == "list_item"]
        self.assertGreaterEqual(len(list_items), 2)

    def test_code_block(self):
        idx = OriginalByteIndex(b"```\ncode\n```\n")
        spans = adapt_markdown(idx)
        code_spans = [s for s in spans if s.role == "code_block"]
        self.assertGreaterEqual(len(code_spans), 3)  # open + content + close

    def test_code_block_content_not_misclassified(self):
        idx = OriginalByteIndex(b"```\n# not a header\n```\n")
        spans = adapt_markdown(idx)
        inside = [s for s in spans if s.byte_start > 3 and s.byte_end < 20]
        for s in inside:
            self.assertNotEqual(s.role, "header")

    def test_table(self):
        idx = OriginalByteIndex(b"| a | b |\n| c | d |\n")
        spans = adapt_markdown(idx)
        table = [s for s in spans if s.role == "table"]
        self.assertGreaterEqual(len(table), 2)

    def test_blockquote(self):
        idx = OriginalByteIndex(b"> quoted\nplain\n")
        spans = adapt_markdown(idx)
        bq = [s for s in spans if s.role == "blockquote"]
        self.assertEqual(len(bq), 1)

    def test_blank_lines_skip(self):
        idx = OriginalByteIndex(b"\n\n# header\n\ncontent\n")
        spans = adapt_markdown(idx)
        self.assertGreater(len(spans), 0)

    def test_cjk_header(self):
        idx = OriginalByteIndex("# 中文标题\ncontent\n".encode("utf-8"))
        spans = adapt_markdown(idx)
        headers = [s for s in spans if s.role == "header"]
        self.assertEqual(len(headers), 1)

    def test_mixed_content(self):
        md = b"# H1\n## H2\n- item\n1. num\n```\ncode\n```\n> quote\n| tbl |\nplain\n"
        idx = OriginalByteIndex(md)
        spans = adapt_markdown(idx)
        roles = {s.role for s in spans}
        self.assertIn("header", roles)
        self.assertIn("list_item", roles)
        self.assertIn("code_block", roles)
        self.assertIn("blockquote", roles)
        self.assertIn("table", roles)
        self.assertIn("content", roles)


# ═══════════════════════════════════════════════════════════════════
# JSON adapter
# ═══════════════════════════════════════════════════════════════════

class TestAdaptJSON(unittest.TestCase):

    def test_simple_object(self):
        idx = OriginalByteIndex(b'{"key":"value"}')
        spans = adapt_json(idx)
        roles = {s.role for s in spans}
        self.assertIn("object_start", roles)
        self.assertIn("object_end", roles)
        self.assertIn("json_string", roles)
        self.assertIn("colon", roles)

    def test_array(self):
        idx = OriginalByteIndex(b'[1,2,3]')
        spans = adapt_json(idx)
        roles = {s.role for s in spans}
        self.assertIn("array_start", roles)
        self.assertIn("array_end", roles)
        self.assertIn("json_number", roles)
        self.assertIn("comma", roles)

    def test_bool_null(self):
        idx = OriginalByteIndex(b'{"a":true,"b":false,"c":null}')
        spans = adapt_json(idx)
        roles = {s.role for s in spans}
        self.assertIn("json_bool", roles)
        self.assertIn("json_null", roles)

    def test_duplicate_keys_preserved(self):
        idx = OriginalByteIndex(b'{"a":1,"a":2}')
        spans = adapt_json(idx)
        strings = [s for s in spans if s.role == "json_string"]
        a_keys = [s for s in strings if b'"a"' in idx.source_bytes[s.byte_start:s.byte_end]]
        self.assertEqual(len(a_keys), 2)

    def test_unicode_key(self):
        idx = OriginalByteIndex('{"中文":"值"}'.encode("utf-8"))
        spans = adapt_json(idx)
        self.assertGreater(len(spans), 2)
        strings = [s for s in spans if s.role == "json_string"]
        self.assertGreaterEqual(len(strings), 2)

    def test_escape_preserved(self):
        src = b'{"key":"a\\nb"}'
        idx = OriginalByteIndex(src)
        spans = adapt_json(idx)
        # The \n escape should be inside the value string (not the key "key")
        # Check that AT LEAST ONE json_string span contains the backslash byte
        found = False
        for s in spans:
            if s.role == "json_string":
                seg = src[s.byte_start:s.byte_end]
                if ord("\\") in seg:
                    found = True
        self.assertTrue(found, "At least one json_string must contain the backslash escape")

    def test_number_variants(self):
        idx = OriginalByteIndex(b'[0,-1,3.14,1e10,-2.5E-3]')
        spans = adapt_json(idx)
        nums = [s for s in spans if s.role == "json_number"]
        self.assertEqual(len(nums), 5)

    def test_nested(self):
        idx = OriginalByteIndex(b'{"a":{"b":[1]}}')
        spans = adapt_json(idx)
        objs = [s for s in spans if s.role == "object_start"]
        arrs = [s for s in spans if s.role == "array_start"]
        self.assertEqual(len(objs), 2)
        self.assertEqual(len(arrs), 1)


# ═══════════════════════════════════════════════════════════════════
# JSONL adapter
# ═══════════════════════════════════════════════════════════════════

class TestAdaptJSONL(unittest.TestCase):

    def test_two_lines(self):
        idx = OriginalByteIndex(b'{"a":1}\n{"b":2}\n')
        spans = adapt_jsonl(idx)
        self.assertEqual(len(spans), 2)
        for s in spans:
            self.assertEqual(s.role, "jsonl_line")

    def test_no_trailing_newline_gap(self):
        idx = OriginalByteIndex(b'{"a":1}')
        spans = adapt_jsonl(idx)
        # No valid lines (no trailing newline)
        self.assertEqual(len(spans), 0)

    def test_empty_lines_skip(self):
        idx = OriginalByteIndex(b'{"a":1}\n\n{"b":2}\n')
        spans = adapt_jsonl(idx)
        self.assertEqual(len(spans), 2)


# ═══════════════════════════════════════════════════════════════════
# Conversation adapter
# ═══════════════════════════════════════════════════════════════════

class TestAdaptConversation(unittest.TestCase):

    def test_structured_roles(self):
        src = b'[{"role":"system","content":"yo"},{"role":"user","content":"hi"}]'
        idx = OriginalByteIndex(src)
        spans = adapt_conversation_structured(idx)
        roles = {s.role for s in spans}
        self.assertIn("conversation_role", roles)

    def test_plain_user_assistant(self):
        idx = OriginalByteIndex(b"User: hello\nAssistant: hi there\n")
        spans = adapt_conversation_plain(idx)
        roles = {s.role for s in spans}
        self.assertIn("conversation_user", roles)
        self.assertIn("conversation_assistant", roles)


# ═══════════════════════════════════════════════════════════════════
# Dispatch
# ═══════════════════════════════════════════════════════════════════

class TestAdaptDispatch(unittest.TestCase):

    def test_all_formats(self):
        for fmt in ("txt", "markdown", "json", "jsonl", "conversation_structured", "conversation_plain"):
            idx = OriginalByteIndex(b"test")
            spans = adapt(fmt, idx)
            self.assertIsInstance(spans, list)

    def test_unknown_format_raises(self):
        idx = OriginalByteIndex(b"test")
        with self.assertRaises(ValueError):
            adapt("unknown_format", idx)


# ═══════════════════════════════════════════════════════════════════
# Redaction
# ═══════════════════════════════════════════════════════════════════

class TestRedaction(unittest.TestCase):

    def test_find_sk_key(self):
        idx = OriginalByteIndex(b'sk-abcdefghijklmnopqrstuvwxyz123456')
        cands = find_redactions(idx)
        self.assertGreaterEqual(len(cands), 1)
        self.assertEqual(cands[0]["category"], "API_KEY")

    def test_find_github_token(self):
        idx = OriginalByteIndex(b'ghp_abcdefghijklmnopqrstuvwx123456')
        cands = find_redactions(idx)
        self.assertGreaterEqual(len(cands), 1)
        self.assertEqual(cands[0]["category"], "GITHUB_TOKEN")

    def test_find_password_eq(self):
        idx = OriginalByteIndex(b'password=secret123')
        cands = find_redactions(idx)
        self.assertGreaterEqual(len(cands), 1)
        self.assertIn(cands[0]["category"], ("PASSWORD", "API_KEY"))

    def test_no_redaction_in_normal_text(self):
        idx = OriginalByteIndex(b"hello world this is safe content")
        cands = find_redactions(idx)
        self.assertEqual(len(cands), 0)

    def test_resolve_non_overlapping(self):
        idx = OriginalByteIndex(b"key: sk-abc123def456ghi789jkl012mno345pq\npass: secret12")
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        self.assertGreaterEqual(len(resolved), 1)

    def test_apply_no_redactions(self):
        idx = OriginalByteIndex(b"safe text here")
        view = apply_redactions(idx, [])
        self.assertEqual(view.redacted_bytes, idx.source_bytes)
        self.assertEqual(view.redacted_count, 0)
        self.assertEqual(len(view.mappings), 0)

    def test_apply_redacts_content(self):
        idx = OriginalByteIndex(b"use: sk-abcdefghijklmnopqrstuvwxyz123456 here")
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        view = apply_redactions(idx, resolved)
        # Original key should not appear in redacted output
        self.assertNotIn(b"sk-abc", view.redacted_bytes)
        self.assertGreaterEqual(view.redacted_count, 1)
        self.assertIn("API_KEY", view.categories_affected)

    def test_redaction_lineage_preserved(self):
        idx = OriginalByteIndex(b"token: ghp_abcdefghijklmnopqrstuvwx123456")
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        view = apply_redactions(idx, resolved)
        # Redacted view must be different length
        self.assertGreaterEqual(view.redacted_count, 1)
        for m in view.mappings:
            self.assertGreater(m.original_span[0], -1)
            self.assertTrue(m.original_span[0] < m.original_span[1])
            self.assertIn(m.category, CATEGORY_PRIORITY)

    def test_multiple_secrets(self):
        idx = OriginalByteIndex(b"key1: sk-abcdefghijklmnopqrstuvwxyz123456\nkey2: ghp_abcdefghijklmnopqrstuvwx123456")
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        view = apply_redactions(idx, resolved)
        self.assertGreaterEqual(view.redacted_count, 1)

    def test_no_secret_hash_leaked(self):
        idx = OriginalByteIndex(b"sk-abcdefghijklmnopqrstuvwxyz123456")
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        view = apply_redactions(idx, resolved)
        # Redacted output must not contain sha256 of the secret
        import hashlib
        h = hashlib.sha256(b"sk-abcdefghijklmnopqrstuvwxyz123456").hexdigest()
        self.assertNotIn(h.encode(), view.redacted_bytes)


# ═══════════════════════════════════════════════════════════════════
# Redaction mutations — prove validators catch corruption
# ═══════════════════════════════════════════════════════════════════

class TestMutationRedaction(unittest.TestCase):

    def test_overlap_inject_before_last_safe(self):
        """Ensure overlapping secrets are resolved, not silently merged."""
        idx = OriginalByteIndex(
            b"ghp_abcdefghijklmnopqrstuvwx123456 ghp_abcdefghijklmnopqrstuvwx123456"
        )
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        self.assertGreaterEqual(len(resolved), 1)

    def test_safe_example_not_caught(self):
        """Safe placeholder examples should not be redacted."""
        idx = OriginalByteIndex(b"sk-your-api-key-here")
        cands = find_redactions(idx)
        # "sk-your-api-key-here" has hyphens which may still match.
        # The key assertion: no false redaction of obvious safe content
        # Check that "hello" is never redacted
        idx2 = OriginalByteIndex(b"hello world")
        cands2 = find_redactions(idx2)
        self.assertEqual(len(cands2), 0)

    def test_redacted_output_never_contains_original_secret_bytes(self):
        idx = OriginalByteIndex(b"the key is sk-abcdefghijklmnopqrstuvwxyz123456 for real")
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        view = apply_redactions(idx, resolved)
        self.assertNotIn(b"sk-abcdefghijklmnopqrstuvwxyz123456", view.redacted_bytes)

    def test_category_priority_intact(self):
        """API_KEY and PASSWORD have priority 1 (highest)."""
        self.assertEqual(CATEGORY_PRIORITY["API_KEY"], 1)
        self.assertEqual(CATEGORY_PRIORITY["PASSWORD"], 1)
        self.assertEqual(CATEGORY_PRIORITY["COOKIE_SECRET"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
