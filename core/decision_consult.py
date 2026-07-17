"""decision_consult.py — 决策前自动检索第二大脑

核心目标: 每次做"决策"前, 自动问第二大脑"有没有相关教训/规则/知识".

入口:
    from core.decision_consult import DecisionConsult
    dc = DecisionConsult()
    result = dc.consult("我想给QClaw做端口动态探测", context={"技术": True})
    if result.has_warnings:
        print(result.format_warnings())
"""
import json
import logging
import urllib.request
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

DEFAULT_BRAIN_URL = "http://localhost:8766"
DEFAULT_LESSON_QUERY_TEMPLATES = [
    "决策 教训 规则",
    "{topic} 经验",
    "不要 {topic}",
    "{topic} 失败",
    "{topic} 注意",
    "{topic} 红线",
]
logger = logging.getLogger(__name__)


@dataclass
class ConsultResult:
    """决策咨询结果"""
    query: str
    matched_lessons: list = field(default_factory=list)         # 匹配到的教训
    matched_rules: list = field(default_factory=list)           # 匹配的规则
    matched_knowledge: list = field(default_factory=list)       # 匹配的相关知识
    warning: str = ""                                           # 顶级警告 (如"这个动作有反复犯的教训")
    errors: list = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.matched_lessons) or bool(self.warning)

    @property
    def has_matches(self) -> bool:
        return bool(self.matched_lessons or self.matched_rules or self.matched_knowledge)

    def format_warnings(self) -> str:
        """格式化为可读的警告文本"""
        lines = [f"🔍 决策前检索: {self.query}"]
        if self.matched_lessons:
            lines.append(f"\n⚠️ 匹配到 {len(self.matched_lessons)} 条历史教训:")
            for m in self.matched_lessons[:5]:
                lines.append(f"  • [{m.get('id', '?')[:8]}] {m.get('title', '?')[:80]}")
                if m.get('summary'):
                    lines.append(f"    → {m['summary'][:100]}")
        if self.matched_rules:
            lines.append(f"\n📜 匹配到 {len(self.matched_rules)} 条规则:")
            for m in self.matched_rules[:3]:
                lines.append(f"  • {m.get('title', '?')[:80]}")
        if self.matched_knowledge:
            lines.append(f"\n💡 匹配到 {len(self.matched_knowledge)} 条相关知识:")
            for m in self.matched_knowledge[:3]:
                lines.append(f"  • {m.get('title', '?')[:80]}")
        if self.warning:
            lines.append(f"\n🚨 {self.warning}")
        return "\n".join(lines)


