你是一个系统架构师 + 代码审查专家。请对 F:/ai 下的整个 Super Jarvis 系统做全面审查。

## 审查范围

### 1. 知识图谱 (data/knowledge-graph.json)
- 读取当前知识图谱，检查节点和边的质量
- 检查分类是否合理
- 检查是否有残留问题

### 2. 共享协议目录 (super-jarvis/)
- 检查目录完整性（有没有缺失的子目录）
- 检查 schema 文件的质量和自洽性
- 检查任务队列是否有残滞留
- 检查决策记录格式
- 检查记忆文件的格式

### 3. 核心模块 (core/)
- codex_bridge.py - 调用方式、错误处理、默认参数
- qclaw.py - 端口探测、健康检查、幻觉检测
- decision_consult.py - 逻辑完整性

### 4. MCP 桥接 (mcp/)
- qclaw_bridge.py - 协议版本、工具完整性
- codex_bridge.py - doctor函数、模型默认值
- fs_tools.py - 工具设计

### 5. 系统文件
- CODEBUDDY.md - 是否与实际一致
- server.py - 基本健康检查

## 输出要求
1. 扫描所有文件，不要跳过
2. 对每个模块输出：✅ 没问题 / ⚠️ 有小问题 + 建议 / ❌ 严重问题 + 具体修复方案
3. 生成报告 F:/ai/super-jarvis/outputs/codex/系统审查报告.md
4. 按严重程度排序：P0(立即修复) > P1(尽快修复) > P2(建议优化)
