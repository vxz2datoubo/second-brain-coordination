# Shadow Cognitive Loop v0

第二大脑「超级智慧」的最小可运行认知闭环。这是第一个真正能"思考"的切片——不是又一个存储/检索库，而是一个**闭环**：

```
摄入(ingest) → 知识原子(atom) → 混合检索(retrieve) → 证据推理(reason) → 反馈回路(feedback)
     ↑                                                                          ↓
     └──────────────── 更新置信度 / 记录冲突 ←──────────────────────────────────┘
```

## 为什么是「Shadow」

它是**隔离**实现，绝不写生产 W3 捕获面（`LIVE_CAPTURE_READY: false` / `W3_PRODUCTION_READY: false`）。它证明闭环能闭合，真实知识由后续 ingestion pipeline 灌入，不在这里混入任何生产数据。

## 五个能力（GPT 提议的最小闭环，已全部落地）

| 能力 | 模块 | 说明 |
|---|---|---|
| 知识原子化 | `atom.py` | 内容寻址的 `KnowledgeAtom`，区分 fact / inference / user_opinion |
| provenance first | `atom.py` | 每个原子强制记录来源类型、摄入者、时间、引用 |
| 混合检索 | `retrieve.py` | 纯 Python BM25 关键词 + 时间有效性 + 可信度加权 + 冲突检测 |
| 证据推理 | `reason.py` | 聚合支持/反证，输出结论 + 置信度 + 「什么情况会错」 |
| 反馈回路 | `feedback.py` | 预测 → 现实 → 差异 → 上调/下调置信度 |

存储：`store.py`（SQLite，零外部依赖，本地即跑）。

## 快速上手

```python
import sys
sys.path.insert(0, "tools")
from cognitive_loop import ShadowStore, ingest, retrieve, reason, record_prediction, apply_outcome

store = ShadowStore("second_brain.db")  # 本地文件，可随 git 忽略

# 摄入（带 provenance）
ingest(store, content="贵州茅台主营白酒", subject="贵州茅台", topic="主营业务",
       nature="fact", confidence=0.9, source_type="document", retriever="gpt")

# 检索
results = retrieve(store.all_atoms(), "茅台做什么生意", now="2026-09-12")

# 推理
answer = reason(store.all_atoms(), "茅台做什么生意", now="2026-09-12")
print(answer.answer, answer.confidence, answer.caveats)

# 反馈闭环
fid = record_prediction(store, "茅台主营", "贵州茅台", "贵州茅台主营白酒", 0.9)
apply_outcome(store, fid, "贵州茅台", "贵州茅台主营白酒", now="2026-09-12")
```

## 机械验收

```bash
python -m unittest discover -s tests/cognitive_loop -p test_*.py
```

`benchmark.py` 对四类能力打分（合成语料，确定性、快速）：

- retrieval 命中 3/3
- reasoning 命中 3/3
- conflict detection 1/1
- feedback loop 1/1

## 多宿主接入（GPT / 洛雪 / maibot / WorkBuddy）

认知闭环是**核心**，宿主是**接入口**。所有宿主走同一套语义：

- **写入**：宿主把可信信息通过 `ingest` 变成知识原子（各自标明 `retriever`，provenance 区分来源）
- **读取**：宿主通过 `retrieve` / `reason` 查询，得到带置信度、带反证、带 caveat 的答案，而不是一段不可信的文本
- **进化**：宿主预测被现实检验后，通过 `apply_outcome` 反馈，闭环自动上调/下调置信度

宿主之间不直接通信，都通过这个核心读写——这保证了「一个第二大脑，多个入口」，而不是多个各自为政的记忆。

## 边界（继承 R175 / 第二大脑治理）

- provenance first：无来源不入库
- fact 与 inference 永不混同
- 时间有效性是一等检索轴
- 冲突显式浮出，不静默掩盖分歧
- 反馈是闭环，不是一次性查表
- 不碰 W3 生产、不做交易、不碰凭证/真实用户数据
