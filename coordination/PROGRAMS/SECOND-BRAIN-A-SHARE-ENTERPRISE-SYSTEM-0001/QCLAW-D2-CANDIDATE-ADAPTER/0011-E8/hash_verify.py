#!/usr/bin/env python3
"""
hash_verify.py — Epoch 15 Gate B: Byte-level Output Comparison
Verifies 3 clean generation runs produce byte-identical outputs.
"""
import sys, os, hashlib, argparse

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description='Hash Verify: byte-level comparison')
    parser.add_argument('--run-dirs', nargs='+', required=True, help='Run output directories to compare')
    args = parser.parse_args()

    print(f"hash_verify.py — Byte-Level Output Comparison")
    print(f"Runs: {args.run_dirs}")

    files = ['D2-CANDIDATE-ADAPTERS.jsonl', 'D2-ADAPTER-SUMMARY.yaml', 'D2-ADAPTER-PACKAGE.json']
    all_identical = True

    for fn in files:
        hashes = {}
        sizes = {}
        for rd in args.run_dirs:
            fp = os.path.join(rd, fn)
            if not os.path.exists(fp):
                print(f"  {fn}: MISSING in {rd}")
                all_identical = False
                continue
            h = sha256_file(fp)
            s = os.path.getsize(fp)
            hashes[rd] = h
            sizes[rd] = s
            print(f"  {os.path.basename(rd)}/{fn}: SHA256={h[:32]}... size={s}")

        unique_hashes = set(hashes.values())
        if len(unique_hashes) == 1:
            print(f"  {fn}: IDENTICAL")
        else:
            print(f"  {fn}: DIFFERENT")
            for rd, h in sorted(hashes.items()):
                print(f"    {rd}: {h}")
            all_identical = False

    if all_identical:
        print(f"\nALL OUTPUTS BYTE-IDENTICAL across {len(args.run_dirs)} runs")
        return 0
    else:
        print(f"\nOUTPUTS DIFFER across runs")
        return 1

if __name__ == '__main__':
    sys.exit(main())
