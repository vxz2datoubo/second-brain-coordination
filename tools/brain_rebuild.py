from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KG_PATH = ROOT / "data" / "knowledge-graph.json"
REPORT_PATH = ROOT / "qclaw-output" / "brain-rebuild-report.md"
CHECKLIST_PATH = ROOT / "qclaw-output" / "thinking-checklist.md"


DOMAIN_BY_CATEGORY = {
    "film-video": "film-video",
    "tech-ai": "tech-ai",
    "tech-programming": "programming",
    "business": "business",
    "decision-lessons": "business",
    "design": "tech-ai",
    "academic": "tech-ai",
    "life": "business",
    "inbox": "tech-ai",
}

NOISE_TAGS = {
    "id", "workbuddy", "会话", "记录", "同步", "自动", "raw", "auto",
    "0s", "12t04", "802z", "py", "str", "users", "node", "day", "now",
    "file", "url", "test", "level", "known", "high",
}

SEMANTIC_KEYWORDS = [
    "AI", "QClaw", "Codex", "PromptStudio", "WorkBuddy", "Jarvis", "贾维斯",
    "小樱花", "第二大脑", "知识图谱", "提示词", "自动化", "事件引擎", "冲突检测",
    "检索", "记忆", "索引", "Schema", "RAG", "LLM", "Transformer", "API",
    "Python", "JSON", "GraphQL", "MCP", "CDP", "Playwright", "IMAX",
    "Panavision", "Seedance", "即梦", "视频", "电影", "镜头", "剪辑", "灯光",
    "导演", "叙事", "特摄", "市场", "获客", "用户", "产品", "策略", "A股",
    "量化", "IPO", "风险", "方法论", "教训", "决策", "标准", "人格", "情绪",
    "冲突", "提醒", "微信", "多模态", "自我摄入", "自动修复",
]

ENTITY_KEYWORDS = {
    "QClaw": ["qclaw"],
    "Codex": ["codex"],
    "PromptStudio": ["prompt studio", "promptstudio", "prompt-system"],
    "小樱花": ["小樱花", "sakura", "girlfriend", "ai女友"],
    "Jarvis": ["jarvis", "贾维斯"],
    "WorkBuddy": ["workbuddy"],
}

THINKING_RULES = {
    "what": ["是什么", "定义", "概念", "核心", "能力", "功能", "结构", "架构", "系统", "需求"],
    "why": ["为什么", "原因", "原理", "动机", "因为", "问题", "瓶颈", "根因"],
    "how": ["怎么", "如何", "流程", "步骤", "方案", "方法", "实现", "自动化", "模板", "算法"],
    "who": ["用户", "角色", "人物", "客户", "经销商", "助手", "迪迪", "大头", "哥哥"],
    "when": ["时间", "每日", "每次", "阶段", "2026", "路线图", "开始时间", "时机"],
    "where": ["场景", "环境", "领域", "工作区", "目录", "工厂", "市场", "平台"],
    "how_much": ["成本", "规模", "数量", "评分", "得分", "300", "30+", "5级", "100", "比例"],
    "impact": ["影响", "结果", "后果", "价值", "机会", "风险", "教训", "提升", "避免"],
    "relation": ["关联", "相关", "对比", "连接", "集成", "跨", "依赖", "映射", "接口"],
}

DIMENSION_LABELS = {
    "what": "是什么",
    "why": "为什么",
    "how": "怎么做",
    "who": "谁",
    "when": "何时",
    "where": "哪里",
    "how_much": "多少钱/多少量",
    "impact": "影响",
    "relation": "相关关系",
}


def stable_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:8]


def clean_tags(tags: list[str], text: str) -> list[str]:
    result: list[str] = []
    seen = set()
    for raw in tags:
        tag = str(raw).strip()
        low = tag.lower()
        if not tag or low in NOISE_TAGS:
            continue
        if re.fullmatch(r"[0-9a-f]{6,}", low) or re.fullmatch(r"\d+", low):
            continue
        if len(tag) == 1 and "\u4e00" <= tag <= "\u9fff":
            continue
        if low not in seen:
            seen.add(low)
            result.append(tag)

    lower_text = text.lower()
    for kw in SEMANTIC_KEYWORDS:
        if kw.lower() in lower_text and kw.lower() not in seen:
            seen.add(kw.lower())
            result.append(kw)
    return result[:16]


