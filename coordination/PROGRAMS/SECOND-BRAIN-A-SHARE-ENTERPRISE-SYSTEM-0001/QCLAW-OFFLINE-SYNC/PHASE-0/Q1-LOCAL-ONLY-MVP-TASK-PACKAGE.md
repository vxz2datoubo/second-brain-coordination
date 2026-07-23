# Q1 纯本地 MVP 任务包

## 目标

在云端(Git/Supabase)尚未建设的情况下, 让QCLAW现在就能够在本地持续消化知识并形成结构化候选包, 为未来批量同步做好准备。

## 时间范围

Q1 = 2026年7月-9月 (本季度)

## MVP 交付清单

### Sprint 1: 候选仓 Shell (Week 1-2)
- [ ] 创建 `F:/aidanao/qclaw-knowledge/` 完整目录结构
- [ ] 初始化 `state/state.sqlite` (packet_state, idempotency, cursor, sync_log 表)
- [ ] 实现 `init_knowledge_repo.py`
- [ ] 实现 `state_machine.py` (状态迁移引擎, 所有转换+验证)
- [ ] 实现 `packet_validator.py` (LearningPacket schema 验证)
- [ ] 单元测试: 状态迁移路径 + Schema验证

### Sprint 2: QCLAW输出包装层 (Week 3-4)
- [ ] 实现 `qclaw_packet_wrapper.py`
  - 拦截 QClawBridge.ask() 输出
  - 生成source_artifacts记录
  - 调用QCLAW做atom/relation提取
  - 写LearningPacket JSONL到 02-candidate-packets/
- [ ] 集成测试: 喂10条样本, 人工审核输出质量
- [ ] 隐私/许可自动标签 (基于内容关键词+路径)

### Sprint 3: 审核流 + 未知管理 (Week 5-6)
- [ ] 实现 `review_queue.py` — 展示 REVIEW_REQUIRED 的packet
- [ ] 实现命令行审核: `review_packet.py <id> approve|reject|quarantine`
- [ ] 实现未知注册表: 所有UNKNOWN_CLASSIFICATION的内容自动进入 07-quarantine/
- [ ] 统计面板: 产出量/审核率/常见问题

### Sprint 4: 出站箱 + 存量处理 (Week 7-8)
- [ ] 实现 `freeze_bundle.py` — 冻结approved包到 05-sync-outbox/
- [ ] 实现 preflight 检查 (隐私/许可/冲突/重复)
- [ ] 处理现有207个存量文件: 分类 → 包装 → 候选
- [ ] 容量监控 + 日志轮转

## MVP 不包含

- Git推送 (等私有仓库创建)
- Supabase投影 (等Supabase项目创建)
- 对象存储 (等云存储配置)
- 双向同步 (等权威库建立)
- 用户审批UI (先用命令行)

## 验收标准

- [ ] QClawBridge.ask() 调用后自动生成结构化LearningPacket
- [ ] 所有packet有内容哈希、来源和隐私标签
- [ ] RESTRICTED_NEVER_SYNC 的内容被硬阻止在Quarantine
- [ ] 状态机所有转换经过测试
- [ ] 现有207个文件 ≥80% 被分类和包装
- [ ] 磁盘增长在预估范围内 (<500MB新增)
