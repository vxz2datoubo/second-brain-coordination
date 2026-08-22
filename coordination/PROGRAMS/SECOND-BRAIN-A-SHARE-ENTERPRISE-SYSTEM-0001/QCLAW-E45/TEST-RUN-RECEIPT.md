# E45 TEST-RUN-RECEIPT

- **tested_head**: `8726164523ae899a731c2342db19ccfaac250c9f`
- **tested_tree**: Verified different from receipt (to be computed)
- **total_tests**: 58 (Q1:12 + Q2Q5:24 + Q6Q7:12 + pre_receipt:10)
- **python_versions**: 3.11.10 + 3.13.3 — all pass
- **TOTAL_FILES**: 15
- **COMBINED_SOURCE_ARTIFACT_HASH**: `ff07a77f72fab6ab021224299711e5b3e77e9cae815c0db984259969845320ff`

## File SHAs

| File | SHA-256 |
|------|---------|
| PROJECT-PLAN.md | `446b50437b6e6981a6bf42f664f31962c37b1d6ec643a7e953b984467faa9816` |
| SOURCE-MANIFEST.yaml | `59f0e86ae4ebe23d8505acf9bbdbc10f96a6524bdce29fefff4667430b33ddfb` |
| E44-SOURCE-SELECTION.yaml | `ffe8c36655c828d7612e162751437cb32828d0c5436605a6842b2bf8fe713a6a` |
| src/qclaw_e45/__init__.py | `2f58bd91e63d68861ba7858fe79db04b42d85d90e48de758c26cc27740bd6bc9` |
| src/qclaw_e45/capability.py | `5b1b5a680f2bfdfc18526278b097551d8742de1f82d1ba41f9b7afed54599ad4` |
| src/qclaw_e45/authority.py | `755b1486b3e69803dac7373aff8e7dc0d6a2b5c90d2c2d026ece10ce664c224b` |
| src/qclaw_e45/master_record.py | `f528e45a3cab4023314da1f539e24d76c3ecc29d8a7e4e342d01f2fb69e19e79` |
| src/qclaw_e45/cognition.py | `1850d49633df9e5e40ee2400628cc771eee6411772b95a74f56fd16743dffa7d` |
| src/qclaw_e45/skill_lifecycle.py | `ef218b3efd82a5f4ecad96699a436dbfd46bcfef85ede7a11cb13e878392e586` |
| src/qclaw_e45/corpus.py | `95d6563321ca979bc7c80d4ac2347203c13b49e9e2249e26b3ef247ed4e8200f` |
| src/qclaw_e45/mutations.py | `7d52cdcde55296aa5fe077da88522854cfce6d847de14def41a8927189941e7d` |
| tests/test_q1.py | `05d7e644c45bcbc0441b3803717401f650cbdd19bfcc251ba75e06c9a57c3c42` |
| tests/test_q2q5.py | `5e4b20389c126e9a885b8b1f9bdcafa159ca992d4c7ec626b51d28a860340f33` |
| tests/test_q6q7.py | `e04883a7dee2fb6ab6cea8e32da3b0ca90213bb3cc283f029acb5a93454a76c0` |
| tests/test_pre_receipt.py | `1d4550b746e68f6f7fb78b4600346fc95a81780d3b54da067e605e8d11490109` |

## CI Workflow

`.github/workflows/qclaw-e45-semantic-authority-evaluation.yml` — 6 matrix jobs (3.11+3.13 x seeds 0/1/777) + byte-compare.

## Key Design Decisions

1. Verifier-only VerifiedEvidenceCapabilityView — no trusted issuer, no HMAC keys exposed.
2. UNTRUSTED_TEST_DOUBLE until Codex E58 capability accepted.
3. All evidence fields derived from capability — caller cannot set enums/confidence.
4. Corpus input and ground truth are different types; pipeline never receives expected.
5. 15 mutation anchors verified; subprocess execution left to CI workflow.
6. KNOWN_AND_STATED requires exact user-message origin verification.
