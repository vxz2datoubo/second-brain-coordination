# Decision Log — SuperBrain + MaiBot 双脑系统

> 最后更新: 2026-07-12 00:46 GMT+8
> 蓝图: `MaiBot_接入超级智慧大脑蓝图_加入自我迭代维修系统_v2.docx`
> 格式: 按时间倒序，每条含决策内容、理由、影响、状态

---

## 决策记录

### D-016: 蓝图 §18 全部完成 — Phase 4-7 实施策略 [2026-07-11]
- **决策:** 在一个会话窗口内完成 Phase 4-7 全部交付（EmotionEngine + GoalEngine + 多Agent + MAPE-K 自我进化），新增 3 个 core 文件（emotion.py, goals.py, agents.py, self_evolve.py），总计 ~2,280 行 Python，48+ API 端点，88/88 E2E 全通过。
- **理由:** (1) 蓝图已有完整定义，纯 Coding 而非 Research，可一次性交付 (2) 各 Phase 依赖关系已在 contracts.py 中预埋 (3) 所有 E2E 测试可并行编写运行
- **决策流程:** 每个 Phase 完成后立即写 E2E 验证 → 先全部通过再进入下一 Phase → 全部完成后更新所有台账
- **影响:** 
  - 新增文件: goals.py (~600行), agents.py (~540行), self_evolve.py (~640行)
  - 新增 API: 15 (Goal) + 6 (Agent) + 18 (Evolve) = 39 个新端点
  - 总计 API: 48+
  - E2E 测试: 12/12 (Phase 4) + 19/19 (Phase 5) + 27/27 (Phase 6) + 30/30 (Phase 7) = 88/88
  - 服务不中断: server.py 始终保持语法正确并热更新
- **状态:** ✅ 全部实现 + E2E 验证通过

### D-015: 冲突检测人性化输出 — 双字段方案 (P2.7) [2026-07-10]

### D-2026-07-09-02 | superbrain_bridge Phase 0 插件骨架实施

- **决策:** 一次性完成 P0.2-P0.9 (7文件的完整插件骨架 + 3 个 Mock Tool)，而非逐文件分步
- **理由:** 参考 hello_world_plugin 和 deskpet-plugin 的成熟模板，MockMemoryStore 设计可直接复用到 Phase 1 HTTP 模式；一次性交付减少上下文切换
- **影响:** Phase 0 交付物 P0.2-P0.9 全部完成，仅剩 P0.10 (MaiBot 加载验证)
- **状态:** ✅ 已完成

---

### D-2026-07-09-01 | MaiBot 保留旧配置，兼容 v1.0.11

- **决策:** 不迁移到新生成的默认配置，保留经过 v1.0.11 自动迁移验证的旧 bot_config.toml + model_config.toml
- **理由:** MaiBot v1.0.11 自动迁移系统成功处理了旧配置（零报错），所有个性化设置（SiliconFlow + 月卡双 provider、自定义模型优先级、超时配置）均保留
- **影响:** 配置文件结构已兼容新架构，无需手工合并
- **状态:** ✅ 已确认

---

### D-2026-07-08-02 | 双窗口启动方案 v4.0

- **决策:** 放弃 v3.1 单窗口日志追读方案，改为双窗口（窗口1= MaiBot 主程序 .bat，窗口2= PowerShell 追读 STT/TTS/Dashboard 日志）+ 桌宠 Electron 独立窗口
- **理由:** 单窗口方案日志追读不可靠、Ctrl+C 处理有阻塞风险
- **影响:** 启动脚本 `yi_jian_qi_dong.ps1` v4.0 已实现，含按端口杀进程逻辑
- **状态:** ✅ 已部署，待重启验证

---

### D-2026-07-08-01 | person_fact_writeback 超时修复

- **决策:** memory_flow_service.py 中 utils task hard_timeout 30s→90s；模型优先级改为 sf-ds4-flash 优先（硅基更快）→ 深度求索兜底
- **理由:** 月卡 API 间歇性超时导致记忆写入失败，硅基 API 更快且成功率更高
- **影响:** 记忆系统写入可靠性提升
- **状态:** ✅ 已修复生效

---

### D-2026-07-01-01 | MaiBot 双实例方案

- **决策:** 洛雪(8001)弃用，主力切换为小艾(8002/桌宠 WS 8523)；模型主力 sf-ds4-flash + sf-ds4-pro，提供商统一为硅基流动
- **理由:** 洛雪因模型从 DeepSeek 切千问后角色表现力下降（不像真人），小艾在 DeepSeek V4 上表现更好
- **影响:** 所有配置已迁移，洛雪实例保留但不再使用
- **状态:** ✅ 已生效

---

### D-2026-06-17-01 | 多 Agent 决策架构 v3.0

- **决策:** 信号标准化（+1/0/-1）、加权融合公式、冲突升级为 Bull vs Bear 辩论 + Judge 裁决、决策审计、权重演化
- **理由:** 原 v2.0 决策机制缺少融合和冲突处理，新架构可量化各 Agent 贡献
- **影响:** `AGENTS.md` 决策规范已更新
- **状态:** ✅ 已设计，部分实现

---


### D-2026-07-10-01 | 冲突检测人性化输出双字段设计

- **决策:** _format_conflict_result 返回 dict 含 human_text (蓝图 §7.6 对话语气) + structured (机器可读 JSON), 而非单一纯文本
- **理由:** MaiBot 需要自然对话语气（"等一下，我记得…"），但 Planner/决策层仍需结构化数据（conflict_count, severity, recommended_action），双字段可同时服务两端
- **影响:** 3 种场景（单冲突/多冲突/无冲突）各有不同 human_text 模板, date_display 用 _pretty_date() 格式化（2026年10月1日）
- **替代方案:** A) 纯文本（Planner 无法解析） B) 纯 JSON（不像真人） C) 双字段（推荐）
- **状态:** ✅ 已实现
---

## 待决策事项

| ID | 议题 | 选项 | 推荐 | 阻塞项 |
|----|------|------|------|--------|
| **P3** | 抖音/快手热榜 API 集成方案 | A) 抖音官方 API 已成功 / 快手放弃 B) 等 DailyHotApi 恢复 C) 自建抓取服务 | A（推荐） | 快手无可用纯 JSON 端点 |
| **P2** | 看新闻/视频行为绑定记忆系统 | A) 新增 memory task B) 扩展原文存储 C) 暂不做 | A（推荐） | 等待用户决策 |
| **P1** | Timing Gate 私聊修复方案 | A) FrequencyThresholdTurnGate 对私聊直接放行 B) 改为 reply_necessity 模式 + 降低阈值至 50 | A（推荐） | 等待用户决策 |
