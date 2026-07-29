#!/usr/bin/env python3
"""
generate_adapters.py — Epoch 16 Gate B R1
Source-field-driven D2 participant ontology mapping.
NO hard-coded atom-index lists. Classification from subject_family, 
subject_subtype, perspective_class, atom_type, confidence, misclassification_risk.
"""
import sys, os, json, hashlib, unicodedata, argparse
from datetime import datetime, timezone

os.environ['PYTHONHASHSEED'] = os.environ.get('PYTHONHASHSEED', '0')

# ============================================================
# D2 Canonical Contract (from d2_game_core.py @ d6f9e2e4)
# ============================================================
D2_VALID_FAMILIES = {
    "retail", "institutional_quant", "active_capital",
    "policy_industrial_foreign_aggregate",
}
D2_VALID_SUBTYPES = {
    "retail_liquidity_taker", "retail_anchored_holder",
    "systematic_rebalancer", "long_horizon_fund",
    "event_driven_active", "short_horizon_momentum",
    "policy_aggregate", "industrial_aggregate", "foreign_aggregate",
}
SUBTYPE_TO_FAMILY = {
    "retail_liquidity_taker": "retail",
    "retail_anchored_holder": "retail",
    "systematic_rebalancer": "institutional_quant",
    "long_horizon_fund": "institutional_quant",
    "event_driven_active": "active_capital",
    "short_horizon_momentum": "active_capital",
    "policy_aggregate": "policy_industrial_foreign_aggregate",
    "industrial_aggregate": "policy_industrial_foreign_aggregate",
    "foreign_aggregate": "policy_industrial_foreign_aggregate",
}
DISPOSITIONS = ["MAPPED", "UNMAPPED", "AMBIGUOUS", "CONTEXT_ONLY", "PERSON_IDENTITY_QUARANTINED"]

# Mapping tables derived from PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml
Q0_TO_D2_FAMILY = {
    "RetailPopulationFamily": "retail",
    "QuantStrategyFamily": "institutional_quant",
    "ActiveSpeculativeCapitalFamily": "active_capital",
    # LargeCapitalFamily needs subtype-level resolution
}
Q0_TO_D2_SUBTYPE = {
    "DayTraderRetail": "retail_liquidity_taker",
    "PositionalRetail": "retail_anchored_holder",
    "IPOReversalRetail": "retail_liquidity_taker",
    "SmallCapHunterRetail": "retail_liquidity_taker",
    "IndexETFInvestor": "retail_anchored_holder",
    "SocialMediaFollowerRetail": "retail_liquidity_taker",
    "PublicFundSubtype": "long_horizon_fund",
    "PrivateFundSubtype": "long_horizon_fund",
    "StatisticalArbitrageQuant": "systematic_rebalancer",
    "HighFrequencyQuant": "systematic_rebalancer",
    "FactorModelQuant": "systematic_rebalancer",
    "SwingSpeculator": "short_horizon_momentum",
    "ThemeCoordinator": "event_driven_active",
    "StabilizationCapitalSubtype": "policy_aggregate",
    "IndustrialCapitalSubtype": "industrial_aggregate",
    "ForeignCapitalSubtype": "foreign_aggregate",
}

# ============================================================
# Helpers
# ============================================================
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def compute_deterministic_id(*components):
    payload = '||'.join(str(c) for c in components)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(',', ':'))

def nfc(s):
    if isinstance(s, str):
        return unicodedata.normalize('NFC', s)
    return s

# ============================================================
# Source lock
# ============================================================
EXPECTED_SOURCE_LOCK = {
    'KNOWLEDGE-ATOMS.jsonl': {
        'sha256': '47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d',
        'size': 59631,
    },
    'KNOWLEDGE-RELATIONS.jsonl': {
        'sha256': '39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a',
        'size': 52892,
    },
    'ADVERSARIAL-QUESTION-SET.jsonl': {
        'sha256': '2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927',
        'size': 40889,
    },
    'PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml': {
        'sha256': 'f526d66f4c6d2de1b904607e07fa92d7691a00a4ebaa5d1844bac1378d645d25',
        'size': 7514,
    },
}

