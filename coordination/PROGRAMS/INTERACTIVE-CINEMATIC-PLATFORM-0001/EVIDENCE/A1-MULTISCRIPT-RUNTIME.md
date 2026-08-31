# A1 多剧本运行时施工收据

- `agent_id`: `CODEX`
- `slice`: `A1_MULTI_SCRIPT_RUNTIME_AND_DIRECTOR_SWITCHING`
- `base_sha`: `f2895367fcd0ed60305ccc005971789e0644d72b`
- `executor_status`: `EXECUTOR_VERIFIED_ONLY`
- `scope`: 合成 `ScriptPackage/v1` 注册表、四种可选风格档案、旧场景初始化兼容、明确 `DirectorBrief/v2` 绑定和 CLI 检查入口。
- `non_scope`: 新的旗舰剧情内容、真实照片、外部模型、真实媒体、抖音实接、付费调用、部署、Eustia 导入和 canonical knowledge 写入。

## 可验证行为

1. 现有四个合成 scenario 均被解析为经批准的、仅合成来源的 `ScriptPackage/v1`。
2. 旧 `--scenario` 初始化仍生成原始账本和可重放路径；新 `--script-id + --script-revision` 初始化生成同一初始状态。
3. `director-v2` 需要精确 `script_id`、`script_revision` 和 style profile，并从不可变账本导出唯一 campaign、状态哈希和连续性哈希。
4. director v2 再绑定角色修订、当前场景资产和注册的导演策略版本；脚本、版本、风格、campaign 或场景资产不一致时 fail closed。
5. 四种风格记录不同渲染规则，但共享已验证剧情状态、连续性哈希、角色版本和镜头事实。

## 验收命令

```powershell
python -m unittest tests.test_interactive_cinematic_multiscript
python -m unittest discover -s tests -p "test_creative_*.py"
python tools/verify_interactive_cinematic_platform.py
git diff --check
```

精确 HEAD 在 A1 完整回归和洁净克隆复现后才冻结并放入正式集中审核包。上述是施工者证据，不是独立验收。

## 当前施工者验证结果

- `tests.test_interactive_cinematic_multiscript`：7/7 通过。
- 既有 `test_creative_*.py` 回归：136/136 通过，用时约 95 秒。
- 控制面验证器：通过；未读取私有数据，未发起外部调用。
- 下一步：执行 staged diff 检查、提交、推送，再从独立干净克隆复现 A1 专项验证。
