# R127 P2.4 WPDCR

agent_id: CODEX

## R132 P2.4B Structural Analogy

Planned/actual difficulty: D2/D2. The core task was not matching items; it was proving that a useful-looking structural lane cannot become a second discovery, admission, or evidence authority. The implemented lane therefore runs only after `ContextAssembler.assemble()` has completed all candidate, rank, budget, relation, provenance, and trust work.

Work and evidence: `StructuralFeature/v1` contains only atom-type, safe role class, normalized lifecycle bucket, bounded relation-type multiset from already endpoint-safe bundle relations, and a redacted temporal shape. `AnalogyItem/v1` uses a deterministic feature digest and bundle-local evidence positions, never atom/source/user/project/privacy identities. Exact feature matches are discrete, not numeric. `non_evidentiary: true` is explicit and the independently bounded items are projected only at `GPTSecondBrainContextBundle.context.analogies`.

Adversarial findings: zero/one/many restricted hidden relation neighbors yielded identical public features, items, omission count, admission, evidence, ranking, and trust output. Foreign, revoked, and invalid-time endpoints were suppressed. Default-off plans retain their prior plan hash; enabled analogy changes neither evidence atom IDs, ranking, scores, budget, admission report, votes, confidence, nor trust gate. Repeated and fresh-store construction remained deterministic.

Validation: focused GPT ContextBundle 12/12 PASS; full synthetic Phase 3 291/291 PASS; public safety 108 files/0 issues; YAML/JSON parse 13/7 PASS; `git diff --check` PASS. Exact final-head Python 3.11/3.13 CI remains the post-push GPT acceptance gate.

Plan change: inspection established that no store or graph-schema change was needed; consuming the already safe `bundle.relations` removes the raw-adjacency path entirely. No A/B expansion beyond receipt refresh was justified. R120-W01 and R122 stay deferred. Cross-agent handoff is GPT exact-head review of the new Draft PR; all external/private/formal/live/production/permission/trading/merge locks remain in force.

LOCAL_EXECUTION_ISSUES

- `R132-RECEIPT-PATH-001`
  - 问题特征: 本地 YAML receipt 验证命令把 `Path('.').parent` 当作 Program root，实际仍解析为当前 Phase-3 目录。
  - 发现途径与对照测试: 首次命令报 `FileNotFoundError`；仅将根目录推导改为 `Path('.').resolve().parent` 后，同一 parser 通过三个 receipt 与 Phase-3 13 YAML/7 JSON。
  - 根因范围与限制: 只影响这条验证命令的相对路径构造；未改写仓库文件，runtime、focused 与 full regression 结果不受影响。
  - 可逆解决办法与撤销方式: 使用 resolved absolute Phase-3 root 后再取 parent；回退到相对表达式即可复现错误。

## R131 provider-result canonical guard remediation

Planned/actual difficulty: D1/D1. The narrow defect was safety-policy drift: request egress used the canonical Phase-3 guard while result terms used a smaller inline regex. The hardest part was proving rejection occurs before candidate discovery, rather than merely observing an absent final bundle.

Work performed: the result guard now invokes the same canonical credential and prompt-injection predicates as request egress. Three adversarial classes were exercised: a private-key marker, an English `developer message` injection marker outside the old regex, and a Chinese `系统提示` marker. For every class, the provider result produced the same public bundle as default fallback and the index received only the original safe query.

Validation: focused Memory Palace 37/37 PASS; full synthetic Phase 3 287/287 PASS; public safety 108 files/0 issues; YAML/JSON parse 13/7 PASS; `git diff --check` PASS. Exact final-head Python 3.11/3.13 CI remains a post-push GPT acceptance gate.

Plan change and negative result: the expected minimal runtime patch exposed stale R127 handoff and receipt metadata. The task-owned audit records were refreshed without expanding runtime behavior. No additional AMED A/B improvement was warranted; structural analogy, external provider service, private source/store/canary, formal/live/production, permission, trading, and merge remain locked.

Discoveries and UNKNOWN: canonical request/result guard reuse prevents policy drift at this boundary. R120-W01 and R122 remain deferred. Cross-agent impact is limited to GPT reviewing PR #329 at the exact pushed head; no other agent action is required. LOCAL_EXECUTION_ISSUES = NONE_OBSERVED. Next acceptance gate: ordinary additive push, exact-head CI on Python 3.11/3.13, then GPT review.

Planned/actual difficulty: D2/D2. The central discovery is that the legacy callable string-concatenation seam is incompatible with a single governed semantic authority, even though P2.3 admission happens later. The contract therefore limits the future provider to public-safe enrichment and requires every resulting atom to use the existing assembler gate.

Structural analogy is deliberately separated from evidence. The hardest boundary is preventing a useful-looking analogy from changing support, counter, confidence, vote, or trust outcome; the proposed independent redacted-context lane makes this testable and reversible.

Rejected approaches: external embedding/vector service, provider atom-ID return, new numeric semantic weight, raw structural features, and analogy as evidence. GPT owns the numeric-weight decision and all implementation/private/formal/live/merge gates. Postflight requires YAML parse, public-safe scan, diff check, remote PR visibility, and GPT review. LOCAL_EXECUTION_ISSUES = NONE_OBSERVED.
