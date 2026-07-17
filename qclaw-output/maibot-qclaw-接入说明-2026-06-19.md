# MaiBot / 开发期 QClaw 接入说明

日期：2026-06-19

## 已完成

1. `MaiBot/config/bot_config.toml` 已注册 `qclaw-bridge`
2. `MaiBot` 重启后可直接发现 `qclaw_ask` / `qclaw_analyze_douyin`
3. `QClaw` 工具结果会被视为高价值 MCP 结果，优先回灌第二大脑
4. 开发期新增本地辅助脚本 `tools/qclaw_dev_assist.py`

## MaiBot 侧用途

- 长消息总结
- 关系意图重分析
- 多候选回复草稿生成
- 长 prompt 润色
- 风格拟人化扩写

## 开发期用途

可直接在工作区调用：

```bash
python F:/ai/tools/qclaw_dev_assist.py "帮我重写这段拟人化 prompt，要求更像真人"
python F:/ai/tools/qclaw_dev_assist.py "总结这批关系设计文档的共性" qclaw-summary.md
```

## 注意

1. QClaw 是纯算力，不负责真实文件读取判断
2. 涉及本地文件事实时，必须由 Codex / WorkBuddy / MaiBot 本地链路先喂上下文
3. 改完 `bot_config.toml` 后要重启 MaiBot 才会生效

## 下一步建议

把 `qclaw_ask` 纳入一条受控委派规则：

- 私聊长消息
- 复杂情绪判断
- 需要多候选回复时
- 需要长文本风格润色时

只在这些场景触发，避免让 QClaw 抢主体人格。