def lock_sources(q0_dir):
    source_files = [
        'KNOWLEDGE-ATOMS.jsonl',
        'KNOWLEDGE-RELATIONS.jsonl',
        'ADVERSARIAL-QUESTION-SET.jsonl',
        'PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml',
    ]
    lock = {}
    for fn in source_files:
        fp = os.path.join(q0_dir, fn)
        if not os.path.exists(fp):
            raise FileNotFoundError(f"Source file not found: {fp}")
        actual_hash = sha256_file(fp)
        actual_size = os.path.getsize(fp)
        expected = EXPECTED_SOURCE_LOCK.get(fn, {})
        exp_hash = expected.get('sha256', '')
        exp_size = expected.get('size', None)
        if exp_hash and actual_hash != exp_hash:
            raise ValueError(f"Hash mismatch for {fn}: expected {exp_hash[:16]}..., got {actual_hash[:16]}...")
        if exp_size is not None and actual_size != exp_size:
            raise ValueError(f"Size mismatch for {fn}: expected {exp_size}, got {actual_size}")
        lock[fn] = {'sha256': actual_hash, 'size': actual_size}
    return lock

# ============================================================
# I/O
# ============================================================
def _reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        seen[key] = value
    return seen

def read_jsonl(path):
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line, object_pairs_hook=_reject_duplicate_keys))
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"JSONL parse error {path}:L{i}: {e}")
    return records

# ============================================================
# Load quarantine manifest
# ============================================================
def load_quarantine_manifest(manifest_path):
    import yaml
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    ids = [entry['id'] for entry in data.get('quarantined_deterministic_ids', [])]
    return set(ids)

# ============================================================
# Classification — source-field-driven, NO atom_index lists
# ============================================================
def classify_atom(atom, quarantine_ids):
    """
    Classification algorithm (source-field-driven):
    
    1. If deterministic_id in quarantine_ids → PERSON_IDENTITY_QUARANTINED
    2. If has subject_family that maps to D2:
       a) LOW confidence + HIGH misclassification_risk → AMBIGUOUS
       b) Otherwise → MAPPED (subject_family takes precedence over perspective_class)
    3. If has subject_family but unmappable to D2 → UNMAPPED
    4. No subject_family:
       a) perspective_class == MARKET_STRUCTURE → CONTEXT_ONLY
       b) atom_type == VALIDATION_TASK → UNMAPPED
       c) Others → UNMAPPED or CONTEXT_ONLY based on perspective
    5. NEVER emit UNMAPPED_UNKNOWN as family
    """
    did = atom['deterministic_id']
    sf = atom.get('subject_family', '')
    ss = atom.get('subject_subtype', '')
    pcls = atom.get('perspective_class', '')
    atype = atom.get('atom_type', '')
    conf = atom.get('confidence', '')
    risk = atom.get('misclassification_risk', '')

    # RULE 1: Quarantine
    if did in quarantine_ids:
        return 'PERSON_IDENTITY_QUARANTINED', None, None, None

    # RULE 2: Has mappable subject_family
    if sf and (sf in Q0_TO_D2_FAMILY or sf == 'LargeCapitalFamily'):
        # LargeCapitalFamily: needs subtype resolution
        if sf == 'LargeCapitalFamily':
            d2_sub = Q0_TO_D2_SUBTYPE.get(ss)
            if d2_sub:
                d2_family = SUBTYPE_TO_FAMILY[d2_sub]
            else:
                # Unknown LargeCapital subtype → UNMAPPED
                return 'UNMAPPED', None, None, None
        else:
            d2_family = Q0_TO_D2_FAMILY[sf]
            if ss and ss in Q0_TO_D2_SUBTYPE:
                d2_sub = Q0_TO_D2_SUBTYPE[ss]
                if SUBTYPE_TO_FAMILY.get(d2_sub) != d2_family:
                    # Subtype-family mismatch → UNMAPPED
                    return 'UNMAPPED', None, None, None
            else:
                d2_sub = None
        
        # If subtype is None, assign default per family
        if not d2_sub:
            defaults = {
                'retail': 'retail_liquidity_taker',
                'institutional_quant': 'systematic_rebalancer',
                'active_capital': 'short_horizon_momentum',
                'policy_industrial_foreign_aggregate': 'policy_aggregate',
            }
            d2_sub = defaults.get(d2_family, '')
        
        # Confidence/risk check for ambiguity
        if conf == 'LOW' and risk == 'HIGH':
            return 'AMBIGUOUS', d2_family, d2_sub, None
        
        return 'MAPPED', d2_family, d2_sub, None

    # RULE 3: Has subject_family but not mappable
    if sf:
        return 'UNMAPPED', None, None, None

    # RULE 4: No subject_family
    if pcls == 'MARKET_STRUCTURE':
        return 'CONTEXT_ONLY', None, None, None
    
    if atype == 'VALIDATION_TASK':
        return 'UNMAPPED', None, None, None

    # Fallback
    return 'UNMAPPED', None, None, None


