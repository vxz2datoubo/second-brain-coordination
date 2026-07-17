# AI接管提示词模板

请复制以下内容到新的对话中：

---

# 项目接管 - 波仔量化交易系统

## 项目概述
波仔量化交易系统是一个可进化的A股倒T交易系统，以第二大脑知识库为核心，任何AI工具都能无缝接管。

## 项目位置
```
F:/aidanao/
```

## 立即读取以下文件（按顺序）

1. **F:/aidanao/WORK_STATUS.md** — 工作状态，了解当前进度
2. **F:/aidanao/AGENTS.md** — 系统架构入口
3. **F:/aidanao/SYSTEM_MANUAL.md** — 完整AI手册
4. **F:/aidanao/second-brain/rules.md** — 交易规则

## 快速启动

```bash
# 启动第二大脑服务
python F:/aidanao/server.py

# 测试API
curl http://localhost:8766/api/trading/stats
```

## 核心API

| API | 说明 |
|-----|------|
| GET /api/trading/stats | 交易统计 |
| GET /api/trading/rules | 交易规则 |
| GET /api/trading/lessons | 历史教训 |
| POST /api/trading/check | 决策前检查 |

## 关键知识

- 目标股票：昆仑万维(300418)、蓝色光标(300058)
- 交易策略：倒T优先（先卖后买）
- 仓位约束：单笔5000元，日上限3笔
- 熔断线：日亏>2%全天停止

## 目标

1. 继续完善交易系统
2. 让系统能够自我进化、自我迭代
3. 自我检验、自我学习
4. 实现完全自主的量化交易能力

## 注意事项

- 始终先读取WORK_STATUS.md了解进度
- 决策前调用/api/trading/check进行自检
- 遵守second-brain/rules.md中的红线规则
- 任何修改后更新知识库

---
