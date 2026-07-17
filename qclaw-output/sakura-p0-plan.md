# QClaw 输出 | 2026-06-16 23:57
> 模型: openclaw/default | 端口: 2258 | 耗时: 159s | 上下文: 647字符

我来为 Sakura AI 女友项目制定一份**可在一周内完成**的 P0 阶段执行计划，重点在快速见效、低风险改造。下面分五个方向逐一拆解，每一项都包含**问题 → 改动文件 → 关键代码 → 预期效果**四要素，可以直接照单执行。

P0 计划已落地为 `C:\Users\Administrator\.qclaw\workspace\sakura-p0-plan.md`（22.9KB / 5 个工作日排期）。

## 🎯 关键设计决策

| 方向 | 核心思路 | 选型 |
|---|---|---|
| **P0-1 瘦身** | 拆 `LLMClient` + `MessageBus`，主类只做编排 | `requests.Session` 复用连接 / 指数退避 1-2-4s / 单例工厂 |
| **P0-2 配置** | 3 JSON → 1 YAML，点号访问 | `pyyaml` + 内存缓存（无 Pydantic 依赖） |
| **P0-3 宠物** | 拖拽持久化 + 单击随机回复 + 滚轮切表情 | Tkinter + Pillow，不引新框架 |
| **P0-4 Bug** | UIA 加 `safe_get` / 回显改滑窗哈希 / LLM 加重试 | 错误类型白名单只对 `Timeout/ConnectionError` 重试 |
| **P0-5 拟人** | 思考延迟高斯分布 + 打字时长按字数 + 标点停顿 | 集中到 `utils/humanizer.py` 一处 |

## ⚠️ 需要你拍板的两点

1. **`llm_client.py` 里的 `requests.Session`** —— 默认全局复用连接池，**长连接下服务端可能主动断开**。要我加个 5 分钟空闲重连吗？
2. **`EchoDetector` 窗口 15s** —— 是我拍的板。如果你在 QQ 上打字特别快需要调短到 8s，告诉我即可。

## 📂 文件路径

- **计划文档**：`C:\Users\Administrator\.qclaw\workspace\sakura-p0-plan.md`
- 内含 5 段**可直接复制**的 Python 代码（`llm_client.py` / `message_bus.py` / `config_loader.py` / `desktop_pet.py` / `humanizer.py` / `echo_detector.py` / `uia_helpers.py`）

确认排期没问题就 **D1 开拆 `bot_engine.py`**；想调整顺序（比如先把 P0-4 Bug 修完再动架构）也可以说。