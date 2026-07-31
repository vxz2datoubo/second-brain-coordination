# SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md — E24
## 系统发现

### 1. 共享 CI Workflow SHA 校验
- **发现**：`phase3-integrated-offline-memory.yml` 本地 blob SHA `38f50fe7b56bfef2415262d771602a7a6efce22ef8464813050afa71cdf6afeb` 与 main canonical **精确匹配**
- `cd6752278deb2d5b3bf0a5ce21fe998318929de68a03a8f3adda2a853cc56c36` 为误报（origin/main ref 不可直接读）
- **教训**：用 `git hash-object` 直接比对文件 blob，不依赖 ref 间接引用的 refspec（origin/main 可能是 stale shallow fetch）

### 2. D2 Game Core 规范检索
- PR #58 (Codex Phase 4) 分支不可达（HTTP 404）
- 规范 D2 需从 commit `d6f9e2e4d38861e91353be177c9ceacedde6d7ee` 提取
- `git show d6f9e2e4:d2_game_core.py` 返回完整 75587B 文件，SHA `33a7d821...`

### 3. 双 Python 环境
- 3.11.10（QClaw 自带）与 3.13.3（手动安装）均已确认可用
- 双版本下 E24 证据运行器产出完全一致
- 3.12 已弃用（E22 被 GPT 拒绝）

### 4. Git Database API 推送模式
- `git push` 持续失败（Connection reset / RST）
- Git Database API（create blob → tree → commit → update ref）已验证可用
- 模式在先前的 push_e22.py、push_e23.py 中建立
- E24 将复用该模式推送两提交（corrective tested + receipt-only）

## 改进机会
- 将 Git Database API 推送流程标准化为 skill/template
- 用 `git hash-object` 替代 `git show origin/main:...` 做 CI blob 校验
- D2 snapshot YAML 应与 commit hash 绑定而非仅文件 hash（防止自证）