def build_ambiguous_hypotheses(d2_family, d2_sub, atom):
    """Build hypothesis list for ambiguous atoms."""
    hypotheses = []
    if d2_family and d2_sub:
        # Single primary hypothesis; add contrasting alternative
        hypotheses = [{'family': d2_family, 'subtype': d2_sub}]
        # Add an alternative from a different family
        families = sorted(D2_VALID_FAMILIES - {d2_family})
        if families:
            alt = families[0]
            alt_sub = next((s for s, f in SUBTYPE_TO_FAMILY.items() if f == alt), None)
            if alt_sub:
                hypotheses.append({'family': alt, 'subtype': alt_sub})
        return hypotheses
    
    # Fallback: no family/subtype resolved → build generic hypotheses from subject_family
    sf = atom.get('subject_family', '')
    if sf == 'ActiveSpeculativeCapitalFamily':
        hypotheses = [
            {'family': 'active_capital', 'subtype': 'short_horizon_momentum'},
            {'family': 'retail', 'subtype': 'retail_liquidity_taker'},
        ]
    elif sf == 'QuantStrategyFamily':
        hypotheses = [
            {'family': 'institutional_quant', 'subtype': 'systematic_rebalancer'},
            {'family': 'active_capital', 'subtype': 'event_driven_active'},
        ]
    elif sf == 'LargeCapitalFamily':
        hypotheses = [
            {'family': 'institutional_quant', 'subtype': 'long_horizon_fund'},
            {'family': 'policy_industrial_foreign_aggregate', 'subtype': 'policy_aggregate'},
        ]
    elif sf == 'RetailPopulationFamily':
        hypotheses = [
            {'family': 'retail', 'subtype': 'retail_liquidity_taker'},
            {'family': 'retail', 'subtype': 'retail_anchored_holder'},
        ]
    return hypotheses

# ============================================================
# Lossless field preservation
# ============================================================
def compute_source_field_hash(atom):
    """Hash of lossless source fields for integrity verification."""
    fields = canonical_json({
        'deterministic_id': atom.get('deterministic_id', ''),
        'atom_index': atom.get('atom_index', 0),
        'atom_type': atom.get('atom_type', ''),
        'perspective_class': atom.get('perspective_class', ''),
        'confidence': atom.get('confidence', ''),
        'evidence_status': atom.get('evidence_status', ''),
        'misclassification_risk': atom.get('misclassification_risk', ''),
        'content_zh': atom.get('content_zh', ''),
        'content_en': atom.get('content_en', ''),
        'source_file': atom.get('source_file', ''),
        'source_section': atom.get('source_section', ''),
        'subject_family': atom.get('subject_family', ''),
        'subject_subtype': atom.get('subject_subtype', ''),
        'tags': atom.get('tags', []),
    })
    return hashlib.sha256(fields.encode('utf-8')).hexdigest()

