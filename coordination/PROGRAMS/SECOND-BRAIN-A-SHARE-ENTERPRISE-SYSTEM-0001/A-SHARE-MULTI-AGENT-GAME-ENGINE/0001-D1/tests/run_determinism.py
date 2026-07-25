import hashlib, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(seed):
 with tempfile.TemporaryDirectory(prefix='d1-') as d:
  dst=Path(d)/'d1'; shutil.copytree(ROOT,dst,ignore=shutil.ignore_patterns('__pycache__'))
  env=dict(os.environ,PYTHONHASHSEED=str(seed),PYTHONDONTWRITEBYTECODE='1')
  subprocess.run([sys.executable,'tests/test_synthetic_engine.py'],cwd=dst,env=env,check=True,capture_output=True)
  return subprocess.run([sys.executable,'tests/test_synthetic_engine.py','--normalized'],cwd=dst,env=env,check=True,capture_output=True).stdout.strip()
a,b=run(1),run(777)
if a!=b: raise SystemExit('NON_DETERMINISTIC_NORMALIZED_OUTPUT')
print('normalized_sha256='+hashlib.sha256(a).hexdigest()); print(a.decode())
