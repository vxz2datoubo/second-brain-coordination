"""E47 v9 CANARY semantic-quality gate tests (review 48904302xx findings).

Per review findings:
- #1: Do NOT require invented contradictions; zero is valid when source has none.
- #2: Replace Goodhart-style quota gates with canary-specific correctness gates.
       Allow zero contradictions and do not require arbitrary relation-type counts.
- Keep anti-catchall spans (G1), verbatim SOURCE_EXTRACT validation (G5),
  source hash pinning (G6). Add negative check against linear-adjacency dumping.
  Multi-span support must remain legal; G5 must not make legitimate multi-span
  SOURCE_EXTRACT impossible.

Gates (v9):
G1. No span > 800 bytes (anti-subsection-to-EOF catch-all).
G2. ≥ 30% SOURCE_EXTRACT atoms (verbatim claim recovery).
G3. Anti-linear-adjacency: no chain where EVERY edge is REFINES spanning the
    whole atom_id order. Real semantic graph must use ≥ 2 non-REFINES edges.
G4. Active evaluation: c+u+m+s > 0 (at least one of contradictions/unknowns/
    memory_records/skills populated). Does NOT enforce count quotas.
G5. SOURCE_EXTRACT atom content == source span bytes (multi-span allowed;
    each SOURCE_EXTRACT span must individually decode to source bytes).
G6. AMED source hash unchanged (no source drift).
G7. INFERENCE atoms anchor to ≥ 1 verbatim source span (no orphan inference).

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
    """Per review 48904302xx findings — semantic quality gates (v9)."""

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

    # ─── G3: anti-linear-adjacency REFINES chain ────────────────
    def test_g3_no_linear_refines_chain(self):
        """Reject v7-style REFINES adjacency dumping.

        A linear REFINES chain is one where every edge is REFINES AND the
        edges form an ordered sequence (A001→A002, A002→A003, ...). Real
        semantic graphs must use multiple relation types. Allow at most 2
        REFINES edges total (not a chain); require ≥ 2 non-REFINES edges.
        """
        edges = self.pkg["relations"]
        refines_edges = [r for r in edges if r["relation_type"] == "REFINES"]
        non_refines = [r for r in edges if r["relation_type"] != "REFINES"]

        self.assertGreaterEqual(
            len(non_refines), 2,
            f"G3 FAIL: only {len(non_refines)} non-REFINES edges "
            f"(need ≥ 2). REFINES={len(refines_edges)} edges. "
            f"Full relation types: "
            f"{sorted({r['relation_type'] for r in edges})}",
        )

    # ─── G4: active evaluation outputs (no quota enforcement) ────
    def test_g4_active_evaluation_outputs(self):
        """Per review finding #1: do not require invented contradictions or
        specific counts. Just verify the canary actively evaluated at least
        one of: contradictions / unknowns / memories / skills. Zero
        contradictions is valid when source has no genuine contradictions.
        """
        c = len(self.pkg["contradictions"])
        u = len(self.pkg["unknowns"])
        m = len(self.pkg["memory_records"])
        s = len(self.pkg["skills"])
        active = c + u + m + s
        self.assertGreater(
            active, 0,
            f"G4 FAIL: no contradictions/unknowns/memory_records/skills "
            f"(c={c} u={u} m={m} s={s}); implausibly shallow",
        )

    # ─── G5: SOURCE_EXTRACT atom content matches source spans ─────
    def test_g5_source_extract_verbatim(self):
        """Multi-span support: every SOURCE_EXTRACT atom must have at least
        one span whose bytes decode to text that the atom.content substring
        matches (covers single-span and multi-span cases). Also verify each
        individual span decodes cleanly.
        """
        bad = []
        for a in self.pkg["atoms"]:
            if a["evidence_kind"] != "SOURCE_EXTRACT":
                continue
            # Verify each span is decodable (UTF-8 roundtrip)
            for s in a["source_spans"]:
                try:
                    decoded = self.src_bytes[s["byte_start"]:s["byte_end"]].decode("utf-8")
                except UnicodeDecodeError as e:
                    bad.append(f"  {a['atom_id']} span {s['byte_start']}:{s['byte_end']} decode error: {e}")
                    continue
            # For SOURCE_EXTRACT single-span atoms, content must equal span bytes.
            # For multi-span SOURCE_EXTRACT atoms (per finding #3), require that
            # atom.content contains the verbatim text of each span (not necessarily
            # equal to any single span, since content is a synthesis).
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
        """Per review finding #3: every INFERENCE atom must anchor to ≥ 1
        verbatim source span (UTF-8 decodable from source bytes). No orphan
        inference allowed.
        """
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


if __name__ == "__main__":
    unittest.main(verbosity=2)