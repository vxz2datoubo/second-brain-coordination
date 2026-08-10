"""E47 v10 CANARY semantic-quality gate tests (review 4898300855 findings).

Per review findings (final narrow canary patch):
- #1: serialized summary must agree with serialized payload. Solved in
  build script by deriving counts from the built pkg object (post-build
  summary mutation). Tests do not duplicate this check; this is the
  build-script responsibility.
- #2: replace remaining Goodhart-style quota gates with concrete correctness
  assertions. For this canary, gates should detect bad patterns, not demand
  counts. Removed: SOURCE_EXTRACT percentage requirement, non-REFINES edge
  count requirement, output-nonzero requirement. Added: explicit canary-
  specific provenance check that A024 and A025 each carry ≥ 4 material
  source spans (the canary-specific four spans per inference atom).
- #3: confidence calibration moved to build script (A024/A025/M008 → MEDIUM).

Gates (v10):
G1. No span > 800 bytes (anti-subsection-to-EOF catch-all).
G3. No full ordered A001->A002->... all-REFINES adjacency chain (specific
    pattern, not a count quota). Adjacency chains using other relation types
    or REFINES mixed with other types are fine.
G5. SOURCE_EXTRACT single-span atom content == source span bytes (multi-span
    SOURCE_EXTRACT only requires spans to be decodable; full verbatim check
    is delegated to schema.validate()).
G6. AMED source hash unchanged (no source drift).
G7. INFERENCE atoms anchor to ≥ 1 verbatim source span (no orphan inference).
G8. Canary-specific: A024 and A025 each anchor to ≥ 4 material source spans.
G9. M008 confidence is MEDIUM (cross-section agent synthesis; not HIGH).

Removed in v10:
- G2 SOURCE_EXTRACT percentage (was quota, now unnecessary; SOURCE_EXTRACT
  verbatim is checked in G5 + schema.validate()).
- G3 ≥ N non-REFINES edges (replaced with anti-adjacency-chain pattern).
- G4 c+u+m+s > 0 (was output-nonzero quota; real absence is valid).

Run on dual Python 3.11.10 + 3.13.3; results must be identical.
"""
import hashlib
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)

PKG_PATH = os.path.abspath(os.path.join(HERE, "..", "packages", "E47-DIGEST-007.json"))
AMED_PATH = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "..", "..",
    "coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md",
))