# ============================================================
# Generate adapters
# ============================================================
def generate_adapters(atoms, relations, questions, source_lock, quarantine_ids):
    records = []
    atom_ids_seen = set()
    summary = {
        'MAPPED': 0, 'UNMAPPED': 0, 'AMBIGUOUS': 0,
        'CONTEXT_ONLY': 0, 'PERSON_IDENTITY_QUARANTINED': 0,
    }

    schema_version = '23.0'
    route_epoch = 16
    task_id = 'QCLAW-PR100-SOURCE-DERIVED-SEMANTIC-MAPPING-AND-EXECUTABLE-EVIDENCE-CLOSURE-0018-E16'
    
    metadata = {
        'adapter_version': '1.0.0',
        'schema_version': schema_version,
        'route_epoch': route_epoch,
        'task_id': task_id,
        'source_head': 'e54e04b',
        'd2_interface_head': 'd6f9e2e',
        'generation_timestamp': '2026-07-29T23:40:00+08:00',
    }

    # Process atoms sorted by deterministic_id for stability
    sorted_atoms = sorted(atoms, key=lambda a: a['deterministic_id'])

    for atom in sorted_atoms:
        did = atom['deterministic_id']
        idx = atom['atom_index']
        atype = atom.get('atom_type', '')
        pcls = atom.get('perspective_class', '')
        sf = atom.get('subject_family', '')
        ss = atom.get('subject_subtype', '')

        if did in atom_ids_seen:
            raise ValueError(f"Duplicate atom ID: {did}")
        atom_ids_seen.add(did)

        disposition, d2_family, d2_sub, _ = classify_atom(atom, quarantine_ids)
        adapter_id = compute_deterministic_id('Q0-D2-ADAPTER', did, f'v{schema_version}', disposition)
        source_hash = compute_source_field_hash(atom)

        record = {
            'adapter_id': adapter_id,
            'source_deterministic_id': did,
            'atom_index': idx,
            'atom_type': atype,
            'perspective_class': pcls,
            'disposition': disposition,
            # Lossless source field preservation
            'source_confidence': atom.get('confidence', ''),
            'source_evidence_status': atom.get('evidence_status', ''),
            'source_misclassification_risk': atom.get('misclassification_risk', ''),
            'source_field_hash': source_hash,
        }

        if disposition == 'MAPPED':
            record['d2_participant_family'] = d2_family
            record['d2_participant_subtype'] = d2_sub
            record['q0_subject_family'] = sf
            if ss:
                record['q0_subject_subtype'] = ss
            record['mapping_confidence'] = atom.get('confidence', 'MEDIUM')

            # CLAIM/HYPOTHESIS/UNKNOWN → CANDIDATE_ONLY downgrade
            if atype in ('CLAIM', 'HYPOTHESIS', 'UNKNOWN'):
                record['downgrade_note'] = 'CANDIDATE_ONLY'

            summary['MAPPED'] += 1

        elif disposition == 'AMBIGUOUS':
            hypotheses = build_ambiguous_hypotheses(d2_family, d2_sub, atom)
            record['d2_hypotheses'] = hypotheses
            record['ambiguity_reason'] = f'LOW confidence ({atom.get("confidence","")}) + HIGH misclassification_risk'
            if atype in ('CLAIM', 'HYPOTHESIS', 'UNKNOWN'):
                record['downgrade_note'] = 'CANDIDATE_ONLY'
            summary['AMBIGUOUS'] += 1

        elif disposition == 'PERSON_IDENTITY_QUARANTINED':
            record['quarantine_reason'] = 'Named person identity content; no agent identity emitted'
            record['quarantine_rule'] = 'NO_AGENT_IDENTITY'
            summary['PERSON_IDENTITY_QUARANTINED'] += 1

        elif disposition == 'CONTEXT_ONLY':
            record['context_reason'] = 'Market structure/metadata atom; not a participant mapping'
            summary['CONTEXT_ONLY'] += 1

        elif disposition == 'UNMAPPED':
            record['unmapped_reason'] = 'No mappable D2 family from source fields'
            # HARD CHECK: UNMAPPED must NOT have family
            if 'd2_participant_family' in record:
                raise ValueError(f"UNMAPPED atom {idx} has family field")
            summary['UNMAPPED'] += 1

        # FINAL GUARD: UNMAPPED_UNKNOWN never valid as family
        if record.get('d2_participant_family') == 'UNMAPPED_UNKNOWN':
            raise ValueError(f"UNMAPPED_UNKNOWN emitted as family for atom {idx}")

        records.append(record)

    # Verify count
    assert len(records) == 99, f"Expected 99 records, got {len(records)}"
    assert len(atom_ids_seen) == 99, f"Expected 99 unique IDs, got {len(atom_ids_seen)}"

    # Build package
    package = {
        'metadata': metadata,
        'source_lock': source_lock,
        'summary': summary,
        'adapters': records,
        'relation_count': len(relations),
        'question_count': len(questions),
    }
    return package

