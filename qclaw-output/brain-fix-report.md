# Brain Fix Report

Generated: 2026-06-17T13:09:15.374226

## Files
- Source: `F:\ai\data\knowledge-graph.json`
- Backup: `F:\ai\data\knowledge-graph-backup-20260617-130724.json`
- Report: `F:\ai\qclaw-output\brain-fix-report.md`

## Stage 1 Diagnostics

### Edge Contract
- Node key/id match: 190/190
- `source`/`target` fields before: 0 present, 0 valid pairs
- `source_id`/`target_id` fields before: 7694 present, 3088 valid pairs
- Invalid endpoint references before: 8710

### Tag Field Format
- Formats before: {'list': 190}
- Total tags before: 1528
- Unique tags before: 475
- Top tags before:
- 话: 70
- workbuddy: 70
- 0: 70
- 录: 67
- 会话: 66
- id: 65
- f: 52
- ai: 40
- 化: 33
- 用: 31
- 动: 19
- c: 19
- 度: 17
- 系: 16
- 格: 16
- 系统: 15
- 索: 15
- 统: 14
- 分: 14
- 行: 14
- 实: 12
- 1: 11
- 真: 11
- 记忆: 11
- 记: 11

### Duplicate Nodes
- Duplicate title groups before: 14
- Duplicate nodes before: 109
- Largest duplicate groups:
- 会话: ai (2026-06-16): 27 nodes
- 会话: .workbuddy (2026-06-16): 14 nodes
- WorkBuddy 跨项目记忆: 13 nodes
- 记忆: a112e458-4c79-4b41-96b6-03e953dffd50_memory: 13 nodes
- 项目记忆: MEMORY: 9 nodes
- 会话: work (2026-06-16): 9 nodes
- 会话: ai (2026-06-15): 4 nodes
- 项目记忆: 2026-06-14: 4 nodes
- 项目记忆: 2026-06-15: 4 nodes
- 会话: .workbuddy (2026-06-15): 3 nodes
- 会话: QQSafeChat (2026-06-16): 3 nodes
- 项目记忆: 2026-06-16: 2 nodes
- 会话: QQSafeChat (2026-06-17): 2 nodes
- task1-persona-design: 2 nodes

### Content Length Distribution Before
- Min/median/avg/max: 16 / 173.0 / 913.6 / 8000
- 0-50: 1
- 51-100: 2
- 101-500: 124
- 501-1000: 15
- 1001-2000: 16
- 2001-4000: 24
- 4001-8000: 8
- 8000+: 0

### Category Distribution Before
- tech-programming: 87
- film-video: 46
- tech-ai: 24
- business: 12
- decision-lessons: 9
- life: 5
- academic: 4
- design: 2
- inbox: 1

## Stage 2 Repairs

### Edge Repair
- Kept valid unique edges: 117
- Removed edges with missing endpoints: 4606
- Removed self-loop edges after duplicate mapping: 697
- Removed duplicate undirected edges: 2274
- Added compatibility aliases on kept edges: `source` and `target` mirror `source_id` and `target_id`.

### Tag Cleanup
- Tags remain as list format on all nodes.
- Removed single-character CJK tokens, pure numbers, UUID/hex fragments, and operational noise such as `id`, `workbuddy`, `会话`, `记录`.
- Re-added bounded semantic terms from title/summary/content.
- Total tags after: 542
- Unique tags after: 118
- Top tags after:
- ai: 60
- 视频: 27
- 用户: 22
- qclaw: 19
- 第二大脑: 17
- api: 16
- json: 16
- 提示词: 12
- imax: 12
- panavision: 12
- 检索: 12
- python: 11
- 架构: 11
- 镜头: 11
- 市场: 11
- 设计: 11
- 教训: 10
- 决策: 10
- codex: 10
- llm: 9
- ui: 9
- 电影: 8
- 策略: 8
- 知识图谱: 8
- 方法论: 8

### Duplicate Merge
- Duplicate groups merged: 14
- Nodes before/after: 190 -> 95
- Removed duplicate nodes: 95
- Duplicate title groups after: 0

### Category Adjustment
- Reclassified using existing `category-index.json` keywords plus title/content heuristics.
- Raw session-log titles (`会话:`) moved to `inbox`.
- Design/persona, film/video, AI/memory, programming/code, business, academic and decision terms are weighted by evidence in title/content.

Category distribution after:
- film-video: 25
- tech-programming: 16
- inbox: 16
- tech-ai: 15
- business: 9
- decision-lessons: 5
- life: 3
- academic: 3
- design: 3

## Post-Fix Validation

### Edge Contract After
- `source_id`/`target_id`: 117 present, 117 valid pairs
- `source`/`target`: 117 present, 117 valid pairs
- Invalid endpoint references after: 0

### Tag Field Format After
- Formats after: {'list': 95}

### Content Length Distribution After
- Min/median/avg/max: 16 / 260 / 1117.7 / 12500
- 0-50: 1
- 51-100: 2
- 101-500: 61
- 501-1000: 13
- 1001-2000: 7
- 2001-4000: 3
- 4001-8000: 5
- 8000+: 3
