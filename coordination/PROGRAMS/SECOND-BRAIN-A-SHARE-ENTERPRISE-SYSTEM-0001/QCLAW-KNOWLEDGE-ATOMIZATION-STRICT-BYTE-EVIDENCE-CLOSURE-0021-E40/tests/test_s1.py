"""E40 S1 — ByteLedger mutation + functional tests"""
import unittest, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"


class TestOwnershipSpan(unittest.TestCase):
    def test_valid_span(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        s = OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "atom-1")
        self.assertEqual(s.byte_start, 0)
        self.assertEqual(s.byte_end, 5)

    def test_zero_length_rejected(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        with self.assertRaises(ValueError) as ctx:
            OwnershipSpan(5, 5, Owner.ATOM_CANDIDATE)
        self.assertIn("zero_length", str(ctx.exception))

    def test_negative_start_rejected(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        with self.assertRaises(ValueError):
            OwnershipSpan(-1, 5, Owner.ATOM_CANDIDATE)

    def test_negative_end_rejected(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        with self.assertRaises(ValueError):
            OwnershipSpan(0, -1, Owner.ATOM_CANDIDATE)

    def test_inverted_rejected(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        with self.assertRaises(ValueError) as ctx:
            OwnershipSpan(5, 3, Owner.ATOM_CANDIDATE)
        self.assertIn("inverted", str(ctx.exception))

    def test_invalid_owner(self):
        from qclaw_e40.ledger import OwnershipSpan
        with self.assertRaises(ValueError):
            OwnershipSpan(0, 5, "GARBAGE")

    def test_all_three_owners_accepted(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        for o in Owner:
            s = OwnershipSpan(0, 5, o)
            self.assertEqual(s.owner, o)

    def test_overlap_detection(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        a = OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE)
        b = OwnershipSpan(3, 8, Owner.ATOM_CANDIDATE)
        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

    def test_no_overlap_adjacent(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        a = OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE)
        b = OwnershipSpan(5, 10, Owner.ATOM_CANDIDATE)
        self.assertFalse(a.overlaps(b))
        self.assertFalse(b.overlaps(a))


class TestByteLedgerMutation(unittest.TestCase):
    """Mutation tests — prove that violations are rejected."""

    def test_out_of_range_start_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(10)
        with self.assertRaises(ValueError) as ctx:
            ledger.add(10, 12, Owner.ATOM_CANDIDATE)
        self.assertIn("out_of_range", str(ctx.exception))

    def test_out_of_range_end_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(10)
        with self.assertRaises(ValueError) as ctx:
            ledger.add(5, 11, Owner.ATOM_CANDIDATE)
        self.assertIn("out_of_range", str(ctx.exception))

    def test_overlap_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(5, 10, Owner.ATOM_CANDIDATE)
        with self.assertRaises(ValueError) as ctx:
            ledger.add(8, 12, Owner.ATOM_CANDIDATE)
        self.assertIn("overlap", str(ctx.exception))

    def test_exact_duplicate_overlap_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(5, 10, Owner.ATOM_CANDIDATE)
        with self.assertRaises(ValueError):
            ledger.add(5, 10, Owner.ATOM_CANDIDATE)

    def test_contained_overlap_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(5, 15, Owner.ATOM_CANDIDATE)
        with self.assertRaises(ValueError):
            ledger.add(7, 10, Owner.ATOM_CANDIDATE)

    def test_finalize_detects_gap(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(0, 10, Owner.ATOM_CANDIDATE)
        # gap: [10, 20)
        with self.assertRaises(ValueError) as ctx:
            ledger.finalize()
        self.assertIn("finalize_failed", str(ctx.exception))

    def test_add_after_finalize_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(10)
        ledger.add(0, 10, Owner.ATOM_CANDIDATE)
        ledger.finalize()
        with self.assertRaises(RuntimeError) as ctx:
            ledger.add(0, 5, Owner.STRUCTURE)
        self.assertIn("finalized", str(ctx.exception))

    def test_add_after_freeze_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(0, 10, Owner.ATOM_CANDIDATE)
        ledger.freeze()
        with self.assertRaises(RuntimeError) as ctx:
            ledger.add(10, 20, Owner.ATOM_CANDIDATE)
        self.assertIn("frozen", str(ctx.exception))

    def test_illegal_owner_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(10)
        with self.assertRaises(ValueError):
            ledger.add(0, 5, "ILLEGAL_OWNER")

    def test_negative_total_rejected(self):
        from qclaw_e40.ledger import ByteLedger
        with self.assertRaises(ValueError):
            ByteLedger(-1)


class TestByteLedgerFunctional(unittest.TestCase):
    def test_full_coverage_no_gap(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(0, 10, Owner.ATOM_CANDIDATE, "a")
        ledger.add(10, 15, Owner.STRUCTURE, "header")
        ledger.add(15, 20, Owner.ATOM_CANDIDATE, "b")
        ledger.finalize()
        cov = ledger.coverage()
        self.assertEqual(cov["covered_bytes"], 20)
        self.assertEqual(cov["gap_count"], 0)
        self.assertTrue(cov["finalized"])

    def test_empty_ledger_finalize_fails(self):
        from qclaw_e40.ledger import ByteLedger
        ledger = ByteLedger(5)
        with self.assertRaises(ValueError):
            ledger.finalize()

    def test_coverage_counts_owners(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(30)
        ledger.add(0, 10, Owner.ATOM_CANDIDATE)
        ledger.add(10, 15, Owner.STRUCTURE)
        ledger.add(15, 30, Owner.UNKNOWN_ERROR)
        cov = ledger.coverage()
        self.assertIn("ATOM_CANDIDATE", cov["owners"])
        self.assertIn("STRUCTURE", cov["owners"])
        self.assertIn("UNKNOWN_ERROR", cov["owners"])
        self.assertEqual(cov["owners"]["ATOM_CANDIDATE"], 10)
        self.assertEqual(cov["owners"]["STRUCTURE"], 5)
        self.assertEqual(cov["owners"]["UNKNOWN_ERROR"], 15)

    def test_multiple_gaps_detected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(30)
        ledger.add(0, 5, Owner.ATOM_CANDIDATE)
        ledger.add(10, 15, Owner.STRUCTURE)
        ledger.add(20, 25, Owner.ATOM_CANDIDATE)
        # gaps: [5,10), [15,20), [25,30)
        with self.assertRaises(ValueError) as ctx:
            ledger.finalize()
        self.assertIn("finalize_failed", str(ctx.exception))
        self.assertIn("3 gaps", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
