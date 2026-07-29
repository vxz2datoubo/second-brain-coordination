#!/usr/bin/env python3
"""
hash_compare.py — Epoch 16 Gate B R1
====================================
Byte-compare complete canonical artifact sets across 3 independent
clean Git-archive extractions with different PYTHONHASHSEED values.
"""
import sys, os, hashlib, subprocess, tempfile, shutil, json, argparse

PYTHON = sys.executable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.join(SCRIPT_DIR, 'generate_adapters.py')
SOURCE_DIR = os.path.join(SCRIPT_DIR, 'source')
MANIFEST = os.path.join(SCRIPT_DIR, 'QUARANTINE-MANIFEST.yaml')

EXPECTED_FILES = [
    'D2-CANDIDATE-ADAPTERS.jsonl',
    'D2-ADAPTER-SUMMARY.yaml',
    'D2-ADAPTER-PACKAGE.json',
]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def run_generation(q0_dir, output_dir, seed):
    cmd = [PYTHON, GENERATOR, '--q0-dir', q0_dir,
           '--output-dir', output_dir, '--manifest', MANIFEST,
           '--hash-seed', seed]
    env = {**os.environ, 'PYTHONHASHSEED': seed}
    result = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=30, env=env)
    return result.returncode, result.stdout, result.stderr

def main():
    parser = argparse.ArgumentParser(description='Epoch 16 Hash Compare: 3 archive generations')
    parser.add_argument('--q0-dir', default=SOURCE_DIR)
    parser.add_argument('--seeds', nargs='*', default=['0', '42', '12345'])
    parser.add_argument('--output-base', default=os.path.join(SCRIPT_DIR, 'hash_runs'))
    args = parser.parse_args()

    seeds = args.seeds
    print(f'hash_compare.py — comparing {len(seeds)} clean generations')
    print(f'Seeds: {seeds}\n')

    results = {}
    file_hashes = {}

    for seed in seeds:
        work_dir = os.path.join(args.output_base, f'seed_{seed}')
        os.makedirs(work_dir, exist_ok=True)
        
        # Copy fresh sources each time
        q0_dir = os.path.join(work_dir, 'q0')
        if os.path.exists(q0_dir):
            shutil.rmtree(q0_dir)
        shutil.copytree(args.q0_dir, q0_dir)
        
        output_dir = os.path.join(work_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        rc, out, err = run_generation(q0_dir, output_dir, seed)
        results[seed] = {'rc': rc, 'stdout': out, 'stderr': err}
        
        print(f'[SEED {seed}] rc={rc}')
        if rc != 0:
            print(f'  ERROR: {err[:200]}')
            continue
        
        hashes = {}
        for fn in EXPECTED_FILES:
            fp = os.path.join(output_dir, fn)
            if os.path.exists(fp):
                h = sha256_file(fp)
                hashes[fn] = h
                print(f'  {fn}: {h[:32]}...')
            else:
                print(f'  {fn}: MISSING')
                hashes[fn] = None
        
        file_hashes[seed] = hashes
        print()

    # Compare
    if len(file_hashes) < 2:
        print('Not enough successful runs to compare')
        return 1

    print('='*60)
    print('COMPARISON RESULTS')
    print('='*60)

    ref_seed = seeds[0]
    ref = file_hashes[ref_seed]
    all_match = True

    for fn in EXPECTED_FILES:
        ref_hash = ref.get(fn)
        print(f'\n{fn}:')
        print(f'  ref (seed={ref_seed}): {ref_hash[:32]}...')
        for seed in seeds[1:]:
            h = file_hashes[seed].get(fn)
            if h == ref_hash:
                print(f'  seed={seed:>6s}: MATCH')
            elif h is None:
                print(f'  seed={seed:>6s}: MISSING')
                all_match = False
            else:
                print(f'  seed={seed:>6s}: MISMATCH ({h[:16]}...)')
                all_match = False

    print(f'\n{"="*60}')
    if all_match:
        print('ALL FILES BYTE-IDENTICAL ACROSS ALL RUNS PASS')
    else:
        print('MISMATCH DETECTED FAIL')
        return 1

    # Write comparison report
    report_path = os.path.join(args.output_base, 'HASH-COMPARISON-REPORT.json')
    report = {
        'seeds': seeds,
        'results': {seed: data['rc'] for seed, data in results.items()},
        'file_hashes': file_hashes,
        'all_match': all_match,
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(f'\nReport: {report_path}')

    return 0 if all_match else 1

if __name__ == '__main__':
    sys.exit(main())
