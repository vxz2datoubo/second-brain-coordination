"""E52 S0 product and real-source mutation tests."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROGRAM_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from e52_strict_byte import ByteTruthIndex, ScannerProgressError


class TestImmutableIndex(unittest.TestCase):
    def test_private_assignment_and_new_attribute_are_blocked(self):
        index = ByteTruthIndex(b"abc")
        with self.assertRaises(AttributeError):
            index._total_bytes = 99
        with self.assertRaises(AttributeError):
            index.untrusted_alias = b"x"

    def test_exposed_collections_cannot_be_mutated(self):
        index = ByteTruthIndex("a€b".encode("utf-8"))
        with self.assertRaises(TypeError):
            index.boundary_to_codepoint()[0] = 99
        with self.assertRaises(Exception):
            index.chunks()[0].byte_start = 99

    def test_boundary_and_containing_apis_have_distinct_eof_rules(self):
        index = ByteTruthIndex("a€b".encode("utf-8"))
        self.assertEqual(index.codepoint_index_at_boundary(0), 0)
        self.assertEqual(index.codepoint_index_at_boundary(1), 1)
        self.assertEqual(index.codepoint_index_at_boundary(4), 2)
        self.assertEqual(index.codepoint_index_at_boundary(5), 3)
        with self.assertRaises(ValueError):
            index.codepoint_index_at_boundary(2)
        self.assertEqual((index.chunk_containing_byte(2).byte_start, index.chunk_containing_byte(2).byte_end), (1, 4))
        with self.assertRaises(IndexError):
            index.chunk_containing_byte(5)

    def test_line_model_has_no_zero_length_ownership_claim(self):
        records = ByteTruthIndex(b"a\r\n\r\n").line_records()
        self.assertEqual(len(records), 3)
        self.assertEqual((records[0].content_start, records[0].content_end), (0, 1))
        self.assertTrue(records[1].is_blank)
        self.assertEqual((records[1].terminator_start, records[1].terminator_end), (3, 5))
        self.assertTrue(records[2].has_trailing_empty_line)
        self.assertIsNone(records[2].terminator_start)


class TestProductionMutationProbe(unittest.TestCase):
    def test_mutated_real_0xed_branch_times_out_and_child_is_reaped(self):
        source_path = SRC_ROOT / "e52_strict_byte" / "index.py"
        source = source_path.read_text(encoding="utf-8")
        mutated = source.replace(
            "next_index = i + 3  # E52_0XED_PROGRESS_ANCHOR",
            "next_index = i  # E52_0XED_PROGRESS_ANCHOR_MUTATED",
            1,
        ).replace(
            "raise ScannerProgressError(\"UTF-8 scanner made no progress\")",
            "continue  # E52_PROGRESS_GUARD_MUTATED",
            1,
        )
        self.assertNotEqual(source, mutated)
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            module_path = temporary_path / "mutated_index.py"
            module_path.write_text(mutated, encoding="utf-8")
            command = [
                sys.executable,
                "-c",
                "import importlib.util,sys; p=importlib.util.spec_from_file_location('m', r'" + str(module_path) + "'); m=importlib.util.module_from_spec(p); sys.modules[p.name]=m; p.loader.exec_module(m); m._scan_utf8_strict(bytes([0xED,0x80,0x80]))",
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                process.communicate(timeout=0.5)
                self.fail("mutated production scanner unexpectedly terminated")
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=2)
            self.assertIsNotNone(process.returncode)
            self.assertIsNotNone(process.poll())

    def test_real_scanner_rejects_surrogate_without_hanging(self):
        with self.assertRaises(ValueError):
            ByteTruthIndex(bytes([0xED, 0xA0, 0x80]))
        self.assertTrue(issubclass(ScannerProgressError, ValueError))


if __name__ == "__main__":
    unittest.main(verbosity=2)
