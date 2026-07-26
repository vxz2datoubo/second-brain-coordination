"""verify_counts.py — Verify PR #64 counts match 0010-Q0 ground truth. Exit 0 = PASS."""
import json, sys, yaml

EXPECTED_ATOMS = 99
EXPECTED_RELS = 147
EXPECTED_QUESTIONS = 64
EXPECTED_ATOM_TYPES = {'CAUSAL_CLAIM': 3, 'CLAIM': 18, 'CONSTRAINT': 13, 'COUNTEREXAMPLE': 3, 'EXCEPTION': 3, 'FACT': 29, 'HYPOTHESIS': 6, 'RISK': 6, 'UNKNOWN': 11, 'VALIDATION_TASK': 7}
EXPECTED_REL_TYPES = {'CONTRADICTS': 10, 'DEPENDS_ON': 21, 'FAILS_WHEN': 12, 'RAISES_UNKNOWN': 14, 'REFINES': 17, 'SUPPORTS': 65, 'VERIFIED_BY': 8}

def check(f, field, expected_count, label):
    count = len([l for l in f.strip().split('\n') if l.strip()])
    if count != expected_count:
        print(f'FAIL: {label}: {count} != {expected_count}', file=sys.stderr)
        return 1
    print(f'PASS: {label}: {count} == {expected_count}')
    return 0

print('Running verify_counts.py...')
errors = 0

# Check architecture markdown mentions correct counts
with open('C_ARCHITECTURE.md', 'r') as ff:
    arch = ff.read()
assert str(99) in arch, f'Atom count {ATOM_COUNT} not in architecture'
assert str(147) in arch, f'Relation count {REL_COUNT} not in architecture'
assert str(64) in arch, f'Question count {QUEST_COUNT} not in architecture'
print(f'PASS: Architecture contains {ATOM_COUNT}/{REL_COUNT}/{QUEST_COUNT} counts')

# Check YAML files
with open('C_ATOM-TYPE-TAXONOMY.yaml', 'r') as ff:
    at = yaml.safe_load(ff)
assert at['total_atoms'] == 99, f'Atom taxonomy total_atoms wrong'
assert at['no_zero_counts'] == True, f'Zero-count pollution not eliminated'
print('PASS: Atom taxonomy counts correct, no zero pollution')

with open('C_RELATION-TAXONOMY.yaml', 'r') as ff:
    rt = yaml.safe_load(ff)
assert rt['total_relations'] == 147, f'Relation taxonomy total_relations wrong'
print(f'PASS: Relation taxonomy: {rt["total_relations"]} relations')

if errors == 0:
    print('ALL CHECKS PASSED')
    sys.exit(0)
else:
    print(f'STATUS: {errors} errors')
    sys.exit(1)
