# Test Execution Receipt - R112 P1

agent_id: CODEX  
tested executable head: 70324e4a2f90916112638f5b8f6d9e67863bd4c8  
base: 56b72250eed460f32bd63f21046ae9b37b6f0aeb

| Check | Result |
|---|---|
| python -m unittest discover -s tests -p test_knowledge_reconciliation.py | 9/9 PASS |
| python -m unittest discover -s tests | 255/255 PASS |
| python public_safety_scan.py | PASS, 75 files, 0 issues |
| PyYAML/JSON parse of changed contracts | PASS, 3 files |
| git diff --check | PASS |

Negative tests included: domain isolation, provenance union/no duplicate vote, stale gate, temporal historical gate, invalid reconciliation preflight with zero mutation, control-shaped prompt rejection, secret-shaped rejection, private-domain denial, and timezone normalization.

This receipt is additive governance evidence only. The post-push exact remote head and final CI evidence must be published externally in the PR or Issue to avoid an infinite receipt-commit loop.
