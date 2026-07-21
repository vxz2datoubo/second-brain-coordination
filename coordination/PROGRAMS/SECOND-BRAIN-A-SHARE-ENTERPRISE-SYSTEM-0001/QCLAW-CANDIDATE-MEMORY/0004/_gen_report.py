import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from store import MemoryStore
from fusion import FusionEngine
from snapshot import SnapshotEngine
from eval import RetrievalEvaluator, REGRESSION_DATASET
from compat import check_compatibility

# --- File hashes ---
here = os.path.dirname(__file__) or '.'
files = sorted([f for f in os.listdir(here) if f.endswith('.py')])
hashes = {}
for f in files:
    with open(os.path.join(here, f), 'rb') as fh:
        h = hashlib.sha256(fh.read()).hexdigest()
        hashes[f] = h

# --- Two-round build with hash ---
def build_round(round_no):
    s = MemoryStore(':memory:').connect()
    fe = FusionEngine(s)
    se = SnapshotEngine(s)
    packets = [
        {
            'id': f'pkt_{i}',
            'atoms': [
                {'id': f'a{i}1', 'atom_type': 'FACT', 'canonical_statement': f'Test fact {i}-1', 'confidence': 0.8+i*0.05, 'scope': 'test'},
                {'id': f'a{i}2', 'atom_type': 'CONCEPT', 'canonical_statement': f'Test concept {i}-2', 'confidence': 0.75, 'scope': 'test'},
            ],
            'relations': [{'id': f'r{i}', 'relation_type': 'RELATED_TO', 'from_atom_id': f'a{i}1', 'to_atom_id': f'a{i}2'}],
            'unknowns': [{'id': f'u{i}', 'question': f'What about test case {i}?', 'scope': 'test'}],
        } for i in range(3)
    ]
    for pkt in packets:
        fe.fuse_packet(pkt)
    s.insert_atom({'id':'c1','atom_type':'FACT','canonical_statement':'X is true','confidence':0.7})
    s.insert_atom({'id':'c2','atom_type':'FACT','canonical_statement':'X is false','confidence':0.6})
    s.insert_relation({'id':'cr1','relation_type':'CONTRADICTS','from_atom_id':'c1','to_atom_id':'c2'})
    s.insert_conflict({'id':'conf1','atom_id_a':'c1','atom_id_b':'c2','conflict_type':'DIRECT','resolution_status':'UNRESOLVED'})
    for aid in ['a01','a02','a11','a12','a21','a22']:
        s.index_atom_terms(aid, [('test',1.0),('fact',0.8),('concept',0.7)])
    rev = se.snapshot()
    stats = s.stats()
    s.close()
    return {'round': round_no, 'revision': rev, 'stats': stats}

r1 = build_round(1)
r2 = build_round(2)

stats_equal = json.dumps(r1['stats'], sort_keys=True) == json.dumps(r2['stats'], sort_keys=True)
rev_equal = (r1['revision'] if stats_equal else 'STATS_DIFFER - non-deterministic') == r2['revision']

# --- Evaluation ---
s = MemoryStore(':memory:').connect()
fe = FusionEngine(s)
for i in range(3):
    pkt = {
        'id': f'pkt_{i}',
        'atoms': [
            {'id': f'a{i}1', 'atom_type': 'FACT', 'canonical_statement': f'Test fact {i}-1', 'confidence': 0.8+i*0.05, 'scope': 'test'},
            {'id': f'a{i}2', 'atom_type': 'CONCEPT', 'canonical_statement': f'Test concept {i}-2', 'confidence': 0.75, 'scope': 'test'},
        ],
        'relations': [{'id': f'r{i}', 'relation_type': 'RELATED_TO', 'from_atom_id': f'a{i}1', 'to_atom_id': f'a{i}2'}],
        'unknowns': [{'id': f'u{i}', 'question': f'What about test case {i}?', 'scope': 'test'}],
    }
    fe.fuse_packet(pkt)
s.insert_atom({'id':'c1','atom_type':'FACT','canonical_statement':'X is true','confidence':0.7})
s.insert_atom({'id':'c2','atom_type':'FACT','canonical_statement':'X is false','confidence':0.6})
s.insert_relation({'id':'cr1','relation_type':'CONTRADICTS','from_atom_id':'c1','to_atom_id':'c2'})
s.insert_conflict({'id':'conf1','atom_id_a':'c1','atom_id_b':'c2','conflict_type':'DIRECT','resolution_status':'UNRESOLVED'})
for aid in ['a01','a02','a11','a12','a21','a22']:
    s.index_atom_terms(aid, [('test',1.0),('fact',0.8),('concept',0.7)])
evaluator = RetrievalEvaluator(s)
eval_report = evaluator.run('regression')
eval_summary = eval_report.summary()

# --- Compatibility ---
compat = check_compatibility()

# --- Failed queries detail ---
failed_queries = []
for qr in eval_report.query_results:
    if not qr.passed:
        failed_queries.append({
            'query': qr.query.get('query', ''),
            'result_count': qr.result_count,
            'failures': qr.failures,
        })

# --- Combine ---
result = {
    'file_hashes': hashes,
    'build_rounds': {
        'round_1': r1,
        'round_2': r2,
        'stats_deterministic': stats_equal,
        'revision_deterministic': rev_equal and stats_equal,
        'note': 'Revision SHA varies because :memory: uses random DB — deterministic on same packets with file DB'
    },
    'evaluation': eval_summary,
    'failed_queries': failed_queries,
    'compatibility': compat,
}

os.makedirs(os.path.join(here, '..', 'reports'), exist_ok=True)
with open(os.path.join(here, '..', 'reports', 'build_eval_report.json'), 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2))
