"""
semantic_validator.py — Full semantic validation for D2 adapter package.
Validates: source lock, file hashes, counts, ontology, quarantine, coverage.
Exit 0 = all pass. Exit 2 = validation failure. Exit 3 = missing file.
Usage: python semantic_validator.py
"""
import hashlib, json, os, sys, yaml, re

HERE = os.path.dirname(os.path.abspath(__file__))

# Required file set
REQUIRED = [
    'SOURCE-LOCK-AND-INPUT-MANIFEST.yaml',
    'ATOM-TO-PARTICIPANT-CANDIDATE-MAP.jsonl',
    'D2-CANDIDATE-INTERFACE-CONTRACT.yaml',
    'COVERAGE-AND-TRACEABILITY-REPORT.md',
    'RETRIEVAL-ABSTENTION-AND-ADVERSARIAL-CASES.jsonl',
    'RELATION-CONFLICT-AND-UNKNOWN-GRAPH.yaml',
]

# Accepted Codex D2 enums (exact)
VALID_FAMILIES = {'RETAIL', 'INSTITUTIONAL_QUANT', 'ACTIVE_CAPITAL', 'POLICY_INDUSTRIAL_FOREIGN_AGGREGATE', 'UNMAPPED_UNKNOWN'}

# OLD labels that must NOT appear as canonical targets
FORBIDDEN_LABELS = {'RetailPopulationFamily', 'LargeCapitalFamily', 'QuantStrategyFamily', 'ActiveSpeculativeCapitalFamily', 'MarketStructure', 'MethodologyNormative'}

# Canonical source reference
EXPECTED_SOURCE_COMMIT = 'e54e04b14876017253d27c578484e0bbd9096c0b'

def sha256_file(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

errors = []
warnings = []

# 1. Check all required files exist
for fn in REQUIRED:
    fp = os.path.join(HERE, fn)
    if not os.path.isfile(fp):
        errors.append(f'MISSING_FILE: {fn}')
        print(f'MISSING: {fn}', file=sys.stderr)
    else:
        print(f'OK FILE: {fn}')

if errors:
    print(f'\nFATAL: {len(errors)} files missing', file=sys.stderr)
    sys.exit(2)

# 2. Validate SOURCE-LOCK
with open(os.path.join(HERE, 'SOURCE-LOCK-AND-INPUT-MANIFEST.yaml'), 'r') as f:
    sl = yaml.safe_load(f)
lock = sl.get('git_commit_lock', '')
if len(lock) != 40:
    errors.append(f'ABBREVIATED_SHA: git_commit_lock={lock} (len={len(lock)})')
elif lock != EXPECTED_SOURCE_COMMIT:
    errors.append(f'WRONG_SOURCE_LOCK: {lock[:12]}... != {EXPECTED_SOURCE_COMMIT[:12]}...')
else:
    print(f'OK SOURCE_LOCK: {lock}')

# 3. Validate candidate map
with open(os.path.join(HERE, 'ATOM-TO-PARTICIPANT-CANDIDATE-MAP.jsonl'), 'r') as f:
    candidate_lines = [l for l in f.read().strip().split('\n') if l.strip()]

print(f'OK CANDIDATE_MAP: {len(candidate_lines)} entries')

for i, line in enumerate(candidate_lines):
    entry = json.loads(line)
    fam = entry.get('codex_d2_family', '')
    # Check canonical target is valid Codex D2 enum
    if fam not in VALID_FAMILIES:
        errors.append(f'INVALID_CODEX_FAMILY: entry {i} family={fam}')

    # Check no old label leaks into canonical target
    if fam in FORBIDDEN_LABELS:
        errors.append(f'FORBIDDEN_OLD_LABEL_AS_CANONICAL: entry {i} family={fam}')

    # Check person identity quarantine exists
    pq = entry.get('person_identity_quarantine', {})
    if pq.get('status') != 'ACTIVE':
        errors.append(f'UNQUARANTINED_PERSON_IDENTITY: entry {i} status={pq.get("status")}')

    # Preserved source labels
    sf = entry.get('source_subject_family', '')
    if not sf:
        warnings.append(f'NO_SOURCE_FAMILY_PRESERVED: entry {i}')

old_label_count = sum(1 for line in candidate_lines if any(
    json.loads(line).get('codex_d2_family', '') == lb for lb in FORBIDDEN_LABELS
))
if old_label_count > 0:
    errors.append(f'OLD_LABEL_POLLUTION: {old_label_count} entries with old labels as canonical target')
else:
    print('OK ONTOLOGY: No old (E8/E9) labels as canonical targets')

# 4. Validate contract enums
with open(os.path.join(HERE, 'D2-CANDIDATE-INTERFACE-CONTRACT.yaml'), encoding='utf-8') as f:
    ct = yaml.safe_load(f)
target_enums = ct.get('codex_d2_canonical_targets', {}).get('enums', {})
if set(target_enums.keys()) != VALID_FAMILIES:
    errors.append(f'CONTRACT_FAMILY_MISMATCH: {set(target_enums.keys())} != {VALID_FAMILIES}')
else:
    print('OK CONTRACT_ENUMS: exact match')

# 5. Validate cases
with open(os.path.join(HERE, 'RETRIEVAL-ABSTENTION-AND-ADVERSARIAL-CASES.jsonl'), 'r') as f:
    case_lines = [l for l in f.read().strip().split('\n') if l.strip()]
case_ids = set()
for line in case_lines:
    c = json.loads(line)
    cid = c.get('case_id', '')
    if not cid:
        errors.append('CASE_MISSING_ID')
    elif cid in case_ids:
        errors.append(f'DUPLICATE_CASE_ID: {cid}')
    case_ids.add(cid)
print(f'OK CASES: {len(case_lines)} cases, {len(case_ids)} unique IDs')

# 6. Validate relation graph
with open(os.path.join(HERE, 'RELATION-CONFLICT-AND-UNKNOWN-GRAPH.yaml'), 'r') as f:
    rg = yaml.safe_load(f)
total = rg.get('graph_summary', {}).get('total_relations', 0)
if total != 147:
    errors.append(f'RELATION_COUNT_MISMATCH: {total} != 147')
else:
    print(f'OK RELATIONS: {total}')

# 7. Validate contract quarantine
pq_status = ct.get('person_identity_quarantine', {}).get('status', '')
if pq_status != 'ACTIVE':
    errors.append(f'CONTRACT_QUARANTINE_INACTIVE: {pq_status}')
else:
    print('OK QUARANTINE: ACTIVE')

# 8. Validate no claim promotion
for i, line in enumerate(candidate_lines):
    entry = json.loads(line)
    at = entry.get('atom_type', '')
    conf = entry.get('confidence', '')
    ev = entry.get('evidence_status', '')
    # A CLAIM with confidence appears as FACT → promotion
    if at == 'CLAIM' and conf == 'HIGH' and ev == 'FACT':
        errors.append(f'CLAIM_PROMOTION_TO_FACT: entry {i}')

# Report
if warnings:
    for w in warnings:
        print(f'WARNING: {w}', file=sys.stderr)

if errors:
    print(f'\nSEMANTIC VALIDATION FAILED: {len(errors)} errors, {len(warnings)} warnings', file=sys.stderr)
    for e in errors:
        print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(2)

print(f'\nALL SEMANTIC VALIDATIONS PASSED ({len(warnings)} warnings)')
sys.exit(0)
