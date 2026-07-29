#!/usr/bin/env python3
"""
run_production_tests.py — Epoch 16 Gate B R1
===========================================
20+ production entry-point tests invoking real generator/validator
in isolated temp directories. Each test observes intended non-zero failure.
"""
import sys, os, json, hashlib, tempfile, shutil, subprocess, unittest

SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source')
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.join(PROJECT_DIR, 'generate_adapters.py')
VALIDATOR = os.path.join(PROJECT_DIR, 'validate_adapters.py')
MANIFEST = os.path.join(PROJECT_DIR, 'QUARANTINE-MANIFEST.yaml')
PYTHON = sys.executable

# D2 contract
D2_VALID_FAMILIES = {"retail", "institutional_quant", "active_capital", "policy_industrial_foreign_aggregate"}
D2_VALID_SUBTYPES = {"retail_liquidity_taker", "retail_anchored_holder",
    "systematic_rebalancer", "long_horizon_fund", "event_driven_active",
    "short_horizon_momentum", "policy_aggregate", "industrial_aggregate", "foreign_aggregate"}


def create_temp_dir():
    d = tempfile.mkdtemp(prefix='e16_test_')
    return d


def copy_sources(dest_dir):
    src = SOURCE_DIR
    for fn in os.listdir(src):
        if fn.endswith(('.jsonl', '.yaml')):
            shutil.copy2(os.path.join(src, fn), os.path.join(dest_dir, fn))
    return dest_dir


