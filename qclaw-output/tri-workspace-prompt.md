你是一个系统架构师。请为三个AI角色设计一个统一的协作工作区。

## 背景
三个AI角色需要在一个共享目录下协作：
1. WorkBuddy（迪迪）— 中枢调度器，负责路由、记忆、决策、工具调用
2. Codex（你）— 工程实现，负责代码生成、重构、审查、调试
3. QClaw — 后台算力，负责分析、总结、索引、批处理

## 现有目录结构（F:/ai 下已存在的，需要整合进三方协作框架）
- super-jarvis/（共享协议目录，已完成Phase 1）
- data/knowledge-graph.json（知识图谱）
- core/（核心模块：qclaw.py, codex_bridge.py 等）
- mcp/（MCP桥接：qclaw_bridge.py, codex_bridge.py, fs_tools.py）
- qclaw-output/（产出物）
- CODEBUDDY.md（项目上下文文件）
- server.py（第二大脑HTTP服务器）
- app/index.html（前端）

## 输出要求

### 1. 生成 F:/ai/super-jarvis/TRI-WORKSPACE-GUIDE.md
包含：
- 工作区全景图（目录结构+每个路径的用途）
- 每个角色读/写哪些路径
- 文件格式和命名规则
- 三方通信协议（如何发起任务、传递结果、同步状态）
- 错误处理和回退策略

### 2. 生成 F:/ai/super-jarvis/collaboration-prompts.json
包含三个prompt模板，分别面向三个角色。每个prompt应该包含：
- 角色定义
- 工作区说明
- 协作协议
- 当前任务上下文
- 可执行的具体行动

三个模板：
1. "发给 WorkBuddy 的协作prompt" — 让WorkBuddy知道自己是中枢调度器
2. "发给 Codex 的协作prompt" — 让Codex知道自己是工程实现
3. "发给 QClaw 的协作prompt" — 让QClaw知道自己是后台算力

注意：prompt要可以直接复制发给对方，对方拿到后就能理解自己的角色、权限、和协作方式。

先扫描现有super-jarvis目录结构和已有文件再设计。
