# A0 架构基线施工收据

- `agent_id`: `CODEX`
- `program_id`: `INTERACTIVE-CINEMATIC-PLATFORM-0001`
- `base_sha`: `2f12aba6dae4a83038fef1f3d5e737944bd9ce1f`
- `executor_status`: `EXECUTOR_VERIFIED_ONLY`
- `scope`: GitHub 控制面、产品理解映射、稳定接口目录、协作所有权、离线验证器与测试。
- `non_scope`: 真实用户数据、照片、凭证、外部或付费模型、抖音实接、生成媒体、生产部署、交易、canonical knowledge 写入、Eustia 导入。

## A0 验证命令

```powershell
python tools/verify_interactive_cinematic_platform.py
python -m unittest tests.test_interactive_cinematic_platform_architecture
git diff --check
```

精确 HEAD 会在该架构切片冻结并准备正式交接时写入 `AI_HANDOFF.yaml` 和新的执行收据；本文件不能自指向尚未产生的提交。GitHub CI 绿色或施工者本地通过均不构成独立验收。

## 本次施工者验证结果

- `python tools/verify_interactive_cinematic_platform.py`：通过；控制面 10 个必需文件、29 个公共契约、3 个协作分支前缀全部一致；没有外部调用或私有数据读取。
- `python -m unittest tests.test_interactive_cinematic_platform_architecture`：4/4 通过；覆盖正常验证、重复契约拒绝、缺失控制面文件拒绝和错误分支前缀拒绝。
- `python -m unittest discover -s tests -p "test_creative_*.py"`：136/136 通过；用时约 136 秒，证明 A0 未破坏现有合成创作运行时回归。
- `git diff --check`：通过；未发现空白符错误。

## 设计证据与限制

- 用户批准的首季时长约束、题材、模型角色、风格和头像修订行为已记录在 `PRODUCT-UNDERSTANDING-MAP.yaml`，并带漂移检查。
- 外部文档只作为设计边界的链接和说明，不导入外部资产、评论或用户数据。
- 抖音评论图片与真实供应商能力均被建模为未验证能力门，而非当前承诺。
- 下一实施片段为 A1：多剧本运行时与导演切换，必须保持既有合成剧本的存档迁移与回放兼容。
