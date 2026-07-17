# sitecustomize.py - auto UTF-8 on Python startup
import sys, codecs, locale, os

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

for name, val in [('PYTHONIOENCODING','utf-8'), ('PYTHONUTF8','1')]:
    os.environ[name] = val

print('[sitecustomize] UTF-8 ready')