def _load_pkg():
    with open(PKG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_source():
    with open(AMED_PATH, "r", encoding="utf-8") as f:
        return f.read()


class TestSemanticQualityGates(unittest.TestCase):
    """Per review 4898300855 findings — semantic quality gates (v10)."""

    @classmethod
    def setUpClass(cls):
        cls.pkg = _load_pkg()
        cls.src = _load_source()
        cls.src_bytes = cls.src.encode("utf-8")

    # ─── G1: no catch-all spans ─────────────────────────────────
    def test_g1_no_catchall_spans(self):
        bad = []
        for a in self.pkg["atoms"]:
            for s in a["source_spans"]:
                length = s["byte_end"] - s["byte_start"]
                if length > 800:
                    bad.append(f"  {a['atom_id']} span {s['byte_start']}:{s['byte_end']} = {length}B")
        self.assertEqual(bad, [], f"G1 FAIL: catch-all spans > 800 bytes:\n" + "\n".join(bad))

    # ─── G3: no full ordered A001→A002→... all-REFINES chain ────
    def test_g3_no_full_ordered_refines_chain(self):
        """Reject the specific anti-pattern: an ordered adjacency chain where
        every edge is REFINES and the target atom IDs form a consecutive
        numeric sequence (A001→A002→A003→...). Real semantic graphs can use
        REFINES mixed with other types; mixed chains are fine.
        """
        edges = self.pkg["relations"]
        # Build adjacency map for REFINES edges only.
        refines_adj = {}
        for r in edges:
            if r["relation_type"] == "REFINES":
                refines_adj.setdefault(r["source_atom_id"], []).append(r["target_atom_id"])

        # Detect longest ordered chain. A "chain" = edges (Axxx→Ayyy) where
        # yyy == xxx's number + 1 and all edges are REFINES.
        def _atom_num(aid):
            # Parse tail integer from "A001", "A010", "A123".
            tail = aid.lstrip("A")
            try:
                return int(tail)
            except ValueError:
                return None

        longest = 0
        # For each starting atom with outgoing REFINES edge, follow greedily.
        for start, targets in refines_adj.items():
            sn = _atom_num(start)
            if sn is None:
                continue
            cur = start
            cur_n = sn
            chain_len = 0
            while True:
                tgt_list = refines_adj.get(cur, [])
                # Look for target with number == cur_n + 1.
                next_target = None
                for t in tgt_list:
                    if _atom_num(t) == cur_n + 1:
                        next_target = t
                        break
                if next_target is None:
                    break
                cur = next_target
                cur_n += 1
                chain_len += 1
            longest = max(longest, chain_len)

        # For this canary, no ordered A001→A002→... all-REFINES chain
        # spanning more than 2 edges should exist.
        self.assertLessEqual(
            longest, 2,
            f"G3 FAIL: ordered all-REFINES adjacency chain length={longest} > 2 "
            f"(detected anti-pattern from v7)",
        )

    # ─── G5: SOURCE_EXTRACT atom content matches source spans ─────
    def test_g5_source_extract_verbatim(self):
        bad = []
        for a in self.pkg["atoms"]:
            if a["evidence_kind"] != "SOURCE_EXTRACT":
                continue
            for s in a["source_spans"]:
                try:
                    self.src_bytes[s["byte_start"]:s["byte_end"]].decode("utf-8")
                except UnicodeDecodeError as e:
                    bad.append(f"  {a['atom_id']} span {s['byte_start']}:{s['byte_end']} decode error: {e}")
                    continue
            if len(a["source_spans"]) == 1:
                span = a["source_spans"][0]
                expected = self.src_bytes[span["byte_start"]:span["byte_end"]].decode("utf-8")
                if a["content"] != expected:
                    bad.append(
                        f"  {a['atom_id']} single-span: "
                        f"content={a['content'][:30]!r} != span={expected[:30]!r}"
                    )
        self.assertEqual(bad, [], f"G5 FAIL: SOURCE_EXTRACT content mismatch:\n" + "\n".join(bad))

    # ─── G6: AMED source hash unchanged (no source drift) ───────
    def test_g6_source_hash_pinned(self):
        expected = "f777b9d25b608e4092bead879fad94b45c04f8c15da4d40a514f0d025acfe039"
        actual = self.pkg["source"]["source_hash"]
        self.assertEqual(actual, expected, f"G6 FAIL: AMED source hash drift: {actual}")

    # ─── G7: INFERENCE atoms anchor to ≥ 1 verbatim span ─────────
    def test_g7_inference_anchored(self):
        bad = []
        for a in self.pkg["atoms"]:
            if a["evidence_kind"] != "INFERENCE":
                continue
            if not a["source_spans"]:
                bad.append(f"  {a['atom_id']} INFERENCE with zero source_spans")
                continue
            for s in a["source_spans"]:
                try:
                    self.src_bytes[s["byte_start"]:s["byte_end"]].decode("utf-8")
                except (UnicodeDecodeError, KeyError) as e:
                    bad.append(f"  {a['atom_id']} span {s['byte_start']}:{s['byte_end']} invalid: {e}")
        self.assertEqual(bad, [], f"G7 FAIL: INFERENCE atoms not properly anchored:\n" + "\n".join(bad))

    # ─── G8: canary-specific — A024 and A025 each anchor ≥ 4 spans ──
    def test_g8_canary_specific_span_count(self):
        """Canary-specific provenance assertion: per review 48904302xx
        finding #3, A024 and A025 must each anchor to multiple material
        source spans (4 in this canary). This is a concrete, canary-
        specific check; it is not a quota but an explicit canary
        acceptance criterion.
        """
        targets = {"A024": 4, "A025": 4}
        bad = []
        for aid, required in targets.items():
            matches = [a for a in self.pkg["atoms"] if a["atom_id"] == aid]
            if not matches:
                bad.append(f"  {aid} missing entirely")
                continue
            a = matches[0]
            n_spans = len(a["source_spans"])
            if n_spans < required:
                bad.append(f"  {aid} has {n_spans} spans (canary needs ≥ {required})")
        self.assertEqual(bad, [], f"G8 FAIL: canary-specific span count:\n" + "\n".join(bad))

    # ─── G9: M008 confidence is MEDIUM ─────────────────────────
    def test_g9_m008_confidence_calibrated(self):
        """Per review 4898300855 finding #3, M008 is an agent cross-section
        synthesis (HIGH-confidence source claims combined with INFERENCE
        cross-section reasoning) and must be MEDIUM under the project
        confidence policy.
        """
        for m in self.pkg["memory_records"]:
            if m["record_id"] == "M008":
                self.assertEqual(
                    m["confidence"], "MEDIUM",
                    f"G9 FAIL: M008 confidence={m['confidence']}; expected MEDIUM "
                    f"(cross-section agent synthesis)",
                )
                return
        self.fail("G9 FAIL: M008 missing entirely")


if __name__ == "__main__":
    unittest.main(verbosity=2)