def run_generator(q0_dir, output_dir, manifest=MANIFEST, hash_seed='0'):
    cmd = [PYTHON, GENERATOR, '--q0-dir', q0_dir, '--output-dir', output_dir,
           '--manifest', manifest, '--hash-seed', hash_seed]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def run_validator(adapters_path, q0_dir, manifest=MANIFEST, output_dir=None):
    if output_dir is None:
        output_dir = q0_dir
    cmd = [PYTHON, VALIDATOR, '--adapters', adapters_path, '--q0-dir', q0_dir,
           '--manifest', manifest, '--output-dir', output_dir]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def read_jsonl(path):
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path, records):
    with open(path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


class TestNormal(unittest.TestCase):

    def test_01_normal_generation_and_validation(self):
        """Full generation + validation on clean sources."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0, 'Generator failed')
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            self.assertTrue(os.path.exists(adapters_path))
            adapters = read_jsonl(adapters_path)
            self.assertEqual(len(adapters), 99)
            rc, _, err = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            self.assertEqual(rc, 0, f'Validator failed: {err[:200]}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_02_hash_mismatch_source_corruption(self):
        """Generator fails when source file has hash mismatch."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            # Corrupt atoms file
            atoms_path = os.path.join(q0_dir, 'KNOWLEDGE-ATOMS.jsonl')
            atoms = read_jsonl(atoms_path)
            atoms[0]['_corrupted'] = True
            write_jsonl(atoms_path, atoms)
            output_dir = os.path.join(tmp, 'output')
            rc, out, err = run_generator(q0_dir, output_dir)
            self.assertNotEqual(rc, 0, f'Generator should have failed on hash mismatch, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_03_corrupted_yaml_hash_mismatch(self):
        """Generator fails when YAML source has hash mismatch."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            yaml_path = os.path.join(q0_dir, 'PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml')
            with open(yaml_path, 'a', encoding='utf-8') as f:
                f.write('\ncorruption: true\n')
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertNotEqual(rc, 0, f'Generator should have failed on hash mismatch, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_04_invalid_family(self):
        """Validator rejects adapter with invalid D2 family."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            for a in adapters:
                if a['disposition'] == 'MAPPED' and 'd2_participant_family' in a:
                    a['d2_participant_family'] = 'INVALID_FAMILY_XYZ'
                    break
            write_jsonl(adapters_path, adapters)
            rc, out, err = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            self.assertNotEqual(rc, 0, f'Validator should have failed on invalid family, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_05_context_only_with_family(self):
        """Validator rejects CONTEXT_ONLY with d2_participant_family."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            for a in adapters:
                if a['disposition'] == 'CONTEXT_ONLY':
                    a['d2_participant_family'] = 'retail'
                    break
            write_jsonl(adapters_path, adapters)
            rc, _, _ = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            self.assertNotEqual(rc, 0, f'Validator should have rejected CONTEXT_ONLY with family, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_06_missing_source_atom(self):
        """Validator rejects adapter with nonexistent source atom."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            adapters[0]['source_deterministic_id'] = 'deadbeef' * 8
            write_jsonl(adapters_path, adapters)
            rc, _, _ = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            self.assertNotEqual(rc, 0, f'Validator should have rejected missing source atom, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_07_extra_adapter(self):
        """Validator rejects extra adapter not in source."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            extra = dict(adapters[0])
            extra['adapter_id'] = 'extra_adapter_not_in_source'
            extra['source_deterministic_id'] = 'extra_did_not_in_source'
            adapters.append(extra)
            write_jsonl(adapters_path, adapters)
            rc, _, _ = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            self.assertNotEqual(rc, 0, f'Validator should have rejected extra adapter, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_08_duplicate_adapter_id(self):
        """Validator rejects duplicate adapter IDs."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            adapters[1]['adapter_id'] = adapters[0]['adapter_id']
            write_jsonl(adapters_path, adapters)
            rc, _, _ = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            self.assertNotEqual(rc, 0, f'Validator should have rejected duplicate adapter IDs, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_09_claim_downgrade_note(self):
        """Validator warns about CLAIM mapped without downgrade."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            for a in adapters:
                if a['disposition'] == 'MAPPED' and a.get('atom_type') == 'CLAIM':
                    a.pop('downgrade_note', None)
                    break
            write_jsonl(adapters_path, adapters)
            rc, out, _ = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            # Warning only, still passes
            self.assertIn('WARN', out, 'Should warn about missing downgrade note')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_10_confidence_upgrade(self):
        """Validator rejects confidence upgrade."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            for a in adapters:
                if a['disposition'] == 'MAPPED' and a.get('source_confidence') == 'LOW':
                    a['mapping_confidence'] = 'HIGH'
                    break
            write_jsonl(adapters_path, adapters)
            rc, out, _ = run_validator(adapters_path, q0_dir, output_dir=output_dir)
            self.assertNotEqual(rc, 0, f'Validator should have failed on confidence upgrade, rc={rc}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_11_missing_source_field_hash(self):
        """All adapters carry source_field_hash (structural check)."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            missing = [a['adapter_id'][:16] for a in adapters if not a.get('source_field_hash')]
            self.assertEqual(len(missing), 0, f'Missing source_field_hash: {len(missing)}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_12_different_hash_seeds(self):
        """Generator produces identical output with different PYTHONHASHSEED."""
        tmp1 = create_temp_dir()
        tmp2 = create_temp_dir()
        try:
            q0_1 = copy_sources(tmp1)
            q0_2 = copy_sources(tmp2)
            out1 = os.path.join(tmp1, 'output')
            out2 = os.path.join(tmp2, 'output')
            run_generator(q0_1, out1, hash_seed='0')
            run_generator(q0_2, out2, hash_seed='42')
            a1 = read_jsonl(os.path.join(out1, 'D2-CANDIDATE-ADAPTERS.jsonl'))
            a2 = read_jsonl(os.path.join(out2, 'D2-CANDIDATE-ADAPTERS.jsonl'))
            self.assertEqual(len(a1), len(a2))
            for i, (r1, r2) in enumerate(zip(a1, a2)):
                for key in ['adapter_id', 'source_deterministic_id', 'disposition']:
                    self.assertEqual(r1.get(key), r2.get(key), f'Record {i}: {key} differs')
        finally:
            shutil.rmtree(tmp1, ignore_errors=True)
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_13_quarantine_manifest_respected(self):
        """Generator quarantines named-person atoms regardless of subject_family."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            quarantined = [a for a in adapters if a['disposition'] == 'PERSON_IDENTITY_QUARANTINED']
            self.assertEqual(len(quarantined), 18, f'Expected 18 quarantined, got {len(quarantined)}')
            for q in quarantined:
                self.assertNotIn('d2_participant_family', q)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_14_all_adapters_have_source_field_hash(self):
        """Every adapter carries a valid source_field_hash."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            for a in adapters:
                sfh = a.get('source_field_hash', '')
                self.assertEqual(len(sfh), 64, f'Invalid hash length: {sfh[:10]}...')
                self.assertNotEqual(sfh, '0' * 64, f'Zero hash: {a["adapter_id"][:16]}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_15_subtype_family_consistency(self):
        """MAPPED adapters have valid subtypes in valid families."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            mapped = [a for a in adapters if a['disposition'] == 'MAPPED']
            self.assertGreater(len(mapped), 0)
            for m in mapped:
                subtype = m.get('d2_participant_subtype', '')
                family = m.get('d2_participant_family', '')
                self.assertIn(subtype, D2_VALID_SUBTYPES, f'Invalid subtype: {subtype}')
                self.assertIn(family, D2_VALID_FAMILIES, f'Invalid family: {family}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_16_no_zero_hashes(self):
        """No adapter contains zero/empty hash fields."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            for a in adapters:
                sfh = a.get('source_field_hash', '')
                aid = a.get('adapter_id', '')
                self.assertTrue(sfh and len(sfh) == 64, f'Bad sfh={sfh[:10]}...')
                self.assertTrue(aid and len(aid) == 64, f'Bad aid={aid[:10]}...')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_17_unmapped_no_family(self):
        """UNMAPPED adapters must not carry family/subtype."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            unmapped = [a for a in adapters if a['disposition'] == 'UNMAPPED']
            self.assertGreater(len(unmapped), 0)
            for u in unmapped:
                self.assertNotIn('d2_participant_family', u)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_18_ambiguous_multiple_hypotheses(self):
        """AMBIGUOUS adapters have at least 2 hypotheses."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            ambiguous = [a for a in adapters if a['disposition'] == 'AMBIGUOUS']
            for am in ambiguous:
                hyps = am.get('d2_hypotheses', [])
                self.assertGreaterEqual(len(hyps), 2, f'Only {len(hyps)} hypotheses')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_19_output_files_completeness(self):
        """Generator produces all required output files."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            required = [
                'D2-CANDIDATE-ADAPTERS.jsonl',
                'D2-ADAPTER-SUMMARY.yaml',
                'D2-ADAPTER-PACKAGE.json',
                'GENERATION-RECEIPT.json',
            ]
            for fn in required:
                fp = os.path.join(output_dir, fn)
                self.assertTrue(os.path.exists(fp) and os.path.getsize(fp) > 0, f'Missing: {fn}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_20_reproducible_generation(self):
        """Two independent generations produce byte-identical output."""
        tmp1 = create_temp_dir()
        tmp2 = create_temp_dir()
        try:
            q0_1 = copy_sources(tmp1)
            q0_2 = copy_sources(tmp2)
            out1 = os.path.join(tmp1, 'o')
            out2 = os.path.join(tmp2, 'o')
            run_generator(q0_1, out1, hash_seed='0')
            run_generator(q0_2, out2, hash_seed='0')
            f1 = os.path.join(out1, 'D2-CANDIDATE-ADAPTERS.jsonl')
            f2 = os.path.join(out2, 'D2-CANDIDATE-ADAPTERS.jsonl')
            with open(f1, 'rb') as f:
                d1 = f.read()
            with open(f2, 'rb') as f:
                d2 = f.read()
            self.assertEqual(d1, d2, 'Generation not byte-identical between runs')
        finally:
            shutil.rmtree(tmp1, ignore_errors=True)
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_21_atom_indices_14_to_20_are_mapped(self):
        """Atoms 14-20 with subject_family must be MAPPED, not CONTEXT_ONLY."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            # Find atoms with atom_index 14-20
            for a in adapters:
                idx = a.get('atom_index', 0)
                sf = a.get('q0_subject_family', '') or ''
                if 14 <= idx <= 20:
                    if sf:
                        self.assertEqual(a['disposition'], 'MAPPED',
                            f'Atom {idx} with sf={sf} was {a["disposition"]}, not MAPPED')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_22_no_unmapped_unknown_family(self):
        """UNMAPPED_UNKNOWN never appears as family value."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            for a in adapters:
                family = a.get('d2_participant_family', '')
                self.assertNotEqual(family, 'UNMAPPED_UNKNOWN',
                    f'Atom {a.get("atom_index")}: found UNMAPPED_UNKNOWN family')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_23_lossless_preservation_fields(self):
        """All adapters carry lossless source fields."""
        tmp = create_temp_dir()
        try:
            q0_dir = copy_sources(tmp)
            output_dir = os.path.join(tmp, 'output')
            rc, _, _ = run_generator(q0_dir, output_dir)
            self.assertEqual(rc, 0)
            adapters_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
            adapters = read_jsonl(adapters_path)
            required_fields = ['source_deterministic_id', 'source_confidence',
                               'source_evidence_status', 'source_field_hash', 'atom_type']
            for a in adapters:
                for field in required_fields:
                    self.assertIn(field, a, f'Missing {field} in adapter {a.get("adapter_id","")[:16]}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
