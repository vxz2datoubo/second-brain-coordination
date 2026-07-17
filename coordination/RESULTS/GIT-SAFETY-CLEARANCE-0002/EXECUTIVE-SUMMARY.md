# GIT-SAFETY-CLEARANCE-0002 — Executive Summary

## Decision Snapshot

1. **当前是否可以安全执行 `git init`？**
   - **不建议现在执行。**
   - 技术上不存在嵌套仓库阻塞，但当前工作区还没有经过批准的忽略规则，也仍存在确认的明文秘密与运行态会话文件。

2. **当前是否可以安全执行初始 `git add`？**
   - **不可以。**
   - 目前如果直接 `git add .`，高概率会卷入明文凭据、浏览器会话、数据库、日志、审计结果、缓存和第三方二进制。

3. **阻塞 Git 基线的当前问题**
   - `core/tushare_bridge.py` 中的硬编码 Tushare token
   - `core/qclaw.py` 中的硬编码 QClaw fallback token
   - `daytrade_system/live/tdx_mcp_client.py` 中的硬编码 TDX OAuth token
   - `mcp/tdx_live_bridge.py` 中带真实值的 env fallback
   - `data/wallet.json` 中的真实 API key / token
   - `chatgpt_bridge/playwright_state.json` 与 `chatgpt_bridge/playwright_user_data/` 中的真实 Cookie / localStorage session material
   - 历史审计文件 `coordination/RESULTS/GIT-BASELINE-AND-FOUNDATION-AUDIT-0002/SECRET-SCAN.md` 仍含明文 token

4. **不阻塞但应后续处理的问题**
   - `second-brain/rules.md`、`second-brain/lessons.md` 是否作为源码资产入库，仍需用户决定
   - `official-guide/`、`maibot/`、`codex_siliconflow_proxy/`、`tools/dreamina/` 是否纳入同一个仓库，仍需用户决定
   - 旧结果包与新结果包的长期保留策略需要收敛

5. **建议的首次提交范围**
   - 采用**清洁基线**策略。
   - 先提交母系统源码、测试、治理文档、配置模板、已批准的审计摘要。
   - 不提交数据库、日志、实时数据、浏览器状态、钱包文件、回滚包、第三方虚拟环境和未批准的第三方镜像资料。

6. **Foundation 是否建议进入首次提交？**
   - **建议进入，但只包括源码 / 文档 / 测试部分。**
   - 具体包括：
     - `brain_core/foundation_data_governance.py`
     - `brain_core/service.py` 的 Foundation 代码增量
     - `apps/cli/brainctl.py` 的 Foundation CLI 增量
     - `docs/governance/*.md`
     - `tests/test_foundation_data_governance.py`
   - 不包括 Foundation 运行态写回：
     - `bulletin/super-second-brain-v01-board.md`
     - `data/super_brain_v01.sqlite`
     - `data/audit/events.jsonl`

7. **建议先建“清洁基线”还是带上当前 Foundation 运行态一并提交？**
   - **建议先建“清洁基线”。**
   - 但“清洁基线”的源码状态可以直接采用**当前已验证通过的 Foundation 代码状态**。

## Strict Baseline Simulation

- 拟直接纳入首提的严格安全范围：`60` 个文件，约 `2.63 MB`
- 拟在脱敏后纳入的文件：`4` 个，约 `37.9 KB`
- 明确永久排除或当前必须排除的运行态 / 数据 / 缓存：`16,113` 个文件，约 `721.21 MB`
- 需用户决定是否纳入的范围：`204` 个文件，约 `33.18 MB`

## Largest Safe Candidate In Strict Baseline

- `brain_core/trading_domain.py` — `1,224,073` bytes

## Biggest Risk That Changed This Round

上轮审计主要盯住了桥接代码和数据目录；这轮确认了一个更隐蔽的问题：

- **旧审计报告本身也可能成为秘密泄露源。**

当前最典型的例子是：

- `coordination/RESULTS/GIT-BASELINE-AND-FOUNDATION-AUDIT-0002/SECRET-SCAN.md`

这个文件不应在未清洗前进入任何初始 Git 基线。
