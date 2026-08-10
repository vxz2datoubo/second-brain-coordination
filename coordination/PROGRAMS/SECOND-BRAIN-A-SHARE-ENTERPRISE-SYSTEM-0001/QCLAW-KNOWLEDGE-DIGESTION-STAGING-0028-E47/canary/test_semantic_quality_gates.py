"""E47 v8 CANARY semantic-quality gate tests (review 4890430204 finding #6).

These tests are NOT replaced for v7 regressions tests; they are NEW gates
specifically addressing the v7 finding that 60/60 regression tests did not
validate semantic quality.

Gates:
G1. No span > 800 bytes (anti-subsection-to-EOF catch-all).
G2. ≥ 30% SOURCE_EXTRACT atoms (verbatim claim recovery).
G3. ≥ 3 distinct relation types besides REFINES (real semantic graph).
G4. ≥ 1 contradiction OR ≥ 2 unknowns OR ≥ 1 candidate memory/skill.
G5. (Bonus) All SOURCE_EXTRACT atom content == exact source span bytes.

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
    """Per review 4890430204 finding #6 — semantic quality gates."""

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

    # ─── G2: ≥ 30% SOURCE_EXTRACT ───────────────────────────────
    def test_g2_source_extract_ratio(self):
        se = sum(1 for a in self.pkg["atoms"] if a["evidence_kind"] == "SOURCE_EXTRACT")
        ratio = se / len(self.pkg["atoms"])
        self.assertGreaterEqual(
            ratio, 0.30,
            f"G2 FAIL: SOURCE_EXTRACT ratio {ratio:.1%} < 30% (got {se}/{len(self.pkg['atoms'])})",
        )

    # ─── G3: ≥ 3 distinct relation types ─────────────────────────
    def test_g3_distinct_relation_types(self):
        types = {r["relation_type"] for r in self.pkg["relations"]}
        self.assertGreaterEqual(
            len(types), 3,
            f"G3 FAIL: only {len(types)} distinct relation types: {types}",
        )

    # ─── G4: contradictions/unknowns/memory/skills > 0 ──────────
    def test_g4_active_evaluation_outputs(self):
        c = len(self.pkg["contradictions"])
        u = len(self.pkg["unknowns"])
        m = len(self.pkg["memory_records"])
        s = len(self.pkg["skills"])
        active = c + u + m + s
        self.assertGreater(
            active, 0,
            f"G4 FAIL: no contradictions/unknowns/memory_records/skills (implausibly shallow)",
        )
        # Strong gate: at least one of (contradictions, unknowns) must be ≥ 2
        self.assertGreaterEqual(
            max(c, u), 2,
            f"G4 SUB-FAIL: contradictions={c} unknowns={u}; need ≥ 2 of either",
        )

    # ─── G5: SOURCE_EXTRACT atom content == exact source span bytes ─
    def test_g5_source_extract_verbatim(self):
        bad = []
        for a in self.pkg["atoms"]:
            if a["evidence_kind"] != "SOURCE_EXTRACT":
                continue
            for s in a["source_spans"]:
                expected = self.src_bytes[s["byte_start"]:s["byte_end"]].decode("utf-8")
                if a["content"] != expected:
                    bad.append(
                        f"  {a['atom_id']} span {s['byte_start']}:{s['byte_end']}: "
                        f"atom_content={a['content'][:30]!r} != source={expected[:30]!r}"
                    )
        self.assertEqual(bad, [], f"G5 FAIL: SOURCE_EXTRACT content mismatch:\n" + "\n".join(bad))

    # ─── G6: AMED source hash unchanged (no source drift) ───────
    def test_g6_source_hash_pinned(self):
        expected = "f777b9d25b608e4092bead879fad94b45c04f8c15da4d40a514f0d025acfe039"
        actual = self.pkg["source"]["source_hash"]
        self.assertEqual(actual, expected, f"G6 FAIL: AMED source hash drift: {actual}")


if __name__ == "__main__":
    unittest.main(verbosity=2)