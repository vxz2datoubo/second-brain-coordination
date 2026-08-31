# 接手与验证手册

## 从干净工作树接手

1. 只从远端分支创建新工作树；不要依赖任何聊天记录、未提交文件或运行时目录。
2. 先阅读 `PROGRAM.yaml`、`STATUS.yaml`、`MODULE-OWNERSHIP.yaml`、`AI_HANDOFF.yaml`、本文件和对应切片证据。
3. 确认 branch、base SHA、HEAD SHA（若正式交接已冻结）和执行者身份一致。任何不一致先记录事实，不能猜测补齐。
4. 执行下方的离线验证。A0 不读取凭证、不调用网络供应商、不产生真实媒体。
5. 接手时先在 `STATUS.yaml` 声明唯一进行中切片、可改路径、完成条件和非目标；一次切片只做书面范围。

## A0 复现命令

```powershell
python tools/verify_interactive_cinematic_platform.py
python -m unittest tests.test_interactive_cinematic_platform_architecture
git diff --check
git status --short
```

期望：验证器输出 JSON `"status": "pass"`；单元测试通过；`git diff --check` 无输出。验证器只检查控制面结构和契约目录，不代表对创作质量或外部模型的独立验收。

## A1 及以后的一般验证

```powershell
python -m unittest discover -s tests -p "test_creative_*.py"
python tools/verify_creative_runtime.py --expected-head (git rev-parse HEAD)
python tools/verify_interactive_cinematic_platform.py
git diff --check
```

施工者可在另一份干净克隆复现上述命令，称为“施工者洁净复现”；这不等于独立验收。正式独立验算必须由未参与实现的 GPT 或其他未参与执行者完成，并记录 exact HEAD。

## 离线与外部服务边界

- 当前仅可使用确定性离线叙事/媒体适配器。
- 真实 DeepSeek、MiniMax H3、抖音或其他外部服务，需要用户对具体提供方、凭证存放、预算、保留期限和公开范围的单独批准。
- 不扫描、不读取、不复制凭证、cookie、账户资料或私有媒体。它们必须位于 Git 之外的本地私有层。
- 不导入 Eustia 历史目录或其中任何资产；先完成独立来源与内容审查。

## 回滚

GitHub 控制面和运行时改动都按切片提交。发生问题时由集成者以一个新的 revert PR 回滚精确切片提交；不要 force-push、rebase、amend、reset 或重写历史。真实外部任务的停止、撤销与删除由未来的本地私有运营流程处理，不由 Git 回滚假装完成。

## 合并清单

只有 GPT 作为独立集成者在以下全部成立时可提出合并：精确 HEAD、可复跑命令、测试收据、`AI_HANDOFF.yaml`、实际执行者和独立复核者、无私有数据/凭证、用户明确授权。Codex 不可自审、自验收或自合并。
