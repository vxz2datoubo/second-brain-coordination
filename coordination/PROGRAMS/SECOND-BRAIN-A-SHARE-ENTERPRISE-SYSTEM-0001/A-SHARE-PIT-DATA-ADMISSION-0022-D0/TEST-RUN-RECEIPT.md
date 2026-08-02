# Test Run Receipt

`agent_id: CODEX`
`task_id: CODEX-PR90-R2-STRUCTURED-RULE-REGISTER-AND-REPRODUCIBLE-RECEIPT-CLOSURE`
`workspace_alias: PR90-R2-CODEX-WORKTREE`
`tested_head: abc9b618eacec0a3004a56b614e56f196161c107`

Normalization for every hash: replace CRLF/CR with LF, UTF-8 encode, SHA-256. The `receipt_head` is the receipt-only commit containing this file; its exact SHA and full three-file delta are reported in the PR/Issue completion receipt.

| Check | Exact command | UTC start/end | Exit | Count | stdout SHA-256 | stderr SHA-256 |
| --- | --- | --- | ---: | --- | --- | --- |
| environment | `python --version && python -c "import platform,yaml; print(platform.platform()); print('pyyaml='+yaml.__version__)"` | 2026-07-24T08:05:06.754556Z / 2026-07-24T08:05:07.163724Z | 0 | Python/platform/PyYAML | `fdb832deb5ea5a29aed43cf38eacf0338ee91e46850d902bb3591bb4be87b67f` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| structural duplicate-key validator | `python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/A-SHARE-PIT-DATA-ADMISSION-0022-D0/validate_d0_admission_contract.py` | 2026-07-24T08:05:07.163833Z / 2026-07-24T08:05:07.298230Z | 0 | 16 required artifacts plus duplicate-key self-test | `fb49571bb59ed4d95000b70183c3b5d528a32fcdd2574f661983cdddde6be2d5` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| YAML parse | `python -c "import yaml,pathlib; d=pathlib.Path(r'coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/A-SHARE-PIT-DATA-ADMISSION-0022-D0'); [yaml.safe_load(p.read_text(encoding='utf-8')) for p in d.glob('*.yaml')]; print('yaml_parse_ok',len(list(d.glob('*.yaml'))))"` | 2026-07-24T08:05:07.298310Z / 2026-07-24T08:05:07.490714Z | 0 | 13 YAML files | `70324a2f578c99b8da800ab1cd6e3fe43aeb476eabac4428dbaace816b274aa2` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Python AST | `python -c "import ast,pathlib; ast.parse(pathlib.Path(r'coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/A-SHARE-PIT-DATA-ADMISSION-0022-D0/validate_d0_admission_contract.py').read_text(encoding='utf-8')); print('ast_parse_ok')"` | 2026-07-24T08:05:07.490794Z / 2026-07-24T08:05:07.614232Z | 0 | 1 validator file | `f2f355967f5e7c8103863ae7a16661b2255de3b0118e98e741b384383245a350` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| public-safe scan | `python -c "import pathlib,re,sys; d=pathlib.Path(r'coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/A-SHARE-PIT-DATA-ADMISSION-0022-D0'); p=re.compile(r'(?i)(ghp_[A-Za-z0-9]{20,}|AIza[\w-]{20,}|sk-[A-Za-z0-9]{20,}|[A-Z]:\\)'); hits=[str(x) for x in d.rglob('*') if x.is_file() and p.search(x.read_text(encoding='utf-8'))]; print('public_safe_scan',len(list(d.glob('*.*'))),'hits',len(hits)); sys.exit(bool(hits))"` | 2026-07-24T08:05:07.614347Z / 2026-07-24T08:05:07.747282Z | 0 | 16 package files; 0 hits | `6746263777bd31877a0bf1e5d530d1a57890b71f8d57a81c4211abab5a8f6ac8` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| PR #51 regression | `python -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION/tests -p test_*.py` | 2026-07-24T08:05:07.747399Z / 2026-07-24T08:05:08.109161Z | 0 | 61 tests | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `f2a0dac988004de0103f5d7404db9a6631fd6a3ef4008e04a6acfd69a85fd4ea` |

Environment output: Windows 11 `10.0.22631`, Python `3.13.13`, PyYAML `6.0.3`.

Negative execution evidence: two preliminary receipt-capture harnesses exited before target testing because of PowerShell quoting and unavailable old-runtime APIs. Neither ran any target check; the final Python-standard-library harness above ran the complete command set at `tested_head` and all required checks passed.

No real source, adapter activation, local data, replay, labeling, backtest, account, or trading interface was used.
