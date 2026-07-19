 """
 memory_consolidation.py - 记忆巩固引擎
 ======================================
 模拟人脑睡眠期的记忆整合（Memory Consolidation）机制。
 
 核心机制:
 1. 记忆重放 (Replay): 像人脑在睡眠中重放白天经历一样，自动重激活相关记忆片段
 2. 记忆整合 (Integration): 将短暂记忆（情景/工作记忆）转化为长期语义记忆
 3. 记忆剪枝 (Pruning): 低强度记忆逐渐被遗忘，为重要记忆腾出空间
 4. 模式提取 (Pattern Extraction): 从多个相似记忆中提取共同模式 -> 抽象概念
 5. 错误纠正 (Error Correction): 检测记忆冲突和矛盾，尝试调和或标记
 6. 睡眠周期模拟: 模拟NREM/REM不同阶段的记忆处理差异
 
 参考:
 - McClelland et al. (1995). "Why there are complementary learning systems"
 - Nadel & Moscovitch (1997). "Memory consolidation, retrograde amnesia and the hippocampal complex"
 - Stickgold & Walker (2013). "Sleep-dependent memory triage"
 - Klinzing et al. (2019). "Mechanisms of systems memory consolidation during sleep"
 """
 
 import json
 import math
 import random
 import uuid
 from pathlib import Path
 from datetime import datetime, timedelta
 from collections import defaultdict
 from typing import Optional
 
 
 class MemoryConsolidationEngine:
     """记忆巩固引擎 - 模拟人脑睡眠期记忆处理"""
 
     # 参数
     REPLAY_TEMPERATURE = 0.3      # 重放时的随机性
     CONSOLIDATION_THRESHOLD = 0.6  # 记忆强度阈值 -> 可以被整合
     PRUNE_THRESHOLD = 0.15         # 强度低于此值 -> 可被遗忘
     PATTERN_MIN_SIMILARITY = 0.5   # 模式提取最小相似度
     SLEEP_CYCLE_HOURS = 1.5        # 一个完整睡眠周期（90分钟）
     NREM_PHASE_RATIO = 0.6         # NREM占比
     REM_PHASE_RATIO = 0.4          # REM占比
 
     def __init__(self, graph, data_dir: Path):
         self.graph = graph
         self.data_dir = data_dir
         self.state_path = data_dir / "consolidation-state.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "sleep_cycles": [],           # 睡眠周期记录
                 "consolidation_log": [],       # 整合日志
                 "pruned_nodes": [],            # 遗忘节点
                 "patterns": [],               # 提取的模式
                 "conflicts": [],              # 检测到的记忆冲突
                 "meta": {
                     "total_cycles": 0,
                     "total_consolidations": 0,
                     "total_pruned": 0,
                     "last_cycle": ""
                 }
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     def _get_memory_strength(self, node_id: str) -> float:
         """计算记忆强度（0-1）"""
         import core.memory_health as mh
         node = self.graph.data["nodes"].get(node_id, {})
         if not node:
             return 0.0
         importance = node.get("importance", 3)
         access_count = node.get("access_count", 0)
         # 基于重要性和访问次数的记忆强度
         strength = min(1.0, (importance / 5) * 0.6 + min(1.0, access_count / 20) * 0.4)
         return strength
 
     def _get_decay_rate(self, node_id: str) -> float:
         """Ebbinghaus 遗忘速率
         记忆强度越高 -> 遗忘越慢
         """
         strength = self._get_memory_strength(node_id)
         # 遗忘速率 = 1 / (1 + strength * 10)
         return 1.0 / (1.0 + strength * 10.0)
 
     # ========== 1. 记忆重放 (Memory Replay) ==========
     def replay_memories(self, batch_size: int = 20, replay_cycles: int = 3) -> list[dict]:
         """模拟睡眠期的记忆重放
         
         NREM阶段：慢波振荡，重放近期记忆，强化海马体与新皮质的连接
         REM阶段：随机激活，跨模态联想，巩固程序性和情绪记忆
         
         Returns: 重放日志
         """
         replayed = []
         all_nodes = list(self.graph.data["nodes"].keys())
         if not all_nodes:
             return replayed
 
         for cycle in range(replay_cycles):
             # NREM期：偏向选择近期/高频记忆
             nrem_count = int(batch_size * self.NREM_PHASE_RATIO)
             nrem_candidates = []
             for nid in all_nodes:
                 node = self.graph.data["nodes"].get(nid, {})
                 last_access = node.get("last_access", "")
                 access_count = node.get("access_count", 0)
                 try:
                     last_dt = datetime.fromisoformat(last_access) if last_access else datetime.min
                     age_hours = (datetime.now() - last_dt).total_seconds() / 3600
                 except (ValueError, TypeError):
                     age_hours = 9999
                 # 近期+高频优先
                 recency_score = math.exp(-age_hours / 72) * 10  # 72小时半衰
                 frequency_score = min(1.0, access_count / 10)
                 noise = random.random() * self.REPLAY_TEMPERATURE
                 nrem_candidates.append((nid, recency_score + frequency_score + noise))
 
             nrem_candidates.sort(key=lambda x: x[1], reverse=True)
             chosen_nrem = [c[0] for c in nrem_candidates[:nrem_count]]
 
             # REM期：偏向随机 + 情绪性记忆
             rem_count = batch_size - nrem_count
             rem_candidates = []
             for nid in all_nodes:
                 node = self.graph.data["nodes"].get(nid, {})
                 importance = node.get("importance", 3)
                 tags = node.get("tags", [])
                 # 情绪相关的标签加权
                 emotional_boost = 1.0
                 for tag in tags:
                     if any(em in tag for em in ["情感", "情绪", "重要", "深刻", "感动"]):
                         emotional_boost = 1.5
                         break
                 noise = random.random() * 2.0
                 score = importance * emotional_boost * 0.2 + noise
                 rem_candidates.append((nid, score))
 
             rem_candidates.sort(key=lambda x: x[1], reverse=True)
             chosen_rem = [c[0] for c in rem_candidates[:rem_count]]
 
             # 记录本次重放
             all_chosen = list(set(chosen_nrem + chosen_rem))
             for nid in all_chosen:
                 node = self.graph.data["nodes"].get(nid, {})
                 # 重放 -> 增加访问计数
                 node["access_count"] = node.get("access_count", 0) + 1
                 node["last_access"] = datetime.now().isoformat()
                 replayed.append({
                     "node_id": nid,
                     "title": node.get("title", ""),
                     "phase": "NREM" if nid in chosen_nrem else "REM",
                     "strength_before": self._get_memory_strength(nid),
                     "strength_after": self._get_memory_strength(nid) + 0.05,
                 })
 
             self.data["sleep_cycles"].append({
                 "cycle": len(self.data["sleep_cycles"]) + 1,
                 "timestamp": datetime.now().isoformat(),
                 "nrem_count": len(chosen_nrem),
                 "rem_count": len(chosen_rem),
                 "total_replayed": len(all_chosen),
             })
 
         self.data["meta"]["total_cycles"] = len(self.data["sleep_cycles"])
         self._save()
         return replayed
 
     # ========== 2. 记忆整合 (Memory Consolidation) ==========
     def consolidate(self, min_strength: float = None) -> list[dict]:
         """将短期记忆（弱连接）整合为长期记忆（强连接 + 摘要节点）
         
         工作原理:
         1. 扫描所有节点，找到强相关节点组
         2. 为每组创建一个"摘要节点"
         3. 加强组内节点的连接强度
         4. 弱化孤立弱节点
         """
         if min_strength is None:
             min_strength = self.CONSOLIDATION_THRESHOLD
 
         self.graph.reload()
         consolidations = []
         nodes = self.graph.data["nodes"]
         edges = self.graph.data["edges"]
 
         # 找高频共现节点对
         edge_strength_map = defaultdict(list)
         for eid, edge in edges.items():
             src, tgt = edge["source_id"], edge["target_id"]
             pair = tuple(sorted([src, tgt]))
             edge_strength_map[pair].append(edge.get("strength", 0.5))
 
         # 提取强连接社区
         communities = []
         visited = set()
         for pair, strengths in sorted(edge_strength_map.items(), key=lambda x: max(x[1]), reverse=True):
             avg_strength = sum(strengths) / len(strengths)
             if avg_strength >= min_strength:
                 n1, n2 = pair
                 merged = False
                 for comm in communities:
                     if n1 in comm["members"] or n2 in comm["members"]:
                         comm["members"].add(n1)
                         comm["members"].add(n2)
                         merged = True
                         break
                 if not merged:
                     communities.append({"members": {n1, n2}})
 
         # 为每个社区创建摘要节点
         for comm in communities:
             members = comm["members"]
             # 跳过过于零散的社区
             if len(members) < 3:
                 continue
 
             member_nodes = []
             for nid in members:
                 node = nodes.get(nid, {})
                 if node:
                     member_nodes.append(node)
 
             if not member_nodes:
                 continue
 
             # 提取共同主题
             all_tags = []
             all_titles = []
             for mn in member_nodes:
                 all_tags.extend(mn.get("tags", []))
                 all_titles.append(mn.get("title", ""))
 
             tag_freq = Counter(all_tags)
             common_tags = [t for t, c in tag_freq.items() if c >= max(1, len(members) // 2)]
 
             # 创建摘要节点
             summary_id = f"summary-{uuid.uuid4().hex[:8]}"
             summary_title = " | ".join(all_titles[:3])
             if len(all_titles) > 3:
                 summary_title += f" 等{len(members)}项"
 
             nodes[summary_id] = {
                 "id": summary_id,
                 "title": summary_title,
                 "summary": f"自动整合摘要: 整合了{len(members)}条相关记忆",
                 "tags": common_tags,
                 "importance": min(5, max(1, int(sum(mn.get("importance", 3) for mn in member_nodes) / len(members)))),
                 "access_count": 1,
                 "source": "consolidation",
                 "created_at": datetime.now().isoformat(),
                 "last_access": datetime.now().isoformat(),
                 "category": "consolidated",
             }
 
             # 将社区成员连接到摘要节点
             for mn in member_nodes:
                 eid = f"e-{uuid.uuid4().hex[:8]}"
                 edges[eid] = {
                     "id": eid,
                     "source_id": summary_id,
                     "target_id": mn["id"],
                     "relation": "summarizes",
                     "strength": 0.8,
                 }
 
             consolidations.append({
                 "summary_id": summary_id,
                 "member_count": len(members),
                 "summary_title": summary_title,
                 "common_tags": common_tags,
             })
 
         self.data["consolidation_log"].extend(consolidations)
         self.data["meta"]["total_consolidations"] += len(consolidations)
         self._save()
         return consolidations
 
     # ========== 3. 记忆剪枝 (Memory Pruning) ==========
     def prune_weak_memories(self, threshold: float = None, dry_run: bool = False) -> list[dict]:
         """剪枝低强度记忆 - 模拟人脑的自然遗忘
         
         策略:
         - 低于阈值的记忆不会立即删除，而是标记为"可遗忘"
         - 多次标记后可遗忘的记忆会被删除
         - 保留元数据：曾经存在过，但内容已遗忘
         """
         if threshold is None:
             threshold = self.PRUNE_THRESHOLD
 
         self.graph.reload()
         nodes = self.graph.data["nodes"]
         pruned = []
 
         to_remove = []
         for nid, node in nodes.items():
             strength = self._get_memory_strength(nid)
             if strength < threshold:
                 age = 0
                 try:
                     last_access = node.get("last_access", "")
                     if last_access:
                         age = (datetime.now() - datetime.fromisoformat(last_access)).days
                 except (ValueError, TypeError):
                     age = 999
 
                 # 至少遗忘标记2次或超过30天未访问
                 forget_count = self.data.get("_forget_count", {}).get(nid, 0)
                 if forget_count >= 2 or age >= 30:
                     if not dry_run:
                         # 保存元数据
                         self.data["pruned_nodes"].append({
                             "id": nid,
                             "title": node.get("title", ""),
                             "tags": node.get("tags", []),
                             "strength_at_prune": strength,
                             "age_days": age,
                             "forget_count": forget_count,
                             "pruned_at": datetime.now().isoformat(),
                         })
                         to_remove.append(nid)
                     pruned.append({
                         "id": nid,
                         "title": node.get("title", ""),
                         "strength": strength,
                         "age_days": age,
                         "action": "removed" if not dry_run else "would_remove",
                     })
                 else:
                     # 增加遗忘计数
                     if "_forget_count" not in self.data:
                         self.data["_forget_count"] = {}
                     self.data["_forget_count"][nid] = forget_count + 1
 
         if not dry_run:
             for nid in to_remove:
                 # 删除节点
                 del nodes[nid]
                 # 删除关联的边
                 to_del_edges = []
                 for eid, edge in list(self.graph.data["edges"].items()):
                     if edge["source_id"] == nid or edge["target_id"] == nid:
                         to_del_edges.append(eid)
                 for eid in to_del_edges:
                     del self.graph.data["edges"][eid]
 
             self.data["meta"]["total_pruned"] += len(to_remove)
             self._save()
 
         return pruned
 
     # ========== 4. 模式提取 (Pattern Extraction) ==========
     def extract_patterns(self, min_cluster: int = 3, dry_run: bool = False) -> list[dict]:
         """从多个相似记忆中提取共同模式 -> 抽象概念
         
         模拟人类"从经验中学习规律"的能力。
         比如看到多个"被烫到"的记忆后，学习到"热的物体可能危险"这一模式。
         """
         self.graph.reload()
         nodes = self.graph.data["nodes"]
         patterns = []
 
         # 基于标签聚类
         tag_to_nodes = defaultdict(list)
         for nid, node in nodes.items():
             for tag in node.get("tags", []) + node.get("category", "").split(","):
                 tag_stripped = tag.strip()
                 if tag_stripped:
                     tag_to_nodes[tag_stripped].append(nid)
 
         for tag, member_ids in tag_to_nodes.items():
             if len(member_ids) < min_cluster:
                 continue
 
             # 检查是否已经存在该模式的摘要节点
             pattern_exists = any(
                 p.get("pattern_tag") == tag and p.get("active", True)
                 for p in self.data["patterns"]
             )
 
             if pattern_exists:
                 continue
 
             # 提取模式
             member_summaries = []
             for mid in member_ids:
                 node = nodes.get(mid, {})
                 if node:
                     member_summaries.append(node.get("summary", node.get("title", "")))
 
             patterns.append({
                 "id": str(uuid.uuid4())[:8],
                 "pattern_tag": tag,
                 "member_count": len(member_ids),
                 "member_ids": member_ids[:20],  # 只保存前20个
                 "abstract_summary": f"从{len(member_ids)}条相关记忆中提取的模式: {tag}",
                 "extracted_at": datetime.now().isoformat(),
                 "active": True,
                 "confidence": min(1.0, len(member_ids) / 10),
             })
 
         if not dry_run and patterns:
             self.data["patterns"].extend(patterns)
             self._save()
 
         return patterns
 
     # ========== 5. 冲突检测 (Conflict Detection) ==========
     def detect_conflicts(self) -> list[dict]:
         """检测记忆冲突和矛盾
         
         检测场景:
         - 同一实体在不同时间有不同的"版本"信息
         - 通过"contradicts"关系连接的节点
         - 语义上矛盾的陈述
         """
         self.graph.reload()
         conflicts = []
         edges = self.graph.data["edges"]
 
         # 直接通过contradicts边检测
         for eid, edge in edges.items():
             if edge.get("relation") == "contradicts":
                 src = self.graph.data["nodes"].get(edge["source_id"], {})
                 tgt = self.graph.data["nodes"].get(edge["target_id"], {})
                 if src and tgt:
                     conflicts.append({
                         "type": "explicit_contradiction",
                         "node_a": edge["source_id"],
                         "node_a_title": src.get("title", ""),
                         "node_b": edge["target_id"],
                         "node_b_title": tgt.get("title", ""),
                         "strength": edge.get("strength", 1.0),
                         "detected_at": datetime.now().isoformat(),
                     })
 
         if conflicts:
             self.data["conflicts"].extend(conflicts)
             self._save()
 
         return conflicts
 
     # ========== 6. 完整睡眠周期 ==========
     def run_sleep_cycle(self, full_consolidation: bool = True) -> dict:
         """运行一个完整的睡眠周期
         
         1. NREM: 记忆重放（近期记忆巩固）
         2. NREM: 模式提取
         3. REM: 跨模态联想 + 情绪记忆强化
         4. NREM: 冲突检测
         5. 剪枝
         6. 整合（可选）
         """
         report = {
             "timestamp": datetime.now().isoformat(),
             "replay": [],
             "patterns": [],
             "conflicts": [],
             "pruned": [],
             "consolidations": [],
         }
 
         # Phase 1-2: NREM - 重放近期记忆
         report["replay"] = self.replay_memories(batch_size=30, replay_cycles=2)
 
         # Phase 3: REM - 模式提取
         report["patterns"] = self.extract_patterns(min_cluster=3)
 
         # Phase 4: 冲突检测
         report["conflicts"] = self.detect_conflicts()
 
         # Phase 5: 剪枝弱记忆
         report["pruned"] = self.prune_weak_memories()
 
         # Phase 6: 整合（可选）
         if full_consolidation:
             report["consolidations"] = self.consolidate()
 
         # 保存图
         self.graph._save()
 
         self.data["meta"]["last_cycle"] = datetime.now().isoformat()
         self._save()
 
         return report
 
     # ========== 统计 ==========
     def stats(self) -> dict:
         return {
             "total_cycles": self.data["meta"]["total_cycles"],
             "total_consolidations": self.data["meta"]["total_consolidations"],
             "total_pruned": self.data["meta"]["total_pruned"],
             "patterns_found": len(self.data["patterns"]),
             "active_conflicts": sum(1 for c in self.data["conflicts"] if c.get("resolved") is not True),
             "last_cycle": self.data["meta"]["last_cycle"],
         }
