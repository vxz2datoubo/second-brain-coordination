# R2 Test Run Receipt

task_id: `CODEX-PR95-R2-ENTERPRISE-DEPTH-PUBLIC-PATH-AND-REMOTE-PUBLICATION-CLOSURE`  
route_epoch: `3`  
tested_head_full_sha: `3963792bfcc47ad4d8fcd80fe5edde7ae4729003`  
receipt_head_ref: `THIS_COMMIT`

## Preserved failed checks

1. The first R2 static validator on `2a68a5751f67a630d77d0bff084c0af7048607a7` failed closed: the rational/best-response action contract omitted `competing_hypotheses`. Commit `3963792` added the required field before the successful tested run.
2. The first local-path regular expression treated the `https://` prefix in a JSON Schema URI as a drive path. The scanner was corrected to require a non-letter before a drive prefix; this was a scanner false positive, not a physical-path disclosure.

## Successful tested run

| Check | Exact command class | Exit | Normalized stdout SHA-256 | Normalized stderr SHA-256 | Result |
| --- | --- | ---: | --- | --- | --- |
| Strict validator | `python -` inline strict YAML loader, JSON parser, duplicate-key fixture, matrix references, fixture/invariant and action-contract assertions, plus base-to-tested allowlist assertion | 0 | `f96da40229e37e3deafe7bc1e0c170d43d99399e7e1c8581fa5e7065c9555404` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | PASS: 27 YAML, 1 JSON, 8 matrix requirements, 12+ fixtures, 22 changed paths. |
| Local physical-path scan | `rg -n --pcre2 '(?<![A-Za-z])[A-Za-z]:[\\/]|(?<!https:)/(?:home|Users)/' <D0-root>` | 1 interpreted as clean | `7849211ace5c33379729472fee9fb0469082a7c80d6248f3e59b8b41a5e08179` | empty SHA above | PASS: zero matches. |
| Credential-value scan | `python -` non-disclosing regex scan for GitHub-token, private-key, AWS-access-key and value-bearing credential assignments | 0 | `2241d25f4bc116da78f9235d4b8626b57ca9bc10f4b34f710d7a06ebdd4c3a94` | empty SHA above | PASS: zero matching files; no values emitted. |
| Whitespace scan | `git diff --check 150e339a98ba07a70a369c33d46a10b077707cee` | 0 | `531a62067629ec38e912d348148c7183f3fefa118a984525fe78804a85755a4d` | empty SHA above | PASS. |

The inline validator is intentionally not committed because the allowlist forbids committed helpers/generators. It is fully described above and its actual tested head, exit code, counts and normalized output hashes are retained. No real data, source activation, replay, backtest, MARL, account, order, trade or performance test was run.
