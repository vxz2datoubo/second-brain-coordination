# E34 Test Run Receipt

- Task: `CODEX-PEOS-0010-E33-ARCHIVE-CHANGED-FILES-TOKEN-CONTRACT-AND-SINGLE-RECEIPT-CLOSURE-0026-E34`
- Route epoch: `35`
- Tested commit/tree: `c2f3aef1fdc40da5b7f119654ec9f65f597dccca` / `666a28613cabe0653bddd717314ceac2b696417d`
- Exact GitHub Actions run: `30706808220`
- Python 3.11 job `91387230459`: `122/122 PASS`; three clean Git-archive roots.
- Python 3.13 job `91387230487`: `122/122 PASS`; three clean Git-archive roots.
- Archive content SHA-256: `7c0110fbeae6b7a8613b157e1162e613d75e26177475ddb4b104a53346acebb5`
- Archive artifact-set SHA-256: `83c89e43f25e9962c8115464c20e9e41d88e83b5287551867fc9359699e53e40`
- Artifact digests: Python 3.11 `sha256:c13d989c12afac40128f699a22a0367501ef5a8028ed16718f60e1d69a891752`; Python 3.13 `sha256:11091f94eb12b2a924d727de307235a7087429adcb7fd457a0c498e56f142c8f`.

## Exact tested command

```text
PYTHONHASHSEED=1 python -B ./coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL/ci_verify.py --changed-files ./.e32-changed-files.txt --commit c2f3aef1fdc40da5b7f119654ec9f65f597dccca --tree 666a28613cabe0653bddd717314ceac2b696417d --tested-commit c2f3aef1fdc40da5b7f119654ec9f65f597dccca --tested-tree 666a28613cabe0653bddd717314ceac2b696417d
```

Both jobs exited `0`. The machine-readable archive matrix records the three roots, commands, checksums and all 64 declared public-safe artifacts. No production, account, market-data or trade function was run.