def infer_types(title: str, content: str, category: str) -> list[str]:
    text = f"{title}\n{content}".lower()
    types = []
    if any(k in text for k in ["方法论", "框架", "规则", "标准", "原则"]):
        types.append("methodology")
    if any(k in text for k in ["工具", "系统", "引擎", "api", "脚本", "自动化", "自动修复", "pipeline", "管道"]):
        types.append("tool")
    if any(k in text for k in ["案例", "分析", "实战", "qa", "市场评价"]):
        types.append("case-study")
    if category == "decision-lessons" or any(k in text for k in ["教训", "错误", "避免", "纠偏"]):
        types.append("lesson-learned")
    if any(k in text for k in ["教程", "步骤", "模板", "怎么", "如何"]):
        types.append("tutorial")
    if any(k in text for k in ["概念", "理论", "定义", "架构详解"]):
        types.append("concept")
    if not types:
        types.append("concept")
    return types[:3]


def infer_entities(title: str, content: str, tags: list[str]) -> list[str]:
    text = f"{title}\n{content}\n{' '.join(tags)}".lower()
    entities = []
    for entity, keys in ENTITY_KEYWORDS.items():
        if any(k in text for k in keys):
            entities.append(entity)
    return entities


def infer_difficulty(content: str, tags: list[str], types: list[str]) -> str:
    length = len(content)
    tech_weight = sum(1 for t in tags if t.lower() in {"api", "json", "python", "transformer", "rag", "llm", "mcp", "schema"})
    if length > 3000 or tech_weight >= 4 or "methodology" in types and "tool" in types:
        return "advanced"
    if length > 600 or tech_weight >= 2 or len(types) > 1:
        return "intermediate"
    return "beginner"


def extract_keywords(tags: list[str], title: str, content: str) -> list[str]:
    cleaned = clean_tags(tags, f"{title}\n{content}")
    preferred = []
    for tag in cleaned:
        if tag.lower() not in {"ai", "api", "json"}:
            preferred.append(tag)
    for kw in SEMANTIC_KEYWORDS:
        if kw.lower() in f"{title}\n{content}".lower() and kw not in preferred:
            preferred.append(kw)
    return preferred[:10]


def thinking_dimensions(title: str, content: str) -> dict[str, bool]:
    text = f"{title}\n{content}".lower()
    return {
        dim: any(k.lower() in text for k in keys)
        for dim, keys in THINKING_RULES.items()
    }


