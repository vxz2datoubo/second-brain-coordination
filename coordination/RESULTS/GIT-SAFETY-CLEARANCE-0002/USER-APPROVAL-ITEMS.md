# User Approval Items

## Approval Needed Before Git Baseline

1. **第二大脑知识文本是否入库**
   - `second-brain/rules.md`
   - `second-brain/lessons.md`

2. **第三方镜像资料是否纳入同仓**
   - `official-guide/`
   - `maibot/`
   - `MAIBOT_DOCS/`

3. **`codex_siliconflow_proxy/` 是否作为同仓子工程保留**
   - 当前目录混有源码、状态和 `.venv`
   - 若保留，建议先拆 source / state

4. **`tools/dreamina/dreamina.exe` 如何处理**
   - 首提建议排除
   - 如要长期保留，应明确授权和分发方式

5. **旧审计结果包是否长期入库**
   - `coordination/RESULTS/GIT-BASELINE-AND-FOUNDATION-AUDIT-0002/SECRET-SCAN.md` 当前含明文秘密，不可直接入库
   - 是否只保留新的脱敏摘要，需要你批准

6. **Foundation 代码是否作为首次基线当前状态直接纳入**
   - 建议：是
   - 但仅限代码 / 文档 / 测试，不含运行态写回

## Approval Not Needed For The Recommendation

这些已经足够明确，建议直接排除：

1. `data/`
2. `logs/`
3. `backups/`
4. `handoff/`
5. `qclaw-output/`
6. `chatgpt_bridge/playwright_state.json`
7. `chatgpt_bridge/playwright_user_data/`
8. `data/wallet.json`