class DecisionConsult:
    """决策前自动检索第二大脑

    核心能力:
    1. 给定一个"决策主题", 自动扩展多组查询关键词
    2. 分别搜 [决策教训] [规则] [相关知识] 三个类别
    3. 合并去重, 按相关度排序
    4. 判断是否有"红线类教训" → 触发警告
    """

    def __init__(self, brain_url: str = DEFAULT_BRAIN_URL):
        self.brain_url = brain_url.rstrip("/")

    def _search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        errors: Optional[list] = None,
    ) -> list:
        """调用第二大脑搜索 API"""
        payload = {"query": query, "top_k": top_k}
        if category:
            payload["category"] = category
        data = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(
                f"{self.brain_url}/api/retrieve/search",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                return result.get("results", [])
        except Exception as e:
            error = {
                "query": query,
                "category": category,
                "exception_type": type(e).__name__,
                "message": str(e),
            }
            logger.warning(
                "Decision consult search failed: query=%r category=%r exception_type=%s",
                query,
                category,
                error["exception_type"],
                exc_info=True,
            )
            if errors is not None:
                errors.append(error)
            return []

    def _expand_queries(self, topic: str, context: Optional[dict] = None) -> list:
        """扩展查询关键词, 覆盖不同表述方式"""
        queries = [template.format(topic=topic) for template in DEFAULT_LESSON_QUERY_TEMPLATES]
        queries.extend([
            f"{topic}",
            f"{topic} 教训",
        ])
        if context:
            for k, v in context.items():
                if isinstance(v, str):
                    queries.append(f"{v} {topic}")
        # 去重
        return list(dict.fromkeys(queries))

    def _is_real_lesson(self, node: dict) -> bool:
        """判断节点是否是真教训 (排除自动摄入的记忆节点)

        严格规则:
        1. category == "decision-lessons" → 算教训
        2. 标题以"教训"开头 (无论 category) → 算教训
        3. 标题以"机制"/"原则"/"硬检查"开头 + category 是 design/tech-ai → 算教训
        4. 其他 → 不算
        """
        title = node.get("title", "")
        category = node.get("category", "")

        # 硬黑名单
        blacklist = [
            "WorkBuddy 跨项目记忆",
            "记忆: a112e458",
            "项目记忆: MEMORY",
            "全部公开课知识",  # 抖音抓的脏数据
        ]
        if any(b in title for b in blacklist):
            return False

        # 决策类: 默认就算
        if category == "decision-lessons":
            return True

        # 标题以"教训"开头 (无论 category)
        if title.startswith("教训"):
            return True

        # 标题以"机制"/"原则"/"硬检查"/"规则"开头 + 合理类别
        if category in ("design", "tech-ai"):
            for prefix in ["机制:", "原则:", "硬检查", "规则:", "原则:"]:
                if title.startswith(prefix):
                    return True

        return False

    def consult(self, topic: str, context: Optional[dict] = None) -> ConsultResult:
        """核心: 咨询第二大脑关于某个决策主题的教训和规则

        Args:
            topic: 决策主题 (如 "端口动态探测", "改写prompt")
            context: 上下文, 可包含额外检索词 (如 {"技术": "Python"})

        Returns:
            ConsultResult, 含匹配的教训/规则/知识
        """
        result = ConsultResult(query=topic)
        queries = self._expand_queries(topic, context)

        # 1) 检索决策教训 (优先级最高, 强制走 decision-lessons 类别)
        lessons_dict = {}  # 用 id 去重
        for q in queries:
            hits = self._search(q, top_k=3, category="decision-lessons", errors=result.errors)
            for h in hits:
                node_id = h.get("id")
                if not node_id:
                    continue
                if self._is_real_lesson(h) and node_id not in lessons_dict:
                    lessons_dict[node_id] = h
        # 按 score 排序
        lessons = sorted(lessons_dict.values(), key=lambda x: x.get("score", 0), reverse=True)
        result.matched_lessons = lessons[:10]

        # 2) 检索规则
        rules_dict = {}
        for q in [f"规则 {topic}", f"硬规则 {topic}", f"决策 {topic}", f"红线 {topic}"]:
            hits = self._search(q, top_k=2, errors=result.errors)
            for h in hits:
                node_id = h.get("id")
                if not node_id:
                    continue
                if self._is_real_lesson(h) and node_id not in rules_dict:
                    rules_dict[node_id] = h
        result.matched_rules = list(rules_dict.values())[:5]

        # 3) 检索相关知识 (排除决策类和跨项目记忆)
        knowledge_dict = {}
        for q in queries:
            hits = self._search(q, top_k=2, errors=result.errors)
            for h in hits:
                node_id = h.get("id")
                if not node_id:
                    continue
                if (node_id not in knowledge_dict
                        and not self._is_real_lesson(h)
                        and "WorkBuddy 跨项目记忆" not in h.get("title", "")):
                    knowledge_dict[node_id] = h
        knowledge = sorted(knowledge_dict.values(), key=lambda x: x.get("score", 0), reverse=True)
        result.matched_knowledge = knowledge[:5]

        # 4) 顶级警告: 如果教训里有"致命"相关
        critical = [l for l in lessons if l.get("score", 0) >= 5.5 or any(
            kw in l.get("title", "") for kw in ["不要", "切勿", "严禁", "红线", "致命", "降级"]
        )]
        if critical:
            result.warning = f"发现 {len(critical)} 条高风险教训, 决策前必读!"

        return result


def quick_consult(topic: str) -> ConsultResult:
    """便捷函数"""
    return DecisionConsult().consult(topic)


# === 决策前钩子 (供迪迪调用) ===
def before_decision(topic: str, silent: bool = False) -> ConsultResult:
    """迪迪在每次做"决策"前应调用这个函数

    用法:
        from core.decision_consult import before_decision
        result = before_decision("我准备用单例模式改造QClaw")
        if result.has_warnings and not silent:
            print(result.format_warnings())
            input("确认要继续吗? (y/n)")
    """
    result = quick_consult(topic)
    if result.has_warnings and not silent:
        print(result.format_warnings())
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python -m core.decision_consult <决策主题>")
        sys.exit(1)
    topic = " ".join(sys.argv[1:])
    print(before_decision(topic, silent=False).format_warnings())
