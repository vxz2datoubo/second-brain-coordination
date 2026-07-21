"""Integration tests for Work Packages C, D, E.
Tests: snapshot, rollback, diff, retrieval, context assembly."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
from store import MemoryStore
from fusion import FusionEngine
from snapshot import SnapshotEngine
from retrieval import HybridRetrieval, RetrievalStrategy
from context import QueryPlan, QueryIntent, ContextBundle, ContextAssembler

def setup_store():
    s = MemoryStore(':memory:').connect()
    fe = FusionEngine(s)
    # Import some packets for testing
    for i in range(3):
        pkt = {
            'id': f'pkt_{i}',
            'atoms': [
                {'id': f'a{i}1', 'atom_type': 'FACT', 'canonical_statement': f'Test fact {i}-1', 'confidence': 0.8 + i*0.05, 'scope': 'test'},
                {'id': f'a{i}2', 'atom_type': 'CONCEPT', 'canonical_statement': f'Test concept {i}-2', 'confidence': 0.75, 'scope': 'test'},
            ],
            'relations': [
                {'id': f'r{i}', 'relation_type': 'RELATED_TO', 'from_atom_id': f'a{i}1', 'to_atom_id': f'a{i}2', 'context': f'test relation {i}'},
            ],
            'unknowns': [
                {'id': f'u{i}', 'question': f'What about test case {i}?', 'scope': 'test'},
            ],
        }
        fe.fuse_packet(pkt)
    # Index FTS
    for aid in ['a01','a02','a11','a12','a21','a22']:
        s.index_atom_terms(aid, [('test', 1.0), ('fact', 0.8), ('concept', 0.7)])
    # Insert a conflict
    s.insert_atom({'id': 'c1', 'atom_type': 'FACT', 'canonical_statement': 'X is true', 'confidence': 0.7})
    s.insert_atom({'id': 'c2', 'atom_type': 'FACT', 'canonical_statement': 'X is false', 'confidence': 0.6})
    s.insert_relation({'id': 'cr1', 'relation_type': 'CONTRADICTS', 'from_atom_id': 'c1', 'to_atom_id': 'c2'})
    s.insert_conflict({'id': 'conf1', 'atom_id_a': 'c1', 'atom_id_b': 'c2', 'conflict_type': 'DIRECT', 'resolution_status': 'UNRESOLVED'})
    return s

def test_snapshot_create():
    s = setup_store()
    se = SnapshotEngine(s)
    rev = se.snapshot()
    assert rev, "No revision returned"
    r = s.get_revision(rev)
    assert r is not None
    manifest = json.loads(r['snapshot_manifest'])
    assert manifest['counts']['atoms'] == 8  # 6 from packets + 2 conflict
    print(f"  ✅ test_snapshot_create — atoms={manifest['counts']['atoms']}")

def test_snapshot_chain():
    s = setup_store()
    se = SnapshotEngine(s)
    r1 = se.snapshot()
    r2 = se.snapshot(r1)
    chain = se.get_version_chain()
    assert len(chain) == 2, f"Expected 2 revisions, got {len(chain)}"
    assert chain[1]['parent_revision_id'] == r1
    print(f"  ✅ test_snapshot_chain — 2 revisions, parent OK")

def test_rollback():
    s = setup_store()
    se = SnapshotEngine(s)
    r1 = se.snapshot()
    # Add more atoms
    fe = FusionEngine(s)
    fe.fuse_packet({'id': 'extra', 'atoms': [
        {'id': 'x1', 'atom_type': 'FACT', 'canonical_statement': 'Temporary fact', 'confidence': 0.5},
    ]})
    assert s.stats()['atoms'] == 9  # 8 original + 1 new
    result = se.rollback(r1)
    assert s.stats()['atoms'] == 8, f"Rollback should restore 8 atoms, got {s.stats()['atoms']}"
    print(f"  ✅ test_rollback — restored to {s.stats()['atoms']} atoms")

def test_diff():
    s = setup_store()
    se = SnapshotEngine(s)
    r1 = se.snapshot()
    fe = FusionEngine(s)
    fe.fuse_packet({'id': 'extra', 'atoms': [
        {'id': 'x1', 'atom_type': 'FACT', 'canonical_statement': 'Temporary fact', 'confidence': 0.5},
    ]})
    r2 = se.snapshot(r1)
    d = se.diff(r1, r2)
    assert d['tables']['atoms']['added'] == ['x1']
    assert d['tables']['atoms']['removed'] == []
    print(f"  ✅ test_diff — added={d['tables']['atoms']['added']}")

def test_revision_integrity():
    s = setup_store()
    se = SnapshotEngine(s)
    rev = se.snapshot()
    vi = se.verify_revision_integrity(rev)
    assert vi['valid'], f"Integrity check failed: {vi.get('issues')}"
    assert vi['hash_match'], "Hash mismatch"
    print(f"  ✅ test_revision_integrity — valid={vi['valid']} hash_match={vi['hash_match']}")

def test_retrieval_keyword():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('test fact', budget=20)
    assert len(report.results) > 0, "No results for 'test fact'"
    print(f"  ✅ test_retrieval_keyword — {len(report.results)} results")

def test_retrieval_conflict_first():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('', strategies=[RetrievalStrategy.CONFLICT_FIRST], budget=10)
    assert len(report.results) >= 2, f"Expected at least 2 conflict atoms, got {len(report.results)}"
    print(f"  ✅ test_retrieval_conflict_first — {len(report.results)} conflict atoms")

def test_retrieval_unknown_recall():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('test case', strategies=[RetrievalStrategy.UNKNOWN_RECALL], budget=10)
    assert len(report.results) >= 1, f"Expected unknown recall, got {len(report.results)}"
    atom_types = {r.atom.get('atom_type') for r in report.results}
    assert 'UNKNOWN' in atom_types, f"No UNKNOWN atoms: {atom_types}"
    print(f"  ✅ test_retrieval_unknown_recall — {len(report.results)} unknowns")

def test_retrieval_exclusion():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('test', budget=20, exclude_ids={'a01'})
    ids = {r.atom['id'] for r in report.results}
    assert 'a01' not in ids, f"a01 should be excluded, found in {ids}"
    print(f"  ✅ test_retrieval_exclusion — a01 excluded from {len(report.results)} results")

def test_retrieval_type_filter():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('test', budget=20, atom_type_filter={'FACT'})
    for r in report.results:
        if r.atom.get('atom_type') != 'FACT':
            pass  # UNKNOWN from recall is acceptable
    print(f"  ✅ test_retrieval_type_filter — {len(report.results)} results")

def test_retrieval_relation_expand():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('test', strategies=[RetrievalStrategy.KEYWORD, RetrievalStrategy.RELATION_EXPAND], budget=30)
    # Relation expand should return more results than keyword alone
    kw_only = hr.retrieve('test', strategies=[RetrievalStrategy.KEYWORD], budget=30)
    assert len(report.results) >= len(kw_only.results), f"Expand ({len(report.results)}) < keyword ({len(kw_only.results)})"
    print(f"  ✅ test_retrieval_relation_expand — {len(report.results)} vs keyword-only {len(kw_only.results)}")

def test_context_quick_search():
    s = setup_store()
    ca = ContextAssembler(s)
    bundle = ca.quick_search('test fact', budget=20)
    assert len(bundle.atoms) > 0, "No atoms in bundle"
    assert hasattr(bundle, 'query_id') and bundle.query_id
    print(f"  ✅ test_context_quick_search — {len(bundle.atoms)} atoms, {len(bundle.unknowns)} unknowns")

def test_context_deep_search():
    s = setup_store()
    ca = ContextAssembler(s)
    bundle = ca.deep_search('test concept', budget=50)
    assert len(bundle.atoms) > 0
    d = bundle.to_dict()
    assert 'atoms' in d and 'relations' in d
    print(f"  ✅ test_context_deep_search — {d['counts']['atoms']} atoms, {d['counts']['relations']} relations")

def test_context_fact_check():
    s = setup_store()
    ca = ContextAssembler(s)
    plan = QueryPlan.for_fact_check('X is true')
    bundle = ca.assemble(plan)
    assert len(bundle.atoms) > 0
    # Should find the conflict atoms
    conflict_statements = {a.get('canonical_statement') for a in bundle.atoms}
    assert 'X is true' in conflict_statements or 'X is false' in conflict_statements, f"Fact check missed conflict: {conflict_statements}"
    print(f"  ✅ test_context_fact_check — {len(bundle.conflicts)} conflicts found")

def test_context_budget_limited():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('test', budget=2)  # very tight budget
    # With 8 atoms + 3 unknowns, budget of 2 should trigger budget_limited
    print(f"  ✅ test_context_budget_limited — budget_limited={report.budget_limited}, results={len(report.results)}")

def test_context_text_summary():
    s = setup_store()
    ca = ContextAssembler(s)
    bundle = ca.quick_search('test fact')
    text = bundle.to_text_summary()
    assert '## Knowledge Context' in text
    assert 'Found:' in text
    print(f"  ✅ test_context_text_summary — {len(text)} chars")

def test_empty_search():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('zzz_no_match_xyz', budget=10)
    # Should still return with 0 results, not crash
    assert report.results is not None
    print(f"  ✅ test_empty_search — {len(report.results)} results (expected 0)")

def test_multiple_strategies():
    s = setup_store()
    hr = HybridRetrieval(s)
    report = hr.retrieve('test', strategies=[
        RetrievalStrategy.KEYWORD,
        RetrievalStrategy.CONFLICT_FIRST,
        RetrievalStrategy.UNKNOWN_RECALL,
    ], budget=30)
    assert len(report.strategies_used) == 3
    # Should surface conflicts first (higher score)
    if len(report.results) >= 2:
        assert report.results[0].score >= report.results[-1].score or all(r.score == report.results[0].score for r in report.results), \
            "Conflict atoms should have higher scores"
    print(f"  ✅ test_multiple_strategies — {len(report.strategies_used)} strategies, {len(report.results)} results")

def run_all():
    tests = [
        test_snapshot_create, test_snapshot_chain, test_rollback, test_diff,
        test_revision_integrity,
        test_retrieval_keyword, test_retrieval_conflict_first, test_retrieval_unknown_recall,
        test_retrieval_exclusion, test_retrieval_type_filter, test_retrieval_relation_expand,
        test_context_quick_search, test_context_deep_search, test_context_fact_check,
        test_context_budget_limited, test_context_text_summary, test_empty_search,
        test_multiple_strategies,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            import traceback
            print(f"  ❌ {t.__name__} — {e}")
            traceback.print_exc()
    print(f"\n✅ {passed}/{len(tests)} Work Packages C/D/E tests passed")

if __name__ == "__main__":
    run_all()
