"""Knowledge atomization helpers."""

from __future__ import annotations

import re
from typing import Iterable

from .contracts import EvidenceItem, KnowledgeAtom, RelationEdge, SourceRecord, new_id, now_iso, stable_hash


STOP_WORDS = {
    "的", "了", "和", "是", "在", "我", "你", "他", "她", "它", "我们", "他们",
    "this", "that", "with", "from", "into", "have", "will", "would", "should",
}

TYPE_RULES = {
    "rule": ["必须", "禁止", "不得", "红线", "原则", "规则", "should", "must"],
    "hypothesis": ["可能", "假设", "如果", "预计", "概率", "或许", "might", "may"],
    "strategy": ["策略", "方案", "执行", "仓位", "止损", "复盘"],
    "preference": ["喜欢", "偏好", "审美", "风格", "讨厌"],
    "emotion": ["焦虑", "恐惧", "贪婪", "兴奋", "疲劳", "情绪"],
    "decision": ["决定", "选择", "买入", "卖出", "持仓", "放弃"],
    "image_feature": ["图片", "构图", "镜头", "光影", "材质", "色彩"],
}

CATEGORY_RULES = {
    "交易": ["交易", "股票", "买入", "卖出", "仓位", "止损", "回撤", "A股", "昆仑", "蓝标"],
    "地缘": ["战争", "制裁", "国家", "能源", "美元", "外交", "供应链"],
    "图像": ["图像", "图片", "电影", "镜头", "构图", "材质", "写实", "风格"],
    "情绪": ["情绪", "焦虑", "恐惧", "贪婪", "疲劳", "冲动"],
    "技术": ["代码", "系统", "模块", "API", "算法", "数据库", "架构"],
    "经验": ["教训", "复盘", "错误", "经验", "改进"],
}


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = [s.strip() for s in re.split(r"[。！？!?；;\n]+", text) if s.strip()]
    if not chunks:
        chunks = [text]
    out: list[str] = []
    for chunk in chunks:
        if len(chunk) <= 280:
            out.append(chunk)
            continue
        for i in range(0, len(chunk), 260):
            piece = chunk[i:i + 260].strip()
            if piece:
                out.append(piece)
    return out


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    tokens.extend(m.group(0).lower() for m in re.finditer(r"[a-zA-Z0-9_]+", text))
    chinese = "".join(c for c in text if "\u4e00" <= c <= "\u9fff")
    tokens.extend(chinese[i:i + 2] for i in range(max(0, len(chinese) - 1)))
    tokens.extend(c for c in chinese)
    return [t for t in tokens if t and t not in STOP_WORDS]


def classify_atom(text: str) -> str:
    for atom_type, words in TYPE_RULES.items():
        if any(w.lower() in text.lower() for w in words):
            return atom_type
    return "fact"


def classify_categories(text: str) -> list[str]:
    categories = [
        name for name, words in CATEGORY_RULES.items()
        if any(w.lower() in text.lower() for w in words)
    ]
    return categories or ["通用"]


def classify_para(atom_type: str, categories: Iterable[str]) -> str:
    cats = set(categories)
    if atom_type in {"decision", "strategy"} or "交易" in cats:
        return "Projects"
    if atom_type in {"rule", "preference", "emotion"}:
        return "Areas"
    if atom_type == "source_note":
        return "Archives"
    return "Resources"


def extract_tags(text: str, limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for t in tokenize(text):
        if len(t) == 1 and not ("\u4e00" <= t <= "\u9fff"):
            continue
        counts[t] = counts.get(t, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    return [k for k, _ in ranked[:limit]]


def summarize(text: str, limit: int = 96) -> str:
    return text if len(text) <= limit else text[:limit - 3] + "..."


def atomize_text(source: SourceRecord, text: str) -> tuple[list[EvidenceItem], list[KnowledgeAtom], list[RelationEdge]]:
    evidence: list[EvidenceItem] = []
    atoms: list[KnowledgeAtom] = []
    for index, sentence in enumerate(split_sentences(text)):
        seed = f"{source.id}:{index}:{sentence}"
        ev = EvidenceItem(
            id=new_id("ev", seed),
            source_id=source.id,
            quote=sentence,
            evidence_type=classify_atom(sentence),
            confidence=source.reliability,
            metadata={"sentence_index": index},
        )
        categories = classify_categories(sentence)
        atom_type = classify_atom(sentence)
        atom = KnowledgeAtom(
            id=new_id("atom", seed),
            title=summarize(sentence, 48),
            content=sentence,
            summary=summarize(sentence),
            atom_type=atom_type,
            para=classify_para(atom_type, categories),
            categories=categories,
            tags=extract_tags(sentence),
            source_ids=[source.id],
            evidence_ids=[ev.id],
            support_evidence_ids=[ev.id],
            confidence=ev.confidence,
            importance=min(1.0, 0.35 + len(sentence) / 500.0),
            activation=0.55,
            next_review_at=now_iso(),
            metadata={"source_hash": stable_hash(sentence), "sentence_index": index},
        )
        evidence.append(ev)
        atoms.append(atom)

    edges: list[RelationEdge] = []
    for prev, cur in zip(atoms, atoms[1:]):
        overlap = set(prev.tags) & set(cur.tags)
        if overlap:
            edges.append(
                RelationEdge(
                    id=new_id("rel", f"{prev.id}:{cur.id}"),
                    source_atom_id=prev.id,
                    target_atom_id=cur.id,
                    relation_type="same_source_related",
                    confidence=min(0.8, 0.3 + len(overlap) * 0.1),
                    evidence_ids=list(set(prev.evidence_ids + cur.evidence_ids)),
                    metadata={"matched_tags": sorted(overlap)},
                )
            )
    return evidence, atoms, edges
