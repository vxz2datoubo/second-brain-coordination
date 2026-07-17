# v2.1 调研报告 & 优化路线图

**2026-06-20** | 基于业界文章和大佬经验的第二轮深度学习

## 3个关键发现

### 1. 混合检索是Rank#1优化（20-30%召回提升）
- BM25(精确) + 向量(语义) → RRF融合
- RRF公式: `Σ 1/(60 + rank_i)` ，无需调参
- 我们只有稀疏检索，缺向量层和融合层

### 2. Model2Vec — CPU上就能做语义搜索
- numpy-only，500x快于SentenceTransformer，15x小
- 蒸馏bge-small-zh为Model2Vec格式 → CPU毫秒级中文向量检索
- potion-multilingual-128M支持101种语言

### 3. MemGPT缺页中断式上下文管理
- LLM像OS管理虚拟内存一样管理上下文
- 主上下文(RAM) ↔ 外部存储(硬盘) 按需换页
- 我们有存储但缺动态换页机制

## 优化路线图

**Phase 2 (🔥 性价比最高)**:
- 2.1 jieba分词 (1h, ⭐⭐⭐⭐⭐)
- 2.2 多信号RRF融合 (2h, ⭐⭐⭐⭐) 
- 2.3 重排序 (1h, ⭐⭐⭐)

**Phase 3 (中期)**:
- 3.1 Model2Vec嵌入索引 (3h)
- 3.2 BM25+Dense+RRF混合检索 (2h)
- 3.3 两阶段检索: 向量初筛→图谱精查 (2h)

**Phase 4 (长期)**:
- 4.1 Token预算动态管理
- 4.2 MemGPT式自主记忆管理
- 4.3 选择→压缩→分发Context Engineering

详细报告见 `qclaw workspace/reports/second-brain-research-v2.1_20260620.md`
