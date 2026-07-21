"""Tests for Work Packages F and G — Regression Dataset + Evaluation Metrics."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from store import MemoryStore
from fusion import FusionEngine
from retrieval import HybridRetrieval
from eval import REGRESSION_DATASET, EvalReport, RetrievalEvaluator

def setup_store():
    """Create a store with known content for eval."""
    s = MemoryStore(':memory:').connect()
    fe = FusionEngine(s)
    for i in range(3):
        pkt = {
            'id': f'pkt_{i}',
            'atoms': [
                {'id': f'a{i}1', 'atom_type': 'FACT', 'canonical_statement': f'Test fact {i}-1', 'confidence': 0.8 + i*0.05, 'scope': 'test'},
                {'id': f'a{i}2', 'atom_type': 'CONCEPT', 'canonical_statement': f'Test concept {i}-2', 'confidence': 0.75, 'scope': 'test'},
            ],
            'relations': [
                {'id': f'r{i}', 'relation_type': 'RELATED_TO', 'from_atom_id': f'a{i}1', 'to_atom_id': f'a{i}2'},
            ],
            'unknowns': [
                {'id': f'u{i}', 'question': f'What about test case {i}?', 'scope': 'test'},
            ],
        }
        fe.fuse_packet(pkt)
    # FTS index
    for prefix in ['a0', 'a1', 'a2']:
        s.index_atom_terms(f'{prefix}1', [('test', 1.0), ('fact', 0.8)])
        s.index_atom_terms(f'{prefix}2', [('test', 1.0), ('concept', 0.7)])
    # Conflicts
    s.insert_atom({'id': 'c1', 'atom_type': 'FACT', 'canonical_statement': 'X is true', 'confidence': 0.7})
    s.insert_atom({'id': 'c2', 'atom_type': 'FACT', 'canonical_statement': 'X is false', 'confidence': 0.6})
    s.insert_relation({'id': 'cr1', 'relation_type': 'CONTRADICTS', 'from_atom_id': 'c1', 'to_atom_id': 'c2'})
    s.insert_conflict({'id': 'conf1', 'atom_id_a': 'c1', 'atom_id_b': 'c2', 'conflict_type': 'DIRECT', 'resolution_status': 'UNRESOLVED'})
    return s

def test_dataset_size():
    assert len(REGRESSION_DATASET) >= 30, f"Dataset too small: {len(REGRESSION_DATASET)}"
    print(f"  ✅ test_dataset_size — {len(REGRESSION_DATASET)} queries")

def test_eval_report_creation():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    assert report.total_queries == len(REGRESSION_DATASET)
    assert report.passed + report.failed == report.total_queries
    assert report.pass_rate >= 0.0
    s = report.summary()
    print(f"  ✅ test_eval_report_creation — pass_rate={report.pass_rate:.2f}, mrr={s['mrr']:.3f}")

def test_eval_metrics():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    # All metrics should be computable
    r10 = report.recall_at_k(10)
    p10 = report.precision_at_k(10)
    mrr = report.mrr()
    cc = report.conflict_coverage()
    uc = report.unknown_coverage()
    print(f"  ✅ test_eval_metrics — R@10={r10:.3f} P@10={p10:.3f} MRR={mrr:.3f} CC={cc:.3f} UC={uc:.3f}")

def test_conflict_coverage():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    cc = report.conflict_coverage()
    assert cc >= 0.0 and cc <= 1.0
    print(f"  ✅ test_conflict_coverage — {cc:.3f}")

def test_unknown_coverage():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    uc = report.unknown_coverage()
    assert uc >= 0.0 and uc <= 1.0
    print(f"  ✅ test_unknown_coverage — {uc:.3f}")

def test_failed_queries_detail():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    if report.failed > 0:
        print(f"  i test_failed_queries_detail — {report.failed} failed:")
        for qr in report.query_results:
            if not qr.passed:
                print(f"    - {qr.query.get('query','')}: {qr.failures}")
    else:
        print(f"  ✅ test_failed_queries_detail — all passed")

def test_pass_rate_acceptable():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    # At least 60% pass rate is acceptable for synthetic data
    assert report.pass_rate >= 0.6, f"Pass rate too low: {report.pass_rate:.2f}"
    print(f"  ✅ test_pass_rate_acceptable — {report.pass_rate:.2f}")

def test_individual_query_result():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    # Each QueryResult should have necessary fields
    for qr in report.query_results:
        assert hasattr(qr, 'query')
        assert hasattr(qr, 'result_count')
        assert hasattr(qr, 'matched_ids')
        assert hasattr(qr, 'passed')
    print(f"  ✅ test_individual_query_result — all {len(report.query_results)} query results valid")

def test_summary_round_trip():
    s = setup_store()
    evaluator = RetrievalEvaluator(s)
    report = evaluator.run("test_dataset")
    s2 = report.summary()
    j = json.dumps(s2)
    s3 = json.loads(j)
    assert s3["queries"]["total"] == len(REGRESSION_DATASET)
    print(f"  ✅ test_summary_round_trip — JSON serializable")

def run_all():
    tests = [
        test_dataset_size, test_eval_report_creation, test_eval_metrics,
        test_conflict_coverage, test_unknown_coverage, test_failed_queries_detail,
        test_pass_rate_acceptable, test_individual_query_result, test_summary_round_trip,
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
    print(f"\n✅ {passed}/{len(tests)} Work Packages F/G tests passed")

if __name__ == "__main__":
    run_all()
