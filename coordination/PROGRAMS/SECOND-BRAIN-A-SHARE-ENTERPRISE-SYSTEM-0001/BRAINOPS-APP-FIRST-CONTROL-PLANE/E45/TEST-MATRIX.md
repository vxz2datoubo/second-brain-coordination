# E45 Test Matrix

All tests are deterministic, synthetic and offline.

| Requirement | Test coverage |
|---|---|
| Raw caller witness cannot become positive | caller witness rejection; wrong attestor transport; cross-nonce substitution |
| Positive binding is exact | pre-decision blocked; cross-Claim terminal use rejected |
| Decision is fresh and one-shot | replay after a new ledger instance; expiry rejection |
| Identity splice is rejected | manual holder/correlation/transport splice; Automation and CLI splice |
| Recovery has no bypass | legacy direct recovery non-mutating; issued grant consumed by actual mutation |
| Lost response cannot become success | consumption succeeds, claim write fails, state remains claimed and grant remains consumed |

Expected suite after E45: 83 retained E44 regressions plus 13 E45 adversarial tests.
