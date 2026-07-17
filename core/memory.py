"""
memory.py - 主动学习与记忆引擎
基于 memory-framework 技能模式: L1/L2/L3 三层记忆, WAL 协议, 错误驱动学习

功能:
- MemoryEngine: 交互记录 / 反馈管理 / 上下文检索 / 用户画像
- FeedbackLoop: 反馈闭环 / 权重调整 / 学习要点提取
- 记忆巩固: 合并相似交互, 提炼周期性洞察
- 用户画像: 自动更新偏好、使用模式、知识领域分布

集成 memory-framework 模式:
- L1 (会话级): 最近 N 条交互 (内存缓冲)
- L2 (项目级): memory-index.json (持久化存储)
- L3 (身份级): user-profile.json (长期画像)
- WAL 协议: 先记录交互, 后生成响应
- 错误学习: 记录 bad 反馈 → 分析根因 → 应用修复
"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class MemoryEngine:
    """记忆引擎 — L1/L2/L3 三层记忆 + WAL 协议

    L1 会话缓冲: 内存中的最近交互 (不持久化)
    L2 项目存储: memory-index.json (全部交互 + 反馈)
    L3 身份画像: user-profile.json (偏好/模式/领域)
    """

    MAX_L1_BUFFER = 20  # 会话缓冲上限

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.memory_path = data_dir / "memory-index.json"
        self.feedback_path = data_dir / "feedback-log.json"
        self.profile_path = data_dir / "user-profile.json"
        self.errors_path = data_dir / "errors-log.json"

        # L1: 会话缓冲
        self.l1_buffer: list[dict] = []

        # 加载持久化数据
        self.memory = self._load_json(self.memory_path, {"interactions": [], "meta": {"total_interactions": 0, "total_feedback": 0, "good_rate": 0.0, "last_updated": ""}})
        self.feedback_log = self._load_json(self.feedback_path, {"entries": [], "rules": []})
        self.errors_log = self._load_json(self.errors_path, {"errors": [], "recoveries": [], "meta": {"total_errors": 0}})

        # 确保结构完整 (兼容旧数据)
        self.feedback_log.setdefault("entries", self.feedback_log.pop("feedbacks", []))
        self.feedback_log.setdefault("rules", [])
        self.errors_log.setdefault("errors", [])
        self.errors_log.setdefault("recoveries", [])
        self.errors_log.setdefault("meta", {"total_errors": 0})

    def _load_json(self, path: Path, default: dict) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _save_json(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ========== WAL 协议: 先记录后响应 ==========
    def record(self, user_input: str, system_response: str = "",
               context_ids: list[str] = None, session_id: str = None) -> str:
        """WAL 协议——先记录交互，返回 interaction_id

        在生成响应之前调用此方法，确保即使后续出错也有记录。
        """
        interaction = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "system_response": system_response,
            "context_ids": context_ids or [],
            "feedback": {},
            "session_id": session_id or "",
            "emotion": self._detect_emotion(user_input),
            "learning_points": [],
            "memory_layer": "L2"  # 标记为项目级记忆
        }

        # 写入 L2 持久化
        self.memory["interactions"].append(interaction)
        self.memory["meta"]["total_interactions"] = len(self.memory["interactions"])
        self.memory["meta"]["last_updated"] = interaction["timestamp"]
        self._save_json(self.memory_path, self.memory)

        # 更新 L1 缓冲
        self.l1_buffer.append(interaction)
        if len(self.l1_buffer) > self.MAX_L1_BUFFER:
            self.l1_buffer = self.l1_buffer[-self.MAX_L1_BUFFER:]

        return interaction["id"]

    def _detect_emotion(self, text: str) -> str:
        """简单情绪检测"""
        positive = any(w in text for w in ["谢谢", "好的", "很棒", "不错", "好用", "喜欢", "厉害", "👍", "OK"])
        negative = any(w in text for w in ["不行", "错误", "不对", "失败", "糟糕", "没用", "垃圾", "差"])
        if positive and not negative:
            return "positive"
        if negative:
            return "negative"
        return "neutral"

    # ========== 反馈管理 ==========
    def record_feedback(self, interaction_id: str, rating: str = "neutral",
                        accepted: bool = True, correction: str = "",
                        chosen: str = "", rejected: list[str] = None,
                        feedback_text: str = "") -> Optional[dict]:
        """记录用户反馈。返回更新后的 interaction 或 None。"""
        for ix in self.memory["interactions"]:
            if ix["id"] == interaction_id:
                ix["feedback"] = {
                    "rating": rating,
                    "accepted": accepted,
                    "used_choice": chosen,
                    "rejected_choices": rejected or [],
                    "user_correction": correction,
                    "feedback_text": feedback_text
                }

                # 记录到反馈日志
                self.feedback_log["entries"].append({
                    "interaction_id": interaction_id,
                    "timestamp": datetime.now().isoformat(),
                    "rating": rating,
                    "user_input_snippet": ix["user_input"][:100],
                    "correction": correction
                })

                # 更新统计
                self.memory["meta"]["total_feedback"] += 1
                good_count = sum(1 for i in self.memory["interactions"]
                                 if i.get("feedback", {}).get("rating") == "good")
                self.memory["meta"]["good_rate"] = good_count / max(self.memory["meta"]["total_feedback"], 1)
                self.memory["meta"]["last_updated"] = datetime.now().isoformat()

                self._save_json(self.memory_path, self.memory)
                self._save_json(self.feedback_path, self.feedback_log)

                # 错误驱动学习: 记录 bad 评分
                if rating == "bad":
                    self._record_error(interaction_id, ix["user_input"], correction)

                return ix

        return None

    def _record_error(self, interaction_id: str, user_input: str, correction: str):
        """记忆框架错误驱动学习"""
        error = {
            "id": str(uuid.uuid4())[:8],
            "interaction_id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "user_input_snippet": user_input[:200],
            "correction": correction,
            "symptoms": [user_input[:100]],
            "root_cause": "待分析",
            "fix_applied": ""
        }
        self.errors_log["errors"].append(error)
        self.errors_log["meta"]["total_errors"] = len(self.errors_log["errors"])
        self._save_json(self.errors_path, self.errors_log)

    def record_recovery(self, error_id: str, fix: str):
        """记录错误修复"""
        for err in self.errors_log["errors"]:
            if err["id"] == error_id:
                err["fix_applied"] = fix
                break
        self.errors_log["recoveries"].append({
            "error_id": error_id,
            "timestamp": datetime.now().isoformat(),
            "fix": fix
        })
        self._save_json(self.errors_path, self.errors_log)

    # ========== 上下文检索 ==========
    def get_context(self, query: str = "", limit: int = 5,
                    include_l1: bool = True) -> list[dict]:
        """获取相关历史交互作为上下文

        - 先查 L1 缓冲 (最近交互, 时间相关性高)
        - 再查 L2 存储 (关键词匹配 + 时间衰减)
        """
        results = []

        # L1: 最近交互直接包含
        if include_l1 and self.l1_buffer:
            results.extend(self.l1_buffer[-min(limit, len(self.l1_buffer)):])

        # L2: 关键词匹配 + 时间衰减排序
        if query:
            now = datetime.now()
            scored = []
            for ix in self.memory["interactions"]:
                if ix in results:
                    continue
                score = sum(1 for c in query if c in ix.get("user_input", ""))
                if score > 0:
                    # 时间衰减: 24小时衰减50%
                    try:
                        age_hours = (now - datetime.fromisoformat(ix["timestamp"])).total_seconds() / 3600
                        decay = 0.5 ** (age_hours / 24)
                        score *= decay
                    except (ValueError, KeyError):
                        pass
                    scored.append((score, ix))

            scored.sort(key=lambda x: x[0], reverse=True)
            results.extend([r[1] for r in scored[:limit]])

        # 去重
        seen = set()
        unique = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)

        return unique[:limit]

    # ========== 记忆巩固 ==========
    def consolidate(self, days: int = 7) -> dict:
        """记忆巩固: 合并近期相似交互, 提炼学习要点

        参考记忆框架的巩固管道:
        短期缓冲(L1) → LLM提炼 → 长期存储(L2) → 定期复习
        """
        now = datetime.now()
        cutoff = now - timedelta(days=days)

        recent = [ix for ix in self.memory["interactions"]
                  if self._parse_ts(ix["timestamp"]) > cutoff]

        if len(recent) < 3:
            return {"consolidated": 0, "insights": [], "message": "交互不足, 跳过巩固"}

        # 分析模式
        insights = []
        good_rate = sum(1 for ix in recent if ix.get("feedback", {}).get("rating") == "good") / max(len(recent), 1)
        bad_rate = sum(1 for ix in recent if ix.get("feedback", {}).get("rating") == "bad") / max(len(recent), 1)

        if good_rate > 0.8:
            insights.append(f"最近 {days} 天好评率 {good_rate:.0%}，系统表现良好")
        if bad_rate > 0.2:
            insights.append(f"最近 {days} 天差评率 {bad_rate:.0%}，需关注改进点")
            # 找出差评中的共同模式
            bad_inputs = [ix["user_input"][:80] for ix in recent
                          if ix.get("feedback", {}).get("rating") == "bad"]
            if bad_inputs:
                insights.append(f"差评案例: {'; '.join(bad_inputs[:3])}")

        # 常见话题聚类 (简单关键词)
        topic_freq = {}
        for ix in recent:
            for word in ix["user_input"].split():
                if len(word) >= 2:
                    topic_freq[word] = topic_freq.get(word, 0) + 1
        top_topics = sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_topics:
            insights.append(f"热门话题: {', '.join(f'{w}({c}次)' for w, c in top_topics if c >= 2)}")

        return {
            "consolidated": len(recent),
            "period_days": days,
            "insights": insights,
            "good_rate": round(good_rate, 3),
            "bad_rate": round(bad_rate, 3)
        }

    def _parse_ts(self, ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return datetime.min

    # ========== 用户画像 ==========
    def update_profile(self) -> dict:
        """自动更新用户画像 (L3 身份层)"""
        profile = self._load_json(self.profile_path, {
            "preferences": {"output_style": "structured_table", "response_language": "zh-CN", "preferred_categories": [], "avoid_topics": []},
            "patterns": {"common_queries": [], "active_hours": [], "avg_session_length_minutes": 45},
            "knowledge_profile": {"strong_areas": [], "learning_areas": [], "total_knowledge_nodes": 0},
            "meta": {"first_seen": datetime.now().isoformat(), "last_seen": "", "total_sessions": 0}
        })

        interactions = self.memory["interactions"]
        if not interactions:
            return profile

        # 活跃时段
        hours = {}
        for ix in interactions:
            try:
                h = datetime.fromisoformat(ix["timestamp"]).hour
                hours[h] = hours.get(h, 0) + 1
            except: pass
        profile["patterns"]["active_hours"] = [h for h, _ in sorted(hours.items(), key=lambda x: x[1], reverse=True)[:3]]

        # 常见查询模板
        query_templates = {}
        import re
        for ix in interactions[-100:]:
            text = ix.get("user_input", "")
            # 提取查询意图
            for pattern in [r"帮我\w+", r"分析\w+", r"总结\w+", r"怎么\w+", r"什么是\w+", r"如何\w+"]:
                match = re.search(pattern, text)
                if match:
                    tpl = match.group()
                    query_templates[tpl] = query_templates.get(tpl, 0) + 1
        profile["patterns"]["common_queries"] = [
            {"query_template": k, "count": v}
            for k, v in sorted(query_templates.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # 时间戳
        profile["meta"]["last_seen"] = datetime.now().isoformat()
        profile["meta"]["total_sessions"] = len(set(ix.get("session_id", "") for ix in interactions if ix.get("session_id")))

        self._save_json(self.profile_path, profile)
        return profile

    def get_profile(self) -> dict:
        return self._load_json(self.profile_path, {})

    # ========== 统计 ==========
    def stats(self) -> dict:
        return {
            "total_interactions": self.memory["meta"]["total_interactions"],
            "total_feedback": self.memory["meta"]["total_feedback"],
            "good_rate": self.memory["meta"]["good_rate"],
            "l1_buffer_size": len(self.l1_buffer),
            "total_errors": self.errors_log["meta"]["total_errors"],
            "feedback_rules": len(self.feedback_log.get("rules", [])),
            "last_updated": self.memory["meta"]["last_updated"]
        }


class FeedbackLoop:
    """反馈闭环 — 从反馈中学习并调整系统行为"""

    def __init__(self, memory: MemoryEngine, graph, digester):
        self.memory = memory
        self.graph = graph
        self.digester = digester

    def process_feedback(self, interaction_id: str, feedback: dict) -> dict:
        """处理单条反馈, 生成学习要点"""
        learning_points = []
        rating = feedback.get("rating", "neutral")
        correction = feedback.get("user_correction", "")

        if rating == "bad" and correction:
            # 用户纠正 → 可能需要更新知识图谱
            learning_points.append(f"用户纠正: {correction}")
            # 尝试在知识图谱中查找相关节点并更新
            related = self.graph.search_nodes(correction[:30], "title")
            if related:
                for node in related[:1]:
                    self.graph.update_node(node["id"], {
                        "feedback_score": node.get("feedback_score", 0) - 0.1
                    })
                    learning_points.append(f"更新节点 {node['id'][:8]} 反馈评分")

        if rating == "good":
            # 好评 → 加强相关模式的权重
            ix = self.memory.record_feedback(interaction_id, rating=rating)
            if ix:
                for cid in ix.get("context_ids", []):
                    self.graph.touch_node(cid)
            learning_points.append("好评 → 相关节点访问计数+1")

        if feedback.get("rejected_choices"):
            learning_points.append(f"用户拒绝: {feedback['rejected_choices']}")

        # 记录学习要点
        self.memory.record_feedback(
            interaction_id,
            rating=rating,
            accepted=feedback.get("accepted", True),
            correction=correction,
            chosen=feedback.get("chosen", ""),
            rejected=feedback.get("rejected", []),
            feedback_text=feedback.get("feedback_text", "")
        )

        return {
            "interaction_id": interaction_id,
            "learning_points": learning_points,
            "rating": rating
        }

    def adjust_weights(self) -> dict:
        """基于累积反馈调整检索/分类权重"""
        feedback_log = self.memory.feedback_log
        if not feedback_log.get("entries"):
            return {"message": "无反馈数据", "adjustments": []}

        adjustments = []

        # 分析分类准确率
        cat_ratings = {}
        for entry in feedback_log["entries"]:
            # 通过 correction 推断分类是否正确
            if entry.get("correction"):
                cat_ratings["correction_count"] = cat_ratings.get("correction_count", 0) + 1

        if cat_ratings.get("correction_count", 0) > 3:
            adjustments.append("建议: 用户纠正频率较高, 可能需要优化分类关键词")

        # 生成调整规则
        bad_count = sum(1 for e in feedback_log["entries"] if e.get("rating") == "bad")
        good_count = sum(1 for e in feedback_log["entries"] if e.get("rating") == "good")
        total = max(bad_count + good_count, 1)

        if bad_count / total > 0.3:
            adjustments.append(f"警告: 差评率 {bad_count/total:.0%}, 建议检查检索排序逻辑")

        return {
            "total_feedback": len(feedback_log["entries"]),
            "adjustments": adjustments,
            "rules_applied": len(feedback_log.get("rules", []))
        }