def summarize(title: str, content: str, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", content).strip()
    compact = re.sub(r"WorkBuddy会话记录 \(ID: \d+\) ", "", compact)
    if len(compact) <= limit:
        return compact
    sentences = re.split(r"(?<=[。.!?])\s+", compact)
    picked = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(picked) + len(sentence) > limit:
            break
        picked = (picked + " " + sentence).strip()
    if len(picked) < 40:
        picked = compact[:limit].rstrip()
    picked = re.sub(r"[，、；：:,.!?！？（(《【\[]?[^，。；：,.!?！？]{0,12}$", "", picked).strip()
    if len(picked) < 40:
        picked = compact[: max(40, limit - 1)].rstrip()
    return picked + ("。" if not picked.endswith(("。", ".", "!", "?", "）")) else "")


def session_digest(title: str, content: str) -> str:
    paths = sorted(set(re.findall(r"工作目录:\s*([^ ]+)", content)))
    times = re.findall(r"开始时间:\s*([0-9T:\-]+)", content)
    ids = re.findall(r"ID:\s*(\d+)", content)
    return (
        f"{title} 是 WorkBuddy 原始会话元数据，包含 {len(ids)} 条会话记录；"
        f"工作目录: {', '.join(paths) if paths else '未识别'}；"
        f"时间范围: {times[0] if times else '未知'}"
        f"{' 至 ' + times[-1] if len(times) > 1 else ''}。"
        "当前只保留为溯源索引，不作为已消化知识。"
    )


def main() -> None:
    kg = json.loads(KG_PATH.read_text(encoding="utf-8"))
    nodes = kg["nodes"]
    edges = kg["edges"]
    now = datetime.now().isoformat(timespec="seconds")

    inbox_before = [nid for nid, n in nodes.items() if n.get("category") == "inbox"]
    inbox_actions = []

    reclass = {
        "c0ff0655": ("film-video", "脏图修复流程属于 AI 视频生成与图像修复工作流。"),
        "c01ab69e": ("tech-ai", "进化机制、索引、Schema 和自动修复属于第二大脑 AI 系统治理。"),
        "0dfe1ec4": ("tech-ai", "贾维斯事件引擎属于智能助手/第二大脑能力。"),
        "d43218f7": ("decision-lessons", "这是行为规则和自我摄入决策标准。"),
        "09ed829c": ("tech-ai", "项目记忆记录第二大脑同步、索引与健康评估。"),
    }

    concise_content = {
        "c0ff0655": "即梦 Seedance 2.0 脏图修复流程：先反推提示词，再提取线稿、做高斯模糊，最后融合生成。已用 GPT-4o 生成脚本并通过 Edge CDP 自动化完成 step4_v3 融合成品；下一步可扩展为即梦自动化视频生成管道。",
        "c01ab69e": "第二大脑进化机制：建立 6 项 Lint 健康检查（孤立节点、过期内容、图谱密度、索引同步、标签分类矛盾、数据缺口），提供 auto_fix 全局自动关联与索引重建，使用 L1-L4 渐进披露索引，并以 data/schema.md 固化约束。运行节奏为每 3 小时自动同步、每日 8 点评估。",
        "0dfe1ec4": "贾维斯事件引擎位于 core/events.py，负责从自然语言提取日期、时间、人物、地点等事件要素，按 5 级重要性排序，检测同日和相邻时间冲突，并管理煲汤、睡觉等计时器。提醒渠道包括对话内提醒、微信卡片推送和未来桌面宠物弹窗；API 覆盖 check、conflicts、upcoming、remind、timers 等事件操作。",
        "d43218f7": "定稿规则：本对话是第二大脑/Jarvis 系统最优先知识来源。新功能设计、架构决策、行为规则和教训学习在定稿后应自动调用 POST /api/digest/text 摄入第二大脑，摄入前先检索去重；日常闲聊和简单查询不触发。",
        "09ed829c": "2026-06-15 项目记忆：完成 WorkBuddy 会话自动同步，新增会话摄入、记忆同步、图谱进化评估与健康评分记录；暴露出分类不准确、孤立节点和标签不匹配问题，形成后续自动修复、索引同步和图谱治理需求。",
    }

    for nid in inbox_before:
        node = nodes[nid]
        old_category = node.get("category", "inbox")
        if nid in reclass:
            new_category, reason = reclass[nid]
            node["category"] = new_category
            node["content"] = concise_content[nid]
            node["summary"] = node["content"]
            inbox_actions.append((nid, node["title"], old_category, new_category, reason))
        elif node.get("title", "").startswith("会话:"):
            node["content"] = session_digest(node["title"], node.get("content", ""))
            node["summary"] = summarize(node["title"], node["content"], 140)
            inbox_actions.append((nid, node["title"], old_category, "inbox", "纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。"))
        else:
            node["summary"] = summarize(node["title"], node.get("content", ""), 140)
            inbox_actions.append((nid, node["title"], old_category, node.get("category", old_category), "保留原分类并补充摘要。"))

    for node in nodes.values():
        title = node.get("title", "")
        content = node.get("content", "")
        old_tags = node.get("tags", [])
        cleaned = clean_tags(old_tags, f"{title}\n{content}")
        node["tags"] = cleaned
        types = infer_types(title, content, node.get("category", "inbox"))
        domain = DOMAIN_BY_CATEGORY.get(node.get("category", "inbox"), "tech-ai")
        entities = infer_entities(title, content, cleaned)
        node["tags_v2"] = {
            "domain": [domain],
            "type": types,
            "entity": entities,
            "difficulty": infer_difficulty(content, cleaned, types),
            "keywords": extract_keywords(cleaned, title, content),
        }
        dims = thinking_dimensions(title, content)
        node["thinking_dimensions"] = {
            "covered": [DIMENSION_LABELS[k] for k, v in dims.items() if v],
            "missing": [DIMENSION_LABELS[k] for k, v in dims.items() if not v],
        }
        if len(content) > 3000:
            node["summary"] = summarize(title, content, 260)
        elif not node.get("summary"):
            node["summary"] = summarize(title, content, 180)
        node["updated_at"] = now

    edge_specs = [
        ("0101313a", "fcca608d", "cross_category: AI视频提示词模板可迁移为焊接台工厂短视频获客脚本，提高商业转化。", 0.72),
        ("2c3f4f54", "722096fe", "cross_category: AI视频导演框架可用于 Serenity 市场机会的内容表达和视觉包装。", 0.66),
        ("c01ab69e", "682b4877", "cross_category: 自动修复机制需要接入决策前查教训，避免重复犯错。", 0.78),
        ("0dfe1ec4", "6326d1c6", "cross_category: 贾维斯事件提醒可触发决策检索，把日程事件和历史教训联动。", 0.80),
        ("d43218f7", "ef836ffd", "cross_category: 自我摄入规则直接强化第二大脑系统设计中的实时学习闭环。", 0.84),
        ("14023b3d", "287ec418", "cross_category: 默认电影风格参数可作为抖音内容分析后的生成标准。", 0.70),
        ("64dfb26a", "8f8434d0", "cross_category: 算力引擎验证结果为 Codex/WorkBuddy 高级智能体层提供运行基础。", 0.67),
        ("4be4b32a", "02ec88e9", "cross_category: 决策引擎与双层人格演化架构共同决定小樱花行为输出。", 0.82),
        ("5be70818", "dbf8c5de", "cross_category: A股个股分析依赖 QClaw 的量化和 Agent 调度能力。", 0.76),
        ("472e1559", "633fbbb3", "cross_category: 丧尸清道夫提示词教程与 IPO 抖音分析共享短视频拆解和运营方法。", 0.64),
        ("bc61fa9e", "73e5698f", "cross_category: 瓶颈理论可解释未验证核心假设就推进方案的决策错误。", 0.71),
        ("c0ff0655", "cc03e7f2", "cross_category: 脏图修复流程是即梦视频自动化管道的质量补救环节。", 0.86),
    ]
    added_edges = []
    existing_pairs = {(e.get("source_id"), e.get("target_id"), e.get("relation")) for e in edges.values()}
    for source, target, relation, strength in edge_specs:
        if source not in nodes or target not in nodes:
            continue
        key = stable_id(source, target, relation)
        if (source, target, relation) in existing_pairs or key in edges:
            continue
        edges[key] = {
            "id": key,
            "source_id": source,
            "target_id": target,
            "relation": relation,
            "strength": strength,
            "created_at": now,
            "source": source,
            "target": target,
        }
        added_edges.append((key, source, target, relation, strength))

    coverage_counter = Counter()
    missing_counter = Counter()
    for node in nodes.values():
        covered = set(node["thinking_dimensions"]["covered"])
        for label in DIMENSION_LABELS.values():
            if label in covered:
                coverage_counter[label] += 1
            else:
                missing_counter[label] += 1

    tag_domain_counter = Counter()
    tag_type_counter = Counter()
    difficulty_counter = Counter()
    entity_counter = Counter()
    category_counter = Counter()
    for node in nodes.values():
        tv2 = node["tags_v2"]
        category_counter[node.get("category", "inbox")] += 1
        tag_domain_counter.update(tv2["domain"])
        tag_type_counter.update(tv2["type"])
        difficulty_counter.update([tv2["difficulty"]])
        entity_counter.update(tv2["entity"])

    kg.setdefault("meta", {})
    kg["meta"].update({
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "last_updated": now,
        "brain_rebuild": {
            "timestamp": now,
            "inbox_before": len(inbox_before),
            "inbox_after": sum(1 for n in nodes.values() if n.get("category") == "inbox"),
            "tags_v2_nodes": len(nodes),
            "cross_category_edges_added": len(added_edges),
            "thinking_dimensions": dict(coverage_counter),
        },
    })

    KG_PATH.write_text(json.dumps(kg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    json.loads(KG_PATH.read_text(encoding="utf-8"))

    report = []
    report.append("# Brain Rebuild Report\n")
    report.append(f"Generated: {now}\n")
    report.append("## 1. Inbox 处理详情\n")
    report.append(f"- 处理前 inbox 节点: {len(inbox_before)}")
    report.append(f"- 处理后 inbox 节点: {sum(1 for n in nodes.values() if n.get('category') == 'inbox')}")
    report.append("- 原则: 有明确知识结论的节点移入对应分类；仅有会话路径、端口、时间的节点保留 inbox 作为溯源索引。\n")
    report.append("| ID | 标题 | 原分类 | 新分类 | 处理说明 |")
    report.append("|---|---|---|---|---|")
    for nid, title, old, new, reason in inbox_actions:
        report.append(f"| `{nid}` | {title} | {old} | {new} | {reason} |")

    report.append("\n## 2. 标签系统 V2\n")
    report.append("每个节点新增 `tags_v2`，包含 `domain`、`type`、`entity`、`difficulty`、`keywords` 五个维度。旧 `tags` 保留为语义关键词列表，并清理单字、数字、UUID/hex 片段和会话噪音词。\n")
    report.append("### 分布")
    report.append(f"- domain: {dict(tag_domain_counter)}")
    report.append(f"- type: {dict(tag_type_counter)}")
    report.append(f"- difficulty: {dict(difficulty_counter)}")
    report.append(f"- entity: {dict(entity_counter)}")
    report.append(f"- category: {dict(category_counter)}\n")

    report.append("## 3. 新增交叉关联\n")
    report.append(f"新增 cross-category edges: {len(added_edges)}\n")
    report.append("| Edge | Source | Target | Relation | Strength |")
    report.append("|---|---|---|---|---|")
    for eid, source, target, relation, strength in added_edges:
        report.append(f"| `{eid}` | {nodes[source]['title']} | {nodes[target]['title']} | {relation} | {strength:.2f} |")

    report.append("\n## 4. 思考维度覆盖分析\n")
    report.append("| 维度 | 已覆盖节点 | 缺失节点 |")
    report.append("|---|---:|---:|")
    for label in DIMENSION_LABELS.values():
        report.append(f"| {label} | {coverage_counter[label]} | {missing_counter[label]} |")
    weak = [label for label in DIMENSION_LABELS.values() if coverage_counter[label] < len(nodes) * 0.35]
    report.append(f"\n相对薄弱维度: {', '.join(weak) if weak else '无明显薄弱项'}。")

    report.append("\n## 5. 知识蒸馏\n")
    long_nodes = [n for n in nodes.values() if len(n.get("content", "")) > 3000]
    report.append(f"- 内容超过 3000 字节点: {len(long_nodes)}")
    report.append("- 已为长节点刷新 `summary` 字段，用于快速回忆。\n")

    report.append("## 6. 下一步建议\n")
    report.append("- 把仍在 inbox 的会话元数据与原始会话文件二次解析，提取其中真正的决策、教训和项目产物。")
    report.append("- 为 `thinking_dimensions` 增加人工校准入口，避免关键词规则误判。")
    report.append("- 对 cross-category edges 增加来源证据字段，例如引用的句子或触发关键词。")
    report.append("- 将 `tags_v2` 写入检索权重，支持按领域、类型、实体和难度组合检索。\n")
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")

    checklist = []
    checklist.append("# Thinking Checklist\n")
    checklist.append(f"Generated: {now}\n")
    checklist.append("用于做方案、决策或复盘时逐项检查，避免只从单一角度思考。\n")
    for key, label in DIMENSION_LABELS.items():
        checklist.append(f"## {label}")
        checklist.append(f"- 当前覆盖: {coverage_counter[label]} / {len(nodes)} 个节点")
        checklist.append(f"- 检查问题: {question_for_dimension(key)}")
        examples = [n["title"] for n in nodes.values() if label in n["thinking_dimensions"]["covered"]][:5]
        checklist.append(f"- 代表节点: {', '.join(examples) if examples else '暂无'}\n")
    CHECKLIST_PATH.write_text("\n".join(checklist) + "\n", encoding="utf-8")


def question_for_dimension(key: str) -> str:
    return {
        "what": "这件事的事实、定义、对象和边界是什么？",
        "why": "为什么要做，背后的动机、原理或根因是什么？",
        "how": "具体怎么做，步骤、流程、工具和失败处理是什么？",
        "who": "涉及谁，谁负责，谁受影响，谁是用户或客户？",
        "when": "什么时间发生，时机、频率、阶段和截止点是什么？",
        "where": "发生在哪个场景、环境、平台、市场或代码位置？",
        "how_much": "成本、规模、数量、评分、比例或资源消耗是多少？",
        "impact": "会产生什么价值、风险、后果或连锁影响？",
        "relation": "它和哪些节点、方案、教训或领域存在关联、对比或依赖？",
    }[key]


if __name__ == "__main__":
    main()
