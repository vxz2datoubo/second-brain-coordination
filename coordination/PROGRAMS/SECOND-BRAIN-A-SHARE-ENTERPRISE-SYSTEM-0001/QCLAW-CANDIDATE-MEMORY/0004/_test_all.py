"""Full integration test — all Work Packages A through I."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run_all():
    test_files = [
        "_test_store.py",
        "_test_fusion.py",
        "_test_cde.py",
        "_test_fg.py",
    ]

    test_dir = os.path.join(os.path.dirname(__file__), "0004")

    total = 0
    passed = 0
    failed = 0

    for tf in test_files:
        tf_path = os.path.join(test_dir, tf)
        print(f"\n{'='*60}")
        print(f"Running: {tf}")
        print(f"{'='*60}")

        import subprocess
        result = subprocess.run(
            [sys.executable, tf_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=os.path.dirname(__file__),
        )

        output = result.stdout
        print(output)

        if result.stderr:
            print(f"STDERR: {result.stderr[:500]}")

        # Parse pass/fail counts
        for line in output.split('\n'):
            if 'tests passed' in line:
                parts = line.strip().split()
                try:
                    p = int(parts[0].replace('✅', '').strip())
                    t = int(parts[2].split('/')[1])
                    passed += p
                    total += t
                    failed += (t - p)
                except (ValueError, IndexError):
                    pass

    print(f"\n{'='*60}")
    print(f"TOTAL: {passed}/{total} passed ({failed} failed)")
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