# ============================================================
# Write outputs
# ============================================================
def write_outputs(package, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    os.environ['PYTHONHASHSEED'] = '0'

    # 1. Adapter JSONL
    adapter_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
    with open(adapter_path, 'w', encoding='utf-8') as f:
        for rec in package['adapters']:
            f.write(canonical_json(rec) + '\n')

    # 2. Full adapter package JSON
    package_path = os.path.join(output_dir, 'D2-ADAPTER-PACKAGE.json')
    with open(package_path, 'w', encoding='utf-8') as f:
        json.dump(package, f, sort_keys=True, ensure_ascii=True, indent=2)

    # 3. Summary YAML
    summary_path = os.path.join(output_dir, 'D2-ADAPTER-SUMMARY.yaml')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"# D2 Candidate Adapter Summary — Epoch {package['metadata']['route_epoch']}\n\n")
        f.write("metadata:\n")
        for k, v in sorted(package['metadata'].items()):
            f.write(f"  {k}: {v}\n")
        f.write("\nsummary:\n")
        for k, v in sorted(package['summary'].items()):
            f.write(f"  {k}: {v}\n")
        f.write(f"\nsource_lock:\n")
        for fn, info in sorted(package['source_lock'].items()):
            f.write(f"  {fn}:\n")
            f.write(f"    sha256: {info['sha256']}\n")
            f.write(f"    size: {info['size']}\n")

    return {
        'adapters_jsonl': sha256_file(adapter_path),
        'summary_yaml': sha256_file(summary_path),
        'package_json': sha256_file(package_path),
    }

# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='Epoch 16 Gate B R1: D2 Adapter Generator')
    parser.add_argument('--q0-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--manifest', required=True, help='QUARANTINE-MANIFEST.yaml path')
    parser.add_argument('--hash-seed', default='0')
    args = parser.parse_args()

    os.environ['PYTHONHASHSEED'] = args.hash_seed
    print(f"generate_adapters.py — Epoch 16 Gate B R1: Source-field-driven D2 Adapter Builder")
    print(f"PYTHONHASHSEED={args.hash_seed}")

    # Step 1: Lock & verify sources
    print(f"\n[1/6] Locking and verifying sources...")
    source_lock = lock_sources(args.q0_dir)
    for fn, info in sorted(source_lock.items()):
        print(f"  {fn}: SHA256={info['sha256'][:16]}... size={info['size']} PASS")

    # Step 2: Read Q0 sources
    print(f"\n[2/6] Reading Q0 sources...")
    atoms = read_jsonl(os.path.join(args.q0_dir, 'KNOWLEDGE-ATOMS.jsonl'))
    relations = read_jsonl(os.path.join(args.q0_dir, 'KNOWLEDGE-RELATIONS.jsonl'))
    questions = read_jsonl(os.path.join(args.q0_dir, 'ADVERSARIAL-QUESTION-SET.jsonl'))
    print(f"  Atoms: {len(atoms)}, Relations: {len(relations)}, Questions: {len(questions)}")
    assert len(atoms) == 99 and len(relations) == 147 and len(questions) == 64

    # Step 3: Load quarantine manifest
    print(f"\n[3/6] Loading quarantine manifest...")
    quarantine_ids = load_quarantine_manifest(args.manifest)
    print(f"  Quarantined IDs: {len(quarantine_ids)}")

    # Step 4: Generate adapters
    print(f"\n[4/6] Generating D2 adapters (source-field-driven)...")
    package = generate_adapters(atoms, relations, questions, source_lock, quarantine_ids)
    print(f"  Summary: {json.dumps(package['summary'], sort_keys=True)}")

    # Step 5: Write outputs
    print(f"\n[5/6] Writing outputs...")
    output_hashes = write_outputs(package, args.output_dir)
    for fn, h in sorted(output_hashes.items()):
        print(f"  {fn}: SHA256={h[:32]}...")

    # Step 6: Print manifest & receipt
    print(f"\n[6/6] Generation complete")
    print(f"\nOUTPUT MANIFEST:")
    print(f"  adapters: {package['summary']['MAPPED']}")
    print(f"  unmapped: {package['summary']['UNMAPPED']}")
    print(f"  ambiguous: {package['summary']['AMBIGUOUS']}")
    print(f"  context_only: {package['summary']['CONTEXT_ONLY']}")
    print(f"  quarantined: {package['summary']['PERSON_IDENTITY_QUARANTINED']}")
    print(f"  total: {len(package['adapters'])}")

    # Write generation receipt
    receipt_path = os.path.join(args.output_dir, 'GENERATION-RECEIPT.json')
    receipt = {
        'task_id': package['metadata']['task_id'],
        'generation_timestamp': package['metadata']['generation_timestamp'],
        'python_version': sys.version.split()[0],
        'hashseed': args.hash_seed,
        'source_lock': source_lock,
        'output_hashes': output_hashes,
        'summary': package['summary'],
        'total_atoms': len(package['adapters']),
    }
    with open(receipt_path, 'w', encoding='utf-8') as f:
        json.dump(receipt, f, sort_keys=True, ensure_ascii=True, indent=2)
    print(f"  receipt: {receipt_path}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
