#!/usr/bin/env python3
"""
QCLAW E28 — Full Evidence Runner
Runs entire suite + generates archive + WPDCR + receipt evidence.
"""
import os, sys, hashlib, json, subprocess, tempfile, shutil
from pathlib import Path
from datetime import datetime, timezone

THIS = Path(__file__).resolve().parent
SRC = THIS / "src"

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_cmd(cmd: list, cwd=None) -> dict:
    r = subprocess.run(cmd, capture_output=True, cwd=cwd or str(THIS),
                      env={**os.environ, "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8",
                           "PYTHONPATH": str(SRC)})
    return {
        "command": " ".join(cmd),
        "exit": r.returncode,
        "stdout": r.stdout.decode("utf-8", errors="replace")[-2000:],
        "stderr": r.stderr.decode("utf-8", errors="replace")[-500:],
    }

def run_evidence():
    py311 = r"F:\Program Files (x86)\QClaw\v0.2.35.624\resources\python\python.exe"
    py313 = r"C:\Program Files\Python313\python.exe"
    
    result = {
        "epoch": 28,
        "task_id": "QCLAW-KNOWLEDGE-ATOMIZATION-SEMANTIC-LOSSLESS-DETERMINISM-SOURCE-LINEAGE-AND-RECEIPT-CLOSURE-0009-E28",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "python_311": str(py311),
        "python_313": str(py313),
        "stages": []
    }
    
    # Stage 1: Test suite (both Pythons)
    for label, py in [("3.11.10", py311), ("3.13.3", py313)]:
        r = run_cmd([py, str(THIS / "tests" / "run_all_tests.py")])
        r["label"] = f"test_suite_{label}"
        result["stages"].append(r)
    
    # Stage 2: Integrated pipeline (both Pythons)
    for label, py in [("3.11.10", py311), ("3.13.3", py313)]:
        r = run_cmd([py, str(THIS / "run_integrated_pipeline.py")])
        r["label"] = f"integrated_pipeline_{label}"
        result["stages"].append(r)
    
    # Stage 3: Archive provenance - 3 seeds
    archive_dir = THIS / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    for seed in [0, 42, None]:
        seed_label = f"seed_{seed}" if seed is not None else "seed_random"
        seed_dir = archive_dir / seed_label
        if seed_dir.exists():
            shutil.rmtree(str(seed_dir))
        seed_dir.mkdir()
        
        # Run test and pipeline with this seed
        env = {**os.environ, "PYTHONHASHSEED": str(seed) if seed is not None else "random",
               "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(SRC)}
        
        r1 = subprocess.run([py311, str(THIS / "tests" / "run_all_tests.py")],
                          capture_output=True, env=env, cwd=str(seed_dir))
        r2 = subprocess.run([py311, str(THIS / "run_integrated_pipeline.py")],
                          capture_output=True, env=env, cwd=str(seed_dir))
        
        # Copy output to seed dir
        out_src = THIS / "output"
        if out_src.exists():
            shutil.copytree(str(out_src), str(seed_dir / "output"))
        
        result["stages"].append({
            "label": f"archive_{seed_label}",
            "test_exit": r1.returncode,
            "pipeline_exit": r2.returncode,
            "test_output": r1.stdout.decode("utf-8", errors="replace")[-500:],
            "pipeline_output": r2.stdout.decode("utf-8", errors="replace")[-500:],
        })
    
    # Collect hashes of archive artifacts for comparison
    for seed_label in ["seed_0", "seed_42", "seed_random"]:
        sd = archive_dir / seed_label
        out_d = sd / "output"
        if out_d.exists():
            for f in sorted(out_d.iterdir()):
                if f.suffix == ".json":
                    result["stages"].append({
                        "label": f"{seed_label}/{f.name}",
                        "sha256": file_sha256(f),
                        "size": f.stat().st_size
                    })
    
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    return result

if __name__ == "__main__":
    import json
    evidence = run_evidence()
    evidence_path = THIS / "output" / "e28_evidence.json"
    evidence_path.parent.mkdir(exist_ok=True)
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    
    # Quick summary
    print("E28 Evidence Summary:")
    for s in evidence["stages"]:
        if "sha256" not in str(s.get("label", "")):
            print(f"  {s.get('label','?')}: exit={s.get('exit','?')}")
    
    print(f"\nFull evidence: {evidence_path}")
