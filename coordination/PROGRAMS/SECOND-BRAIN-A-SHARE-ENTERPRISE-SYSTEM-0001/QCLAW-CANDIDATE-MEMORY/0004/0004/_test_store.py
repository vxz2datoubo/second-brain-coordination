"""Smoke test for MemoryStore — Work Package A."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from store import MemoryStore
import json

s = MemoryStore(':memory:').connect()

# Insert test atoms
a1 = {'id':'a1','atom_type':'FACT','canonical_statement':'Earth is a planet','confidence':1.0,'verification_status':'VERIFIED'}
a2 = {'id':'a2','atom_type':'FACT','canonical_statement':'Mars is a planet','confidence':1.0}
s.insert_atom(a1)
s.insert_atom(a2)

# Relation
s.insert_relation({'id':'r1','relation_type':'IS_A','from_atom_id':'a1','to_atom_id':'a2','context':'both planetary bodies'})

# Unknown
s.insert_unknown({'id':'u1','question':'Is Pluto still a planet?','scope':'astronomy'})

# Source
s.insert_source({'id':'s1','source_type':'SYNTHETIC','title':'Test Source'})

# Stats
st = s.stats()
print(f"Stats: atoms={st['atoms']} relations={st['relations']} unknowns={st['unknowns']} sources={st['sources']}")
assert st['atoms']==2 and st['relations']==1 and st['unknowns']==1 and st['sources']==1, f'FAIL stats: {st}'

# Integrity
ic = s.integrity_check()
assert ic['integrity_ok'], f'FAIL integrity: {ic["issues"]}'
print(f"Integrity: OK")

# FTS
s.index_atom_terms('a1', [('earth',1.0),('planet',1.0)])
s.index_atom_terms('a2', [('mars',1.0),('planet',1.0)])
results = s.search_fts('earth')
assert len(results) >= 1, f"FTS earth failed: {len(results)}"
print(f"FTS 'earth': {len(results)} results — {results[0]['canonical_statement']}")

results2 = s.search_fts('planet')
assert len(results2) == 2, f"FTS planet failed: {len(results2)}"
print(f"FTS 'planet': {len(results2)} results")

# Duplicate insertion
a1_dup = {'id':'a1','atom_type':'FACT','canonical_statement':'Earth is a planet','confidence':1.0}
s.insert_atom(a1_dup)
st2 = s.stats()
assert st2['atoms'] == 2, f"Dedup failed: {st2['atoms']} atoms"
print(f"Dedup: OK (atoms still {st2['atoms']})")

# Packet import
pkt = {
    'id': 'test_pkt_1',
    'instance_id': 'inst-001',
    'content_hash': 'hash123',
    'atoms': [
        {'id':'a3','atom_type':'CONCEPT','canonical_statement':'Gravity curves spacetime','confidence':0.95},
        {'id':'a4','atom_type':'FACT','canonical_statement':'Light follows geodesics','confidence':0.9},
    ],
    'relations': [
        {'id':'r2','relation_type':'CAUSES','from_atom_id':'a3','to_atom_id':'a4','context':'mass-energy curves spacetime, light follows'},
    ],
    'unknowns': [
        {'id':'u2','question':'How does gravity reconcile with quantum mechanics?','scope':'physics'},
    ],
    'skills': [
        {'id':'sk1','name':'relativity_check','content':'Check if Einstein field equations apply'},
    ],
}
summary = s.import_packet_dict(pkt)
print(f"Import: {summary}")
assert summary['atoms']==2 and summary['relations']==1 and summary['skills']==1, f'Import FAIL: {summary}'

st3 = s.stats()
print(f"Final stats: {st3}")
assert st3['atoms']==4 and st3['packets']==1, f'Final stats FAIL: {st3}'

# Revision
rev = s.create_revision()
print(f"Revision: {rev[:16]}...")
rev2 = s.create_revision(rev)
print(f"Revision 2: {rev2[:16]}...")

# Audit
audit = s.get_audit_events(5)
print(f"Audit events: {len(audit)}")

# Import duplicate packet (idempotent)
summary2 = s.import_packet_dict(pkt)
print(f"Re-import: atoms={summary2['atoms']} duplicates={summary2['duplicates']}")
assert summary2['atoms']==0 and summary2['duplicates']>=2, f'Idempotent FAIL: {summary2}'

print("\n✅ ALL Work Package A tests passed!")
s.close()
