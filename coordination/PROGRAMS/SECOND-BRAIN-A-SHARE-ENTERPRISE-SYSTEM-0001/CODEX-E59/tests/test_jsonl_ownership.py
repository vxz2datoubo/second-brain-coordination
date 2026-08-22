from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e59_runtime.jsonl_ownership import JsonlOwnershipError, parse_jsonl_whole_source  # noqa: E402


class JsonlOwnershipTests(unittest.TestCase):
    def test_empty_source_is_explicit_and_complete(self) -> None:
        ownership = parse_jsonl_whole_source(b"")
        self.assertEqual(ownership.status, "EMPTY_SOURCE")
        self.assertEqual(ownership.segments, ())

    def test_crlf_blank_lines_and_record_are_all_owned(self) -> None:
        source = b"\r\n \t\r\n{\"a\":1}\r\n\n"
        ownership = parse_jsonl_whole_source(source)
        self.assertEqual(ownership.record_count, 1)
        self.assertEqual(ownership.byte_length, len(source))
        self.assertEqual(ownership.segments[0].kind, "LINE_TERMINATOR")
        ownership.assert_complete_partition()

    def test_final_record_without_terminator_is_owned(self) -> None:
        source = b"{\"a\":1}"
        ownership = parse_jsonl_whole_source(source)
        self.assertEqual(ownership.record_count, 1)
        self.assertEqual(ownership.segments[-1].raw.end, len(source))

    def test_invalid_json_fails_with_global_offset(self) -> None:
        with self.assertRaisesRegex(JsonlOwnershipError, "INVALID_JSONL_RECORD at byte offset 5"):
            parse_jsonl_whole_source(b"{\"a\":}\n")

    def test_non_utf8_fails_closed(self) -> None:
        with self.assertRaisesRegex(JsonlOwnershipError, "NON_UTF8_JSONL_RECORD"):
            parse_jsonl_whole_source(b"{\"a\":\xff}\n")

    def test_isolated_surrogate_fails_closed(self) -> None:
        with self.assertRaisesRegex(JsonlOwnershipError, "ISOLATED_SURROGATE at byte offset 6"):
            parse_jsonl_whole_source(b"{\"a\":\"\\uD800\"}\n")

    def test_valid_surrogate_pair_is_owned(self) -> None:
        ownership = parse_jsonl_whole_source(b"{\"a\":\"\\uD83D\\uDE00\"}\n")
        self.assertEqual(ownership.record_count, 1)

    def test_terminator_change_changes_whole_source_digest(self) -> None:
        self.assertNotEqual(parse_jsonl_whole_source(b"{\"a\":1}\n").source_sha256, parse_jsonl_whole_source(b"{\"a\":1}\r\n").source_sha256)
