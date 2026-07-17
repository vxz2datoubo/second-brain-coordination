# QClaw 批量任务调度器 v1.0

**位置**: `F:\ai\qclaw-batch\qclaw_batch.py`
**目的**: 解决"WorkBuddy 监工消耗远大于 QClaw 生产"的问题

## 核心机制

1. **任务列表** → **串行调 QClaw**（避免端口冲突）→ **每完成一个立刻摄入第二大脑** → **写信号文件**
2. WorkBuddy 只在最后扫一次 `BATCH_STATUS.json`，不需要轮询
3. 失败自动重试 3 次

## 使用方式

### 方式 1：命令行（最快）

```bash
python F:/ai/qclaw-batch/qclaw_batch.py \
  "task-name1::详细prompt内容::5000" \
  "task-name2::详细prompt内容::4000"
```

### 方式 2：从文件加载

```bash
python F:/ai/qclaw-batch/qclaw_batch.py --from-file tasks.txt
```

文件格式（每行一个任务）:
```
# 注释行
task-name1::详细prompt::5000
task-name2::详细prompt::4000
```

### 方式 3：预设任务包

```bash
python F:/ai/qclaw-batch/qclaw_batch.py --recipe girlfriend_v1
```

任务包定义在 `F:\ai\qclaw-batch\recipes.json`

## 输出

- **任务文件**: `F:\ai\qclaw-output\<task_name>.md`
- **状态文件**: `F:\ai\qclaw-output\BATCH_STATUS.json`
  - WorkBuddy 扫这一个文件就知道全部结果
- **摄入节点**: 每完成一个任务就调 `/api/digest/text` 摄入第二大脑

## WorkBuddy 协作模式

1. **你** 发需求给 WorkBuddy
2. **WorkBuddy** 解析需求为任务列表，构造详细的 prompt
3. **WorkBuddy** 调用本脚本: `subprocess.run(["python", "F:/ai/qclaw-batch/qclaw_batch.py", "--from-file", "..."])`
4. **QClaw** 串行完成所有任务（无 WorkBuddy 干预）
5. **本脚本** 写完 `BATCH_STATUS.json` 退出
6. **WorkBuddy** 扫一次 `BATCH_STATUS.json`，一次性拿所有结果

**WorkBuddy 算力消耗从 ~150K 降到 ~20K**

## 注意事项

- QClaw 端口动态，每次启动前会做健康检查
- 单个任务 max_tokens 不要超过 6000（QClaw 上限）
- 任务数量建议 1-10 个（太多会触发 QClaw 速率限制）
- 失败任务不会终止整个 batch，会记录在状态文件里
